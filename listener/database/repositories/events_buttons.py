"""Repository for events_buttons (Event packet, code BUTN)."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsButtonsRepository(RepositoryBase):
    """Local player's controller state, one row per change the game reports."""

    TABLE_NAME = "telemetry.events_buttons"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        button_status: int,
        buttons_pressed: list[str],
    ):
        sql = """
            INSERT INTO telemetry.events_buttons (
                session_uid, overall_frame_identifier, session_time,
                button_status, buttons_pressed
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time, button_status, buttons_pressed),
            table_name=self.TABLE_NAME,
        )
