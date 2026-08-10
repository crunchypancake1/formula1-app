import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

# uint16 speed, float throttle/steer/brake, uint8 clutch, int8 gear, uint16 rpm,
# uint8 drs, uint8 revLightsPercent, uint16 revLightsBitValue,
# uint16[4] brakesTemp, uint8[4] tyresSurfaceTemp, uint8[4] tyresInnerTemp,
# uint16 engineTemp, float[4] tyresPressure, uint8[4] surfaceType
_CAR_TELEMETRY_FORMAT = '<H3fBbHBBH4H4B4BH4f4B'
_CAR_TELEMETRY_FORMAT_SIZE = struct.calcsize(_CAR_TELEMETRY_FORMAT)


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
    brakes_temperature: tuple                # uint16[4] | celsius per wheel
    tyres_surface_temp: tuple                # uint8[4]  | celsius per wheel
    tyres_inner_temp: tuple                  # uint8[4]  | celsius per wheel
    engine_temperature: int                  # uint16 | celsius
    tyres_pressure: tuple                    # float[4]  | PSI per wheel
    surface_type: tuple                      # uint8[4]  | enum per wheel


@dataclass
class CarTelemetryPacket:
    header: PacketHeader
    car_telemetry_data: list[CarTelemetryData]


def unpack_car_telemetry(packet_header: PacketHeader, data: bytes) -> CarTelemetryPacket:
    """Unpack Car Telemetry packet (Packet ID: 6). 22 cars of telemetry data."""
    car_data_bytes = data[:(_CAR_TELEMETRY_FORMAT_SIZE * 22)]

    car_list = []
    for f in struct.iter_unpack(_CAR_TELEMETRY_FORMAT, car_data_bytes):
        # f indices: 0=speed, 1=throttle, 2=steer, 3=brake, 4=clutch, 5=gear,
        # 6=rpm, 7=drs, 8=revLightsPercent(skip), 9=revLightsBitValue(skip),
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
            # f[8] = revLightsPercent (discarded)
            # f[9] = revLightsBitValue (discarded)
            brakes_temperature=(f[10], f[11], f[12], f[13]),
            tyres_surface_temp=(f[14], f[15], f[16], f[17]),
            tyres_inner_temp=(f[18], f[19], f[20], f[21]),
            engine_temperature=f[22],
            tyres_pressure=(f[23], f[24], f[25], f[26]),
            surface_type=(f[27], f[28], f[29], f[30]),
        ))

    return CarTelemetryPacket(packet_header, car_list)
