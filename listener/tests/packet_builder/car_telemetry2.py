"""Car Telemetry 2 packet builder (Packet ID 16)."""

import struct

from packets.constants import MAX_CARS

from .header import build_header

_CAR_TELEMETRY2_FORMAT = '<2BH2BH2B'


def build_car_telemetry2_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
) -> bytes:
    """Build a complete Car Telemetry 2 packet (header + body). 269 bytes total."""
    header = build_header(
        packet_id=16,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = b''
    for i in range(MAX_CARS):
        if i < num_drivers:
            body += struct.pack(
                _CAR_TELEMETRY2_FORMAT,
                i % 2,               # active_aero_mode
                1,                   # active_aero_available
                100 + i,             # active_aero_activation_distance
                1,                   # overtake_available
                i % 2,               # overtake_active
                200 + i,             # overtake_activation_distance
                1,                   # regulations_2026
                i % 2,               # driving_wrong_way
            )
        else:
            body += struct.pack(
                _CAR_TELEMETRY2_FORMAT,
                0, 0, 0, 0, 0, 0, 0, 0,
            )

    return header + body
