"""Repository for car_frame hypertable."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class CarFrameRepository(RepositoryBase):
    """Manages car_frame hypertable — combined Motion + Telemetry + Lap Data + Car Status + Car Damage per frame."""

    TABLE_NAME = "telemetry.car_frame"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert_batch(self, rows: list[tuple]):
        """
        Batch INSERT combined frame rows (up to 22 per frame).

        Each tuple: (session_uid, user_id, session_time, overall_frame_identifier,
                      world_pos_x..roll (12 motion fields),
                      speed..engine_temperature (9 telemetry scalars),
                      brakes_temp_rl..fr (4), tyres_surface_temp_rl..fr (4), tyres_inner_temp_rl..fr (4),
                      tyres_pressure_rl..fr (4), surface_type_rl..fr (4) (20 per-wheel telemetry fields),
                      current_lap_num..position (4 lap scalars),
                      sector..result_status (4 lap enums),
                      gap/pit fields (10 new lap data fields),
                      pit_limiter..network_paused (8 car status),
                      front_brake_bias..ers_harvest_limit_per_lap (7 ERS/fuel/brake-bias),
                      active_aero_mode..driving_wrong_way (8 Car Telemetry 2 / packet 16 fields))
        """
        if not rows:
            return

        sql = """
            INSERT INTO telemetry.car_frame (
                timestamp, session_uid, user_id, session_time,
                overall_frame_identifier,
                -- Motion
                world_pos_x, world_pos_y, world_pos_z,
                world_velocity_x, world_velocity_y, world_velocity_z,
                g_force_lateral, g_force_longitudinal, g_force_vertical,
                yaw, pitch, roll,
                -- Telemetry scalars
                speed, throttle, steer, brake,
                clutch, gear, engine_rpm, drs, engine_temperature,
                -- Telemetry per-wheel temps
                brakes_temp_rl, brakes_temp_rr, brakes_temp_fl, brakes_temp_fr,
                tyres_surface_temp_rl, tyres_surface_temp_rr, tyres_surface_temp_fl, tyres_surface_temp_fr,
                tyres_inner_temp_rl, tyres_inner_temp_rr, tyres_inner_temp_fl, tyres_inner_temp_fr,
                tyres_pressure_rl, tyres_pressure_rr, tyres_pressure_fl, tyres_pressure_fr,
                -- Telemetry per-wheel surface type
                surface_type_rl, surface_type_rr, surface_type_fl, surface_type_fr,
                -- Lap Data scalars
                current_lap_num, lap_distance, current_lap_time_ms,
                position,
                -- Lap Data enums
                sector, pit_status, driver_status, result_status,
                -- Lap Data gaps and pit timing
                gap_to_leader_ms, gap_to_car_ahead_ms, gap_to_car_behind_ms,
                total_distance, safety_car_delta, num_pit_stops,
                pit_lane_timer_active, pit_lane_time_ms, pit_stop_time_ms,
                pit_stop_should_serve_pen,
                -- Car Status
                pit_limiter, drs_allowed, drs_activation_distance,
                actual_tyre_compound, visual_tyre_compound, tyres_age_laps,
                vehicle_fia_flags, network_paused,
                -- Car Status: ERS/fuel/brake-bias (restricted-null per Part 2.2)
                front_brake_bias, fuel_in_tank, fuel_remaining_laps,
                ers_store_energy, ers_deploy_mode, ers_deployed_this_lap,
                ers_harvest_limit_per_lap,
                -- Car Telemetry 2 / Packet 16 (2026 Season Pack)
                active_aero_mode, active_aero_available, active_aero_activation_distance,
                overtake_available, overtake_active, overtake_activation_distance,
                is_2026_regulations, driving_wrong_way
            ) VALUES (
                clock_timestamp(), %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (timestamp, session_uid, user_id) DO NOTHING
        """

        self._execute_many(sql, rows, table_name=self.TABLE_NAME)
