import dataclasses
import struct
from dataclasses import dataclass
from typing import Any, List

from .packet_header import PacketHeader

_MARSHAL_ZONE_FORMAT = '<fb'
_MARSHAL_ZONE_FORMAT_SIZE = struct.calcsize(_MARSHAL_ZONE_FORMAT)
@dataclass
class MarshalZone:
    zone_start: float                       # float     |   Fraction (0..1) of way through the lap the marshal zone starts
    zone_flag: int                          # int8      |   -1 = invalid/unknown, 0 = none, 1 = green, 2 = blue, 3 = yellow

_WEATHER_FORECAST_SAMPLE_FORMAT = '<3B4bB'
_WEATHER_FORECAST_SAMPLE_FORMAT_SIZE = struct.calcsize(_WEATHER_FORECAST_SAMPLE_FORMAT)
@dataclass
class WeatherForecastSample:
    session_type: int                       # uint8     |   0 = unknown, see appendix
    time_offset: int                        # uint8     |   Time in minutes the forecast is for
    weather: int                            # uint8     |   Weather (0 = clear, 1 = light cloud, etc.)
    track_temperature: int                  # int8      |   Track temp in degrees Celsius
    track_temperature_change: int           # int8      |   Track temp. change (0 = up, 1 = down, 2 = no change)
    air_temperature: int                    # int8      |   Air temp. in degrees Celsius
    air_temperature_change: int             # int8      |   Air temp. change (0 = up, 1 = down, 2 = no change)
    rain_percentage: int                    # uint8     |   Rain percentage (0-100)

PRE_MARSHAL_ZONES_FORMAT = '<BbbBHBbBHH6B'
PRE_MARSHAL_ZONES_FORMAT_SIZE = struct.calcsize(PRE_MARSHAL_ZONES_FORMAT)

BETWEEN_MARSHAL_FORECAST_FORMAT = '<BBB'
BETWEEN_MARSHAL_FORECAST_FORMAT_SIZE = struct.calcsize(BETWEEN_MARSHAL_FORECAST_FORMAT)

BETWEEN_FORECAST_WEEKEND_FORMAT = '<2B3I14BI33B'
BETWEEN_FORECAST_WEEKEND_FORMAT_SIZE = struct.calcsize(BETWEEN_FORECAST_WEEKEND_FORMAT)

WEEKEND_STRUCTURE_FORMAT = '<12B'
WEEKEND_STRUCTURE_FORMAT_SIZE = struct.calcsize(WEEKEND_STRUCTURE_FORMAT)

