"""Repository for car_frame_motion_ex table (Packet 13 — Motion Ex, player only)."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class CarFrameMotionExRepository(RepositoryBase):
    """Manages car_frame_motion_ex hypertable — player-car extended motion data per frame."""

    TABLE_NAME = "telemetry.car_frame_motion_ex"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(self, row: tuple):
        """
        INSERT a single motion_ex row (player car only — one row per frame).

        Each tuple: (session_uid, user_id, session_time, overall_frame_identifier,
                      suspension_position (4), suspension_velocity (4), suspension_acceleration (4),
                      wheel_speed (4), wheel_slip_ratio (4), wheel_slip_angle (4),
                      wheel_lat_force (4), wheel_long_force (4), wheel_vert_force (4),
                      wheel_camber (4), wheel_camber_gain (4),
                      height_of_cog, local_velocity (3), angular_velocity (3),
                      angular_acceleration (3), front_wheels_angle,
                      front/rear_aero_height, front/rear_roll_angle, chassis_yaw/pitch)
        """
        sql = """
            INSERT INTO telemetry.car_frame_motion_ex (
                timestamp, session_uid, user_id, session_time,
                overall_frame_identifier,
                suspension_position_rl, suspension_position_rr,
                suspension_position_fl, suspension_position_fr,
                suspension_velocity_rl, suspension_velocity_rr,
                suspension_velocity_fl, suspension_velocity_fr,
                suspension_acceleration_rl, suspension_acceleration_rr,
                suspension_acceleration_fl, suspension_acceleration_fr,
                wheel_speed_rl, wheel_speed_rr, wheel_speed_fl, wheel_speed_fr,
                wheel_slip_ratio_rl, wheel_slip_ratio_rr,
                wheel_slip_ratio_fl, wheel_slip_ratio_fr,
                wheel_slip_angle_rl, wheel_slip_angle_rr,
                wheel_slip_angle_fl, wheel_slip_angle_fr,
                wheel_lat_force_rl, wheel_lat_force_rr,
                wheel_lat_force_fl, wheel_lat_force_fr,
                wheel_long_force_rl, wheel_long_force_rr,
                wheel_long_force_fl, wheel_long_force_fr,
                wheel_vert_force_rl, wheel_vert_force_rr,
                wheel_vert_force_fl, wheel_vert_force_fr,
                wheel_camber_rl, wheel_camber_rr,
                wheel_camber_fl, wheel_camber_fr,
                wheel_camber_gain_rl, wheel_camber_gain_rr,
                wheel_camber_gain_fl, wheel_camber_gain_fr,
                height_of_cog_above_ground,
                local_velocity_x, local_velocity_y, local_velocity_z,
                angular_velocity_x, angular_velocity_y, angular_velocity_z,
                angular_acceleration_x, angular_acceleration_y, angular_acceleration_z,
                front_wheels_angle,
                front_aero_height, rear_aero_height,
                front_roll_angle, rear_roll_angle,
                chassis_yaw, chassis_pitch
            ) VALUES (
                clock_timestamp(), %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
            ON CONFLICT (timestamp, session_uid, user_id) DO NOTHING
        """
        self._execute(sql, row, table_name=self.TABLE_NAME)
