import struct
from dataclasses import dataclass

from .constants import MAX_CARS
from .packet_header import PacketHeader

_LOBBY_PLAYER_FORMAT = '<BH2B32s3BHB'
LOBBY_PLAYER_DATA_SIZE = struct.calcsize(_LOBBY_PLAYER_FORMAT)
MAX_LOBBY_PLAYERS = MAX_CARS

@dataclass
class LobbyPlayer:
    ai_controlled: int                      # uint8     |   Whether the vehicle is AI (1) or Human (0) controlled
    team_id: int                            # uint16    |   Team id - see appendix
    nationality: int                        # uint8     |   Nationality of the driver
    platform: int                           # uint8     |   1 = Steam, 3 = PlayStation, 4 = Xbox, 6 = Origin, 255 = unknown
    m_name: str                             # char[32]  |   Name of participant in UTF-8 format - null terminated
    car_number: int                         # uint8     |   Car number of the player
    your_telemetry: int                     # uint8     |   The player's UDP setting, 0 = restricted, 1 = public
    show_online_names: int                  # uint8     |   The player's show online names setting, 0 = off, 1 = on
    tech_level: int                         # uint16    |   F1 World tech level
    ready_status: int                       # uint8     |   0 = not ready, 1 = ready, 2 = spectating

_NUM_PLAYERS_FORMAT = '<B'
_NUM_PLAYERS_FORMAT_SIZE = struct.calcsize(_NUM_PLAYERS_FORMAT)

@dataclass
class LobbyInfoPacket:
    header: PacketHeader                    #           |   Header
    num_players: int                        # uint8     |   Number of players in the lobby data
    lobby_players: list[LobbyPlayer]       #           |   List of lobby players

def unpack_lobby_info(packet_header: PacketHeader, data: bytes) -> LobbyInfoPacket:
    """
    Unpack Lobby Info packet (Packet ID: 9).

    Contains lobby information for all players in a multiplayer session.
    Sent every ~5 seconds while in the lobby.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        LobbyInfoPacket with lobby player data for all players
    """
    num_players = struct.unpack(_NUM_PLAYERS_FORMAT, data[:_NUM_PLAYERS_FORMAT_SIZE])[0]

    lobby_players_list = []

    for unpacked_player in struct.iter_unpack(_LOBBY_PLAYER_FORMAT, data[_NUM_PLAYERS_FORMAT_SIZE:]):
        name = unpacked_player[4].rstrip(b'\x00').decode('utf-8')
        player = LobbyPlayer(
            ai_controlled=unpacked_player[0],
            team_id=unpacked_player[1],
            nationality=unpacked_player[2],
            platform=unpacked_player[3],
            m_name=name,
            car_number=unpacked_player[5],
            your_telemetry=unpacked_player[6],
            show_online_names=unpacked_player[7],
            tech_level=unpacked_player[8],
            ready_status=unpacked_player[9],
        )

        lobby_players_list.append(player)

    return LobbyInfoPacket(packet_header, num_players, lobby_players_list)
