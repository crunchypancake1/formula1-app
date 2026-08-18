import struct
from dataclasses import dataclass

from .constants import MAX_CARS
from .packet_header import PacketHeader

# uint8 activeAeroMode, uint8 activeAeroAvailable, uint16 activeAeroActivationDistance,
# uint8 overtakeAvailable, uint8 overtakeActive, uint16 overtakeActivationDistance,
# uint8 2026Regulations, uint8 drivingWrongWay
_CAR_TELEMETRY2_FORMAT = '<2BH2BH2B'
_CAR_TELEMETRY2_FORMAT_SIZE = struct.calcsize(_CAR_TELEMETRY2_FORMAT)


@dataclass
class CarTelemetry2Data:
    active_aero_mode: int                    # uint8  | 0 = Corner mode, 1 = Straight mode
    active_aero_available: int               # uint8  | 0/1
    active_aero_activation_distance: int     # uint16 | 0 = n/a, else metres
    overtake_available: int                  # uint8  | 0/1
    overtake_active: int                     # uint8  | 0/1
    overtake_activation_distance: int        # uint16 | 0 = n/a, else metres
    regulations_2026: int                    # uint8  | 0 = pre-2026 car, 1 = 2026 regs apply
    driving_wrong_way: int                   # uint8


@dataclass
class CarTelemetry2Packet:
    header: PacketHeader
    car_telemetry2_data: list[CarTelemetry2Data]


def unpack_car_telemetry2(packet_header: PacketHeader, data: bytes) -> CarTelemetry2Packet:
    """Unpack Car Telemetry 2 packet (Packet ID: 16). MAX_CARS cars of telemetry data."""
    car_data_bytes = data[:(_CAR_TELEMETRY2_FORMAT_SIZE * MAX_CARS)]

    car_list = []
    for f in struct.iter_unpack(_CAR_TELEMETRY2_FORMAT, car_data_bytes):
        car_list.append(CarTelemetry2Data(
            active_aero_mode=f[0],
            active_aero_available=f[1],
            active_aero_activation_distance=f[2],
            overtake_available=f[3],
            overtake_active=f[4],
            overtake_activation_distance=f[5],
            regulations_2026=f[6],
            driving_wrong_way=f[7],
        ))

    return CarTelemetry2Packet(packet_header, car_list)
