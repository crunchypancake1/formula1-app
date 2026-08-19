import struct
from dataclasses import dataclass

from .constants import MAX_CARS
from .packet_header import PacketHeader

# uint16 speed, float throttle/steer/brake, uint8 clutch, int8 gear, uint16 rpm,
# uint8 drs, uint8 revLightsPercent, uint16 revLightsBitValue,
# uint16[4] brakesTemp, uint8[4] tyresSurfaceTemp, uint8[4] tyresInnerTemp,
# uint8 engineTemp, float[4] tyresPressure, uint8[4] surfaceType
_CAR_TELEMETRY_FORMAT = '<H3fBbHBBH4H4B4BB4f4B'
_CAR_TELEMETRY_FORMAT_SIZE = struct.calcsize(_CAR_TELEMETRY_FORMAT)

# Packet-level tail after the car array: uint8 mfdPanelIndex,
# uint8 mfdPanelIndexSecondaryPlayer, int8 suggestedGear
_TELEMETRY_TAIL_FORMAT = '<2Bb'
_TELEMETRY_TAIL_FORMAT_SIZE = struct.calcsize(_TELEMETRY_TAIL_FORMAT)

# m_mfdPanelIndex sentinel meaning the MFD is closed
MFD_CLOSED = 255


@dataclass
class CarTelemetryData:
    speed: int                               # uint16 | km/h
    throttle: float                          # float  | 0.0-1.0
    steer: float                             # float  | -1.0 to 1.0
    brake: float                             # float  | 0.0-1.0
    clutch: int                              # uint8  | 0-100
    gear: int                                # int8   | R=-1, N=0, 1-8
    engine_rpm: int                          # uint16
    drs: int                                 # uint8  | 0=off, 1=on
    rev_lights_percent: int                  # uint8  | 0-100
    rev_lights_bit_value: int                # uint16 | bit 0 = leftmost LED
    brakes_temperature: tuple                # uint16[4] | celsius per wheel
    tyres_surface_temp: tuple                # uint8[4]  | celsius per wheel
    tyres_inner_temp: tuple                  # uint8[4]  | celsius per wheel
    engine_temperature: int                  # uint8  | celsius
    tyres_pressure: tuple                    # float[4]  | PSI per wheel
    surface_type: tuple                      # uint8[4]  | enum per wheel


@dataclass
class CarTelemetryPacket:
    header: PacketHeader
    car_telemetry_data: list[CarTelemetryData]
    # The three fields below describe the local player only — there is no
    # equivalent for any other car.
    mfd_panel_index: int                     # uint8 | 255 = MFD closed
    mfd_panel_index_secondary_player: int    # uint8 | 255 = MFD closed
    suggested_gear: int                      # int8  | 0 = no gear suggested


def unpack_car_telemetry(packet_header: PacketHeader, data: bytes) -> CarTelemetryPacket:
    """Unpack Car Telemetry packet (Packet ID: 6). MAX_CARS cars of telemetry data."""
    car_array_size = _CAR_TELEMETRY_FORMAT_SIZE * MAX_CARS
    car_data_bytes = data[:car_array_size]

    car_list = []
    for f in struct.iter_unpack(_CAR_TELEMETRY_FORMAT, car_data_bytes):
        # f indices: 0=speed, 1=throttle, 2=steer, 3=brake, 4=clutch, 5=gear,
        # 6=rpm, 7=drs, 8=revLightsPercent, 9=revLightsBitValue,
        # 10-13=brakesTemp[4], 14-17=tyresSurfaceTemp[4], 18-21=tyresInnerTemp[4],
        # 22=engineTemp, 23-26=tyresPressure[4], 27-30=surfaceType[4]
        car_list.append(CarTelemetryData(
            speed=f[0],
            throttle=f[1],
            steer=f[2],
            brake=f[3],
            clutch=f[4],
            gear=f[5],
            engine_rpm=f[6],
            drs=f[7],
            rev_lights_percent=f[8],
            rev_lights_bit_value=f[9],
            brakes_temperature=(f[10], f[11], f[12], f[13]),
            tyres_surface_temp=(f[14], f[15], f[16], f[17]),
            tyres_inner_temp=(f[18], f[19], f[20], f[21]),
            engine_temperature=f[22],
            tyres_pressure=(f[23], f[24], f[25], f[26]),
            surface_type=(f[27], f[28], f[29], f[30]),
        ))

    tail = struct.unpack_from(_TELEMETRY_TAIL_FORMAT, data, car_array_size)

    return CarTelemetryPacket(packet_header, car_list, *tail)
