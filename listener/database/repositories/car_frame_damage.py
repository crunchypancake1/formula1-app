"""Repository for car_frame_damage (Packet 10 — Car Damage)."""

import logging
from datetime import datetime
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase
from database.repositories.car_frame import _build_insert_sql

CAR_FRAME_DAMAGE_COLUMNS: tuple[str, ...] = (
    "timestamp", "session_uid", "user_id", "session_time", "overall_frame_identifier",
    "tyres_wear_rl", "tyres_wear_rr", "tyres_wear_fl", "tyres_wear_fr",
    "tyres_damage_rl", "tyres_damage_rr", "tyres_damage_fl", "tyres_damage_fr",
    "brakes_damage_rl", "brakes_damage_rr", "brakes_damage_fl", "brakes_damage_fr",
    "tyre_blisters_rl", "tyre_blisters_rr", "tyre_blisters_fl", "tyre_blisters_fr",
    "front_left_wing_damage", "front_right_wing_damage", "rear_wing_damage",
    "floor_damage", "diffuser_damage", "sidepod_damage",
    "drs_fault", "ers_fault",
    "gearbox_damage", "engine_damage",
    "engine_mguh_wear", "engine_es_wear", "engine_ce_wear",
    "engine_ice_wear", "engine_mguk_wear", "engine_tc_wear",
    "engine_blown", "engine_seized",
)


class CarFrameDamageRepository(RepositoryBase):
    """Per-driver damage and wear per frame. No row is written for a Restricted driver."""

    TABLE_NAME = "telemetry.car_frame_damage"
    COLUMNS = CAR_FRAME_DAMAGE_COLUMNS

    _SQL = _build_insert_sql(
        "telemetry.car_frame_damage",
        CAR_FRAME_DAMAGE_COLUMNS,
        "timestamp, session_uid, user_id, overall_frame_identifier",
    )

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_batch(self, rows: list[tuple]):
        """Batch INSERT damage rows. Each tuple matches CAR_FRAME_DAMAGE_COLUMNS in order."""
        if not rows:
            return
        self._execute_many(self._SQL, rows, table_name=self.TABLE_NAME)

    def delete_after(
        self,
        session_uid: str,
        session_time: float,
        session_start: Optional[datetime] = None,
    ) -> int:
        """Discard rows recorded after a flashback's rewind point."""
        return self._delete_frames_after(
            self.TABLE_NAME, session_uid, session_time, session_start
        )
