"""Service for Motion Ex data (Packet 13 — player car only)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from database.repositories.car_frame_motion_ex import CarFrameMotionExRepository
from packets.motion_ex import MotionExPacket


class MotionExService:
    """
    Writes the player's extended motion data.

    The packet has no car index — it always describes header.player_car_index
    and never any other car, in every session type. There is deliberately no
    attempt to attribute it to anyone else.
    """

    def __init__(self, repo: CarFrameMotionExRepository, logger: Optional[logging.Logger] = None):
        self._repo = repo
        self._logger = logger or logging.getLogger(__name__)

    def write_motion_ex(
        self,
        packet: MotionExPacket,
        user_map: dict[int, int],
        session_start: Optional[datetime] = None,
    ):
        user_id = user_map.get(packet.header.player_car_index)
        if user_id is None:
            return

        session_time = packet.header.session_time
        timestamp = (
            session_start + timedelta(seconds=session_time)
            if session_start is not None
            else datetime.now(timezone.utc)
        )

        data = packet.motion_ex_data
        row = (
            timestamp,
            str(packet.header.session_uid),
            user_id,
            session_time,
            packet.header.overall_frame_identifier,
            # Per-wheel groups, each in the game's RL, RR, FL, FR order
            *data.suspension_position,
            *data.suspension_velocity,
            *data.suspension_acceleration,
            *data.wheel_speed,
            *data.wheel_slip_ratio,
            *data.wheel_slip_angle,
            *data.wheel_lat_force,
            *data.wheel_long_force,
            *data.wheel_vert_force,
            *data.wheel_camber,
            *data.wheel_camber_gain,
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

    def discard_after(
        self,
        session_uid: str,
        session_time: float,
        session_start: Optional[datetime] = None,
    ) -> int:
        """
        Delete rows recorded after a flashback's rewind point.

        session_start is what lets the DELETE bound `timestamp` as well, so
        TimescaleDB can exclude every chunk this session does not occupy.
        """
        return self._repo.delete_after(session_uid, session_time, session_start)
