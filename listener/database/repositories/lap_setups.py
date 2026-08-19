"""Repository for lap-to-setup junction table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class LapSetupsRepository(RepositoryBase):
    TABLE_NAME = "telemetry.lap_setups"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_lap_setup(
        self,
        session_uid: str,
        user_id: int,
        lap_number: int,
        setup_id: int,
        next_front_wing_value: Optional[float] = None,
    ):
        """Link a completed lap to the setup it was driven on."""
        sql = """
            INSERT INTO telemetry.lap_setups (
                session_uid, user_id, lap_number, setup_id, next_front_wing_value
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, user_id, lap_number) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, user_id, lap_number, setup_id, next_front_wing_value),
            table_name=self.TABLE_NAME,
        )
