"""Motion packet builder (Packet ID 0)."""

import math
import struct

from packets.constants import MAX_CARS

from .header import build_header

_CAR_MOTION_FORMAT = '<6f6h3h3f'


def build_motion_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
    lap_distance: float = 0.0,
    track_length: float = 5793.0,
) -> bytes:
    """Build a complete Motion packet (header + body)."""
    header = build_header(
        packet_id=0,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = b''
    for i in range(MAX_CARS):
        if i < num_drivers:
            progress = (lap_distance / track_length) if track_length > 0 else 0
            angle = progress * 2 * math.pi
            x = math.cos(angle) * 100 + i * 2
            z = math.sin(angle) * 100
            y = 10.0

            forward_x = int(-math.sin(angle) * 32767)
            forward_z = int(math.cos(angle) * 32767)

            body += struct.pack(
                _CAR_MOTION_FORMAT,
                x, y, z,                    # world_position x/y/z
                50.0, 0.0, 50.0,            # world_velocity x/y/z
                forward_x, 0, forward_z,    # forward_dir x/y/z (int16)
                0, 32767, 0,                # right_dir x/y/z (int16)
                100, 500, 1000,             # g_force lat/long/vert (int16, quantised /1000)
                angle, 0.01, 0.0,           # yaw/pitch/roll
            )
        else:
            body += struct.pack(_CAR_MOTION_FORMAT, *([0.0] * 6 + [0] * 9 + [0.0] * 3))

    return header + body
