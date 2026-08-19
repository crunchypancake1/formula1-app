"""Repository for the sessions, tracks and weather_forecast tables."""

import json
import logging
from datetime import datetime
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase, safe_enum_name
from enums import (
    Formula,
    GameModeIDs,
    RulesetIDs,
    SessionTypeIDs,
    TemperatureChange,
    WeatherIDs,
)

# Static session configuration, in INSERT order. Everything that changes while
# the session runs belongs on session_timeline instead.
SESSION_COLUMNS: tuple[str, ...] = (
    "session_uid", "weekend_link", "session_link", "season_link", "session_start_utc",
    "track_id", "session_type", "formula", "game_mode", "ruleset",
    "total_laps", "session_duration", "num_sessions_in_weekend", "weekend_structure",
    "time_of_day", "session_length",
    "network_game", "ai_difficulty", "forecast_accuracy", "equal_car_performance",
    "sli_pro_native_support",
    "assist_steering", "assist_braking", "assist_gearbox", "assist_pit",
    "assist_pit_release", "assist_ers", "assist_drs",
    "assist_anti_lock_brakes", "assist_traction_control",
    "dynamic_racing_line", "dynamic_racing_line_type",
    "dynamic_racing_line_hi_vis", "dynamic_racing_line_colour_blind",
    "recovery_mode", "flashback_limit", "recurring_rewind_prompt",
    "surface_type", "low_fuel_mode", "race_starts", "tyre_temperature",
    "pit_lane_tyre_sim", "car_damage", "car_damage_rate",
    "collisions", "collisions_off_for_first_lap_only",
    "mp_unsafe_pit_release", "mp_off_for_griefing",
    "corner_cutting_stringency", "parc_ferme_rules", "pit_stop_experience",
    "safety_car", "safety_car_experience", "formation_lap", "formation_lap_experience",
    "red_flags", "affects_licence_level_solo", "affects_licence_level_mp",
    "speed_units_lead_player", "temperature_units_lead_player",
    "speed_units_secondary_player", "temperature_units_secondary_player",
)

_SESSION_UPDATES = ",\n                ".join(
    f"{c} = EXCLUDED.{c}" for c in SESSION_COLUMNS
    # The anchor is written once and never moved: every frame timestamp in the
    # session is derived from it, so re-deriving it after a restart would
    # silently shift every row written from then on.
    if c not in ("session_uid", "session_start_utc")
)

_INSERT_SESSION_SQL = f"""
    INSERT INTO telemetry.sessions ({", ".join(SESSION_COLUMNS)})
    VALUES ({", ".join(["%s"] * len(SESSION_COLUMNS))})
    ON CONFLICT (session_uid) DO UPDATE SET
        {_SESSION_UPDATES}
"""


