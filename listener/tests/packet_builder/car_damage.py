"""Car Damage packet builder (Packet ID 10)."""

import struct

from packets.constants import MAX_CARS

from .header import build_header

_CAR_DAMAGE_FORMAT = '<4f4B4B4B18B'


def build_car_damage_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
    tyre_wear_pct: float = 15.0,
) -> bytes:
    """Build a complete Car Damage packet (header + body).

    Args:
        tyre_wear_pct: Base tyre wear percentage applied to all active cars.
            Rear tyres get slightly more wear than fronts.
    """
    header = build_header(
        packet_id=10,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = b''
    for i in range(MAX_CARS):
        if i < num_drivers:
            body += struct.pack(
                _CAR_DAMAGE_FORMAT,
                # 4 float: tyres_wear RL/RR/FL/FR
                tyre_wear_pct, tyre_wear_pct - 1.0, tyre_wear_pct - 3.0, tyre_wear_pct - 2.0,
                # 4 uint8: tyres_damage
                5, 4, 3, 4,
                # 4 uint8: brakes_damage
                2, 2, 1, 1,
                # 4 uint8: tyre_blisters
                10, 8, 5, 7,
                # 18 uint8: remaining damage fields (all zero)
                *([0] * 18),
            )
        else:
            body += struct.pack(
                _CAR_DAMAGE_FORMAT,
                0.0, 0.0, 0.0, 0.0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                *([0] * 18),
            )

    return header + body
