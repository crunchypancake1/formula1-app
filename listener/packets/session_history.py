import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

_LAP_HISTORY_FORMAT = "<LHBHBHBB"
_LAP_HISTORY_FORMAT_SIZE = struct.calcsize(_LAP_HISTORY_FORMAT)
@dataclass
class LapHistory:
    lap_time_in_ms: int                # uint32    |   Lap time in milliseconds
    sector_1_time_ms_part: int         # uint16    |   Sector 1 milliseconds part
    sector_1_time_minutes_part: int    # uint8     |   Sector 1 whole minute part
    sector_2_time_ms_part: int         # uint16    |   Sector 2 time milliseconds part
    sector_2_time_minutes_part: int    # uint8     |   Sector 2 whole minute part
    sector_3_time_ms_part: int         # uint16    |   Sector 3 time milliseconds part
    sector_3_time_minutes_part: int    # uint8     |   Sector 3 whole minute part
    lap_valid_bit_flags: int           # uint8     |   0x01 bit set-lap valid, 0x02 bit set-sector 1 valid, 0x04 bit set-sector 2 valid, 0x08 bit set-sector 3 valid

_TYRE_STINT_HISTORY_FORMAT = "<3B"
@dataclass
class TyreStintHistory:
    end_lap: int                       # uint8     |   Lap the tyre usage ends on (255 if current tyre)
    tyre_actual_compound: int          # uint8     |   Actual tyres used by this driver
    tyre_visual_compound: int          # uint8     |   Visual tyres used by this driver


@dataclass
class SessionHistoryPacket:
    header: PacketHeader               #           |   Header
    car_index: int                     # uint8     |   Index of the car this lap data relates to
    num_laps: int                      # uint8     |   Number of laps in the data (including current partial lap)
    num_tyre_stints: int               # uint8     |   Number of tyre stints in t
    best_lap_time_lap_num: int         # uint8     |   Lap the best lap time was achieved on
    best_sector_1_lap_num: int         # uint8     |   Lap the best Sector 1 time was achieved on
    best_sector_2_lap_num: int         # uint8     |   Lap the best Sector 2 time was achieved on
    best_sector_3_lap_num: int         # uint8     |   Lap the best Sector 3 time was achieved on
    lap_history_list: list[LapHistory] #           |   100 laps of data max
    tyre_stints_list: list[TyreStintHistory] #     |   Up to 8 tyre stints

def unpack_session_history(packet_header: PacketHeader, data: bytes) -> SessionHistoryPacket:
    """
    Unpack Session History packet (Packet ID: 11).

    Contains lap history (up to 100 laps) and tyre stint history (up to 8 stints)
    for a single car. Sent at ~20Hz cycling through all cars.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        SessionHistoryPacket with lap and tyre stint history for one car
    """
    # Simple fields
    simple_fields_format = '<7B'
    simple_fields_format_size = struct.calcsize(simple_fields_format)

    simple_fields = struct.unpack('<7B', data[:simple_fields_format_size])

    # Lap History Data
    lap_history_list_format_size = (_LAP_HISTORY_FORMAT_SIZE * 100)
    lap_history_bytes = data[simple_fields_format_size:simple_fields_format_size + lap_history_list_format_size]

    lap_history_list = []

    for unpacked_lap_history in struct.iter_unpack(_LAP_HISTORY_FORMAT, lap_history_bytes):
        lap_history_list.append(LapHistory(*unpacked_lap_history))

    # Tyre Stints History
    tyre_stint_bytes = data[simple_fields_format_size + lap_history_list_format_size:]

    tyre_stints_list = []

    for unpacked_tyre_stints in struct.iter_unpack(_TYRE_STINT_HISTORY_FORMAT, tyre_stint_bytes):
        tyre_stints_list.append(TyreStintHistory(*unpacked_tyre_stints))

    return SessionHistoryPacket(packet_header, *simple_fields, lap_history_list=lap_history_list, tyre_stints_list=tyre_stints_list)
