"""Repository for events_overtakes table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsOvertakesRepository(RepositoryBase):
    """Manages events_overtakes table — one row per overtake."""

    TABLE_NAME = "telemetry.events_overtakes"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        overtaking_user_id: int,
        overtaken_user_id: int,
    ):
        sql = """
            INSERT INTO telemetry.events_overtakes (
                session_uid, overall_frame_identifier, session_time,
                overtaking_user_id, overtaken_user_id
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, overtaking_user_id) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time,
             overtaking_user_id, overtaken_user_id),
            table_name=self.TABLE_NAME,
        )
