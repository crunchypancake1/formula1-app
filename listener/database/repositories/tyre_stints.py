"""Repository for tyre_stints table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class TyreStintsRepository(RepositoryBase):
    """Manages tyre_stints table — stint history from Session History packets."""

    TABLE_NAME = "telemetry.tyre_stints"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def upsert_stints_batch(self, stints: list[tuple]):
        """
        Batch upsert tyre stint records.

        Each stint tuple: (session_uid, user_id, stint_number, end_lap,
                          actual_compound, visual_compound)
        """
        if not stints:
            return

        sql = """
            INSERT INTO telemetry.tyre_stints (
                session_uid, user_id, stint_number,
                end_lap, actual_compound, visual_compound
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (session_uid, user_id, stint_number)
            DO UPDATE SET
                end_lap = EXCLUDED.end_lap,
                actual_compound = EXCLUDED.actual_compound,
                visual_compound = EXCLUDED.visual_compound
        """

        self._execute_many(sql, stints, table_name=self.TABLE_NAME)
