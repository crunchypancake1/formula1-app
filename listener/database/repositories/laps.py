"""Repository for laps table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class LapsRepository(RepositoryBase):
    """Manages laps table - authoritative lap records with sectors and validity."""

    TABLE_NAME = "telemetry.laps"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def upsert_laps_batch(self, laps: list):
        """
        Batch upsert multiple lap records.

        Each lap should be a tuple of
        (session_uid, user_id, lap_number, lap_time_ms,
         sector1_time_ms, sector2_time_ms, sector3_time_ms,
         is_valid, sector1_valid, sector2_valid, sector3_valid).
        """
        if not laps:
            return

        sql = """
            INSERT INTO telemetry.laps (
                session_uid, user_id, lap_number,
                lap_time_ms, sector1_time_ms, sector2_time_ms, sector3_time_ms,
                is_valid, sector1_valid, sector2_valid, sector3_valid
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (session_uid, user_id, lap_number)
            DO UPDATE SET
                lap_time_ms = EXCLUDED.lap_time_ms,
                sector1_time_ms = EXCLUDED.sector1_time_ms,
                sector2_time_ms = EXCLUDED.sector2_time_ms,
                sector3_time_ms = EXCLUDED.sector3_time_ms,
                is_valid = EXCLUDED.is_valid,
                sector1_valid = EXCLUDED.sector1_valid,
                sector2_valid = EXCLUDED.sector2_valid,
                sector3_valid = EXCLUDED.sector3_valid
        """

        self._execute_many(sql, laps, table_name=self.TABLE_NAME)
