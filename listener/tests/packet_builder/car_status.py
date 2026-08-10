"""Car Status packet builder (Packet ID 7)."""

import struct

from .header import build_header

_CAR_STATUS_FORMAT = '<5B3fHHBBHBBBb3fB3fB'
_MAX_CARS = 22


def build_car_status_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
) -> bytes:
    """Build a complete Car Status packet (header + body)."""
    header = build_header(
        packet_id=7,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = b''
    for i in range(_MAX_CARS):
        if i < num_drivers:
            body += struct.pack(
                _CAR_STATUS_FORMAT,
                # 5 uint8: tractionControl, antiLock, fuelMix, frontBrakeBias, pitLimiter
                0, 0, 0, 55, 0,
                # 3 float: fuelInTank, fuelCapacity, fuelRemainingLaps
                50.0, 110.0, 20.0,
                # 2 uint16: maxRPM, idleRPM
                12000, 4000,
                # 2 uint8: maxGears, drsAllowed
                8, 1,
                # uint16: drsActivationDistance
                100,
                # 3 uint8: actualTyreCompound, visualTyreCompound, tyresAgeLaps
                18,     # C3 actual
                16,     # SOFT visual
                5,      # tyres age
                # int8: vehicleFiaFlags
                0,      # no flags
                # 3 float: enginePowerICE, enginePowerMGUK, ersStoreEnergy
                750.0, 120.0, 4000000.0,
                # uint8: ersDeployMode
                2,
                # 3 float: ersHarvestedMGUK/MGUH, ersDeployedThisLap
                200000.0, 300000.0, 100000.0,
                # uint8: networkPaused
                0,
            )
        else:
            body += struct.pack(
                _CAR_STATUS_FORMAT,
                0, 0, 0, 0, 0,
                0.0, 0.0, 0.0,
                0, 0,
                0, 0,
                0,
                0, 0, 0,
                0,
                0.0, 0.0, 0.0,
                0,
                0.0, 0.0, 0.0,
                0,
            )

    return header + body
