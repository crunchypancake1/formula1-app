"""Repository for classification tables (race and qualifying)."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase, safe_enum_name
from enums import ResultReason, ResultStatus


class FinalClassificationRepository(RepositoryBase):
    """Manages race_classification and qualifying_classification tables."""

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_race_classification_batch(self, classifications: list):
        """
        Insert multiple race classification records in a batch.

        Each classification should be a dict with user_id and all required race-specific fields.
        """
        if not classifications:
            return

        sql = """
            INSERT INTO telemetry.race_classification (
                session_uid, user_id, position, num_laps, grid_position,
                num_pit_stops, result_status, result_reason,
                best_lap_time_ms, total_race_time, penalties_time,
                num_penalties, num_tyre_stints,
                tyre_stints_actual, tyre_stints_visual, tyre_stints_end_laps
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (session_uid, user_id) DO UPDATE SET
                position = EXCLUDED.position,
                num_laps = EXCLUDED.num_laps,
                grid_position = EXCLUDED.grid_position,
                num_pit_stops = EXCLUDED.num_pit_stops,
                result_status = EXCLUDED.result_status,
                result_reason = EXCLUDED.result_reason,
                best_lap_time_ms = EXCLUDED.best_lap_time_ms,
                total_race_time = EXCLUDED.total_race_time,
                penalties_time = EXCLUDED.penalties_time,
                num_penalties = EXCLUDED.num_penalties,
                num_tyre_stints = EXCLUDED.num_tyre_stints,
                tyre_stints_actual = EXCLUDED.tyre_stints_actual,
                tyre_stints_visual = EXCLUDED.tyre_stints_visual,
                tyre_stints_end_laps = EXCLUDED.tyre_stints_end_laps
        """

        params_list = [
            (
                c["session_uid"],
                c["user_id"],
                c["position"],
                c["num_laps"],
                c["grid_position"],
                c["num_pit_stops"],
                safe_enum_name(ResultStatus, c["result_status"], self._logger),
                safe_enum_name(ResultReason, c["result_reason"], self._logger) if c.get("result_reason") is not None else None,
                c["best_lap_time_ms"],
                c["total_race_time"],
                c["penalties_time"],
                c["num_penalties"],
                c["num_tyre_stints"],
                c["tyre_stints_actual"],
                c["tyre_stints_visual"],
                c["tyre_stints_end_laps"],
            )
            for c in classifications
        ]

        self._execute_many_strict(sql, params_list, table_name="telemetry.race_classification")

    def insert_qualifying_classification_batch(self, classifications: list):
        """
        Insert multiple qualifying classification records in a batch.

        Each classification should be a dict with user_id and qualifying-specific fields.
        """
        if not classifications:
            return

        sql = """
            INSERT INTO telemetry.qualifying_classification (
                session_uid, user_id, position, num_laps,
                best_lap_time_ms, result_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (session_uid, user_id) DO UPDATE SET
                position = EXCLUDED.position,
                num_laps = EXCLUDED.num_laps,
                best_lap_time_ms = EXCLUDED.best_lap_time_ms,
                result_status = EXCLUDED.result_status
        """

        params_list = [
            (
                c["session_uid"],
                c["user_id"],
                c["position"],
                c["num_laps"],
                c["best_lap_time_ms"],
                safe_enum_name(ResultStatus, c["result_status"], self._logger),
            )
            for c in classifications
        ]

        self._execute_many_strict(sql, params_list, table_name="telemetry.qualifying_classification")
