"""Repository for events_collisions table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsCollisionsRepository(RepositoryBase):
    """Manages events_collisions table — one row per collision."""

    TABLE_NAME = "telemetry.events_collisions"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        user1_id: int,
        user2_id: int,
    ):
        sql = """
            INSERT INTO telemetry.events_collisions (
                session_uid, overall_frame_identifier, session_time,
                user1_id, user2_id
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, user1_id) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time, user1_id, user2_id),
            table_name=self.TABLE_NAME,
        )
