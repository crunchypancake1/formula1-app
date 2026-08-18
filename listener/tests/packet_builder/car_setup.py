"""Car Setup packet builder (Packet ID 5)."""

import struct

from packets.constants import MAX_CARS

from .header import build_header

_CAR_SETUP_FORMAT = '<4B4f6B3B4fBf'


def build_car_setup_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
    next_front_wing_value: float = 0.0,
) -> bytes:
    """Build a complete Car Setups packet (header + body)."""
    header = build_header(
        packet_id=5,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = b''
    for i in range(MAX_CARS):
        if i < num_drivers:
            body += struct.pack(
                _CAR_SETUP_FORMAT,
                3, 3, 50, 50,           # front_wing, rear_wing, on_throttle, off_throttle
                5.0, 3.0, 0.05, 0.1,    # front_camber, rear_camber, front_toe, rear_toe
                40, 40, 5, 5, 3, 3,     # front/rear susp, ARB, ride height
                90, 55, 5,              # brake_pressure, brake_bias, engine_braking
                23.0, 23.0, 22.5, 22.5,  # tyre pressures RL/RR/FL/FR
                0,                      # ballast
                100.0,                  # fuel_load
            )
        else:
            body += struct.pack(
                _CAR_SETUP_FORMAT,
                0, 0, 0, 0,
                0.0, 0.0, 0.0, 0.0,
                0, 0, 0, 0, 0, 0,
                0, 0, 0,
                0.0, 0.0, 0.0, 0.0,
                0,
                0.0,
            )

    body += struct.pack('<f', next_front_wing_value)

    return header + body
