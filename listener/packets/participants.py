import struct
from dataclasses import dataclass

from .packet_header import PacketHeader

_PARTICIPANT_FORMAT = '<7B32s2BHBB12B'
PARTICIPANT_DATA_SIZE = struct.calcsize(_PARTICIPANT_FORMAT)
MAX_CARS = 22

@dataclass
class Participant:
    ai_controlled: int                      # uint8     |   Whether the vehicle is AI (1) or Human (0) controlled
    driver_id: int                          # uint8     |   Driver id - see appendix, 255 if network human
    network_id: int                         # uint8     |   Network id – unique identifier for network players
    team_id: int                            # uint8     |   Team id - see appendix
    my_team: int                            # uint8     |   My team flag – 1 = My Team, 0 = otherwise
    race_number: int                        # uint8     |   Race number of the car
    nationality: int                        # uint8     |   Nationality of the driver
    name: str                               # char      |   Name of participant in UTF-8 format – null terminated (m_name[32]). Will be truncated with … (U+2026) if too long
    your_telemetry: int                     # uint8     |   The player's UDP setting, 0 = restricted, 1 = public
    show_online_names: int                  # uint8     |   The player's show online names setting, 0 = off, 1 = on
    tech_level: int                         # uint16    |   F1 World tech level
    platform: int                           # uint8     |   1 = Steam, 3 = PlayStation, 4 = Xbox, 6 = Origin, 255 = unknown
    num_colours: int                        # uint8     |   Number of colours valid for this car
    livery_colours: list[tuple]             #           |   4 RGB tuples

_NUM_ACTIVE_CARS_FORMAT = '<B'
_NUM_ACTIVE_CARS_FORMAT_SIZE = struct.calcsize(_NUM_ACTIVE_CARS_FORMAT)
@dataclass # 1350 bytes
class ParticipantsPacket:
    header: PacketHeader                    #           |   Header
    num_active_cars: int                    # uint8     |   Number of active cars in the data – should match number of cars on HUD
    participants: list[Participant]         #           |   List of participants

def unpack_participants(packet_header: PacketHeader, data: bytes) -> ParticipantsPacket:
    """
    Unpack Participants packet (Packet ID: 4).

    Contains driver roster for the session - names, teams, nationalities,
    AI status, etc. for all 22 cars. Sent every ~5 seconds.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        ParticipantsPacket with participant data for all cars
    """
    num_active_cars = struct.unpack(_NUM_ACTIVE_CARS_FORMAT, data[:_NUM_ACTIVE_CARS_FORMAT_SIZE])[0]

    participants_list = []

    for unpacked_participant in struct.iter_unpack(_PARTICIPANT_FORMAT, data[_NUM_ACTIVE_CARS_FORMAT_SIZE:]):
        name = unpacked_participant[7].rstrip(b'\x00').decode('utf-8')
        livery_values = unpacked_participant[13:]
        colours = [tuple(livery_values[i:i + 3]) for i in range(0, 12, 3)]
        participant = Participant(
            ai_controlled=unpacked_participant[0],
            driver_id=unpacked_participant[1],
            network_id=unpacked_participant[2],
            team_id=unpacked_participant[3],
            my_team=unpacked_participant[4],
            race_number=unpacked_participant[5],
            nationality=unpacked_participant[6],
            name=name,
            your_telemetry=unpacked_participant[8],
            show_online_names=unpacked_participant[9],
            tech_level=unpacked_participant[10],
            platform=unpacked_participant[11],
            num_colours=unpacked_participant[12],
            livery_colours=colours,
        )

        participants_list.append(participant)

    return ParticipantsPacket(packet_header, num_active_cars, participants_list)
