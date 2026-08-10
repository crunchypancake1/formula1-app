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
