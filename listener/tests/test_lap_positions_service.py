import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from packets.constants import MAX_CARS
from services.lap_positions import LapPositionsService

from .mock_repo import MockRepo


def _make_lap_positions_packet(session_uid=123, num_laps=1, lap_start=0, positions=None):
    if positions is None:
        # Default: 1 lap, 22 positions all zero
        positions = [[0] * MAX_CARS]
    header = SimpleNamespace(session_uid=session_uid)
    return SimpleNamespace(
        header=header,
        num_laps=num_laps,
        lap_start=lap_start,
        positions=positions,
    )


def _make_service():
    repo = MockRepo()
    svc = LapPositionsService(repo)
    return svc, repo


def test_position_inversion():
    svc, repo = _make_service()
    # car 0 is in position 2, car 1 is in position 1
    lap_positions = [0] * MAX_CARS
    lap_positions[0] = 2  # car_index 0 -> position 2
    lap_positions[1] = 1  # car_index 1 -> position 1
    packet = _make_lap_positions_packet(
        num_laps=1, positions=[lap_positions],
    )
    svc.handle_lap_positions_packet(packet, user_map={0: 100, 1: 101})
    _, kwargs = repo.last_call("upsert_lap_positions")
    positions = kwargs["positions"]
    # Position 1 should be driver 101, position 2 should be driver 100
    assert positions[0] == 101
    assert positions[1] == 100


def test_trailing_zeros_trimmed():
    svc, repo = _make_service()
    lap_positions = [0] * MAX_CARS
    lap_positions[0] = 1  # car 0 at position 1
    packet = _make_lap_positions_packet(
        num_laps=1, positions=[lap_positions],
    )
    svc.handle_lap_positions_packet(packet, user_map={0: 100})
    _, kwargs = repo.last_call("upsert_lap_positions")
    positions = kwargs["positions"]
    assert positions[-1] != 0


def test_ai_drivers_skipped():
    svc, repo = _make_service()
    lap_positions = [0] * MAX_CARS
    lap_positions[0] = 1  # car 0 at position 1 (in user_map)
    lap_positions[1] = 2  # car 1 at position 2 (NOT in user_map — AI)
    packet = _make_lap_positions_packet(
        num_laps=1, positions=[lap_positions],
    )
    svc.handle_lap_positions_packet(packet, user_map={0: 100})
    _, kwargs = repo.last_call("upsert_lap_positions")
    positions = kwargs["positions"]
    # Only position 1 should have a driver
    assert positions[0] == 100
    assert len(positions) == 1


def test_lap_start_offset():
    svc, repo = _make_service()
    lap_positions = [0] * MAX_CARS
    lap_positions[0] = 1
    packet = _make_lap_positions_packet(
        num_laps=1, lap_start=5, positions=[lap_positions],
    )
    svc.handle_lap_positions_packet(packet, user_map={0: 100})
    _, kwargs = repo.last_call("upsert_lap_positions")
    # actual_lap_number = lap_start + lap_index + 1 = 5 + 0 + 1 = 6
    assert kwargs["lap_number"] == 6
