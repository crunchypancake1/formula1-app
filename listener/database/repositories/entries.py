"""Repository for entries table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase, safe_enum_name
from enums import Nationalities


class EntriesRepository(RepositoryBase):
    """Manages entries table - driver roster (22 entries per session)."""

    TABLE_NAME = "telemetry.entries"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def find_weekend_driver_name(self, session_uid: str, team_id: int, race_number: int) -> str | None:
        """Look up driver_name by team_id + race_number in another session of the same weekend."""
        if not self.enabled:
            return None
        try:
            with self._client.connection() as conn:
                if conn is None:
                    return None
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT u.driver_name
                        FROM telemetry.entries e
                        JOIN telemetry.sessions s ON s.session_uid = e.session_uid
                        JOIN identity.users u ON u.id = e.user_id
                        WHERE s.weekend_link = (
                            SELECT weekend_link FROM telemetry.sessions WHERE session_uid = %s
                        )
                        AND e.team_id = %s
                        AND e.race_number = %s
                        AND e.session_uid != %s
                        LIMIT 1
                        """,
                        (session_uid, team_id, race_number, session_uid),
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            self._logger.error(f"Failed weekend driver lookup: {e}", exc_info=True)
            return None

    def max_player_number(self) -> int:
        """Return the highest N from existing 'Player N' driver names, or 0."""
        if not self.enabled:
            return 0
        try:
            with self._client.connection() as conn:
                if conn is None:
                    return 0
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COALESCE(MAX(CAST(SUBSTRING(driver_name FROM 'Player (\\d+)') AS INTEGER)), 0) "
                        "FROM identity.users WHERE driver_name ~ '^Player \\d+$'"
                    )
                    return cur.fetchone()[0]
        except Exception as e:
            self._logger.error(f"Failed to query max player number: {e}", exc_info=True)
            return 0

    def _resolve_user_ids(self, entries: list) -> dict[str, int]:
        """
        Resolve driver names to user IDs using identity.get_or_create_driver().

        Exact case-insensitive match, or create new user if not found.

        Returns:
            Mapping of driver_name -> user_id
        """
        if not entries or not self.enabled:
            return {}

        unique_names = set(entry["driver_name"] for entry in entries)

        user_id_map = {}
        try:
            with self._client.connection() as conn:
                if conn is None:
                    return {}
                with conn.cursor() as cur:
                    for name in unique_names:
                        cur.execute(
                            "SELECT identity.get_or_create_driver(%s)",
                            (name,),
                        )
                        result = cur.fetchone()
                        if result:
                            user_id_map[name] = result[0]
                conn.commit()
        except Exception as e:
            self._logger.error(
                f"Failed to resolve user IDs: {e}",
                exc_info=True,
            )
            return {}

        return user_id_map

    def insert_entries_batch(self, entries: list) -> dict[int, int]:
        """
        Insert multiple entries in a batch. Returns car_index -> user_id map.

        PK is (session_uid, user_id), with unique constraint on (session_uid, car_index).
        """
        if not entries:
            return {}

        for entry in entries:
            entry["driver_name"] = entry["driver_name"].replace("\x00", "")

        user_id_map = self._resolve_user_ids(entries)

        sql = """
            INSERT INTO telemetry.entries (
                session_uid, user_id, car_index,
                team_id, race_number,
                telemetry_setting,
                livery_colors
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (session_uid, car_index) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                team_id = EXCLUDED.team_id,
                race_number = EXCLUDED.race_number,
                telemetry_setting = EXCLUDED.telemetry_setting,
                livery_colors = EXCLUDED.livery_colors
        """

        car_index_to_user_id = {}
        nationality_updates: list[tuple] = []
        params_list = []
        for entry in entries:
            user_id = user_id_map.get(entry["driver_name"])
            if user_id is None:
                self._logger.warning(
                    "Skipping entry for '%s' (car_index=%d) - user_id resolution failed",
                    entry["driver_name"], entry["car_index"],
                )
                continue
            car_index_to_user_id[entry["car_index"]] = user_id
            nationality = safe_enum_name(Nationalities, entry["nationality"], self._logger)
            if nationality is not None:
                nationality_updates.append((nationality, user_id))
            params_list.append((
                entry["session_uid"],
                user_id,
                entry["car_index"],
                entry["team_id"],
                entry["race_number"],
                entry["telemetry_setting"],
                entry["livery_colors"],
            ))

        self._execute_many(sql, params_list, table_name=self.TABLE_NAME)

        if nationality_updates:
            nationality_sql = (
                "UPDATE identity.users SET nationality = %s WHERE id = %s AND nationality IS NULL"
            )
            self._execute_many(nationality_sql, nationality_updates, table_name="identity.users")

        return car_index_to_user_id
