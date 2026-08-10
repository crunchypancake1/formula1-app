"""Repository for per-lap tyre set snapshots."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class TyreSetsInventoryRepository(RepositoryBase):
    """Named TyreSetsInventoryRepository to avoid collision with TyreStintsRepository."""
    TABLE_NAME = "telemetry.tyre_sets"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_snapshot(self, rows: list[tuple]):
        """
        Insert a snapshot of available tyre sets for a driver on a lap.

        Each tuple: (session_uid, user_id, lap_number, actual_compound,
                     visual_compound, wear, life_span, usable_life,
                     lap_delta_time_ms, fitted)
        """
        sql = """
            INSERT INTO telemetry.tyre_sets (
                session_uid, user_id, lap_number,
                actual_compound, visual_compound, wear,
                life_span, usable_life, lap_delta_time_ms, fitted
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self._execute_many(sql, rows, table_name=self.TABLE_NAME)
