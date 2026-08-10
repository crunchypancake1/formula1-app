"""Repository for events_retirements table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsRetirementsRepository(RepositoryBase):
    """Manages events_retirements table — one row per retirement."""

    TABLE_NAME = "telemetry.events_retirements"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        user_id: int,
        reason: str,
    ):
        sql = """
            INSERT INTO telemetry.events_retirements (
                session_uid, overall_frame_identifier, session_time,
                user_id, reason
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, user_id) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time, user_id, reason),
            table_name=self.TABLE_NAME,
        )
