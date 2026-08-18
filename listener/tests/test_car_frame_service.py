import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.car_frame import CarFrameService

from .mock_repo import MockRepo


def _make_motion(car_index):
    return SimpleNamespace(
        world_position_x=float(car_index), world_position_y=0.0, world_position_z=0.0,
        world_velocity_x=0.0, world_velocity_y=0.0, world_velocity_z=0.0,
        g_force_lateral=0.0, g_force_longitudinal=0.0, g_force_vertical=0.0,
        yaw=0.0, pitch=0.0, roll=0.0,
    )


def _make_telemetry(car_index):
    return SimpleNamespace(
        speed=200 + car_index, throttle=1.0, steer=0.0, brake=0.0, clutch=0, gear=7,
        engine_rpm=11000, drs=0, engine_temperature=100,
        brakes_temperature=(400, 400, 400, 400),
        tyres_surface_temp=(100, 100, 100, 100),
        tyres_inner_temp=(95, 95, 95, 95),
        tyres_pressure=(23.5, 23.5, 22.0, 22.0),
        surface_type=(0, 0, 0, 0),
    )


def _make_lap(car_index, car_position=1, driver_status=1, gap_to_car_ahead=0):
    return SimpleNamespace(
        current_lap_num=1, lap_distance=1000.0, current_lap_time_in_ms=30000,
        car_position=car_position, sector=0, pit_status=0, driver_status=driver_status,
        result_status=2,
        delta_to_race_leader_minutes_part=0, delta_to_race_leader_ms_part=0,
        delta_to_car_in_front_minutes_part=0, delta_to_car_in_front_ms_part=gap_to_car_ahead,
        total_distance=1000.0, safety_car_delta=0.0,
        num_pit_stops=0, pit_lane_timer_active=0,
        pit_lane_time_in_lane_in_ms=0, pit_stop_timer_in_ms=0,
        pit_stop_should_serve_pen=0,
    )


def _make_status():
    return SimpleNamespace(
        pit_limiter=0, drs_allowed=1, drs_activation_distance=100,
        actual_tyre_compound=20, visual_tyre_compound=16,
        tyres_age_laps=5, vehicle_fia_flags=0, network_paused=0,
        front_brake_bias=58, fuel_in_tank=50.0, fuel_remaining_laps=10.0,
        ers_store_energy=4000000.0, ers_deploy_mode=1, ers_deployed_this_lap=100000.0,
        ers_harvest_limit_per_lap=200000.0,
    )


def _make_damage():
    return SimpleNamespace(
        tyres_wear=(1.0, 1.0, 1.0, 1.0), tyres_damage=(0, 0, 0, 0),
        brakes_damage=(0, 0, 0, 0), tyre_blisters=(0, 0, 0, 0),
        front_left_wing_damage=0, front_right_wing_damage=0, rear_wing_damage=0,
        floor_damage=0, diffuser_damage=0, sidepod_damage=0,
        drs_fault=0, ers_fault=0, gearbox_damage=0, engine_damage=0,
        engine_mguh_wear=0, engine_es_wear=0, engine_ce_wear=0,
        engine_ice_wear=0, engine_mguk_wear=0, engine_tc_wear=0,
        engine_blown=0, engine_seized=0,
    )


def _make_telemetry2(regs_2026=1, driving_wrong_way=0):
    return SimpleNamespace(
        active_aero_mode=1, active_aero_available=1, active_aero_activation_distance=50,
        overtake_available=1, overtake_active=0, overtake_activation_distance=100,
        regulations_2026=regs_2026, driving_wrong_way=driving_wrong_way,
    )


def _pad_list(items, count=22, default=None):
    """Pad a list to 22 elements."""
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
    p1_row = [r for r in rows if r[1] == 100][0]
    # gap_to_car_behind_ms is at index 55
    assert p1_row[55] == 1500


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
    # Motion fields are indices 4-15 (12 fields), should all be None
    motion_fields = row[4:16]
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
    # car_position is at index 48
    assert row[48] is None


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
    # status fields start at 4+12+29+18 = 63, tyres_age_laps is 6th field (index 68)
    # Layout: meta(4) + motion(12) + telemetry(29) + lap(18) + status(8)
    # status: pit_limiter(63), drs_allowed(64), drs_activation_distance(65),
    #         actual_tyre(66), visual_tyre(67), tyres_age_laps(68)
    assert row[68] is None


# --- Task 7: restricted-telemetry / packet-16 smoke coverage ---
# status_ext fields (7) start at index 71 (4 + 12 + 29 + 18 + 8 = 71):
#   front_brake_bias(71), fuel_in_tank(72), fuel_remaining_laps(73),
#   ers_store_energy(74), ers_deploy_mode(75), ers_deployed_this_lap(76),
#   ers_harvest_limit_per_lap(77)
# telemetry2 fields (8) start at index 78:
#   active_aero_mode(78), active_aero_available(79),
#   active_aero_activation_distance(80), overtake_available(81),
#   overtake_active(82), overtake_activation_distance(83),
#   is_2026_regulations(84), driving_wrong_way(85)


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
    assert all(v is None for v in row[71:78])


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
    assert row[71] == 58  # front_brake_bias
    assert row[77] == 200000.0  # ers_harvest_limit_per_lap


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
    assert rows[0][1] == 101


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
    assert row[71] == 58  # front_brake_bias populated, not NULL
    assert row[77] == 200000.0  # ers_harvest_limit_per_lap populated, not NULL

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
    # 7 regs-gated fields are None (indices 78-84)
    assert all(v is None for v in row[78:85])
    # driving_wrong_way (index 85) stays populated regardless of regs
    assert row[85] is True


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
    assert row[78] == 1  # active_aero_mode
    assert row[84] is True  # is_2026_regulations
