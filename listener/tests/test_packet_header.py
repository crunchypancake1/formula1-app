import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

import pytest

from packets.packet_header import (
    PACKET_HEADER_FORMAT_SIZE,
    PacketValidationError,
    unpack_packet_header,
    validate_packet_header,
)

from .packet_builder.header import build_header

_HEADER_FORMAT = '<HBBBBBQfIIBB'


class TestUnpackPacketHeader:

    def test_unpack_valid_header(self):
        raw = build_header(
            packet_id=6,
            session_uid=123456789,
            session_time=42.5,
            frame_identifier=100,
            overall_frame_identifier=200,
            player_car_index=3,
        )
        assert len(raw) == PACKET_HEADER_FORMAT_SIZE

        header = unpack_packet_header(raw)

        assert header.packet_format == 2025
        assert header.game_year == 25
        assert header.game_major_version == 1
        assert header.game_minor_version == 0
        assert header.packet_version == 1
        assert header.packet_id == 6
        assert header.session_uid == 123456789
        assert header.session_time == pytest.approx(42.5)
        assert header.frame_identifier == 100
        assert header.overall_frame_identifier == 200
        assert header.player_car_index == 3
        assert header.secondary_player_car_index == 255


class TestValidatePacketHeader:

    def test_validate_valid_header(self):
        raw = build_header(
            packet_id=0,
            session_uid=1,
            session_time=0.0,
            frame_identifier=0,
            overall_frame_identifier=0,
        )
        header = unpack_packet_header(raw)
        validate_packet_header(header)

    def test_validate_wrong_format(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2024, 25, 1, 0, 1, 0, 1, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="packet_format"):
            validate_packet_header(header)

    def test_validate_wrong_year(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2025, 24, 1, 0, 1, 0, 1, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="game_year"):
            validate_packet_header(header)

    def test_validate_invalid_packet_id(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2025, 25, 1, 0, 1, 16, 1, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="packet_id"):
            validate_packet_header(header)

    def test_validate_invalid_player_car_index(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2025, 25, 1, 0, 1, 0, 1, 0.0, 0, 0, 22, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="player_car_index"):
            validate_packet_header(header)
