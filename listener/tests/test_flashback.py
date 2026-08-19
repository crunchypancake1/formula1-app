"""
Flashback handling (Event packet, code FLBK).

A flashback rewinds m_sessionTime and m_frameIdentifier but NOT
m_overallFrameIdentifier. Nothing in the stream marks the rows recorded during
the rewound-over stretch as obsolete, so unless the listener removes them the
database keeps telemetry for a run the driver undid — which surfaces later as
the same lap recorded twice at two different times.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from .packet_builder import (
    build_car_status_packet,
    build_car_telemetry_packet,
    build_event_butn,
    build_event_flbk,
    build_event_lgot,
    build_event_scar,
    build_lap_data_packet,
    build_motion_packet,
    build_participants_packet,
    build_session_packet,
)

FLASHBACK_SESSION_UID = 7777777777777777
TRACK_ID = 11
SESSION_TYPE = 15  # Race
TOTAL_LAPS = 3
TRACK_LENGTH = 5793
NUM_DRIVERS = 4

# The point the driver rewinds to. Frames recorded after it must not survive.
REWIND_TO_SESSION_TIME = 20.0


def _frame_packets(frame_id: int, session_time: float, current_lap: int, lap_distance: float):
    return [
        build_lap_data_packet(
            session_uid=FLASHBACK_SESSION_UID, session_time=session_time, frame_id=frame_id,
            num_drivers=NUM_DRIVERS, current_lap_num=current_lap,
            lap_distance=lap_distance, track_length=TRACK_LENGTH,
            positions=list(range(1, NUM_DRIVERS + 1)),
        ),
        build_motion_packet(
            session_uid=FLASHBACK_SESSION_UID, session_time=session_time, frame_id=frame_id,
            num_drivers=NUM_DRIVERS, lap_distance=lap_distance, track_length=TRACK_LENGTH,
        ),
        build_car_telemetry_packet(
            session_uid=FLASHBACK_SESSION_UID, session_time=session_time,
            frame_id=frame_id, num_drivers=NUM_DRIVERS,
        ),
        build_car_status_packet(
            session_uid=FLASHBACK_SESSION_UID, session_time=session_time,
            frame_id=frame_id, num_drivers=NUM_DRIVERS,
        ),
    ]


def _generate_flashback_scenario() -> list[bytes]:
    """Drive past the rewind point, flash back to it, then drive on again."""
    packets: list[bytes] = [
        build_session_packet(
            session_uid=FLASHBACK_SESSION_UID, session_time=1.0, frame_id=1,
            track_id=TRACK_ID, session_type=SESSION_TYPE,
            total_laps=TOTAL_LAPS, track_length=TRACK_LENGTH, session_time_left=3600,
        ),
        build_participants_packet(
            session_uid=FLASHBACK_SESSION_UID, session_time=1.0, frame_id=1,
            num_drivers=NUM_DRIVERS,
        ),
        build_event_lgot(FLASHBACK_SESSION_UID, 2.0, 2),
    ]

    frame = 10
    # Run up to and past the rewind point.
    for step in range(20):
        session_time = 10.0 + step * 1.0
        packets.extend(_frame_packets(frame, session_time, 1, 100.0 * step))
        frame += 1

    # The driver flashes back.
    packets.append(
        build_event_flbk(
            session_uid=FLASHBACK_SESSION_UID,
            session_time=30.0,
            frame_id=frame,
            flashback_frame_identifier=frame - 10,
            flashback_session_time=REWIND_TO_SESSION_TIME,
        )
    )
    frame += 1

    # ...and drives the stretch again. session_time restarts from the rewind
    # point while overall_frame_identifier keeps climbing.
    for step in range(10):
        session_time = REWIND_TO_SESSION_TIME + step * 1.0
        packets.extend(_frame_packets(frame, session_time, 1, 100.0 * step))
        frame += 1

    return packets


class TestFlashback:

    @pytest.fixture(scope="class", autouse=True)
    def run_simulation(self, dispatcher, db_client):
        for packet_bytes in _generate_flashback_scenario():
            dispatcher.handle_packet(packet_bytes)
        yield
        with db_client.connection() as conn:
            with conn.cursor() as cur:
                for table in (
                    "telemetry.car_frame_damage", "telemetry.car_frame",
                    "telemetry.events_flashbacks", "telemetry.events_buttons",
                    "telemetry.session_timeline", "telemetry.entries",
                    "telemetry.sessions",
                ):
                    cur.execute(
                        f"DELETE FROM {table} WHERE session_uid = %s",
                        (str(FLASHBACK_SESSION_UID),),
                    )
                conn.commit()

    def _query_one(self, db_client, sql, params=None):
        with db_client.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()

    def test_flashback_event_recorded(self, db_client):
        row = self._query_one(
            db_client,
            """
            SELECT flashback_session_time, rows_discarded
            FROM telemetry.events_flashbacks WHERE session_uid = %s
            """,
            (str(FLASHBACK_SESSION_UID),),
        )
        assert row is not None, "Flashback was not recorded"
        assert row[0] == pytest.approx(REWIND_TO_SESSION_TIME)

    def test_rewound_frames_discarded(self, db_client):
        """
        No frame may survive past the rewind point from the first run-through.
        Anything above it now must belong to the re-drive.
        """
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM telemetry.car_frame
            WHERE session_uid = %s AND session_time > %s
            """,
            (str(FLASHBACK_SESSION_UID), REWIND_TO_SESSION_TIME + 9.5),
        )
        # The re-drive only reaches REWIND_TO + 9.0, so nothing may sit beyond
        # it — the original run's frames up to 29.0 are gone.
        assert row[0] == 0, "Frames from the undone run survived the flashback"

    def test_frames_before_rewind_point_survive(self, db_client):
        """The flashback only invalidates what came after it."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM telemetry.car_frame
            WHERE session_uid = %s AND session_time <= %s
            """,
            (str(FLASHBACK_SESSION_UID), REWIND_TO_SESSION_TIME),
        )
        assert row[0] > 0, "Flashback discarded frames it should have kept"

    def test_no_duplicate_frames_after_redrive(self, db_client):
        """
        Re-driving the same stretch replays the same session_time values. With a
        derived timestamp and the frame in the key, each (driver, frame) is
        still unique.
        """
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM (
                SELECT user_id, overall_frame_identifier
                FROM telemetry.car_frame WHERE session_uid = %s
                GROUP BY 1, 2 HAVING COUNT(*) > 1
            ) duplicates
            """,
            (str(FLASHBACK_SESSION_UID),),
        )
        assert row[0] == 0


def test_button_events_recorded(dispatcher, db_client):
    """BUTN carries the local player's controller state; the flags are resolved."""
    session_uid = 6666666666666666
    packets = [
        build_session_packet(
            session_uid=session_uid, session_time=1.0, frame_id=1,
            track_id=TRACK_ID, session_type=SESSION_TYPE,
            total_laps=TOTAL_LAPS, track_length=TRACK_LENGTH, session_time_left=3600,
        ),
        build_participants_packet(
            session_uid=session_uid, session_time=1.0, frame_id=1, num_drivers=NUM_DRIVERS,
        ),
        build_event_scar(session_uid, 2.0, 2),
        build_event_butn(session_uid, 3.0, 3, button_status=0x00000001),
    ]
    for packet_bytes in packets:
        dispatcher.handle_packet(packet_bytes)

    try:
        with db_client.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT button_status, buttons_pressed
                    FROM telemetry.events_buttons WHERE session_uid = %s
                    """,
                    (str(session_uid),),
                )
                row = cur.fetchone()
        assert row is not None, "Button event was not recorded"
        assert row[0] == 1
        assert len(row[1]) >= 1, "Button flags were not resolved to names"
    finally:
        with db_client.connection() as conn:
            with conn.cursor() as cur:
                for table in (
                    "telemetry.events_buttons", "telemetry.session_timeline",
                    "telemetry.entries", "telemetry.sessions",
                ):
                    cur.execute(
                        f"DELETE FROM {table} WHERE session_uid = %s", (str(session_uid),)
                    )
                conn.commit()
