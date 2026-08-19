"""Repository for car_frame_motion_ex (Packet 13 — Motion Ex, player car only)."""

import logging
from datetime import datetime
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase
from database.repositories.car_frame import _build_insert_sql


def _per_wheel(prefix: str) -> tuple[str, ...]:
    """Expand a per-wheel column prefix into the game's RL, RR, FL, FR order."""
    return tuple(f"{prefix}_{corner}" for corner in ("rl", "rr", "fl", "fr"))


CAR_FRAME_MOTION_EX_COLUMNS: tuple[str, ...] = (
    "timestamp", "session_uid", "user_id", "session_time", "overall_frame_identifier",
    *_per_wheel("suspension_position"),
    *_per_wheel("suspension_velocity"),
    *_per_wheel("suspension_acceleration"),
    *_per_wheel("wheel_speed"),
    *_per_wheel("wheel_slip_ratio"),
    *_per_wheel("wheel_slip_angle"),
    *_per_wheel("wheel_lat_force"),
    *_per_wheel("wheel_long_force"),
    *_per_wheel("wheel_vert_force"),
    *_per_wheel("wheel_camber"),
    *_per_wheel("wheel_camber_gain"),
    "height_of_cog_above_ground",
    "local_velocity_x", "local_velocity_y", "local_velocity_z",
    "angular_velocity_x", "angular_velocity_y", "angular_velocity_z",
    "angular_acceleration_x", "angular_acceleration_y", "angular_acceleration_z",
    "front_wheels_angle",
    "front_aero_height", "rear_aero_height",
    "front_roll_angle", "rear_roll_angle",
    "chassis_yaw", "chassis_pitch",
)


class CarFrameMotionExRepository(RepositoryBase):
    """Player-car extended motion data per frame."""

    TABLE_NAME = "telemetry.car_frame_motion_ex"
    COLUMNS = CAR_FRAME_MOTION_EX_COLUMNS

    _SQL = _build_insert_sql(
        "telemetry.car_frame_motion_ex",
        CAR_FRAME_MOTION_EX_COLUMNS,
        "timestamp, session_uid, user_id, overall_frame_identifier",
    )

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(self, row: tuple):
        """INSERT one motion_ex row. The tuple matches CAR_FRAME_MOTION_EX_COLUMNS in order."""
        self._execute(self._SQL, row, table_name=self.TABLE_NAME)

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
