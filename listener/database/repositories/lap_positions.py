"""Repository for lap_positions table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class LapPositionsRepository(RepositoryBase):
    """Manages lap_positions table - position grid at lap start."""

    TABLE_NAME = "telemetry.lap_positions"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def upsert_lap_positions(
        self,
        session_uid: str,
        lap_number: int,
        positions: list,
    ):
        """
        Upsert lap positions record.

        Composite key (session_uid, lap_number). Handles multi-packet sessions.
        """
        sql = """
            INSERT INTO telemetry.lap_positions (
                session_uid, lap_number, positions
            ) VALUES (
                %s, %s, %s
            )
            ON CONFLICT (session_uid, lap_number)
            DO UPDATE SET
                positions = EXCLUDED.positions
        """

        params = (
            session_uid,
            lap_number,
            positions,
        )

        self._execute(sql, params, table_name=self.TABLE_NAME)
