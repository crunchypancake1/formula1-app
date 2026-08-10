"""Repository for events_penalties table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsPenaltiesRepository(RepositoryBase):
    """Manages events_penalties table — one row per penalty."""

    TABLE_NAME = "telemetry.events_penalties"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        user_id: int,
        other_user_id: Optional[int],
        penalty_type: str,
        infringement_type: str,
        time_seconds: Optional[int] = None,
        lap_num: Optional[int] = None,
        places_gained: Optional[int] = None,
    ):
        sql = """
            INSERT INTO telemetry.events_penalties (
                session_uid, overall_frame_identifier, session_time,
                user_id, other_user_id, penalty_type, infringement_type,
                time_seconds, lap_num, places_gained
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, user_id) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time,
             user_id, other_user_id, penalty_type, infringement_type,
             time_seconds, lap_num, places_gained),
            table_name=self.TABLE_NAME,
        )
