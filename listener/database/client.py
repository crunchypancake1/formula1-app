"""PostgreSQL connection pool client with graceful degradation."""

import logging
from contextlib import contextmanager
from typing import Any, Optional

try:
    from psycopg_pool import ConnectionPool
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    ConnectionPool = None  # type: ignore[assignment,misc]


class PostgresClient:
    """PostgreSQL connection pool with graceful degradation on connection failure."""

    def __init__(
        self,
        connection_string: str,
        pool_min: int = 10,
        pool_max: int = 20,
        logger: Optional[logging.Logger] = None,
    ):
        self._logger = logger or logging.getLogger(__name__)
        self._enabled = False
        self._pool: Optional[Any] = None

        if not PSYCOPG_AVAILABLE or ConnectionPool is None:
            self._logger.warning(
                "psycopg[pool] not installed; PostgreSQL writes disabled"
            )
            return

        # Attempt to create connection pool with health check
        try:
            self._logger.info(
                f"Initializing PostgreSQL connection pool "
                f"(min={pool_min}, max={pool_max})"
            )
            self._pool = ConnectionPool(
                connection_string,
                min_size=pool_min,
                max_size=pool_max,
                timeout=5.0,
                # Every frame is its own small transaction, so an fsync per
                # commit is the listener's throughput ceiling — it blocks the
                # packet handler and the socket sheds datagrams behind it. The
                # trade is the last fraction of a second of frames on an OS
                # crash; the game resends its state continuously, so the next
                # packet restores it. Passed at connect time rather than as a
                # SET, which a rollback would revert.
                kwargs={"options": "-c synchronous_commit=off"},
            )

            # Test connection
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()

            self._enabled = True
            self._logger.info("PostgreSQL connection pool initialized successfully")

        except Exception as e:
            self._enabled = False
            self._logger.warning(
                f"PostgreSQL connection failed: {e}. "
                "Telemetry listener will continue running but data will not be persisted.",
                exc_info=True,
            )

    @property
    def enabled(self) -> bool:
        """Whether the database connection is available."""
        return self._enabled

    @contextmanager
    def connection(self):
        """
        Get a connection from the pool.

        Yields None if database is not enabled, otherwise yields a psycopg connection.
        """
        if not self._enabled or self._pool is None:
            yield None
            return

        with self._pool.connection() as conn:
            yield conn

    def close(self):
        """Close the connection pool."""
        if self._pool is not None:
            self._logger.info("Closing PostgreSQL connection pool")
            self._pool.close()
            self._enabled = False
