import struct
from dataclasses import dataclass


class PacketValidationError(Exception):
    """Raised when packet header validation fails."""
    pass


_PACKET_HEADER_FORMAT = '<HBBBBBQfIIBB'
PACKET_HEADER_FORMAT_SIZE = struct.calcsize(_PACKET_HEADER_FORMAT)

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


def validate_packet_header(header: PacketHeader) -> None:
    """
    Validate that a packet header is from F1 25 game.

    This filters out random network broadcasts and other UDP traffic
    that might arrive on the same port but aren't F1 25 packets.

    Raises:
        PacketValidationError: If header values indicate non-F1 packet
    """
    if header.packet_format != 2025:
        raise PacketValidationError(f"Invalid packet_format: {header.packet_format} (expected 2025)")

    if header.game_year != 25:
        raise PacketValidationError(f"Invalid game_year: {header.game_year} (expected 25)")

    if header.packet_version != 1:
        raise PacketValidationError(f"Invalid packet_version: {header.packet_version} (expected 1)")

    if header.packet_id < 0 or header.packet_id > 15:
        raise PacketValidationError(f"Invalid packet_id: {header.packet_id} (expected 0-15)")

    if header.player_car_index > 21 and header.player_car_index != 255:
        raise PacketValidationError(f"Invalid player_car_index: {header.player_car_index}")
