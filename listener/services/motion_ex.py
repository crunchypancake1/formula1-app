"""Service for Motion Ex data (Packet 13 — player car only)."""

import logging
from typing import Optional

from database.repositories.car_frame_motion_ex import CarFrameMotionExRepository
from packets.motion_ex import MotionExPacket


class MotionExService:
    def __init__(self, repo: CarFrameMotionExRepository, logger: Optional[logging.Logger] = None):
        self._repo = repo
        self._logger = logger or logging.getLogger(__name__)

    def write_motion_ex(self, packet: MotionExPacket, user_map: dict[int, int]):
        player_index = packet.header.player_car_index
        user_id = user_map.get(player_index)
        if user_id is None:
            return

        data = packet.motion_ex_data
        row = (
            str(packet.header.session_uid),
            user_id,
            packet.header.session_time,
            packet.header.overall_frame_identifier,
            # Flatten tuples in schema column order
            *data.suspension_position,       # 4: RL,RR,FL,FR
            *data.suspension_velocity,       # 4
            *data.suspension_acceleration,   # 4
            *data.wheel_speed,               # 4
            *data.wheel_slip_ratio,          # 4
            *data.wheel_slip_angle,          # 4
            *data.wheel_lat_force,           # 4
            *data.wheel_long_force,          # 4
            *data.wheel_vert_force,          # 4
            *data.wheel_camber,              # 4
            *data.wheel_camber_gain,         # 4
            data.height_of_cog_above_ground,
            data.local_velocity_x,
            data.local_velocity_y,
            data.local_velocity_z,
            data.angular_velocity_x,
            data.angular_velocity_y,
            data.angular_velocity_z,
            data.angular_acceleration_x,
            data.angular_acceleration_y,
            data.angular_acceleration_z,
            data.front_wheels_angle,
            data.front_aero_height,
            data.rear_aero_height,
            data.front_roll_angle,
            data.rear_roll_angle,
            data.chassis_yaw,
            data.chassis_pitch,
        )
        try:
            self._repo.insert(row)
        except Exception as e:
            self._logger.error(f"Failed to insert motion_ex: {e}", exc_info=True)
