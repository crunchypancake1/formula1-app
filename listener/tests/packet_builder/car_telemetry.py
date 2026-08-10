"""Car Telemetry packet builder (Packet ID 6)."""

import struct

from .header import build_header

_CAR_TELEMETRY_FORMAT = '<H3fBbHBBH4H4B4BH4f4B'
_MAX_CARS = 22


def build_car_telemetry_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
    base_speed: int = 280,
) -> bytes:
    """Build a complete Car Telemetry packet (header + body)."""
    header = build_header(
        packet_id=6,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = b''
    for i in range(_MAX_CARS):
        if i < num_drivers:
            speed = base_speed + i * 2
            body += struct.pack(
                _CAR_TELEMETRY_FORMAT,
                speed,                  # speed (uint16)
                0.8,                    # throttle
                0.05,                   # steer
                0.0,                    # brake
                0,                      # clutch
                6,                      # gear
                10500 + i * 50,         # engine_rpm
                0,                      # drs
                50,                     # revLightsPercent (discarded)
                0,                      # revLightsBitValue (discarded)
                # brakes_temp RL/RR/FL/FR
                400, 410, 380, 390,
                # tyres_surface_temp RL/RR/FL/FR
                100, 102, 98, 99,
                # tyres_inner_temp RL/RR/FL/FR
                105, 107, 103, 104,
                # engine_temperature
                120,
                # tyres_pressure RL/RR/FL/FR
                23.5, 23.5, 22.0, 22.0,
                # surface_type RL/RR/FL/FR (0 = TARMAC)
                0, 0, 0, 0,
            )
        else:
            body += struct.pack(
                _CAR_TELEMETRY_FORMAT,
                0, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                0,
                0.0, 0.0, 0.0, 0.0,
                0, 0, 0, 0,
            )

    return header + body
