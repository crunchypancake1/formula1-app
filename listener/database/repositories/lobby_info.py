"""Repository for lobby_info table."""

import json
import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class LobbyInfoRepository(RepositoryBase):
    """Manages telemetry.lobby_info table — lobby player snapshots."""

    TABLE_NAME = "telemetry.lobby_info"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def upsert(
        self,
        session_uid: str,
        players: list[dict],
        num_players: int,
    ):
        sql = """
            INSERT INTO telemetry.lobby_info (
                session_uid, num_players, players
            ) VALUES (%s, %s, %s)
            ON CONFLICT (session_uid) DO UPDATE SET
                num_players = EXCLUDED.num_players,
                players = EXCLUDED.players,
                updated_at = NOW()
        """
        self._execute(
            sql,
            (session_uid, num_players, json.dumps(players)),
            table_name=self.TABLE_NAME,
        )