REMAINING_FIELDS_FORMAT = '<2f'
REMAINING_FIELDS_FORMAT_SIZE = struct.calcsize(REMAINING_FIELDS_FORMAT)
@dataclass
class SessionPacket:
    header: PacketHeader                    # Header
    weather: int                            # uint8     |   Weather (0 = clear, 1 = light cloud, etc.)
    track_temperature: int                  # int8      |   Track temp. in degrees Celsius
    air_temperature: int                    # int8      |   Air temp. in degrees Celsius
    total_laps: int                         # uint8     |   Total number of laps in this race
    track_length: int                       # uint16    |   Track length in metres
    session_type: int                       # uint8     |   Session type (0 = unknown, etc.)
    track_id: int                           # int8      |   Track ID (-1 for unknown)
    formula_type: int                       # uint8     |   Formula (0 = F1 Modern, etc.)
    session_time_left: int                  # uint16    |   Time left in session (seconds)
    session_duration: int                   # uint16    |   Session duration (seconds)
    pit_speed_limit: int                    # uint8     |   Pit speed limit (km/h)
    game_paused: int                        # uint8     |   Whether the game is paused
    is_spectating: int                      # uint8     |   Whether the player is spectating
    spectator_car_index: int                # uint8     |   Index of the car being spectated
    sli_pro_native_support: int             # uint8     |   SLI Pro support (0 = inactive, 1 = active)
    num_marshal_zones: int                  # uint8     |   Number of marshal zones to follow
    marshal_zones: List[MarshalZone]        # [21]      |   List of marshal zones – max 21
    safety_car_status: int                  # uint8     |   Safety car status (0 = no safety car, etc.)
    network_game: int                       # uint8     |   Network game (0 = offline, 1 = online)
    num_weather_forecast_samples: int       # uint8     |   Number of weather forecast samples to follow
    weather_forecast_samples: list[WeatherForecastSample] # Array of weather forecast samples (max 64)
    forecast_accuracy: int                  # uint8     |   0 = Perfect, 1 = Approximate
    ai_difficulty: int                      # uint8     |   AI Difficulty rating (0-110)
    season_link_identifier: int             # uint32    |   Identifier for season
    weekend_link_identifier: int            # uint32    |   Identifier for weekend
    session_link_identifier: int            # uint32    |   Identifier for session
    pit_stop_window_ideal_lap: int          # uint8     |   Ideal lap to pit for current strategy
    pit_stop_window_latest_lap: int         # uint8     |   Latest lap to pit for current strategy
    pit_stop_rejoin_position: int           # uint8     |   Predicted position to rejoin
    assist_steering: int                    # uint8     |   Steering assist (0 = off, 1 = on)
    assist_braking: int                     # uint8     |   Braking assist (0 = off, 1 = low, etc.)
    assist_gearbox: int                     # uint8     |   Gearbox assist (1 = manual, etc.)
    assist_pit: int                         # uint8     |   Pit assist (0 = off, 1 = on)
    assist_pit_release: int                 # uint8     |   Pit release assist (0 = off, 1 = on)
    assist_ers: int                         # uint8     |   ERS assist (0 = off, 1 = on)
    assist_drs: int                         # uint8     |   DRS assist (0 = off, 1 = on)
    dynamic_racing_line: int                # uint8     |   Dynamic racing line (0 = off, 1 = corners, etc.)
    dynamic_racing_line_type: int           # uint8     |   Racing line type (0 = 2D, 1 = 3D)
    game_mode: int                          # uint8     |   Game mode ID
    rule_set: int                           # uint8     |   Ruleset
    time_of_day: int                        # uint32    |   Local time of day (minutes since midnight)
    session_length: int                     # uint8     |   Session length (0 = None, etc.)
    speed_units_lead_player: int            # uint8     |   Speed units for lead player (0 = MPH, 1 = KPH)
    temperature_units_lead_player: int      # uint8     |   Temperature units for lead player (0 = Celsius, etc.)
    speed_units_secondary_player: int       # uint8     |   Speed units for secondary player
    temperature_units_secondary_player: int # uint8     |   Temperature units for secondary player
    num_safety_car_periods: int             # uint8     |   Number of safety cars during session
    num_virtual_safety_car_periods: int     # uint8     |   Number of virtual safety cars
    num_red_flag_periods: int               # uint8     |   Number of red flags
    equal_car_performance: int              # uint8     |   Equal car performance (0 = off, 1 = on)
    recovery_mode: int                      # uint8     |   Recovery mode (0 = None, 1 = Flashbacks, etc.)
    flashback_limit: int                    # uint8     |   Flashback limit (0 = Low, etc.)
    surface_type: int                       # uint8     |   Surface type (0 = Simplified, 1 = Realistic)
    low_fuel_mode: int                      # uint8     |   Low fuel mode (0 = Easy, 1 = Hard)
    race_starts: int                        # uint8     |   Race starts (0 = Manual, 1 = Assisted)
    tyre_temperature: int                   # uint8     |   Tyre temperature (0 = Surface only, etc.)
    pit_lane_tyre_sim: int                  # uint8     |   Pit lane tyre sim (0 = On, 1 = Off)
    car_damage: int                         # uint8     |   Car damage (0 = Off, 1 = Reduced, etc.)
    car_damage_rate: int                    # uint8     |   Car damage rate (0 = Reduced, etc.)
    collisions: int                         # uint8     |   Collisions (0 = Off, 1 = Player-to-Player off, etc.)
    collisions_off_for_first_lap_only: int  # uint8     |   Collisions off for first lap only (0 = Disabled, etc.)
    mp_unsafe_pit_release: int              # uint8     |   Multiplayer unsafe pit release (0 = On, etc.)
    mp_off_for_griefing: int                # uint8     |   Multiplayer off for griefing (0 = Disabled, etc.)
    corner_cutting_stringency: int          # uint8     |   Corner cutting stringency (0 = Regular, etc.)
    parc_ferme_rules: int                   # uint8     |   Parc Ferme rules (0 = Off, 1 = On)
    pit_stop_experience: int                # uint8     |   Pit stop experience (0 = Automatic, etc.)
    safety_car: int                         # uint8     |   Safety car (0 = Off, etc.)
    safety_car_experience: int              # uint8     |   Safety car experience (0 = Broadcast, etc.)
    formation_lap: int                      # uint8     |   Formation lap (0 = Off, 1 = On)
    formation_lap_experience: int           # uint8     |   Formation lap experience (0 = Broadcast, etc.)
    red_flags: int                          # uint8     |   Red flags (0 = Off, etc.)
    affects_licence_level_solo: int         # uint8     |   Affects license level (solo)
    affects_licence_level_mp: int           # uint8     |   Affects license level (MP)
    num_sessions_in_weekend: int            # uint8     |   Number of sessions in weekend
    weekend_structure: list[int]            # uint8[12] |   List of session types to show weekend structure
    sector_2_lap_distance_start: float      # float     |   Sector 2 start distance (meters)
    sector_3_lap_distance_start: float      # float     |   Sector 3 start distance (meters)

