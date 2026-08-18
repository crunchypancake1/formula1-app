import logging
import struct
from dataclasses import dataclass

from utils.bounded_set import BoundedSet

logger = logging.getLogger(__name__)


class PacketValidationError(Exception):
    """Raised when packet header validation fails."""
    pass


_PACKET_HEADER_FORMAT = '<HBBBBBQfIIBB'
PACKET_HEADER_FORMAT_SIZE = struct.calcsize(_PACKET_HEADER_FORMAT)

# Expected body size (total packet size minus the 29-byte header) per
# packet_id, for the 2026 / 2026 Season Pack wire format. Packet 3 (Event) is
# variable-length and intentionally omitted — its size depends on the event
# details union and cannot be checked this way.
#
# Packets 8 (Final Classification), 9 (Lobby Info) and 11 (Session History)
# are also variable-length (car-count / entry-count dependent); the values
# below are their maximums, so validation against this table must treat them
# as upper bounds rather than exact matches. See VARIABLE_LENGTH_PACKET_IDS.
#
# NOTE: laid down here for the dispatcher (Task 7) to wire into per-packet
# size validation — not consumed anywhere in this file yet.
EXPECTED_BODY_SIZE: dict[int, int] = {
    0: 1296,   # Motion
    1: 897,    # Session
    2: 1370,   # Lap Data
    4: 1441,   # Participants
    5: 1204,   # Car Setups
    6: 1419,   # Car Telemetry
    7: 1416,   # Car Status
    8: 1105,   # Final Classification (MAX; variable-length)
    9: 1033,   # Lobby Info (MAX; variable-length)
    10: 1104,  # Car Damage
    11: 1431,  # Session History (MAX; variable-length) — unchanged from F1 25
    12: 202,   # Tyre Sets — unchanged from F1 25
    13: 244,   # Motion Ex
    14: 75,    # Time Trial
    15: 1202,  # Lap Positions
    16: 240,   # Car Telemetry 2
}

# Packet IDs whose body size is a maximum (car-count / entry-count
# dependent), not an exact match, in EXPECTED_BODY_SIZE.
VARIABLE_LENGTH_PACKET_IDS = {8, 9, 11}

@dataclass
class PacketHeader:
    packet_format: int               # uint16    |    2025
    game_year: int                   # uint8     |    Game year - last two digits e.g. 25
    game_major_version: int          # uint8     |    Game major version - "X.00"
    game_minor_version: int          # uint8     |    Game minor version - "1.XX"
    packet_version: int              # uint8     |    Version of this packet type, all start from 1
    packet_id: int                   # uint8     |    Identifier for the packet type, see below
    session_uid: int                 # uint64    |    Unique identifier for the session
    session_time: float              # float     |    Session timestamp
    frame_identifier: int            # uint32    |    Identifier for the frame the data was retrieved on
    overall_frame_identifier: int    # uint32    |    Overall identifier for the frame the data was retrieved on, doesn't go back after flashbacks
    player_car_index: int            # uint8     |    Index of player's car in the array
    secondary_player_car_index: int  # uint8     |    Index of secondary player's car in the array (splitscreen) 255 if no second player

def unpack_packet_header(data: bytes) -> PacketHeader:
    """
    Unpack packet header from UDP data.

    The header is present at the start of every UDP packet (29 bytes).
    Contains session_uid, packet_id, timestamps, and frame identifiers.

    Args:
        data: Raw packet header bytes (29 bytes)

    Returns:
        PacketHeader with all header fields populated
    """
    unpacked_packet_header = struct.unpack(_PACKET_HEADER_FORMAT, data)
    return PacketHeader(*unpacked_packet_header)


# Tracks (session_uid, packet_format) pairs that have already produced a
# "wrong format" rejection log line, so a mismatched game (e.g. still on the
# F1 25 / 2025 UDP format) logs once per session instead of once per packet
# — the game can emit ~1000 packets/sec.
_logged_format_rejections = BoundedSet(max_size=200)


def _log_format_rejection_once(header: "PacketHeader") -> None:
    key = (header.session_uid, header.packet_format)
    if key in _logged_format_rejections:
        return
    _logged_format_rejections.add(key)
    logger.warning(
        "Ignoring packetFormat %s — set UDP Format to 2026 in Game Options "
        "→ Settings → UDP Telemetry Settings.",
        header.packet_format,
    )


def validate_packet_header(header: PacketHeader) -> None:
    """
    Validate that a packet header is from F1 26 (2026 Season Pack) game.

    This filters out random network broadcasts and other UDP traffic
    that might arrive on the same port but aren't F1 26 packets.

    Raises:
        PacketValidationError: If header values indicate non-F1 packet
    """
    if header.packet_format != 2026:
        _log_format_rejection_once(header)
        raise PacketValidationError(f"Invalid packet_format: {header.packet_format} (expected 2026)")

    if header.game_year != 26:
        _log_format_rejection_once(header)
        raise PacketValidationError(f"Invalid game_year: {header.game_year} (expected 26)")

    if header.packet_version != 1:
        raise PacketValidationError(f"Invalid packet_version: {header.packet_version} (expected 1)")

    if header.packet_id < 0 or header.packet_id > 16:
        raise PacketValidationError(f"Invalid packet_id: {header.packet_id} (expected 0-16)")

    if header.player_car_index > 23 and header.player_car_index != 255:
        raise PacketValidationError(f"Invalid player_car_index: {header.player_car_index}")
