"""Session History packet builder (Packet ID 11)."""

import struct

from .header import build_header

_SIMPLE_FIELDS_FORMAT = '<7B'
_LAP_HISTORY_FORMAT = '<LHBHBHBB'
_TYRE_STINT_HISTORY_FORMAT = '<3B'
_MAX_LAPS = 100
_MAX_STINTS = 8


def build_session_history_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    car_index: int,
    num_laps: int = 3,
    lap_times_ms: list[int] | None = None,
) -> bytes:
    """Build a complete Session History packet for one car."""
    header = build_header(
        packet_id=11,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    if lap_times_ms is None:
        lap_times_ms = [88000 + car_index * 500 + lap * 200 for lap in range(num_laps)]

    best_lap_num = 1
    best_s1_lap = 1
    best_s2_lap = 1
    best_s3_lap = 1

    body = struct.pack(
        _SIMPLE_FIELDS_FORMAT,
        car_index,
        num_laps,
        1,              # num_tyre_stints
        best_lap_num,
        best_s1_lap,
        best_s2_lap,
        best_s3_lap,
    )

    # Lap history (100 laps)
    for lap_idx in range(_MAX_LAPS):
        if lap_idx < num_laps:
            lap_time = lap_times_ms[lap_idx] if lap_idx < len(lap_times_ms) else 90000
            # Split lap time roughly into 3 sectors
            s1_ms = lap_time * 33 // 100
            s2_ms = lap_time * 34 // 100
            s3_ms = lap_time - s1_ms - s2_ms

            body += struct.pack(
                _LAP_HISTORY_FORMAT,
                lap_time,      # lap_time_in_ms
                s1_ms,         # sector_1_time_ms_part
                0,             # sector_1_time_minutes_part
                s2_ms,         # sector_2_time_ms_part
                0,             # sector_2_time_minutes_part
                s3_ms,         # sector_3_time_ms_part
                0,             # sector_3_time_minutes_part
                0x0F,          # lap_valid_bit_flags (all valid: 0x01|0x02|0x04|0x08)
            )
        else:
            body += struct.pack(_LAP_HISTORY_FORMAT, 0, 0, 0, 0, 0, 0, 0, 0)

    # Tyre stint history (8 stints)
    for stint_idx in range(_MAX_STINTS):
        if stint_idx == 0:
            body += struct.pack(
                _TYRE_STINT_HISTORY_FORMAT,
                255,    # end_lap (255 = current tyre)
                18,     # tyre_actual_compound (C3)
                16,     # tyre_visual_compound (SOFT)
            )
        else:
            body += struct.pack(_TYRE_STINT_HISTORY_FORMAT, 0, 0, 0)

    return header + body
