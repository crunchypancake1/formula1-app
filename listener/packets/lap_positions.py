import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

_LAP_POSITIONS_HEADER_FORMAT = "<BB"
_LAP_POSITIONS_HEADER_SIZE = struct.calcsize(_LAP_POSITIONS_HEADER_FORMAT)
_MAX_LAPS = 50
_MAX_CARS = 22

@dataclass
class LapPositionsPacket:
    header: PacketHeader
    num_laps: int                   # uint8
    lap_start: int                  # uint8
    positions: list[list[int]]      # [50][22] positions, 0 if no record

def unpack_lap_positions(packet_header: PacketHeader, data: bytes) -> LapPositionsPacket:
    """
    Unpack Lap Positions packet (Packet ID: 15).

    Contains position grid at the start of each lap (50 laps x 22 cars).
    Used to construct lap-by-lap position charts. Sent periodically during session.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        LapPositionsPacket with position data for all laps and cars

    Raises:
        ValueError: If packet data is too short
    """
    if len(data) < 1102:
        raise ValueError("Lap positions packet is shorter than expected")

    num_laps, lap_start = struct.unpack(_LAP_POSITIONS_HEADER_FORMAT, data[:_LAP_POSITIONS_HEADER_SIZE])
    positions_bytes = data[_LAP_POSITIONS_HEADER_SIZE:_LAP_POSITIONS_HEADER_SIZE + (_MAX_LAPS * _MAX_CARS)]

    positions = []
    for i in range(_MAX_LAPS):
        row = list(positions_bytes[i * _MAX_CARS:(i + 1) * _MAX_CARS])
        positions.append(row)

    return LapPositionsPacket(packet_header, num_laps, lap_start, positions)
