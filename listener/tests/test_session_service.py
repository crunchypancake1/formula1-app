import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.session import _resolve_session_type, SessionService

from . import factories
from .mock_repo import MockRepo


def _make_session_packet(session_uid=123, session_type=15, track_id=11, **overrides):
    """A Session packet with every field the service reads populated."""
    defaults = dict(
        header=factories.make_header(packet_id=1, session_uid=session_uid),
        session_type=session_type, track_id=track_id, total_laps=3, track_length=5793,
        formula_type=0, game_mode=0, rule_set=0, session_duration=3600,
        num_sessions_in_weekend=4, time_of_day=720, session_length=5,
        weekend_link_identifier=1000, session_link_identifier=2000,
        season_link_identifier=3000,
        weather=0, track_temperature=30, air_temperature=25,
        session_time_left=3600, safety_car_status=0, pit_speed_limit=80,
        sector_2_lap_distance_start=2400.0, sector_3_lap_distance_start=4200.0,
        num_marshal_zones=0, marshal_zones=[],
        num_weather_forecast_samples=0, weather_forecast_samples=[],
        weekend_structure=[1, 5, 10, 15, 0, 0, 0, 0, 0, 0, 0, 0],
        start_reaction_time=0.0,
        num_active_aero_zones_full=0, active_aero_zones_full=[],
        num_active_aero_zones_partial=0, active_aero_zones_partial=[],
        num_drs_zones=0, drs_zones=[], active_aero_track_status=0,
        network_game=1, ai_difficulty=90, forecast_accuracy=0,
        equal_car_performance=1, sli_pro_native_support=0,
        assist_steering=0, assist_braking=0, assist_gearbox=1, assist_pit=0,
        assist_pit_release=0, assist_ers=0, assist_drs=0,
        anti_lock_brakes_assist=0, traction_control_assist=0,
        dynamic_racing_line=0, dynamic_racing_line_type=0,
        dynamic_racing_line_hi_vis=0, dynamic_racing_line_colour_blind=0,
        recovery_mode=0, flashback_limit=0, recurring_rewind_prompt=0,
        surface_type=1, low_fuel_mode=0, race_starts=0, tyre_temperature=0,
        pit_lane_tyre_sim=0, car_damage=2, car_damage_rate=1,
        collisions=0, collisions_off_for_first_lap_only=0,
        mp_unsafe_pit_release=0, mp_off_for_griefing=0,
        corner_cutting_stringency=1, parc_ferme_rules=1, pit_stop_experience=0,
        safety_car=1, safety_car_experience=0, formation_lap=1,
        formation_lap_experience=0, red_flags=1,
        affects_licence_level_solo=0, affects_licence_level_mp=0,
        speed_units_lead_player=1, temperature_units_lead_player=0,
        speed_units_secondary_player=1, temperature_units_secondary_player=0,
        game_paused=0, is_spectating=0, spectator_car_index=255,
        pit_stop_window_ideal_lap=0, pit_stop_window_latest_lap=0,
        pit_stop_rejoin_position=0,
        num_safety_car_periods=0, num_virtual_safety_car_periods=0,
        num_red_flag_periods=0,
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
