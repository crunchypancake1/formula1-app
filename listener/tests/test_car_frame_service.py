import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.repositories.car_frame import COLUMN_INDEX
from packets.constants import MAX_CARS
from services.car_frame import CarFrameService

from . import factories
from .mock_repo import MockRepo

# Row tuples are addressed by column name so these tests cannot drift when a
# column is added — the same lookup the service itself uses.
IDX = COLUMN_INDEX


def _make_motion(car_index):
    return factories.make_motion(car_index)


def _make_telemetry(car_index):
    return factories.make_telemetry(car_index)


def _make_lap(car_index, car_position=1, driver_status=1, gap_to_car_ahead=0):
    return factories.make_lap(
        car_position=car_position,
        driver_status=driver_status,
        gap_to_car_ahead=gap_to_car_ahead,
    )


def _make_status(**overrides):
    return factories.make_status(**overrides)


def _make_damage(**overrides):
    return factories.make_damage(**overrides)


def _make_telemetry2(regs_2026=1, driving_wrong_way=0):
    return factories.make_telemetry2(
        regulations_2026=regs_2026, driving_wrong_way=driving_wrong_way
    )


def _pad_list(items, count=MAX_CARS, default=None):
    """Pad a per-car list out to the full car array the game always sends."""
    return items + [default] * (count - len(items))


def _make_service():
    car_frame_repo = MockRepo()
    svc = CarFrameService(car_frame_repo)
    return svc, car_frame_repo


def test_formation_lap_dropped():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100}, motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        race_started=False,
    )
    assert car_frame_repo.call_count("insert_batch") == 0


def test_race_started_writes_frames():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100}, motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        race_started=True,
    )
    assert car_frame_repo.call_count("insert_batch") == 1


def test_skips_ai_drivers():
    svc, car_frame_repo = _make_service()
    # user_map only has car 0, car 1 is AI (not in map)
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0), _make_motion(1)]),
        telemetry_data=_pad_list([_make_telemetry(0), _make_telemetry(1)]),
        lap_data_list=_pad_list([_make_lap(0), _make_lap(1)]),
        car_status_data=_pad_list([_make_status(), _make_status()]),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    rows = args[0]
    assert len(rows) == 1


def test_skips_garage_drivers():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0, driver_status=0)]),
        car_status_data=_pad_list([_make_status()]),
        race_started=True,
    )
    assert car_frame_repo.call_count("insert_batch") == 0


def test_gap_behind_computation():
    svc, car_frame_repo = _make_service()
    # P1 driver and P2 driver, P2 has gap_to_car_ahead=1500
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100, 1: 101},
        motion_data=_pad_list([_make_motion(0), _make_motion(1)]),
        telemetry_data=_pad_list([_make_telemetry(0), _make_telemetry(1)]),
        lap_data_list=_pad_list([
            _make_lap(0, car_position=1, gap_to_car_ahead=0),
            _make_lap(1, car_position=2, gap_to_car_ahead=1500),
        ]),
        car_status_data=_pad_list([_make_status(), _make_status()]),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    rows = args[0]
    # Find the P1 row (user_id=100)
    p1_row = [r for r in rows if r[IDX["user_id"]] == 100][0]
    assert p1_row[IDX["gap_to_car_behind_ms"]] == 1500


def test_missing_data_uses_none_tuples():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=None,
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    motion_fields = row[IDX["world_pos_x"]:IDX["roll"] + 1]
    assert all(v is None for v in motion_fields)


def test_position_255_becomes_none():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0, car_position=255)]),
        car_status_data=_pad_list([_make_status()]),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert row[IDX["position"]] is None


def test_tyre_age_255_becomes_none():
    svc, car_frame_repo = _make_service()
    status = _make_status()
    status.tyres_age_laps = 255
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([status]),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert row[IDX["tyres_age_laps"]] is None


# --- Restricted-telemetry and packet-16 coverage ---

# The Car Status fields the game zeroes for a Restricted driver.
RESTRICTED_STATUS_COLUMNS = (
    "front_brake_bias", "fuel_mix", "fuel_in_tank", "fuel_capacity",
    "fuel_remaining_laps", "ers_store_energy", "ers_deploy_mode",
    "ers_deployed_this_lap", "ers_harvest_limit_per_lap",
    "ers_harvested_this_lap_mguk", "ers_harvested_this_lap_mguh",
    "engine_power_ice", "engine_power_mguk",
)

# The packet-16 fields that only mean anything under 2026 regulations.
REGS_GATED_COLUMNS = (
    "active_aero_mode", "active_aero_available", "active_aero_activation_distance",
    "overtake_available", "overtake_active", "overtake_activation_distance",
)


