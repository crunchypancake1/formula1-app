import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.car_setup import CarSetupData, CarSetupPacket

from . import factories

from services.car_setup import CarSetupService

from .mock_repo import MockRepo


def _make_setup(**overrides):
    return factories.make_car_setup(**overrides)


def _make_blank_setup():
    """The all-zero setup the game sends for another player's car online."""
    return factories.build(CarSetupData)


def _make_setup_packet(setups=None, next_front_wing_value=4.0, player_car_index=0):
    if setups is None:
        setups = [_make_setup()]
    return CarSetupPacket(
        header=factories.make_header(packet_id=5, player_car_index=player_car_index),
        car_setups=setups,
        next_front_wing_value=next_front_wing_value,
    )


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


def test_all_zeros_setup_writes_nothing():
    """
    An all-zeros setup packet — what the game sends for another player's car
    online, and for every car to a spectator — is not a setup. It must never
    reach the database: a row of zeroes would read as a real (and absurd)
    setup rather than as data that was withheld.
    """
    svc, car_setups_repo, lap_setups_repo = _make_service()
    packet = _make_setup_packet(setups=[_make_blank_setup()])
    svc.handle_car_setup_packet(packet, session_uid="123", user_map={0: 100})
    assert ("123", 100) not in svc._cached_setup
    svc.on_lap_complete(session_uid="123", user_id=100, lap_number=1, track_id=11)
    assert car_setups_repo.call_count("upsert_setup") == 0
    assert lap_setups_repo.call_count("insert_lap_setup") == 0


def test_failed_upsert_skips_lap_setup():
    svc, car_setups_repo, lap_setups_repo = _make_service(upsert_return=None)
    packet = _make_setup_packet()
    svc.handle_car_setup_packet(packet, session_uid="123", user_map={0: 100})
    svc.on_lap_complete(session_uid="123", user_id=100, lap_number=1, track_id=11)
    assert car_setups_repo.call_count("upsert_setup") == 1
    assert lap_setups_repo.call_count("insert_lap_setup") == 0
