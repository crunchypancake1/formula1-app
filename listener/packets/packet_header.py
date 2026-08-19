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
# packet_id, for the 2026 Season Pack wire format. Consumed by
# PacketDispatcher._validate_body_size.
#
# Packet 3 (Event) is intentionally omitted: its size depends on which member
# of the event details union is present, so it cannot be checked this way.
#
# Packets 8 (Final Classification), 9 (Lobby Info) and 11 (Session History) are
# car-count / entry-count dependent; the values below are their maximums, so
# they are validated as upper bounds. See VARIABLE_LENGTH_PACKET_IDS.
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
    11: 1431,  # Session History (MAX; variable-length)
    12: 202,   # Tyre Sets
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
    packet_format: int               # uint16    |    2026
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
# "wrong format" rejection log line, so a game left on an older UDP format logs
# once per session instead of once per packet — it can emit ~1000 packets/sec.
_logged_format_rejections = BoundedSet(max_size=200)

# Same idea for an unexpected per-packet version.
_logged_version_warnings = BoundedSet(max_size=200)

# Highest packet id in the 2026 Season Pack (16 = Car Telemetry 2).
MAX_PACKET_ID = 16

# Highest valid car index (24 cars), plus the "no player" sentinel.
MAX_CAR_INDEX = 23
NO_PLAYER_CAR_INDEX = 255

EXPECTED_PACKET_VERSION = 1


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

    if header.packet_id < 0 or header.packet_id > MAX_PACKET_ID:
        raise PacketValidationError(
            f"Invalid packet_id: {header.packet_id} (expected 0-{MAX_PACKET_ID})"
        )

    if header.player_car_index > MAX_CAR_INDEX and header.player_car_index != NO_PLAYER_CAR_INDEX:
        raise PacketValidationError(f"Invalid player_car_index: {header.player_car_index}")

    # m_packetVersion exists so EA can revise one packet type in a patch. An
    # unexpected version is worth knowing about, but rejecting the packet would
    # take that packet type silently dark the day it changes — so log once per
    # (session, packet id) and carry on parsing.
    if header.packet_version != EXPECTED_PACKET_VERSION:
        key = (header.session_uid, header.packet_id, header.packet_version)
        if key not in _logged_version_warnings:
            _logged_version_warnings.add(key)
            logger.warning(
                "packet_id %s has version %s (expected %s) — parsing anyway; "
                "check the spec if fields look wrong.",
                header.packet_id, header.packet_version, EXPECTED_PACKET_VERSION,
            )
