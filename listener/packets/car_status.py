import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

# 5×uint8 (tractionControl..pitLimiterStatus), 3×float (fuel*),
# 2×uint16 (maxRPM, idleRPM), 2×uint8 (maxGears, drsAllowed),
# uint16 drsActivationDistance, 3×uint8 (actualTyre, visualTyre, tyresAge),
# int8 vehicleFiaFlags, 3×float (enginePowerICE/MGUK, ersStoreEnergy),
# uint8 ersDeployMode, 3×float (ersHarvested*, ersDeployed), uint8 networkPaused
_CAR_STATUS_FORMAT = '<5B3fHHBBHBBBb3fB3fB'
_CAR_STATUS_FORMAT_SIZE = struct.calcsize(_CAR_STATUS_FORMAT)


@dataclass
class CarStatusData:
    pit_limiter: int                   # uint8  | 0=off, 1=on
    drs_allowed: int                   # uint8  | 0=not allowed, 1=allowed
    drs_activation_distance: int       # uint16 | 0=DRS not available, else metres
    actual_tyre_compound: int          # uint8  | enum
    visual_tyre_compound: int          # uint8  | enum
    tyres_age_laps: int                # uint8  | laps on current set
    vehicle_fia_flags: int             # int8   | -1=invalid, 0=none, 1=green, 2=blue, 3=yellow
    network_paused: int                # uint8  | paused in network game
    front_brake_bias: int              # uint8  | percentage
    fuel_in_tank: float                # float  | kilograms
    fuel_remaining_laps: float         # float  | estimated laps remaining
    ers_store_energy: float            # float  | joules stored in ERS
    ers_deploy_mode: int               # uint8  | 0=none, 1=medium, 2=hotlap, 3=overtake
    ers_deployed_this_lap: float       # float  | joules deployed this lap


@dataclass
class CarStatusPacket:
    header: PacketHeader
    car_status_data: list[CarStatusData]


def unpack_car_status(packet_header: PacketHeader, data: bytes) -> CarStatusPacket:
    """Unpack Car Status packet (Packet ID: 7). 22 cars of status data."""
    car_data_bytes = data[:(_CAR_STATUS_FORMAT_SIZE * 22)]

    car_list = []
    for f in struct.iter_unpack(_CAR_STATUS_FORMAT, car_data_bytes):
        # f indices: 0=tractionControl, 1=antiLockBrakes, 2=fuelMix, 3=frontBrakeBias,
        # 4=pitLimiterStatus, 5=fuelInTank, 6=fuelCapacity, 7=fuelRemainingLaps,
        # 8=maxRPM, 9=idleRPM, 10=maxGears, 11=drsAllowed, 12=drsActivationDistance,
        # 13=actualTyreCompound, 14=visualTyreCompound, 15=tyresAgeLaps,
        # 16=vehicleFiaFlags, 17=enginePowerICE, 18=enginePowerMGUK,
        # 19=ersStoreEnergy, 20=ersDeployMode, 21=ersHarvestedMGUK,
        # 22=ersHarvestedMGUH, 23=ersDeployedThisLap, 24=networkPaused
        car_list.append(CarStatusData(
            pit_limiter=f[4],
            drs_allowed=f[11],
            drs_activation_distance=f[12],
            actual_tyre_compound=f[13],
            visual_tyre_compound=f[14],
            tyres_age_laps=f[15],
            vehicle_fia_flags=f[16],
            network_paused=f[24],
            front_brake_bias=f[3],
            fuel_in_tank=f[5],
            fuel_remaining_laps=f[7],
            ers_store_energy=f[19],
            ers_deploy_mode=f[20],
            ers_deployed_this_lap=f[23],
        ))

    return CarStatusPacket(packet_header, car_list)
