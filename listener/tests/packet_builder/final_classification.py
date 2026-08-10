"""Final Classification packet builder (Packet ID 8)."""

import struct

from .header import build_header

_MAX_TYRE_STINTS = 8
_FINAL_CLASSIFICATION_FORMAT = f'<7BLd3B{_MAX_TYRE_STINTS * 3}B'


def build_final_classification_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
    total_laps: int = 3,
) -> bytes:
    """Build a complete Final Classification packet (header + body)."""
    header = build_header(
        packet_id=8,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    body = struct.pack('<B', num_drivers)

    for i in range(num_drivers):
        position = i + 1
        best_lap_ms = 88000 + i * 500
        total_time = 270.0 + i * 1.5
        grid_position = num_drivers - i

        # Tyre stints: 1 stint on softs
        tyre_actual = [18] + [0] * (_MAX_TYRE_STINTS - 1)    # C3
        tyre_visual = [16] + [0] * (_MAX_TYRE_STINTS - 1)    # SOFT
        tyre_end_laps = [total_laps] + [0] * (_MAX_TYRE_STINTS - 1)

        body += struct.pack(
            _FINAL_CLASSIFICATION_FORMAT,
            position,          # position
            total_laps,        # num_of_laps
            grid_position,     # grid_position
            25 - i if i < 10 else 0,  # points
            0,                 # num_pit_stops
            3,                 # result_status (finished)
            2,                 # result_reason (finished)
            best_lap_ms,       # best_lap_time_in_ms
            total_time,        # total_race_time (double)
            0,                 # penalties_time
            0,                 # num_of_penalties
            1,                 # num_of_tyre_stints
            *tyre_actual,
            *tyre_visual,
            *tyre_end_laps,
        )

    return header + body
