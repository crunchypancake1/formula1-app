"""Phase 0 — byte-count assertions for every F1 26 (2026 Season Pack) packet builder.

Builds each packet at 2026 sizes (MAX_CARS = 24) via tests/packet_builder/
and asserts the output is exactly the documented byte count. This test does
not touch the database, so it should always run (not skip) under pytest.
"""

import struct

import pytest

from .packet_builder import (
    build_car_damage_packet,
    build_car_setup_packet,
    build_car_status_packet,
    build_car_telemetry2_packet,
    build_car_telemetry_packet,
    build_final_classification_packet,
    build_header,
    build_lap_data_packet,
    build_lap_positions_packet,
    build_lobby_info_packet,
    build_motion_packet,
    build_participants_packet,
    build_session_packet,
)

@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Shadow conftest's session-scoped, DB-dependent autouse fixture.

    This suite builds packets in memory only and needs no database — the
    conftest fixture of the same name pulls in `db_client`, which calls
    `pytest.skip` when Postgres isn't running, which would otherwise skip
    every test in this file too. Overriding it locally with a no-op keeps
    these byte-count assertions running unconditionally.
    """
    yield


_MOTION_EX_FORMAT = "<61f"


def _build_motion_ex_packet(session_uid: int, session_time: float, frame_id: int) -> bytes:
    header = build_header(
        packet_id=13,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )
    body = struct.pack(_MOTION_EX_FORMAT, *([0.0] * 61))
    return header + body


class TestPacketBuilderByteSizes:
    """Every packet builder must emit the documented 2026 (24-car) byte size."""

    def test_motion_packet_size(self):
        packet = build_motion_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1325

    def test_session_packet_size(self):
        packet = build_session_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 926

    def test_lap_data_packet_size(self):
        packet = build_lap_data_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1399

    def test_participants_packet_size(self):
        packet = build_participants_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1470

    def test_car_setups_packet_size(self):
        packet = build_car_setup_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1233

    def test_car_telemetry_packet_size(self):
        packet = build_car_telemetry_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1448

    def test_car_status_packet_size(self):
        packet = build_car_status_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1445

    def test_final_classification_packet_size(self):
        packet = build_final_classification_packet(
            session_uid=1, session_time=0.0, frame_id=0, num_drivers=24
        )
        assert len(packet) == 1134

    def test_lobby_info_packet_size(self):
        packet = build_lobby_info_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1062

    def test_car_damage_packet_size(self):
        packet = build_car_damage_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 1133

    def test_lap_positions_packet_size(self):
        packet = build_lap_positions_packet(
            session_uid=1,
            session_time=0.0,
            frame_id=0,
            lap_positions={0: list(range(1, 21))},
        )
        assert len(packet) == 1231

    def test_motion_ex_packet_size(self):
        packet = _build_motion_ex_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 273

    def test_car_telemetry2_packet_size(self):
        packet = build_car_telemetry2_packet(session_uid=1, session_time=0.0, frame_id=0)
        assert len(packet) == 269
