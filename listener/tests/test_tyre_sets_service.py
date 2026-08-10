import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.tyre_sets import TyreSetsService

from .mock_repo import MockRepo


def _make_tyre_set(available=1, actual_compound=20, visual_compound=16,
                   wear=10.0, life_span=20, usable_life=15,
                   lap_delta_time=50, fitted=0):
    return SimpleNamespace(
        available=available,
        actual_compound=actual_compound,
        visual_compound=visual_compound,
        wear=wear,
        life_span=life_span,
        usable_life=usable_life,
        lap_delta_time=lap_delta_time,
        fitted=fitted,
    )


def _make_tyre_sets_packet(session_uid=123, car_idx=0, tyre_set_data=None):
    if tyre_set_data is None:
        tyre_set_data = [_make_tyre_set()]
    header = SimpleNamespace(session_uid=session_uid)
    return SimpleNamespace(
        header=header,
        car_idx=car_idx,
        tyre_set_data=tyre_set_data,
    )


def _make_service():
    repo = MockRepo()
    svc = TyreSetsService(repo)
    return svc, repo


def test_caches_available_sets():
    svc, _ = _make_service()
    packet = _make_tyre_sets_packet(car_idx=0, tyre_set_data=[_make_tyre_set(available=1)])
    svc.handle_tyre_sets_packet(packet, user_map={0: 100})
    cached = svc._cached_sets.get(("123", 0))
    assert cached is not None
    assert len(cached) == 1


def test_unavailable_sets_excluded():
    svc, _ = _make_service()
    packet = _make_tyre_sets_packet(
        car_idx=0,
        tyre_set_data=[
            _make_tyre_set(available=1),
            _make_tyre_set(available=0),
        ],
    )
    svc.handle_tyre_sets_packet(packet, user_map={0: 100})
    cached = svc._cached_sets.get(("123", 0))
    assert len(cached) == 1


def test_lap_complete_writes_snapshot():
    svc, repo = _make_service()
    packet = _make_tyre_sets_packet(car_idx=0, tyre_set_data=[_make_tyre_set()])
    svc.handle_tyre_sets_packet(packet, user_map={0: 100})
    svc.on_lap_complete(session_uid="123", user_id=100, car_index=0, lap_number=1)
    assert repo.call_count("insert_snapshot") == 1


def test_lap_complete_no_cache_noop():
    svc, repo = _make_service()
    svc.on_lap_complete(session_uid="123", user_id=100, car_index=0, lap_number=1)
    assert repo.call_count("insert_snapshot") == 0
