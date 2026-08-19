"""Repository for session_bests (Session History packet, Packet 11)."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class SessionBestsRepository(RepositoryBase):
    """Which lap each of a driver's session bests was set on."""

    TABLE_NAME = "telemetry.session_bests"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def upsert(self, row: tuple):
        """
        Upsert one driver's session bests.

        Tuple order: (session_uid, user_id, best_lap_num, best_sector1_lap_num,
        best_sector2_lap_num, best_sector3_lap_num).
        """
        sql = """
            INSERT INTO telemetry.session_bests (
                session_uid, user_id, best_lap_num,
                best_sector1_lap_num, best_sector2_lap_num, best_sector3_lap_num
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, user_id) DO UPDATE SET
                best_lap_num = EXCLUDED.best_lap_num,
                best_sector1_lap_num = EXCLUDED.best_sector1_lap_num,
                best_sector2_lap_num = EXCLUDED.best_sector2_lap_num,
                best_sector3_lap_num = EXCLUDED.best_sector3_lap_num,
                updated_at = NOW()
        """
        self._execute(sql, row, table_name=self.TABLE_NAME)
