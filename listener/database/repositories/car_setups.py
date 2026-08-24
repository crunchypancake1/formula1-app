"""Repository for car setup library (deduplicated by hash + track)."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class CarSetupsRepository(RepositoryBase):
    TABLE_NAME = "telemetry.car_setups"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def upsert_setup(
        self,
        setup_hash: bytes,
        track_id: int,
        fields: tuple,
        user_id: int,
        session_uid: str,
    ) -> Optional[int]:
        """
        Insert a setup if the hash+track+user combo is new, otherwise return existing setup_id.

        Args:
            setup_hash: SHA-256 hash of all 23 setup values
            track_id: Track ID this setup was used on
            fields: Tuple of 23 setup values matching DB column order
            user_id: User ID this setup belongs to
            session_uid: Session UID where this setup was observed

        Returns:
            setup_id or None if DB write failed
        """
        if not self.enabled:
            return None
        sql = """
            INSERT INTO telemetry.car_setups (
                setup_hash, track_id, user_id, session_uid,
                front_wing, rear_wing, on_throttle, off_throttle,
                front_camber, rear_camber, front_toe, rear_toe,
                front_suspension, rear_suspension, front_anti_roll_bar, rear_anti_roll_bar,
                front_ride_height, rear_ride_height,
                brake_pressure, brake_bias, engine_braking,
                front_left_tyre_pressure, front_right_tyre_pressure,
                rear_left_tyre_pressure, rear_right_tyre_pressure,
                ballast, fuel_load
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (setup_hash, track_id, user_id) DO NOTHING
            RETURNING setup_id
        """
        try:
            with self._client.connection() as conn:
                if conn is None:
                    return None
                with conn.cursor() as cur:
                    cur.execute(sql, (setup_hash, track_id, user_id, session_uid) + fields)
                    row = cur.fetchone()
                    if row is None:
                        cur.execute(
                            "SELECT setup_id FROM telemetry.car_setups WHERE setup_hash = %s AND track_id = %s AND user_id = %s",
                            (setup_hash, track_id, user_id),
                        )
                        row = cur.fetchone()
                conn.commit()
                return row[0] if row else None
        except Exception as e:
            self._log_write_failure(self.TABLE_NAME, e)
            return None
