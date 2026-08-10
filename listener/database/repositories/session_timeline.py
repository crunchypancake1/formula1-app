"""Repository for session_timeline hypertable."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase, safe_enum_name
from enums import SafetyCarStatus, WeatherIDs


class SessionTimelineRepository(RepositoryBase):
    """Manages session_timeline hypertable - dynamic session state snapshots."""

    TABLE_NAME = "telemetry.session_timeline"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_timeline_entry(
        self,
        session_uid: str,
        session_time: float,
        overall_frame_identifier: int,
        session_time_left: float,
        total_laps: int,
        safety_car_status: int,
        weather_track_temp: int,
        weather_air_temp: int,
        weather_state: int,
    ):
        """
        Insert a session timeline entry with dynamic state.

        Uses clock_timestamp() for hypertable time column.
        Low frequency (~2Hz) so no batching needed.
        """
        sql = """
            INSERT INTO telemetry.session_timeline (
                timestamp, session_uid, session_time, overall_frame_identifier,
                session_time_left, total_laps, safety_car_status,
                weather_track_temp, weather_air_temp, weather_state
            ) VALUES (
                clock_timestamp(), %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        params = (
            session_uid,
            session_time,
            overall_frame_identifier,
            session_time_left,
            total_laps if total_laps >= 0 else None,
            safe_enum_name(SafetyCarStatus, safety_car_status, self._logger),
            weather_track_temp,
            weather_air_temp,
            safe_enum_name(WeatherIDs, weather_state, self._logger),
        )

        self._execute(sql, params, table_name=self.TABLE_NAME)
