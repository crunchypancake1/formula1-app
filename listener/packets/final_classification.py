import struct
from dataclasses import dataclass

from .constants import MAX_CARS
from .packet_header import PacketHeader

_MAX_TYRE_STINTS = 8
_FINAL_CLASSIFICATION_FORMAT = f'<7BLd3B{_MAX_TYRE_STINTS * 3}B'
_FINAL_CLASSIFICATION_FORMAT_SIZE = struct.calcsize(_FINAL_CLASSIFICATION_FORMAT)

@dataclass
class FinalClassification:
    position: int                           # uint8     |    Finishing position
    num_of_laps: int                        # uint8     |    Number of laps completed
    grid_position: int                      # uint8     |    Grid position of the car
    points: int                             # uint8     |    Number of points scored
    num_pit_stops: int                      # uint8     |    Number of pit stops made
    result_status: int                      # uint8     |    Result status - 0 = invalid, 1 = inactive, 2 = active, 3 = finished, 4 = didnotfinish, 5 = disqualified, 6 = not classified, 7 = retired
    result_reason: int                      # uint8     |    Result reason - 0 = invalid, 1 = retired, 2 = finished, 3 = terminal damage, 4 = inactive, 5 = not enough laps completed, 6 = black flagged
                                            #             7 = red flagged, 8 = mechanical failure, 9 = session skipped, 10 = session simulated
    best_lap_time_in_ms: int                # uint32    |    Best lap time of the session in milliseconds
    total_race_time: float                  # double    |    Total race time in seconds without penalties
    penalties_time: int                     # uint8     |    Total penalties accumulated in seconds
    num_of_penalties: int                   # uint8     |    Number of penalties applied to this driver
    num_of_tyre_stints: int                 # uint8     |    Number of tyre stints up to maximum
    tyre_stints_actual: list[int]           # uint8[8]  |    Actual tyres used by this driver
    tyre_stints_visual: list[int]           # uint8[8]  |    Visual tyres used by this driver
    tyre_stints_end_laps: list[int]         # uint8[8]  |    The lap number stints end on

@dataclass
class FinalClassificationPacket:
    header: PacketHeader                    #           |   Header
    num_cars: int                           # uint8     |   Number of cars in the final classification
    final_classifications: list[FinalClassification]#  |   List of final classification data for all cars

def unpack_final_classification(packet_header: PacketHeader, data: bytes) -> FinalClassificationPacket:
    """
    Unpack Final Classification packet (Packet ID: 8).

    Contains final race/qualifying results for all cars including positions,
    lap times, pit stops, penalties, and tyre stint data. Sent at session end.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        FinalClassificationPacket with results for all cars
    """
    uint8_format = '<B'
    uint8_size = struct.calcsize(uint8_format)

    # Car Index
    num_cars = min(struct.unpack(uint8_format, data[:uint8_size])[0], MAX_CARS)

    # Tyre Sets
    final_classification_list_format_size = (_FINAL_CLASSIFICATION_FORMAT_SIZE * num_cars)
    final_classification_list_bytes = data[uint8_size:uint8_size + final_classification_list_format_size]

    final_classification_list = []

    for unpacked_final_classification in struct.iter_unpack(_FINAL_CLASSIFICATION_FORMAT, final_classification_list_bytes):
        tyre_stint_values = unpacked_final_classification[-(_MAX_TYRE_STINTS * 3):]
        tyre_stints_actual = list(tyre_stint_values[:_MAX_TYRE_STINTS])
        tyre_stints_visual = list(tyre_stint_values[_MAX_TYRE_STINTS:_MAX_TYRE_STINTS * 2])
        tyre_stints_end_laps = list(tyre_stint_values[_MAX_TYRE_STINTS * 2:])
        fields = unpacked_final_classification[:12]
        final_classification_list.append(
            FinalClassification(
                position=fields[0],
                num_of_laps=fields[1],
                grid_position=fields[2],
                points=fields[3],
                num_pit_stops=fields[4],
                result_status=fields[5],
                result_reason=fields[6],
                best_lap_time_in_ms=fields[7],
                total_race_time=fields[8],
                penalties_time=fields[9],
                num_of_penalties=fields[10],
                num_of_tyre_stints=fields[11],
                tyre_stints_actual=tyre_stints_actual,
                tyre_stints_visual=tyre_stints_visual,
                tyre_stints_end_laps=tyre_stints_end_laps,
            )
        )

    return FinalClassificationPacket(packet_header, num_cars, final_classification_list)
