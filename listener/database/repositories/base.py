"""Base repository class with error handling and JSONB helpers."""

import dataclasses
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from database.client import PostgresClient
from utils.bounded_dict import BoundedDict

# A write that fails once usually fails for every packet that follows it — a
# missing session row takes every child table down for the session's whole life.
# The first of each kind logs in full; the rest collapse into a count this often.
_FAILURE_SUMMARY_INTERVAL_S = 60.0


def safe_enum_name(enum_class: type, value: int, logger: Optional[logging.Logger] = None) -> str:
    """Return the enum member name for a value, or 'UNKNOWN_<value>' if not found."""
    try:
        return enum_class(value).name
    except ValueError:
        if logger:
            logger.warning("Unknown %s value: %d", enum_class.__name__, value)
        return f"UNKNOWN_{value}"


class RepositoryBase:
    """Base class for all database repositories."""

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        self._client = postgres_client
        self._logger = logger or logging.getLogger(__name__)
        # (table, exception type, sqlstate) -> [suppressed count, last logged at]
        self._logged_failures: BoundedDict[tuple, list] = BoundedDict(50)

    @property
    def enabled(self) -> bool:
        """Whether database writes are enabled."""
        return self._client.enabled

    def _log_write_failure(self, table_name: str, exc: Exception, batch: bool = False) -> None:
        """Log a failed write, collapsing repeats of the same failure into a count."""
        key = (table_name, type(exc).__name__, getattr(exc, "sqlstate", None))
        kind = "batch write" if batch else "write"
        now = time.monotonic()
        state = self._logged_failures.get(key)

        if state is None:
            self._logged_failures[key] = [0, now]
            self._logger.error(
                f"Database {kind} failed - {table_name}: {exc}",
                exc_info=True,
            )
            return

        state[0] += 1
        if now - state[1] < _FAILURE_SUMMARY_INTERVAL_S:
            return

        self._logger.error(
            "Database %s failed - %s: %s (%d more in the last %.0fs)",
            kind,
            table_name,
            exc,
            state[0],
            now - state[1],
        )
        self._logged_failures[key] = [0, now]

    def _execute(self, sql: str, params: Optional[tuple] = None, table_name: str = "unknown"):
        """
        Execute a single SQL statement with error handling.

        Logs errors and continues without raising exceptions (fire-and-forget).

        Returns:
            Number of rows affected, or 0 if disabled or failed.
        """
        if not self.enabled:
            return 0

        try:
            with self._client.connection() as conn:
                if conn is None:
                    return 0
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rowcount = cur.rowcount
                conn.commit()
                return rowcount
        except Exception as e:
            self._log_write_failure(table_name, e)
            return 0

    def _delete_frames_after(
        self,
        table: str,
        session_uid: str,
        session_time: float,
        session_start: Optional[datetime] = None,
    ) -> int:
        """
        Delete a frame hypertable's rows above a flashback's rewind point.

        session_time is the authoritative predicate, but it is not the
        partitioning column, so on its own it makes TimescaleDB open every chunk
        in the table. When session_start is known, the identical bound on
        `timestamp` goes in alongside it — frame rows are written at
        session_start + session_time — and chunk exclusion narrows the DELETE to
        the chunks this session occupies.
        """
        if session_start is not None:
            return self._execute(
                f"DELETE FROM {table} "
                "WHERE session_uid = %s AND session_time > %s AND timestamp > %s",
                (
                    session_uid,
                    session_time,
                    session_start + timedelta(seconds=session_time),
                ),
                table_name=table,
            )

        return self._execute(
            f"DELETE FROM {table} WHERE session_uid = %s AND session_time > %s",
            (session_uid, session_time),
            table_name=table,
        )

    def _execute_many(self, sql: str, params_list: list, table_name: str = "unknown"):
        """
        Execute a batch of SQL statements with error handling.

        Logs errors and continues without raising exceptions (fire-and-forget).
        """
        if not self.enabled or not params_list:
            return

        try:
            with self._client.connection() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.executemany(sql, params_list)
                conn.commit()
        except Exception as e:
            self._log_write_failure(table_name, e, batch=True)

    def _execute_many_strict(self, sql: str, params_list: list, table_name: str = "unknown"):
        """
        Execute a batch of SQL statements, propagating exceptions on failure.

        Unlike _execute_many, this raises on error so callers can handle failures
        (e.g., dead-letter queue).
        """
        if not params_list:
            return

        if not self.enabled:
            raise ConnectionError("Database writes are disabled")

        with self._client.connection() as conn:
            if conn is None:
                raise ConnectionError("No database connection available")
            with conn.cursor() as cur:
                cur.executemany(sql, params_list)
            conn.commit()

    def _to_jsonb(self, obj: Any) -> Optional[str]:
        """
        Convert a Python object to JSONB-compatible JSON string.

        Handles dataclasses, lists of dataclasses, dicts, and primitives.
        """
        if obj is None:
            return None

        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return json.dumps(dataclasses.asdict(obj))
        elif isinstance(obj, list):
            return json.dumps([
                dataclasses.asdict(item) if dataclasses.is_dataclass(item) and not isinstance(item, type) else item
                for item in obj
            ])
        else:
            return json.dumps(obj)
