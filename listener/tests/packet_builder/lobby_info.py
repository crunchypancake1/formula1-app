"""Lobby Info packet builder (Packet ID 9)."""

import struct

from packets.constants import MAX_CARS

from .header import build_header

_LOBBY_PLAYER_FORMAT = '<BH2B32s3BHB'


def build_lobby_info_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_players: int = 20,
) -> bytes:
    """Build a complete Lobby Info packet (header + body)."""
    header = build_header(
        packet_id=9,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = struct.pack('<B', num_players)

    for i in range(MAX_CARS):
        if i < num_players:
            body += struct.pack(
                _LOBBY_PLAYER_FORMAT,
                0,                                  # ai_controlled
                0,                                   # team_id
                0,                                   # nationality
                1,                                   # platform (Steam)
                f"Driver{i}".encode("utf-8").ljust(32, b'\x00'),  # name
                i,                                   # car_number
                1,                                   # your_telemetry (public)
                1,                                   # show_online_names
                0,                                   # tech_level
                1,                                   # ready_status (ready)
            )
        else:
            body += struct.pack(
                _LOBBY_PLAYER_FORMAT,
                0, 0, 0, 0,
                b''.ljust(32, b'\x00'),
                0, 0, 0, 0, 0,
            )

    return header + body
