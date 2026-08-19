"""Repository for the session_timeline hypertable."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase
from database.repositories.car_frame import _build_insert_sql

SESSION_TIMELINE_COLUMNS: tuple[str, ...] = (
    "timestamp", "session_uid", "session_time", "overall_frame_identifier",
    "session_time_left", "total_laps",
    "weather_state", "weather_track_temp", "weather_air_temp",
    "safety_car_status", "marshal_zone_flags",
    "num_safety_car_periods", "num_virtual_safety_car_periods", "num_red_flag_periods",
    "game_paused", "is_spectating", "spectator_car_index",
    "pit_stop_window_ideal_lap", "pit_stop_window_latest_lap", "pit_stop_rejoin_position",
)


class SessionTimelineRepository(RepositoryBase):
    """Live session state, sampled once per Session packet (~2Hz)."""

    TABLE_NAME = "telemetry.session_timeline"
    COLUMNS = SESSION_TIMELINE_COLUMNS

    _SQL = _build_insert_sql(
        "telemetry.session_timeline",
        SESSION_TIMELINE_COLUMNS,
        "timestamp, session_uid",
    )

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_timeline_entry(self, row: tuple):
        """Insert one timeline sample. The tuple matches SESSION_TIMELINE_COLUMNS in order."""
        self._execute(self._SQL, row, table_name=self.TABLE_NAME)
