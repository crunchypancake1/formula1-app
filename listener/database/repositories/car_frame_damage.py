"""Repository for car_frame_damage table (Packet 10 — Car Damage)."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class CarFrameDamageRepository(RepositoryBase):
    """Manages car_frame_damage hypertable — per-driver damage and wear data per frame."""

    TABLE_NAME = "telemetry.car_frame_damage"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_batch(self, rows: list[tuple]):
        """
        Batch INSERT damage rows (up to 22 per frame).

        Each tuple: (session_uid, user_id, session_time, overall_frame_identifier,
                      tyres_wear (4), tyres_damage (4), brakes_damage (4), tyre_blisters (4),
                      wing/floor/diffuser/sidepod damage (6), drs/ers fault (2),
                      gearbox/engine damage (2), engine wear (6), engine_blown/seized (2))
        """
        if not rows:
            return

        sql = """
            INSERT INTO telemetry.car_frame_damage (
                timestamp, session_uid, user_id, session_time,
                overall_frame_identifier,
                tyres_wear_rl, tyres_wear_rr, tyres_wear_fl, tyres_wear_fr,
                tyres_damage_rl, tyres_damage_rr, tyres_damage_fl, tyres_damage_fr,
                brakes_damage_rl, brakes_damage_rr, brakes_damage_fl, brakes_damage_fr,
                tyre_blisters_rl, tyre_blisters_rr, tyre_blisters_fl, tyre_blisters_fr,
                front_left_wing_damage, front_right_wing_damage, rear_wing_damage,
                floor_damage, diffuser_damage, sidepod_damage,
                drs_fault, ers_fault,
                gearbox_damage, engine_damage,
                engine_mguh_wear, engine_es_wear, engine_ce_wear,
                engine_ice_wear, engine_mguk_wear, engine_tc_wear,
                engine_blown, engine_seized
            ) VALUES (
                clock_timestamp(), %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (timestamp, session_uid, user_id) DO NOTHING
        """
        self._execute_many(sql, rows, table_name=self.TABLE_NAME)