def test_restricted_car_status_extended_fields_are_null():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        restricted_indices={0},
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert all(row[IDX[c]] is None for c in RESTRICTED_STATUS_COLUMNS)


def test_unrestricted_car_status_extended_fields_are_populated():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        restricted_indices=set(),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert row[IDX["front_brake_bias"]] == 58
    assert row[IDX["ers_harvest_limit_per_lap"]] == 200000.0
    assert row[IDX["fuel_capacity"]] == 110.0
    assert row[IDX["ers_harvested_this_lap_mguk"]] == 50000.0
    assert row[IDX["engine_power_ice"]] == 560000.0


def test_restricted_car_damage_row_is_skipped():
    car_frame_repo = MockRepo()
    car_frame_damage_repo = MockRepo()
    svc = CarFrameService(car_frame_repo, car_frame_damage_repo)
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100, 1: 101},
        motion_data=_pad_list([_make_motion(0), _make_motion(1)]),
        telemetry_data=_pad_list([_make_telemetry(0), _make_telemetry(1)]),
        lap_data_list=_pad_list([_make_lap(0), _make_lap(1)]),
        car_status_data=_pad_list([_make_status(), _make_status()]),
        car_damage_data=_pad_list([_make_damage(), _make_damage()]),
        restricted_indices={0},
        race_started=True,
    )
    args, _ = car_frame_damage_repo.last_call("insert_batch")
    rows = args[0]
    # Only car 1 (unrestricted) gets a damage row; car 0 is skipped entirely.
    assert len(rows) == 1
    assert rows[0][2] == 101  # (timestamp, session_uid, user_id, ...)


def test_local_player_never_restricted_even_if_own_telemetry_restricted():
    """
    The local player's car is always fully visible regardless of their own
    your_telemetry setting (Part 2.2). Upstream (ParticipantsService) already
    excludes the player's own car_index from restricted_indices — this test
    pins that at the CarFrameService boundary: even though the player's own
    `your_telemetry` may be Restricted, as long as their car_index is absent
    from restricted_indices they get both a fully-populated car_frame row
    AND a fully-populated car_frame_damage row.
    """
    car_frame_repo = MockRepo()
    car_frame_damage_repo = MockRepo()
    svc = CarFrameService(car_frame_repo, car_frame_damage_repo)
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        car_damage_data=_pad_list([_make_damage()]),
        # restricted_indices does NOT include car 0 (the local player) —
        # mirrors ParticipantsService always excluding player_car_index,
        # even if that driver's own your_telemetry == 0 (Restricted).
        restricted_indices=set(),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert all(row[IDX[c]] is not None for c in RESTRICTED_STATUS_COLUMNS)
    assert row[IDX["front_brake_bias"]] == 58

    damage_args, _ = car_frame_damage_repo.last_call("insert_batch")
    damage_rows = damage_args[0]
    assert len(damage_rows) == 1
    assert all(v is not None for v in damage_rows[0][4:])


def test_telemetry2_gated_fields_null_when_not_2026_regs():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        car_telemetry2_data=_pad_list([_make_telemetry2(regs_2026=0, driving_wrong_way=1)]),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert all(row[IDX[c]] is None for c in REGS_GATED_COLUMNS)
    # A classic car is positively known not to be on 2026 regs — that is a
    # fact, so it is stored as False. NULL here would mean "no packet 16".
    assert row[IDX["is_2026_regulations"]] is False
    # driving_wrong_way is meaningful on any car, regs or not.
    assert row[IDX["driving_wrong_way"]] is True


def test_telemetry2_absent_leaves_regs_flag_unknown():
    """No packet 16 at all is different from a car that is not on 2026 regs."""
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        car_telemetry2_data=None,
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert row[IDX["is_2026_regulations"]] is None
    assert row[IDX["driving_wrong_way"]] is None


def test_telemetry2_fields_populated_when_2026_regs():
    svc, car_frame_repo = _make_service()
    svc.write_frame(
        session_uid="123", session_time=10.0, overall_frame_identifier=1,
        user_map={0: 100},
        motion_data=_pad_list([_make_motion(0)]),
        telemetry_data=_pad_list([_make_telemetry(0)]),
        lap_data_list=_pad_list([_make_lap(0)]),
        car_status_data=_pad_list([_make_status()]),
        car_telemetry2_data=_pad_list([_make_telemetry2(regs_2026=1)]),
        race_started=True,
    )
    args, _ = car_frame_repo.last_call("insert_batch")
    row = args[0][0]
    assert row[IDX["active_aero_mode"]] == 1
    assert row[IDX["is_2026_regulations"]] is True
    assert all(row[IDX[c]] is not None for c in REGS_GATED_COLUMNS)
