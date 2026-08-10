import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

_LAP_DATA_FORMAT = '<2LHBHBHBHB3f15B2HBfB'
_LAP_DATA_FORMAT_SIZE = struct.calcsize(_LAP_DATA_FORMAT)

@dataclass
class LapData:
    last_lap_time_in_ms: int                    # uint32    |   Last lap time in milliseconds
    current_lap_time_in_ms: int                 # uint32    |   Current time around the lap in milliseconds
    sector1_time_ms_part: int                   # uint16    |   Sector 1 time milliseconds part
    sector1_time_minutes_part: int              # uint8     |   Sector 1 whole minute part
    sector2_time_ms_part: int                   # uint16    |   Sector 2 time milliseconds part
    sector2_time_minutes_part: int              # uint8     |   Sector 2 whole minute part
    delta_to_car_in_front_ms_part: int          # uint16    |   Time delta to car in front milliseconds part
    delta_to_car_in_front_minutes_part: int     # uint8     |   Time delta to car in front whole minute part
    delta_to_race_leader_ms_part: int           # uint16    |   Time delta to race leader milliseconds part
    delta_to_race_leader_minutes_part: int      # uint8     |   Time delta to race leader whole minute part
    lap_distance: float                         # float     |   Distance vehicle is around current lap in metres (Could be negative if line hasn’t been crossed yet)
    total_distance: float                       # float     |   Total distance travelled in session in metres (Could be negative if line hasn’t been crossed yet)
    safety_car_delta: float                     # float     |   Delta in seconds for safety car
    car_position: int                           # uint8     |   Car race position
    current_lap_num: int                        # uint8     |   Current lap number
    pit_status: int                             # uint8     |   0 = none, 1 = pitting, 2 = in pit area
    num_pit_stops: int                          # uint8     |   Number of pit stops taken in this race
    sector: int                                 # uint8     |   0 = sector1, 1 = sector2, 2 = sector3
    current_lap_invalid: int                    # uint8     |   Current lap invalid - 0 = valid, 1 = invalid
    penalties: int                              # uint8     |   Accumulated time penalties in seconds to be added
    total_warnings: int                         # uint8     |   Accumulated number of warnings issued
    corner_cutting_warnings: int                # uint8     |   Accumulated number of corner cutting warnings issued
    num_unserved_drive_through_pens: int        # uint8     |   Num drive through penalties left to serve
    num_unserved_stop_go_pens: int              # uint8     |   Num stop go penalties left to serve
    grid_position: int                          # uint8     |   Grid position the vehicle started the race in
    driver_status: int                          # uint8     |   Status of driver - 0 = in garage, 1 = flying lap, 2 = in lap, 3 = out lap, 4 = on track
    result_status: int                          # uint8     |   Result status - 0 = invalid, 1 = inactive, 2 = active, 3 = finished, 4 = did not finish, 5 = disqualified, 6 = not classified, 7 = retired
    pit_lane_timer_active: int                  # uint8     |   Pit lane timing, 0 = inactive, 1 = active
    pit_lane_time_in_lane_in_ms: int            # uint16    |   If active, the current time spent in the pit lane in ms
    pit_stop_timer_in_ms: int                   # uint16    |   Time of the actual pit stop in ms
    pit_stop_should_serve_pen: int              # uint8     |   Whether the car should serve a penalty at this stop
    speed_trap_fastest_speed: float             # float     |   Fastest speed through speed trap for this car in kmph
    speed_trap_fastest_lap: int                 # uint8     |   Lap no the fastest speed was achieved, 255 = not set

@dataclass # 1285 bytes
class LapDataPacket:
    header: PacketHeader                        #           |   Header
    lap_data: list[LapData]                     # [22]      |   Lap data for all cars on track. Length 22
    time_trial_pb_car_idx: int                  # uint8     |   Index of Personal Best car in time trial (255 if invalid)
    time_trial_rival_car_idx: int               # uint8     |   Index of Rival car in time trial (255 if invalid)

    def player_data(self):
        return self.lap_data[self.header.player_car_index]

def unpack_lap_data(packet_header: PacketHeader, data: bytes) -> LapDataPacket:
    """
    Unpack Lap Data packet (Packet ID: 2).

    Contains lap timing data for all 22 cars, including lap times, sectors,
    positions, pit status, and penalties. Sent at ~2Hz during session.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        LapDataPacket with lap data for all cars
    """
    lap_data_bytes = data[:(_LAP_DATA_FORMAT_SIZE * 22)]
    remaining_bytes = data[(_LAP_DATA_FORMAT_SIZE * 22):]

    lap_data_list = []

    for unpacked_lap_data in struct.iter_unpack(_LAP_DATA_FORMAT, lap_data_bytes):
        lap_data_list.append(LapData(*unpacked_lap_data))

    remaining_fields = struct.unpack('<BB', remaining_bytes)

    return LapDataPacket(packet_header, lap_data_list, *remaining_fields)
