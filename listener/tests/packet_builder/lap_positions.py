"""Lap Positions packet builder (Packet ID 15)."""

import struct

from .header import build_header

_LAP_POSITIONS_HEADER_FORMAT = '<BB'
_MAX_LAPS = 50
_MAX_CARS = 22


def build_lap_positions_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    lap_positions: dict[int, list[int]],
    lap_start: int = 0,
) -> bytes:
    """
    Build a complete Lap Positions packet.

    Args:
        lap_positions: {lap_offset: [position_for_car_0, position_for_car_1, ...]}
            where lap_offset is 0-indexed from lap_start.
            The game encodes positions[car_index] = race_position.
    """
    header = build_header(
        packet_id=15,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    num_laps = max(lap_positions.keys()) + 1 if lap_positions else 0

    body = struct.pack(_LAP_POSITIONS_HEADER_FORMAT, num_laps, lap_start)

    # Build 50 × 22 position grid
    for lap_idx in range(_MAX_LAPS):
        if lap_idx in lap_positions:
            positions = lap_positions[lap_idx]
            row = positions[:_MAX_CARS]
            row += [0] * (_MAX_CARS - len(row))
            body += bytes(row)
        else:
            body += bytes([0] * _MAX_CARS)

    return header + body
