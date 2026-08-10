import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.car_setup import CarSetupService

from .mock_repo import MockRepo


def _make_setup():
    return SimpleNamespace(
        front_wing=10, rear_wing=8,
        on_throttle=80, off_throttle=60,
        front_camber=-3.0, rear_camber=-1.5,
        front_toe=0.1, rear_toe=0.05,
        front_suspension=7, rear_suspension=9,
        front_anti_roll_bar=5, rear_anti_roll_bar=6,
        front_ride_height=3, rear_ride_height=7,
        brake_pressure=90, brake_bias=58, engine_braking=50,
        front_left_tyre_pressure=23.5, front_right_tyre_pressure=23.5,
        rear_left_tyre_pressure=22.0, rear_right_tyre_pressure=22.0,
        ballast=0, fuel_load=50.0,
    )


def _make_setup_packet(setups=None):
    if setups is None:
        setups = [_make_setup()] * 22
    return SimpleNamespace(car_setups=setups)


def _make_service(upsert_return=1):
    car_setups_repo = MockRepo(upsert_setup=upsert_return)
    lap_setups_repo = MockRepo()
    svc = CarSetupService(car_setups_repo, lap_setups_repo)
    return svc, car_setups_repo, lap_setups_repo


def test_caches_setup():
    svc, _, _ = _make_service()
    packet = _make_setup_packet()
    svc.handle_car_setup_packet(packet, session_uid="123", user_map={0: 100})
    assert ("123", 100) in svc._cached_setup


def test_lap_complete_writes_to_db():
    svc, car_setups_repo, lap_setups_repo = _make_service()
    packet = _make_setup_packet()
    svc.handle_car_setup_packet(packet, session_uid="123", user_map={0: 100})
    svc.on_lap_complete(session_uid="123", user_id=100, lap_number=1, track_id=11)
    assert car_setups_repo.call_count("upsert_setup") == 1
    assert lap_setups_repo.call_count("insert_lap_setup") == 1


def test_lap_complete_no_cache_noop():
    svc, car_setups_repo, lap_setups_repo = _make_service()
    svc.on_lap_complete(session_uid="123", user_id=100, lap_number=1, track_id=11)
    assert car_setups_repo.call_count("upsert_setup") == 0
    assert lap_setups_repo.call_count("insert_lap_setup") == 0


def test_setup_hash_deduplication():
    svc, _, _ = _make_service()
    packet = _make_setup_packet()
    svc.handle_car_setup_packet(packet, session_uid="123", user_map={0: 100})
    hash1 = svc._cached_setup[("123", 100)][0]
    svc.handle_car_setup_packet(packet, session_uid="123", user_map={0: 100})
    hash2 = svc._cached_setup[("123", 100)][0]
    assert hash1 == hash2


def test_failed_upsert_skips_lap_setup():
    svc, car_setups_repo, lap_setups_repo = _make_service(upsert_return=None)
    packet = _make_setup_packet()
    svc.handle_car_setup_packet(packet, session_uid="123", user_map={0: 100})
    svc.on_lap_complete(session_uid="123", user_id=100, lap_number=1, track_id=11)
    assert car_setups_repo.call_count("upsert_setup") == 1
    assert lap_setups_repo.call_count("insert_lap_setup") == 0
