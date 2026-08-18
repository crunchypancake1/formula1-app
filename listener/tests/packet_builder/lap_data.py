"""Lap Data packet builder (Packet ID 2)."""

import struct

from packets.constants import MAX_CARS

from .header import build_header

_LAP_DATA_FORMAT = '<2LHBHBHBHB3f15B2HBfB'


def build_lap_data_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
    current_lap_num: int = 1,
    lap_distance: float = 0.0,
    track_length: float = 5793.0,
    positions: list[int] | None = None,
) -> bytes:
    """Build a complete Lap Data packet (header + body)."""
    header = build_header(
        packet_id=2,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    if positions is None:
        positions = list(range(1, num_drivers + 1)) + [0] * (MAX_CARS - num_drivers)

    body = b''
    for i in range(MAX_CARS):
        if i < num_drivers:
            car_position = positions[i] if i < len(positions) else i + 1
            total_distance = (current_lap_num - 1) * track_length + lap_distance

            # Determine sector from lap_distance
            if lap_distance < 2400:
                sector = 0
            elif lap_distance < 4200:
                sector = 1
            else:
                sector = 2

            body += struct.pack(
                _LAP_DATA_FORMAT,
                90000 + i * 100,       # last_lap_time_in_ms
                int(session_time * 1000) % 120000,  # current_lap_time_in_ms
                30000 + i * 10,        # sector1_time_ms_part
                0,                     # sector1_time_minutes_part
                28000 + i * 10,        # sector2_time_ms_part
                0,                     # sector2_time_minutes_part
                500 + i * 10,          # delta_to_car_in_front_ms_part
                0,                     # delta_to_car_in_front_minutes_part
                1000 + i * 50,         # delta_to_race_leader_ms_part
                0,                     # delta_to_race_leader_minutes_part
                lap_distance,          # lap_distance
                total_distance,        # total_distance
                0.0,                   # safety_car_delta
                car_position,          # car_position
                current_lap_num,       # current_lap_num
                0,                     # pit_status (none)
                0,                     # num_pit_stops
                sector,                # sector
                0,                     # current_lap_invalid (valid)
                0,                     # penalties
                0,                     # total_warnings
                0,                     # corner_cutting_warnings
                0,                     # num_unserved_drive_through_pens
                0,                     # num_unserved_stop_go_pens
                car_position,          # grid_position
                4,                     # driver_status (on track)
                2,                     # result_status (active)
                0,                     # pit_lane_timer_active
                0,                     # pit_lane_time_in_lane_in_ms
                0,                     # pit_stop_timer_in_ms
                0,                     # pit_stop_should_serve_pen
                310.0 - i * 2.0,       # speed_trap_fastest_speed
                current_lap_num,       # speed_trap_fastest_lap
            )
        else:
            body += struct.pack(
                _LAP_DATA_FORMAT,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                0.0, 0.0, 0.0,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0,
                0.0, 0,
            )

    # Trailing 2 bytes: time_trial_pb_car_idx, time_trial_rival_car_idx
    body += struct.pack('<BB', 255, 255)

    return header + body
