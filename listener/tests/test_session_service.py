import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.session import _resolve_session_type, SessionService

from .mock_repo import MockRepo


def _make_session_packet(session_uid=123, session_type=15, track_id=11, **overrides):
    defaults = dict(
        header=SimpleNamespace(session_uid=session_uid, session_time=10.0, overall_frame_identifier=1),
        session_type=session_type, track_id=track_id, total_laps=3, track_length=5793,
        formula_type=0, game_mode=0, rule_set=0, session_duration=3600,
        num_sessions_in_weekend=5, time_of_day=720, session_length=5,
        weekend_link_identifier=1000, session_link_identifier=2000,
        weather=0, track_temperature=30, air_temperature=25,
        session_time_left=3600, safety_car_status=0, pit_speed_limit=80,
        sector_2_lap_distance_start=2400.0, sector_3_lap_distance_start=4200.0,
        marshal_zones=[], weather_forecast_samples=[],
        weekend_structure=[1, 5, 10, 15, 0, 0, 0, 0, 0, 0, 0, 0],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_service():
    sessions_repo = MockRepo()
    timeline_repo = MockRepo()
    svc = SessionService(sessions_repo, timeline_repo)
    return svc, sessions_repo, timeline_repo


def test_first_packet_inserts_session():
    svc, sessions_repo, _ = _make_service()
    packet = _make_session_packet()
    svc.handle_session_packet(packet)
    assert sessions_repo.call_count("insert_session") == 1


def test_duplicate_session_not_reinserted():
    svc, sessions_repo, _ = _make_service()
    packet = _make_session_packet()
    svc.handle_session_packet(packet)
    svc.handle_session_packet(packet)
    assert sessions_repo.call_count("insert_session") == 1


def test_timeline_written_every_packet():
    svc, _, timeline_repo = _make_service()
    packet = _make_session_packet()
    svc.handle_session_packet(packet)
    svc.handle_session_packet(packet)
    assert timeline_repo.call_count("insert_timeline_entry") == 2


def test_session_type_cached():
    svc, _, _ = _make_service()
    packet = _make_session_packet(session_type=15)
    svc.handle_session_packet(packet)
    assert svc.get_session_type("123") == 15


def test_sprint_race_detection():
    # Sprint weekend: has sprint shootout ID (10) AND two distinct race IDs (15, 16)
    # The set deduplicates, so we need two different race type IDs to get num_races >= 2
    packet = _make_session_packet(
        session_type=15,
        num_sessions_in_weekend=4,
        weekend_structure=[1, 10, 15, 16, 0, 0, 0, 0, 0, 0, 0, 0],
    )
    result = _resolve_session_type(packet)
    assert result == 100  # SPRINT_RACE


def test_non_sprint_race_unchanged():
    # Regular weekend: no sprint shootout IDs, only one race ID
    packet = _make_session_packet(
        session_type=15,
        num_sessions_in_weekend=5,
        weekend_structure=[1, 2, 3, 5, 15, 0, 0, 0, 0, 0, 0, 0],
    )
    result = _resolve_session_type(packet)
    assert result == 15
