"""Session packet builder (Packet ID 1)."""

import struct

from .header import build_header

_PRE_MARSHAL_ZONES_FORMAT = '<BbbBHBbBHH6B'
_MARSHAL_ZONE_FORMAT = '<fb'
_BETWEEN_MARSHAL_FORECAST_FORMAT = '<BBB'
_WEATHER_FORECAST_SAMPLE_FORMAT = '<3B4bB'
_BETWEEN_FORECAST_WEEKEND_FORMAT = '<2B3I14BI33B'
_WEEKEND_STRUCTURE_FORMAT = '<12B'
_REMAINING_FIELDS_FORMAT = '<2f'
_ZONE_FORMAT = '<2f'
_AERO_TRACK_STATUS_FORMAT = '<BB'
_PARTIAL_AERO_ZONES_COUNT_FORMAT = '<B'
_DRS_ZONES_COUNT_FORMAT = '<B'
_TAIL_ASSIST_FIELDS_FORMAT = '<f5B'

_NUM_MARSHAL_ZONES = 21
_NUM_FORECAST_SAMPLES = 64
_NUM_ACTIVE_AERO_ZONES = 8
_NUM_DRS_ZONES = 4


def build_session_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    track_id: int = 11,
    session_type: int = 15,
    total_laps: int = 3,
    track_length: int = 5793,
    session_time_left: int = 3600,
    session_duration: int = 3600,
    weather: int = 0,
    track_temperature: int = 30,
    air_temperature: int = 25,
    weekend_link: int = 1000,
    session_link: int = 2000,
    active_aero_track_status: int = 0,
    num_active_aero_zones_full: int = 8,
    active_aero_zones_full: list | None = None,
    num_active_aero_zones_partial: int = 8,
    active_aero_zones_partial: list | None = None,
    num_drs_zones: int = 4,
    drs_zones: list | None = None,
    start_reaction_time: float = 0.0,
    anti_lock_brakes_assist: int = 0,
    traction_control_assist: int = 0,
    dynamic_racing_line_hi_vis: int = 0,
    dynamic_racing_line_colour_blind: int = 0,
    recurring_rewind_prompt: int = 0,
) -> bytes:
    """Build a complete Session packet (header + body)."""
    header = build_header(
        packet_id=1,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    # Pre-marshal zones fields
    pre_marshal = struct.pack(
        _PRE_MARSHAL_ZONES_FORMAT,
        weather,               # weather
        track_temperature,     # track_temperature (int8)
        air_temperature,       # air_temperature (int8)
        total_laps,            # total_laps
        track_length,          # track_length (uint16)
        session_type,          # session_type
        track_id,              # track_id (int8)
        0,                     # formula_type (F1 Modern)
        session_time_left,     # session_time_left
        session_duration,      # session_duration
        80,                    # pit_speed_limit
        0,                     # game_paused
        0,                     # is_spectating
        0,                     # spectator_car_index
        0,                     # sli_pro_native_support
        _NUM_MARSHAL_ZONES,    # num_marshal_zones
    )

    # Marshal zones (21 zones)
    marshal_zones = b''
    for i in range(_NUM_MARSHAL_ZONES):
        zone_start = i / _NUM_MARSHAL_ZONES
        marshal_zones += struct.pack(_MARSHAL_ZONE_FORMAT, zone_start, 0)

    # Between marshal/forecast: safety_car_status, network_game, num_forecast_samples
    between_mf = struct.pack(
        _BETWEEN_MARSHAL_FORECAST_FORMAT,
        0,                        # safety_car_status
        1,                        # network_game (online)
        _NUM_FORECAST_SAMPLES,    # num_weather_forecast_samples
    )

    # Weather forecast samples (64 samples)
    forecast = b''
    for i in range(_NUM_FORECAST_SAMPLES):
        forecast += struct.pack(
            _WEATHER_FORECAST_SAMPLE_FORMAT,
            session_type,          # session_type
            min(i * 5, 255),       # time_offset (minutes, uint8 capped)
            weather,               # weather
            track_temperature,     # track_temperature (int8)
            2,                     # track_temperature_change (no change)
            air_temperature,       # air_temperature (int8)
            2,                     # air_temperature_change (no change)
            0,                     # rain_percentage
        )

    # Between forecast and weekend structure
    # Format: '<2B3I14BI33B'
    # forecast_accuracy, ai_difficulty, season_link, weekend_link, session_link,
    # 14× uint8 fields, 1× uint32 (time_of_day), 1× uint8 (session_length),
    # then 33× uint8 for remaining settings
    between_fw = struct.pack(
        _BETWEEN_FORECAST_WEEKEND_FORMAT,
        0,                     # forecast_accuracy
        100,                   # ai_difficulty
        1,                     # season_link_identifier
        weekend_link,          # weekend_link_identifier
        session_link,          # session_link_identifier
        # 14× uint8
        0, 0, 0,               # pit_stop_window_ideal/latest/rejoin
        0, 0, 0, 0, 0, 0, 0,  # assist_steering..dynamic_racing_line
        0,                     # dynamic_racing_line_type
        0,                     # game_mode
        0,                     # rule_set
        0,                     # (padding/unused field)
        720,                   # time_of_day (uint32, minutes since midnight = noon)
        5,                     # session_length
        # 33× uint8 (speed_units through formation_lap_experience + extra settings)
        0, 0, 0, 0,           # speed/temp units
        0, 0, 0,              # num safety/vsc/red flag
        0, 0, 0,              # equal_car_performance, recovery_mode, flashback_limit
        0, 0, 0,              # surface_type, low_fuel_mode, race_starts
        0, 0, 0, 0,           # tyre_temperature, pit_lane_tyre_sim, car_damage, car_damage_rate
        0, 0, 0, 0,           # collisions, collisions_off_first_lap, mp_unsafe_pit, mp_off_griefing
        0, 0, 0,              # corner_cutting, parc_ferme, pit_stop_experience
        0, 0, 0, 0,           # safety_car, safety_car_experience, formation_lap, formation_lap_experience
        0, 0,                 # red_flags, affects_licence_solo
        0,                    # affects_licence_mp
        5,                    # num_sessions_in_weekend
    )

    # Weekend structure (12 uint8s)
    weekend = struct.pack(
        _WEEKEND_STRUCTURE_FORMAT,
        1, 5, 10, 15, 0,      # P1, P2, Q, Race, then padding
        0, 0, 0, 0, 0, 0, 0,
    )

    # Remaining fields: sector2_start, sector3_start (floats)
    remaining = struct.pack(
        _REMAINING_FIELDS_FORMAT,
        2400.0,    # sector_2_lap_distance_start
        4200.0,    # sector_3_lap_distance_start
    )

    # Active aero track status + num full active aero zones
    aero_track_status = struct.pack(
        _AERO_TRACK_STATUS_FORMAT,
        active_aero_track_status,
        num_active_aero_zones_full,
    )

    # Full active aero zones (fixed array of 8)
    zones_full = active_aero_zones_full or [(0.0, 0.0)] * _NUM_ACTIVE_AERO_ZONES
    active_aero_zones_full_bytes = b''
    for zone_start, zone_end in zones_full:
        active_aero_zones_full_bytes += struct.pack(_ZONE_FORMAT, zone_start, zone_end)

    # Num partial active aero zones
    partial_aero_zones_count = struct.pack(_PARTIAL_AERO_ZONES_COUNT_FORMAT, num_active_aero_zones_partial)

    # Partial active aero zones (fixed array of 8)
    zones_partial = active_aero_zones_partial or [(0.0, 0.0)] * _NUM_ACTIVE_AERO_ZONES
    active_aero_zones_partial_bytes = b''
    for zone_start, zone_end in zones_partial:
        active_aero_zones_partial_bytes += struct.pack(_ZONE_FORMAT, zone_start, zone_end)

    # Num DRS zones
    drs_zones_count = struct.pack(_DRS_ZONES_COUNT_FORMAT, num_drs_zones)

    # DRS zones (fixed array of 4)
    zones_drs = drs_zones or [(0.0, 0.0)] * _NUM_DRS_ZONES
    drs_zones_bytes = b''
    for zone_start, zone_end in zones_drs:
        drs_zones_bytes += struct.pack(_ZONE_FORMAT, zone_start, zone_end)

    # Start reaction time + 5 single-byte assist fields
    tail_assist_fields = struct.pack(
        _TAIL_ASSIST_FIELDS_FORMAT,
        start_reaction_time,
        anti_lock_brakes_assist,
        traction_control_assist,
        dynamic_racing_line_hi_vis,
        dynamic_racing_line_colour_blind,
        recurring_rewind_prompt,
    )

    body = (
        pre_marshal + marshal_zones + between_mf + forecast + between_fw + weekend + remaining
        + aero_track_status + active_aero_zones_full_bytes
        + partial_aero_zones_count + active_aero_zones_partial_bytes
        + drs_zones_count + drs_zones_bytes
        + tail_assist_fields
    )
    return header + body
