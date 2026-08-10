"""Header builder — 29-byte packet header for every F1 25 UDP packet."""

import struct

_PACKET_HEADER_FORMAT = '<HBBBBBQfIIBB'


def build_header(
    packet_id: int,
    session_uid: int,
    session_time: float,
    frame_identifier: int,
    overall_frame_identifier: int,
    player_car_index: int = 0,
    secondary_player_car_index: int = 255,
) -> bytes:
    """Build a 29-byte F1 25 packet header."""
    return struct.pack(
        _PACKET_HEADER_FORMAT,
        2025,                          # packet_format
        25,                            # game_year
        1,                             # game_major_version
        0,                             # game_minor_version
        1,                             # packet_version
        packet_id,                     # packet_id
        session_uid,                   # session_uid
        session_time,                  # session_time
        frame_identifier,              # frame_identifier
        overall_frame_identifier,      # overall_frame_identifier
        player_car_index,              # player_car_index
        secondary_player_car_index,    # secondary_player_car_index
    )
