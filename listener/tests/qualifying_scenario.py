"""Qualifying scenario generator — produces a packet sequence for a simulated Q1 session."""

from .packet_builder import (
    build_car_status_packet,
    build_car_telemetry_packet,
    build_event_chqf,
    build_event_send,
    build_event_ssta,
    build_final_classification_packet,
    build_lap_data_packet,
    build_motion_packet,
    build_participants_packet,
    build_session_history_packet,
    build_session_packet,
)

QUALIFYING_SESSION_UID = 8888888888888888
TRACK_ID = 11          # Monza
SESSION_TYPE = 10      # Q1
TOTAL_LAPS = 0         # Not lap-limited in qualifying
TRACK_LENGTH = 5793
NUM_DRIVERS = 20
FRAME_INTERVAL = 0.016


class _FrameCounter:
    def __init__(self):
        self._frame = 0

    def next(self) -> tuple[int, float]:
        self._frame += 1
        return self._frame, (self._frame - 1) * FRAME_INTERVAL

    @property
    def current(self) -> int:
        return self._frame


def generate_qualifying_scenario() -> list[bytes]:
    """Generate a Q1 qualifying session packet sequence."""
    packets: list[bytes] = []
    fc = _FrameCounter()

    # === Frame 1: Session + Participants ===
    frame_id, session_time = fc.next()

    packets.append(build_session_packet(
        session_uid=QUALIFYING_SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        track_id=TRACK_ID,
        session_type=SESSION_TYPE,
        total_laps=TOTAL_LAPS,
        track_length=TRACK_LENGTH,
        session_time_left=1080,
        session_duration=1080,
        weekend_link=2000,
        session_link=3000,
    ))

    packets.append(build_participants_packet(
        session_uid=QUALIFYING_SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
    ))

    # === Session Start event ===
    packets.append(build_event_ssta(QUALIFYING_SESSION_UID, session_time, frame_id))

    # === Out lap frames (lap 1, no timed lap yet) ===
    for i in range(10):
        frame_id, session_time = fc.next()
        progress = (i + 1) / 10
        lap_distance = progress * (TRACK_LENGTH - 1)

        packets.append(build_lap_data_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
            current_lap_num=1,
            lap_distance=lap_distance,
            track_length=TRACK_LENGTH,
        ))
        packets.append(build_motion_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
            lap_distance=lap_distance,
        ))
        packets.append(build_car_telemetry_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
        ))
        packets.append(build_car_status_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
        ))

    # === Timed lap (lap 2) frames ===
    for i in range(15):
        frame_id, session_time = fc.next()
        progress = (i + 1) / 15
        lap_distance = progress * (TRACK_LENGTH - 1)

        include_session = (i == 7)
        if include_session:
            packets.append(build_session_packet(
                session_uid=QUALIFYING_SESSION_UID,
                session_time=session_time,
                frame_id=frame_id,
                track_id=TRACK_ID,
                session_type=SESSION_TYPE,
                total_laps=TOTAL_LAPS,
                track_length=TRACK_LENGTH,
                session_time_left=900,
                weekend_link=2000,
                session_link=3000,
            ))

        packets.append(build_lap_data_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
            current_lap_num=2,
            lap_distance=lap_distance,
            track_length=TRACK_LENGTH,
        ))
        packets.append(build_motion_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
            lap_distance=lap_distance,
        ))
        packets.append(build_car_telemetry_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
        ))
        packets.append(build_car_status_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
        ))

    # === Session history for all cars (1 timed lap) ===
    for car_idx in range(NUM_DRIVERS):
        frame_id, session_time = fc.next()
        packets.append(build_session_history_packet(
            session_uid=QUALIFYING_SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            car_index=car_idx,
            num_laps=1,
            lap_times_ms=[78000 + car_idx * 200],
        ))

    # === Chequered flag ===
    frame_id, session_time = fc.next()
    packets.append(build_event_chqf(QUALIFYING_SESSION_UID, session_time, frame_id))

    # === Final Classification ===
    frame_id, session_time = fc.next()
    packets.append(build_final_classification_packet(
        session_uid=QUALIFYING_SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        total_laps=1,
    ))

    # === Session end ===
    frame_id, session_time = fc.next()
    packets.append(build_event_send(QUALIFYING_SESSION_UID, session_time, frame_id))

    # === Dummy flush trigger ===
    frame_id, session_time = fc.next()
    packets.append(build_lap_data_packet(
        session_uid=QUALIFYING_SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        current_lap_num=2,
        lap_distance=0.0,
    ))

    return packets
