"""Parser for Packet 13 — Motion Ex (player car only)."""

import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

_MOTION_EX_FORMAT = '<61f'
_MOTION_EX_FORMAT_SIZE = struct.calcsize(_MOTION_EX_FORMAT)


@dataclass(frozen=True)
class MotionExData:
    suspension_position: tuple       # float[4] RL,RR,FL,FR
    suspension_velocity: tuple       # float[4]
    suspension_acceleration: tuple   # float[4]
    wheel_speed: tuple               # float[4]
    wheel_slip_ratio: tuple          # float[4]
    wheel_slip_angle: tuple          # float[4]
    wheel_lat_force: tuple           # float[4]
    wheel_long_force: tuple          # float[4]
    height_of_cog_above_ground: float
    local_velocity_x: float
    local_velocity_y: float
    local_velocity_z: float
    angular_velocity_x: float
    angular_velocity_y: float
    angular_velocity_z: float
    angular_acceleration_x: float
    angular_acceleration_y: float
    angular_acceleration_z: float
    front_wheels_angle: float
    wheel_vert_force: tuple          # float[4]
    front_aero_height: float
    rear_aero_height: float
    front_roll_angle: float
    rear_roll_angle: float
    chassis_yaw: float
    chassis_pitch: float
    wheel_camber: tuple              # float[4]
    wheel_camber_gain: tuple         # float[4]


@dataclass(frozen=True)
class MotionExPacket:
    header: PacketHeader
    motion_ex_data: MotionExData


def unpack_motion_ex(packet_header: PacketHeader, data: bytes) -> MotionExPacket:
    """Unpack Packet ID 13 — Motion Ex (player car only)."""
    f = struct.unpack_from(_MOTION_EX_FORMAT, data, 0)
    motion_ex = MotionExData(
        suspension_position=f[0:4],
        suspension_velocity=f[4:8],
        suspension_acceleration=f[8:12],
        wheel_speed=f[12:16],
        wheel_slip_ratio=f[16:20],
        wheel_slip_angle=f[20:24],
        wheel_lat_force=f[24:28],
        wheel_long_force=f[28:32],
        height_of_cog_above_ground=f[32],
        local_velocity_x=f[33],
        local_velocity_y=f[34],
        local_velocity_z=f[35],
        angular_velocity_x=f[36],
        angular_velocity_y=f[37],
        angular_velocity_z=f[38],
        angular_acceleration_x=f[39],
        angular_acceleration_y=f[40],
        angular_acceleration_z=f[41],
        front_wheels_angle=f[42],
        wheel_vert_force=f[43:47],
        front_aero_height=f[47],
        rear_aero_height=f[48],
        front_roll_angle=f[49],
        rear_roll_angle=f[50],
        chassis_yaw=f[51],
        chassis_pitch=f[52],
        wheel_camber=f[53:57],
        wheel_camber_gain=f[57:61],
    )
    return MotionExPacket(header=packet_header, motion_ex_data=motion_ex)