def unpack_session(packet_header: PacketHeader, data: bytes) -> SessionPacket:
    """
    Unpack Session packet (Packet ID: 1).

    Contains session metadata including track, weather, session type, timing,
    marshal zones, weather forecast, and various game settings. Sent at ~2Hz.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        SessionPacket with complete session information
    """
    # Unpack pre-marshal zones fields
    pre_marshal_zones_fields = struct.unpack(PRE_MARSHAL_ZONES_FORMAT, data[:PRE_MARSHAL_ZONES_FORMAT_SIZE])

    offset = PRE_MARSHAL_ZONES_FORMAT_SIZE

    # Unpack Marshal Zones
    pre_marshal_zones_fields[-1]
    marshal_zones_size =_MARSHAL_ZONE_FORMAT_SIZE * 21
    marshal_zones_bytes = data[offset:offset + marshal_zones_size]

    marshal_zones = []
    for unpacked_marshal_zone in struct.iter_unpack(_MARSHAL_ZONE_FORMAT, marshal_zones_bytes):
        marshal_zones.append(MarshalZone(*unpacked_marshal_zone))

    offset += marshal_zones_size

    # Unpack Fields between marshal zones and weather forecast samples
    fields_between_bytes = data[offset:offset + BETWEEN_MARSHAL_FORECAST_FORMAT_SIZE]
    fields_between = struct.unpack(BETWEEN_MARSHAL_FORECAST_FORMAT, fields_between_bytes)

    offset += BETWEEN_MARSHAL_FORECAST_FORMAT_SIZE

    # Unpack Weather Forecast Samples
    fields_between[-1]  # Assuming the first field after marshal zones is the count
    weather_forecast_samples_size = _WEATHER_FORECAST_SAMPLE_FORMAT_SIZE * 64
    weather_forecast_samples_bytes = data[offset:offset + weather_forecast_samples_size]

    weather_forecast_samples = []
    for unpacked_forecast_sample in struct.iter_unpack(_WEATHER_FORECAST_SAMPLE_FORMAT, weather_forecast_samples_bytes):
        weather_forecast_samples.append(WeatherForecastSample(*unpacked_forecast_sample))

    offset += weather_forecast_samples_size

    # Unpack Fields between weather forecast samples and weekend structure
    fields_between_forecast_weekend_bytes = data[offset:offset + BETWEEN_FORECAST_WEEKEND_FORMAT_SIZE]
    fields_between_forecast_weekend = struct.unpack(BETWEEN_FORECAST_WEEKEND_FORMAT, fields_between_forecast_weekend_bytes)

    offset += BETWEEN_FORECAST_WEEKEND_FORMAT_SIZE

    # Unpack weekend structure
    weekend_structure_bytes = data[offset:offset + WEEKEND_STRUCTURE_FORMAT_SIZE]
    weekend_structure = struct.unpack(WEEKEND_STRUCTURE_FORMAT, weekend_structure_bytes)
    weekend_structure_list = list(weekend_structure)

    offset += WEEKEND_STRUCTURE_FORMAT_SIZE

    # Remaining fields after weekend structure
    remaining_fields_bytes = data[offset:offset + REMAINING_FIELDS_FORMAT_SIZE]
    remaining_fields = struct.unpack(REMAINING_FIELDS_FORMAT, remaining_fields_bytes)

    # Construct the full data packet from all unpacked fields in field order.
    # Using Any cast to avoid pyright complaining about the mixed-type tuple.
    all_args: Any = (
        (packet_header,)
        + pre_marshal_zones_fields
        + (marshal_zones,)
        + fields_between
        + (weather_forecast_samples,)
        + fields_between_forecast_weekend
        + (weekend_structure_list,)
        + remaining_fields
    )
    field_names = [f.name for f in dataclasses.fields(SessionPacket)]
    return SessionPacket(**dict(zip(field_names, all_args)))