class SessionsRepository(RepositoryBase):
    """Manages telemetry.sessions plus the track and weather-forecast data derived from Packet 1."""

    TABLE_NAME = "telemetry.sessions"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def update_track_technical_data(
        self,
        track_id: int,
        track_length: int,
        sector2_start: float,
        sector3_start: float,
        marshal_zones: list,
        pit_speed_limit: int,
        active_aero_track_status: Optional[int] = None,
        active_aero_zones_full: Optional[list] = None,
        active_aero_zones_partial: Optional[list] = None,
        drs_zones: Optional[list] = None,
    ) -> bool:
        """
        Fill in a track's technical data from a Session packet, first value wins.

        Only track-static geometry is stored: lengths, sector boundaries, pit
        speed limit, and the *positions* of the marshal, active aero and DRS
        zones. Marshal zone flags are deliberately excluded — they are live race
        control state and go to session_timeline.marshal_zone_flags.

        Returns:
            True if the track exists, False if it does not.
        """
        zone_positions = [
            {"zone_index": idx, "zone_start": zone.zone_start}
            for idx, zone in enumerate(marshal_zones or [])
        ]

        def _zones_json(zones):
            if not zones:
                return None
            return json.dumps([
                {"zone_start": z.zone_start, "zone_end": z.zone_end} for z in zones
            ])

        sql = """
            UPDATE telemetry.tracks
            SET track_length = COALESCE(track_length, %s),
                sector2_start = COALESCE(sector2_start, %s),
                sector3_start = COALESCE(sector3_start, %s),
                marshal_zones = COALESCE(marshal_zones, %s),
                pit_speed_limit = COALESCE(pit_speed_limit, %s),
                active_aero_track_status = COALESCE(active_aero_track_status, %s),
                active_aero_zones_full = COALESCE(active_aero_zones_full, %s),
                active_aero_zones_partial = COALESCE(active_aero_zones_partial, %s),
                drs_zones = COALESCE(drs_zones, %s)
            WHERE track_id = %s
        """

        params = (
            track_length,
            sector2_start,
            sector3_start,
            json.dumps(zone_positions),
            pit_speed_limit,
            active_aero_track_status,
            _zones_json(active_aero_zones_full),
            _zones_json(active_aero_zones_partial),
            _zones_json(drs_zones),
            track_id,
        )
        rows_affected = self._execute(sql, params, table_name="telemetry.tracks")

        if rows_affected == 0:
            self._logger.warning(
                "Track ID %s not found in telemetry.tracks — skipping technical data update.",
                track_id,
            )
            return False
        return True

    def insert_session(self, values: tuple) -> None:
        """
        Insert or refresh a session row. `values` matches SESSION_COLUMNS in order.

        session_start_utc is preserved on conflict — see _SESSION_UPDATES.
        """
        self._execute(_INSERT_SESSION_SQL, values, table_name=self.TABLE_NAME)

    def get_session_start(self, session_uid: str) -> Optional[datetime]:
        """
        Read back the session's wall-clock anchor.

        Every frame table derives its timestamp from this, so it must come from
        the stored row rather than being recomputed — that is what keeps frame
        keys stable when the listener restarts mid-session.
        """
        if not self.enabled:
            return None
        try:
            with self._client.connection() as conn:
                if conn is None:
                    return None
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT session_start_utc FROM telemetry.sessions WHERE session_uid = %s",
                        (session_uid,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            self._logger.error(f"Failed to read session start: {e}", exc_info=True)
            return None

    def capture_start_reaction_time(self, session_uid: str, start_reaction_time: float):
        """
        Record start_reaction_time the first time it is non-zero.

        It stays 0.0 for as long as starts are assisted, so this is a
        first-non-zero-wins update: a real value is never overwritten by a later
        0.0, and a 0.0 never overwrites anything.
        """
        sql = """
            UPDATE telemetry.sessions
            SET start_reaction_time = COALESCE(start_reaction_time, NULLIF(%s, 0))
            WHERE session_uid = %s
        """
        self._execute(sql, (start_reaction_time, session_uid), table_name=self.TABLE_NAME)

    def upsert_weather_forecast(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        forecast_samples: list,
    ):
        """
        Upsert the latest weather forecast for a session (max 64 samples).

        Samples carry the session they predict for, so a race forecast seen
        during practice is kept distinct from the practice forecast itself.
        """
        if not forecast_samples:
            return

        sql = """
            INSERT INTO telemetry.weather_forecast (
                session_uid, forecast_index, forecast_session_type,
                time_offset_minutes,
                weather, track_temperature, track_temperature_change,
                air_temperature, air_temperature_change, rain_percentage,
                overall_frame_identifier, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (session_uid, forecast_index) DO UPDATE SET
                forecast_session_type = EXCLUDED.forecast_session_type,
                time_offset_minutes = EXCLUDED.time_offset_minutes,
                weather = EXCLUDED.weather,
                track_temperature = EXCLUDED.track_temperature,
                track_temperature_change = EXCLUDED.track_temperature_change,
                air_temperature = EXCLUDED.air_temperature,
                air_temperature_change = EXCLUDED.air_temperature_change,
                rain_percentage = EXCLUDED.rain_percentage,
                overall_frame_identifier = EXCLUDED.overall_frame_identifier,
                updated_at = NOW()
        """

        params_list = []
        for idx, sample in enumerate(forecast_samples):
            params_list.append((
                session_uid,
                idx,
                safe_enum_name(SessionTypeIDs, sample.session_type, self._logger),
                sample.time_offset,
                safe_enum_name(WeatherIDs, sample.weather, self._logger),
                sample.track_temperature,
                safe_enum_name(TemperatureChange, sample.track_temperature_change, self._logger),
                sample.air_temperature,
                safe_enum_name(TemperatureChange, sample.air_temperature_change, self._logger),
                sample.rain_percentage,
                overall_frame_identifier,
            ))

        self._execute_many(sql, params_list, table_name="telemetry.weather_forecast")


def resolve_session_enums(session_type: int, formula: int, game_mode: int,
                          ruleset: int, logger: logging.Logger) -> tuple[str, str, str, str]:
    """Resolve the four enum-backed session columns to their stored names."""
    return (
        safe_enum_name(SessionTypeIDs, session_type, logger),
        safe_enum_name(Formula, formula, logger),
        safe_enum_name(GameModeIDs, game_mode, logger),
        safe_enum_name(RulesetIDs, ruleset, logger),
    )
