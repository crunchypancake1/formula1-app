"""Repository for events_flashbacks (Event packet, code FLBK)."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsFlashbacksRepository(RepositoryBase):
    """Records each flashback and how much recorded telemetry it invalidated."""

    TABLE_NAME = "telemetry.events_flashbacks"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        session_time: float,
        flashback_frame_identifier: int,
        flashback_session_time: float,
        rows_discarded: Optional[int] = None,
    ):
        sql = """
            INSERT INTO telemetry.events_flashbacks (
                session_uid, overall_frame_identifier, session_time,
                flashback_frame_identifier, flashback_session_time, rows_discarded
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, session_time,
             flashback_frame_identifier, flashback_session_time, rows_discarded),
            table_name=self.TABLE_NAME,
        )
