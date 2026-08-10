"""Repository for events_driver_actions table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsDriverActionsRepository(RepositoryBase):
    """Manages events_driver_actions table — simple single-driver events."""

    TABLE_NAME = "telemetry.events_driver_actions"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        event_code: str,
        session_time: float,
        user_id: int,
        stop_time: Optional[float] = None,
    ):
        sql = """
            INSERT INTO telemetry.events_driver_actions (
                session_uid, overall_frame_identifier, event_code,
                session_time, user_id, stop_time
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, event_code) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, event_code,
             session_time, user_id, stop_time),
            table_name=self.TABLE_NAME,
        )
