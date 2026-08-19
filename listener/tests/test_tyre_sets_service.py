import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.tyre_sets import TyreSetsPacket

from . import factories

from services.tyre_sets import TyreSetsService

from .mock_repo import MockRepo


def _make_tyre_set(available=1, actual_compound=20, visual_compound=16,
                   wear=10, life_span=20, usable_life=18, lap_delta_time=0,
                   fitted=0, recommended_session=15):
    return factories.make_tyre_set(
        available=available, actual_compound=actual_compound,
        visual_compound=visual_compound, wear=wear, life_span=life_span,
        usable_life=usable_life, lap_delta_time=lap_delta_time,
        fitted=fitted, recommended_session=recommended_session,
    )


def _make_tyre_sets_packet(session_uid=123, car_idx=0, tyre_set_data=None, fitted_idx=0):
    if tyre_set_data is None:
        tyre_set_data = [_make_tyre_set()]
    return TyreSetsPacket(
        header=factories.make_header(packet_id=12, session_uid=session_uid),
        car_idx=car_idx,
        tyre_set_data=tyre_set_data,
        fitted_idx=fitted_idx,
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


def test_all_zero_restricted_packet_produces_zero_rows():
    """
    Pin test (Part 4 Phase 1 services): a restricted (all-zero) tyre-set
    packet has available != 1 for every slot, so this is already correct
    by construction — no rows should ever be cached or written. Guards
    against a future refactor silently breaking this.
    """
    svc, repo = _make_service()
    all_zero_sets = [_make_tyre_set(available=0) for _ in range(20)]
    packet = _make_tyre_sets_packet(car_idx=0, tyre_set_data=all_zero_sets)
    svc.handle_tyre_sets_packet(packet, user_map={0: 100})
    cached = svc._cached_sets.get(("123", 0))
    assert cached == []
    svc.on_lap_complete(session_uid="123", user_id=100, car_index=0, lap_number=1)
    assert repo.call_count("insert_snapshot") == 0
