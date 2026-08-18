import struct
from dataclasses import dataclass

from .constants import MAX_CARS
from .packet_header import PacketHeader

_CAR_MOTION_FORMAT = '<6f6h3h3f'
_CAR_MOTION_FORMAT_SIZE = struct.calcsize(_CAR_MOTION_FORMAT)
_NORM_DIVISOR = 32767.0
_G_FORCE_DIVISOR = 1000.0


@dataclass
class CarMotionData:
    world_position_x: float          # float  | World space X position - metres
    world_position_y: float          # float  | World space Y position
    world_position_z: float          # float  | World space Z position
    world_velocity_x: float          # float  | Velocity in world space X - m/s
    world_velocity_y: float          # float  | Velocity in world space Y
    world_velocity_z: float          # float  | Velocity in world space Z
    world_forward_dir_x: float       # int16  | Forward X direction (normalised, divided by 32767)
    world_forward_dir_y: float       # int16  | Forward Y direction (normalised)
    world_forward_dir_z: float       # int16  | Forward Z direction (normalised)
    world_right_dir_x: float         # int16  | Right X direction (normalised)
    world_right_dir_y: float         # int16  | Right Y direction (normalised)
    world_right_dir_z: float         # int16  | Right Z direction (normalised)
    g_force_lateral: float           # int16  | Lateral G-Force component (quantised, divided by 1000)
    g_force_longitudinal: float      # int16  | Longitudinal G-Force component (quantised, divided by 1000)
    g_force_vertical: float          # int16  | Vertical G-Force component (quantised, divided by 1000)
    yaw: float                       # float  | Yaw angle in radians
    pitch: float                     # float  | Pitch angle in radians
    roll: float                      # float  | Roll angle in radians


@dataclass
class MotionPacket:
    header: PacketHeader
    car_motion_data: list[CarMotionData]


def unpack_motion(packet_header: PacketHeader, data: bytes) -> MotionPacket:
    """Unpack Motion packet (Packet ID: 0). MAX_CARS cars of physics data."""
    car_data_bytes = data[:(_CAR_MOTION_FORMAT_SIZE * MAX_CARS)]

    car_motion_list = []
    for fields in struct.iter_unpack(_CAR_MOTION_FORMAT, car_data_bytes):
        # Normalise int16 direction vectors to float [-1.0, 1.0]
        car_motion_list.append(CarMotionData(
            fields[0], fields[1], fields[2],    # position x/y/z
            fields[3], fields[4], fields[5],    # velocity x/y/z
            fields[6] / _NORM_DIVISOR,           # forward dir x
            fields[7] / _NORM_DIVISOR,           # forward dir y
            fields[8] / _NORM_DIVISOR,           # forward dir z
            fields[9] / _NORM_DIVISOR,           # right dir x
            fields[10] / _NORM_DIVISOR,          # right dir y
            fields[11] / _NORM_DIVISOR,          # right dir z
            fields[12] / _G_FORCE_DIVISOR,       # g-force lateral (quantised int16)
            fields[13] / _G_FORCE_DIVISOR,       # g-force longitudinal (quantised int16)
            fields[14] / _G_FORCE_DIVISOR,       # g-force vertical (quantised int16)
            fields[15], fields[16], fields[17],  # yaw/pitch/roll
        ))

    return MotionPacket(packet_header, car_motion_list)
