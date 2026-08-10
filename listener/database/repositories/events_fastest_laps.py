"""Repository for events_fastest_laps table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsFastestLapsRepository(RepositoryBase):
    """Manages events_fastest_laps table — one row per fastest lap."""

    TABLE_NAME = "telemetry.events_fastest_laps"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        user_id: int,
        lap_time: float,
    ):
        sql = """
            INSERT INTO telemetry.events_fastest_laps (
                session_uid, overall_frame_identifier, session_time,
                user_id, lap_time
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, user_id) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time, user_id, lap_time),
            table_name=self.TABLE_NAME,
        )
