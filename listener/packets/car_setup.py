import struct
from dataclasses import dataclass

from .constants import MAX_CARS
from .packet_header import PacketHeader

# CarSetupData per car:
#   4×uint8 (frontWing, rearWing, onThrottle, offThrottle)
#   4×float (frontCamber, rearCamber, frontToe, rearToe)
#   6×uint8 (frontSusp, rearSusp, frontARB, rearARB, frontHeight, rearHeight)
#   3×uint8 (brakePressure, brakeBias, engineBraking)
#   4×float (RL/RR/FL/FR tyre pressure)
#   1×uint8 (ballast)
#   1×float (fuelLoad)
# = 50 bytes per car
_CAR_SETUP_FORMAT = '<4B4f6B3B4fBf'
_CAR_SETUP_FORMAT_SIZE = struct.calcsize(_CAR_SETUP_FORMAT)


@dataclass
class CarSetupData:
    front_wing: int
    rear_wing: int
    on_throttle: int
    off_throttle: int
    front_camber: float
    rear_camber: float
    front_toe: float
    rear_toe: float
    front_suspension: int
    rear_suspension: int
    front_anti_roll_bar: int
    rear_anti_roll_bar: int
    front_ride_height: int
    rear_ride_height: int
    brake_pressure: int
    brake_bias: int
    engine_braking: int
    rear_left_tyre_pressure: float
    rear_right_tyre_pressure: float
    front_left_tyre_pressure: float
    front_right_tyre_pressure: float
    ballast: int
    fuel_load: float


@dataclass
class CarSetupPacket:
    header: PacketHeader
    car_setups: list[CarSetupData]
    next_front_wing_value: float


def unpack_car_setup(packet_header: PacketHeader, data: bytes) -> CarSetupPacket:
    """Unpack Car Setup packet (Packet ID: 5). 22 cars of setup data."""
    car_data_bytes = data[:(_CAR_SETUP_FORMAT_SIZE * MAX_CARS)]
    remaining = data[(_CAR_SETUP_FORMAT_SIZE * MAX_CARS):]

    car_list = []
    for f in struct.iter_unpack(_CAR_SETUP_FORMAT, car_data_bytes):
        car_list.append(CarSetupData(*f))

    next_front_wing = struct.unpack('<f', remaining[:4])[0]
    return CarSetupPacket(packet_header, car_list, next_front_wing)
