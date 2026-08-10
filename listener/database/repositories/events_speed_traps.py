"""Repository for events_speed_traps table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsSpeedTrapsRepository(RepositoryBase):
    """Manages events_speed_traps table — one row per speed trap trigger."""

    TABLE_NAME = "telemetry.events_speed_traps"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        user_id: int,
        speed: float,
        is_overall_fastest: bool,
        is_driver_fastest: bool,
        fastest_user_id: Optional[int] = None,
        fastest_speed: Optional[float] = None,
    ):
        sql = """
            INSERT INTO telemetry.events_speed_traps (
                session_uid, overall_frame_identifier, session_time,
                user_id, speed, is_overall_fastest, is_driver_fastest,
                fastest_user_id, fastest_speed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, user_id) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time,
             user_id, speed, is_overall_fastest, is_driver_fastest,
             fastest_user_id, fastest_speed),
            table_name=self.TABLE_NAME,
        )
