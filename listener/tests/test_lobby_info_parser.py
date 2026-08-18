import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

from packets.lobby_info import _LOBBY_PLAYER_FORMAT, unpack_lobby_info
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.header import build_header


def _build_lobby_player_bytes(
    ai_controlled=0,
    team_id=0,
    nationality=0,
    platform=1,
    name=b"",
    car_number=0,
    your_telemetry=1,
    show_online_names=1,
    tech_level=0,
    ready_status=0,
):
    name_bytes = name.ljust(32, b'\x00')
    return struct.pack(
        _LOBBY_PLAYER_FORMAT,
        ai_controlled,
        team_id,
        nationality,
        platform,
        name_bytes,
        car_number,
        your_telemetry,
        show_online_names,
        tech_level,
        ready_status,
    )


def _build_full_packet(num_players=1, **player0_kwargs):
    header = build_header(
        packet_id=9,
        session_uid=1,
        session_time=0.0,
        frame_identifier=0,
        overall_frame_identifier=0,
    )
    body = struct.pack('<B', num_players)
    body += _build_lobby_player_bytes(**player0_kwargs)
    return header + body


class TestLobbyInfoParser:

    def test_team_id_uint16_round_trips(self):
        # team_id widened from uint8 to uint16 -- pack a value that
        # overflows a uint8 to prove the width and field order are correct.
        packet = _build_full_packet(
            num_players=1,
            ai_controlled=1,
            team_id=486,
            nationality=7,
            platform=3,
            name=b"SentinelPlayer",
            car_number=44,
            your_telemetry=0,
            show_online_names=1,
            tech_level=9999,
            ready_status=2,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lobby_info(header, body)

        assert result.num_players == 1
        player = result.lobby_players[0]
        assert player.ai_controlled == 1
        assert player.team_id == 486
        assert player.nationality == 7
        assert player.platform == 3
        assert player.m_name == "SentinelPlayer"
        assert player.car_number == 44
        assert player.your_telemetry == 0
        assert player.show_online_names == 1
        assert player.tech_level == 9999
        assert player.ready_status == 2

    def test_team_id_max_uint16(self):
        packet = _build_full_packet(num_players=1, team_id=65535)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lobby_info(header, body)
        assert result.lobby_players[0].team_id == 65535
