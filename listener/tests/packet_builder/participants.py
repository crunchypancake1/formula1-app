"""Participants packet builder (Packet ID 4)."""

import struct

from packets.constants import MAX_CARS

from .header import build_header

_NUM_ACTIVE_CARS_FORMAT = '<B'
_PARTICIPANT_FORMAT = '<B3H3B32s2BHBB12B'

# Real F1 26 team ids (the 2026 grid plus F1 Generic), so the fixtures exercise
# ids the seeded telemetry.teams table actually knows about.
TEAM_IDS = [476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 41]


def _build_participant(
    car_index: int,
    name: str,
    team_id: int,
    race_number: int,
    ai_controlled: int = 0,
    your_telemetry: int = 1,
) -> bytes:
    """Build a single participant entry."""
    name_bytes = name.encode('utf-8')[:32].ljust(32, b'\x00')

    # Livery colors: 4 RGB tuples (12 bytes), use team-based colors
    r, g, b = (200 + car_index) % 256, (100 + car_index * 10) % 256, (50 + car_index * 20) % 256
    livery = [r, g, b] * 4

    return struct.pack(
        _PARTICIPANT_FORMAT,
        ai_controlled,     # ai_controlled
        car_index,         # driver_id (use car_index as driver_id)
        car_index,         # network_id
        team_id,           # team_id
        0,                 # my_team
        race_number,       # race_number
        1,                 # nationality (British)
        name_bytes,        # name (32 bytes)
        your_telemetry,    # 0 = Restricted, 1 = Public
        1,                 # show_online_names
        0,                 # tech_level (uint16)
        1,                 # platform (Steam)
        4,                 # num_colours
        *livery,           # livery_colours (12 bytes)
    )


def build_participants_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    num_drivers: int = 20,
    driver_names: list[str] | None = None,
    restricted_indices: set[int] | None = None,
) -> bytes:
    """
    Build a complete Participants packet (header + body).

    restricted_indices marks car indices whose driver has Your Telemetry set to
    Restricted, so tests can exercise the withheld-data paths.
    """
    header = build_header(
        packet_id=4,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )

    if driver_names is None:
        driver_names = [f"SimTestDriver_{i:02d}" for i in range(num_drivers)]

    restricted = restricted_indices or set()
    body = struct.pack(_NUM_ACTIVE_CARS_FORMAT, num_drivers)

    for i in range(MAX_CARS):
        if i < num_drivers:
            name = driver_names[i] if i < len(driver_names) else f"SimTestDriver_{i:02d}"
            team_id = TEAM_IDS[(i // 2) % len(TEAM_IDS)]
            race_number = i + 1
            body += _build_participant(
                i, name, team_id, race_number,
                your_telemetry=0 if i in restricted else 1,
            )
        else:
            body += _build_participant(i, "", 65535, 0, ai_controlled=1)

    return header + body
