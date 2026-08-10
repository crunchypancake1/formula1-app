"""Repository for sessions table."""

import json
import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase, safe_enum_name
from enums import (
    FlagStatus,
    Formula,
    GameModeIDs,
    RulesetIDs,
    SessionTypeIDs,
    TemperatureChange,
    WeatherIDs,
)


class SessionsRepository(RepositoryBase):
    """Manages sessions table and related structured data tables."""

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
    ) -> bool:
        """
        Update technical track data from session packet (only if not already set).

        Only updates technical fields (track_length, sectors, marshal_zones, pit_speed_limit) when
        they are NULL. Once set, they are never overwritten - track data is static.
        Reference data (name, display_name, country) must already exist in the database.

        Args:
            track_id: Numeric track ID from game (primary key)
            track_length: Track length in metres
            sector2_start: Distance where sector 2 starts
            sector3_start: Distance where sector 3 starts
            marshal_zones: List of MarshalZone dataclass instances
            pit_speed_limit: Pit speed limit in km/h

        Returns:
            True if the track exists, False if track doesn't exist
        """
        zones_data = []
        for idx, zone in enumerate(marshal_zones or []):
            if hasattr(zone, 'zone_flag') and zone.zone_flag >= 0:
                zones_data.append({
                    "zone_index": idx,
                    "zone_start": zone.zone_start,
                    "zone_flag": safe_enum_name(FlagStatus, zone.zone_flag, self._logger),
                })

        sql = """
            UPDATE telemetry.tracks
            SET track_length = COALESCE(track_length, %s),
                sector2_start = COALESCE(sector2_start, %s),
                sector3_start = COALESCE(sector3_start, %s),
                marshal_zones = COALESCE(marshal_zones, %s),
                pit_speed_limit = COALESCE(pit_speed_limit, %s)
            WHERE track_id = %s
        """

        params = (
            track_length,
            sector2_start,
            sector3_start,
            json.dumps(zones_data),
            pit_speed_limit,
            track_id,
        )
        rows_affected = self._execute(sql, params, table_name="telemetry.tracks")

        if rows_affected == 0:
            self._logger.warning(
                f"Track ID {track_id} not found in database - skipping technical data update. "
                "Track must exist before updating technical data."
            )
            return False
        return True


    def insert_session(
        self,
        session_uid: str,
        weekend_link: str,
        session_link: str,
        track_id: int,
        session_type: int,
        formula: int,
        game_mode: int,
        ruleset: int,
        total_laps: int,
        session_duration: int,
        num_sessions_in_weekend: int,
        time_of_day: int,
        session_length: int,
    ):
        """
        Insert a new session record with essential session metadata.

        Only called on first Session packet received.
        Track must be upserted before calling this method.
        """
        sql = """
            INSERT INTO telemetry.sessions (
                session_uid, weekend_link, session_link,
                track_id, session_type, formula, game_mode, ruleset,
                total_laps, session_duration,
                num_sessions_in_weekend,
                time_of_day, session_length
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (session_uid) DO UPDATE SET
                weekend_link = EXCLUDED.weekend_link,
                session_link = EXCLUDED.session_link,
                track_id = EXCLUDED.track_id,
                session_type = EXCLUDED.session_type,
                formula = EXCLUDED.formula,
                game_mode = EXCLUDED.game_mode,
                ruleset = EXCLUDED.ruleset,
                total_laps = EXCLUDED.total_laps,
                session_duration = EXCLUDED.session_duration,
                num_sessions_in_weekend = EXCLUDED.num_sessions_in_weekend,
                time_of_day = EXCLUDED.time_of_day,
                session_length = EXCLUDED.session_length
        """

        params = (
            session_uid,
            weekend_link,
            session_link,
            track_id,
            safe_enum_name(SessionTypeIDs, session_type, self._logger),
            safe_enum_name(Formula, formula, self._logger),
            safe_enum_name(GameModeIDs, game_mode, self._logger),
            safe_enum_name(RulesetIDs, ruleset, self._logger),
            total_laps,
            session_duration,
            num_sessions_in_weekend,
            time_of_day,
            session_length,
        )

        self._execute(sql, params, table_name=self.TABLE_NAME)

    def upsert_weather_forecast(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        forecast_samples: list,
    ):
        """
        Upsert weather forecast samples for a session.

        Stores only the latest forecast (max 64 rows per session).
        Updates existing forecasts via upsert on (session_uid, forecast_index).

        Args:
            session_uid: Session identifier
            overall_frame_identifier: Overall frame identifier (for tracking last update)
            forecast_samples: List of WeatherForecastSample dataclass instances
        """
        if not forecast_samples:
            return

        sql = """
            INSERT INTO telemetry.weather_forecast (
                session_uid, forecast_index, time_offset_minutes,
                weather, track_temperature, track_temperature_change,
                air_temperature, air_temperature_change, rain_percentage,
                overall_frame_identifier, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (session_uid, forecast_index) DO UPDATE SET
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
            params = (
                session_uid,
                idx,
                sample.time_offset,
                safe_enum_name(WeatherIDs, sample.weather, self._logger),
                sample.track_temperature,
                safe_enum_name(TemperatureChange, sample.track_temperature_change, self._logger),
                sample.air_temperature,
                safe_enum_name(TemperatureChange, sample.air_temperature_change, self._logger),
                sample.rain_percentage,
                overall_frame_identifier,
            )
            params_list.append(params)

        self._execute_many(sql, params_list, table_name="telemetry.weather_forecast")

