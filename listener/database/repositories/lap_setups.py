"""Repository for lap-to-setup junction table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class LapSetupsRepository(RepositoryBase):
    TABLE_NAME = "telemetry.lap_setups"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_lap_setup(self, session_uid: str, user_id: int, lap_number: int, setup_id: int):
        """Link a completed lap to its active setup."""
        sql = """
            INSERT INTO telemetry.lap_setups (session_uid, user_id, lap_number, setup_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (session_uid, user_id, lap_number) DO NOTHING
        """
        self._execute(sql, (session_uid, user_id, lap_number, setup_id), table_name=self.TABLE_NAME)
