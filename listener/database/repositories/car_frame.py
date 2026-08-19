"""Repository for the car_frame hypertable."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase

# Column order for an inserted car_frame row. The service builds its tuples
# against this list and looks up field positions by name (see COLUMN_INDEX), so
# adding or reordering a column here is the only change needed — nothing
# depends on a hand-counted offset.
CAR_FRAME_COLUMNS: tuple[str, ...] = (
    # Meta
    "timestamp", "session_uid", "user_id", "session_time", "overall_frame_identifier",
    # Motion / Packet 0
    "world_pos_x", "world_pos_y", "world_pos_z",
    "world_velocity_x", "world_velocity_y", "world_velocity_z",
    "world_forward_dir_x", "world_forward_dir_y", "world_forward_dir_z",
    "world_right_dir_x", "world_right_dir_y", "world_right_dir_z",
    "g_force_lateral", "g_force_longitudinal", "g_force_vertical",
    "yaw", "pitch", "roll",
    # Car Telemetry / Packet 6 — scalars
    "speed", "throttle", "steer", "brake", "clutch", "gear",
    "engine_rpm", "drs", "rev_lights_percent", "rev_lights_bit_value",
    "engine_temperature",
    # Car Telemetry / Packet 6 — per wheel (RL, RR, FL, FR)
    "brakes_temp_rl", "brakes_temp_rr", "brakes_temp_fl", "brakes_temp_fr",
    "tyres_surface_temp_rl", "tyres_surface_temp_rr", "tyres_surface_temp_fl", "tyres_surface_temp_fr",
    "tyres_inner_temp_rl", "tyres_inner_temp_rr", "tyres_inner_temp_fl", "tyres_inner_temp_fr",
    "tyres_pressure_rl", "tyres_pressure_rr", "tyres_pressure_fl", "tyres_pressure_fr",
    "surface_type_rl", "surface_type_rr", "surface_type_fl", "surface_type_fr",
    # Packet 6 packet-level, player car only
    "mfd_panel_index", "mfd_panel_index_secondary_player", "suggested_gear",
    # Lap Data / Packet 2
    "last_lap_time_ms", "current_lap_time_ms", "sector1_time_ms", "sector2_time_ms",
    "lap_distance", "total_distance", "safety_car_delta",
    "position", "grid_position", "current_lap_num",
    "sector", "pit_status", "driver_status", "result_status", "current_lap_invalid",
    "gap_to_leader_ms", "gap_to_car_ahead_ms", "gap_to_car_behind_ms",
    "num_pit_stops", "pit_lane_timer_active", "pit_lane_time_ms",
    "pit_stop_time_ms", "pit_stop_should_serve_pen",
    "penalties_seconds", "total_warnings", "corner_cutting_warnings",
    "num_unserved_drive_through_pens", "num_unserved_stop_go_pens",
    "speed_trap_fastest_speed", "speed_trap_fastest_lap",
    # Car Status / Packet 7 — never restricted
    "pit_limiter", "drs_allowed", "drs_activation_distance",
    "actual_tyre_compound", "visual_tyre_compound", "tyres_age_laps",
    "vehicle_fia_flags", "network_paused",
    "traction_control", "anti_lock_brakes", "max_rpm", "idle_rpm", "max_gears",
    # Car Status / Packet 7 — restricted (NULL for a Restricted driver)
    "front_brake_bias", "fuel_mix", "fuel_in_tank", "fuel_capacity",
    "fuel_remaining_laps", "ers_store_energy", "ers_deploy_mode",
    "ers_deployed_this_lap", "ers_harvest_limit_per_lap",
    "ers_harvested_this_lap_mguk", "ers_harvested_this_lap_mguh",
    "engine_power_ice", "engine_power_mguk",
    # Car Telemetry 2 / Packet 16
    "active_aero_mode", "active_aero_available", "active_aero_activation_distance",
    "overtake_available", "overtake_active", "overtake_activation_distance",
    "is_2026_regulations", "driving_wrong_way",
)

COLUMN_INDEX: dict[str, int] = {name: i for i, name in enumerate(CAR_FRAME_COLUMNS)}


def _build_insert_sql(table: str, columns: tuple[str, ...], conflict: str) -> str:
    placeholders = ", ".join(["%s"] * len(columns))
    return (
        f"INSERT INTO {table} ({', '.join(columns)})\n"
        f"VALUES ({placeholders})\n"
        f"ON CONFLICT ({conflict}) DO NOTHING"
    )


class CarFrameRepository(RepositoryBase):
    """Combined Motion + Lap Data + Car Telemetry + Car Status + Car Telemetry 2 per frame."""

    TABLE_NAME = "telemetry.car_frame"
    COLUMNS = CAR_FRAME_COLUMNS

    _SQL = _build_insert_sql(
        "telemetry.car_frame",
        CAR_FRAME_COLUMNS,
        "timestamp, session_uid, user_id, overall_frame_identifier",
    )

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_batch(self, rows: list[tuple]):
        """
        Batch INSERT combined frame rows — up to MAX_CARS per frame.

        Each tuple must match CAR_FRAME_COLUMNS exactly, in order.
        """
        if not rows:
            return
        self._execute_many(self._SQL, rows, table_name=self.TABLE_NAME)

    def delete_after(self, session_uid: str, session_time: float) -> int:
        """
        Discard rows recorded after a flashback's rewind point.

        A flashback undoes everything the driver did past flashback_session_time,
        so those frames describe a run that no longer happened.
        """
        return self._execute(
            "DELETE FROM telemetry.car_frame WHERE session_uid = %s AND session_time > %s",
            (session_uid, session_time),
            table_name=self.TABLE_NAME,
        )
