"""Event packet builders (Packet ID 3)."""

import struct

from .header import build_header


def _build_event_packet(
    session_uid: int,
    session_time: float,
    frame_id: int,
    event_code: str,
    event_body: bytes = b'',
) -> bytes:
    """Build a generic event packet with the given 4-char code and body."""
    header = build_header(
        packet_id=3,
        session_uid=session_uid,
        session_time=session_time,
        frame_identifier=frame_id,
        overall_frame_identifier=frame_id,
    )
    code_bytes = event_code.encode('ascii')[:4]
    body = struct.pack('<4B', *code_bytes) + event_body
    return header + body


def build_event_ssta(session_uid: int, session_time: float, frame_id: int) -> bytes:
    """Session Started event."""
    return _build_event_packet(session_uid, session_time, frame_id, "SSTA")


def build_event_send(session_uid: int, session_time: float, frame_id: int) -> bytes:
    """Session Ended event."""
    return _build_event_packet(session_uid, session_time, frame_id, "SEND")


def build_event_chqf(session_uid: int, session_time: float, frame_id: int) -> bytes:
    """Chequered Flag event."""
    return _build_event_packet(session_uid, session_time, frame_id, "CHQF")


def build_event_lgot(session_uid: int, session_time: float, frame_id: int) -> bytes:
    """Lights Out event."""
    return _build_event_packet(session_uid, session_time, frame_id, "LGOT")


def build_event_ovtk(
    session_uid: int,
    session_time: float,
    frame_id: int,
    overtaking_index: int,
    overtaken_index: int,
) -> bytes:
    """Overtake event."""
    event_body = struct.pack('<2B', overtaking_index, overtaken_index)
    return _build_event_packet(session_uid, session_time, frame_id, "OVTK", event_body)


def build_event_sptp(
    session_uid: int,
    session_time: float,
    frame_id: int,
    vehicle_index: int,
    speed: float = 310.5,
) -> bytes:
    """Speed Trap event."""
    event_body = struct.pack(
        '<Bf3Bf',
        vehicle_index,
        speed,
        1,                  # is_overall_fastest
        1,                  # is_driver_fastest
        vehicle_index,      # fastest_vehicle_index
        speed,              # fastest_speed
    )
    return _build_event_packet(session_uid, session_time, frame_id, "SPTP", event_body)


def build_event_ftlp(
    session_uid: int,
    session_time: float,
    frame_id: int,
    vehicle_index: int,
    lap_time: float = 88.5,
) -> bytes:
    """Fastest Lap event."""
    event_body = struct.pack('<Bf', vehicle_index, lap_time)
    return _build_event_packet(session_uid, session_time, frame_id, "FTLP", event_body)


def build_event_pena(
    session_uid: int,
    session_time: float,
    frame_id: int,
    vehicle_index: int,
    other_vehicle_index: int = 255,
) -> bytes:
    """Penalty event."""
    event_body = struct.pack(
        '<7B',
        0,                      # penalty_type (warning)
        3,                      # infringement_type (corner cutting)
        vehicle_index,
        other_vehicle_index,
        5,                      # time (seconds)
        1,                      # lap_num
        0,                      # places_gained
    )
    return _build_event_packet(session_uid, session_time, frame_id, "PENA", event_body)


def build_event_coll(
    session_uid: int,
    session_time: float,
    frame_id: int,
    vehicle_1_index: int,
    vehicle_2_index: int,
) -> bytes:
    """Collision event."""
    event_body = struct.pack('<2B', vehicle_1_index, vehicle_2_index)
    return _build_event_packet(session_uid, session_time, frame_id, "COLL", event_body)


def build_event_scar(
    session_uid: int,
    session_time: float,
    frame_id: int,
    safety_car_type: int = 3,
    event_type: int = 3,
) -> bytes:
    """Safety Car event (SCAR). Default values signal formation lap end / race start."""
    event_body = struct.pack('<2B', safety_car_type, event_type)
    return _build_event_packet(session_uid, session_time, frame_id, "SCAR", event_body)


def build_event_rcwn(
    session_uid: int,
    session_time: float,
    frame_id: int,
    vehicle_index: int,
) -> bytes:
    """Race Winner event."""
    event_body = struct.pack('<B', vehicle_index)
    return _build_event_packet(session_uid, session_time, frame_id, "RCWN", event_body)
