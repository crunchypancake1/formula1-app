import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

import pytest

from packets.packet_header import (
    EXPECTED_BODY_SIZE,
    PACKET_HEADER_FORMAT_SIZE,
    VARIABLE_LENGTH_PACKET_IDS,
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

        assert header.packet_format == 2026
        assert header.game_year == 26
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

    def test_validate_valid_header_max_player_car_index(self):
        raw = build_header(
            packet_id=0,
            session_uid=1,
            session_time=0.0,
            frame_identifier=0,
            overall_frame_identifier=0,
            player_car_index=23,
        )
        header = unpack_packet_header(raw)
        validate_packet_header(header)

    def test_validate_wrong_format(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2025, 26, 1, 0, 1, 0, 1, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="packet_format"):
            validate_packet_header(header)

    def test_validate_wrong_year(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2026, 25, 1, 0, 1, 0, 1, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="game_year"):
            validate_packet_header(header)

    def test_validate_invalid_packet_id(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2026, 26, 1, 0, 1, 17, 1, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="packet_id"):
            validate_packet_header(header)

    def test_validate_valid_packet_id_16(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2026, 26, 1, 0, 1, 16, 1, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)
        validate_packet_header(header)

    def test_validate_invalid_player_car_index(self):
        raw = struct.pack(
            _HEADER_FORMAT,
            2026, 26, 1, 0, 1, 0, 1, 0.0, 0, 0, 24, 255,
        )
        header = unpack_packet_header(raw)
        with pytest.raises(PacketValidationError, match="player_car_index"):
            validate_packet_header(header)

    def test_validate_wrong_format_logs_once_per_session(self, caplog):
        """The wrong-format rejection is only logged once per (session, format)."""
        raw = struct.pack(
            _HEADER_FORMAT,
            2025, 25, 1, 0, 1, 0, 999, 0.0, 0, 0, 0, 255,
        )
        header = unpack_packet_header(raw)

        with caplog.at_level("WARNING"):
            for _ in range(5):
                with pytest.raises(PacketValidationError):
                    validate_packet_header(header)

        warnings = [r for r in caplog.records if "Ignoring packetFormat" in r.message]
        assert len(warnings) == 1


class TestExpectedBodySize:

    def test_body_sizes_exclude_event_packet(self):
        assert 3 not in EXPECTED_BODY_SIZE

    def test_variable_length_ids(self):
        assert VARIABLE_LENGTH_PACKET_IDS == {8, 9, 11}

    def test_known_body_sizes(self):
        assert EXPECTED_BODY_SIZE[0] == 1296
        assert EXPECTED_BODY_SIZE[1] == 897
        assert EXPECTED_BODY_SIZE[2] == 1370
        assert EXPECTED_BODY_SIZE[4] == 1441
        assert EXPECTED_BODY_SIZE[5] == 1204
        assert EXPECTED_BODY_SIZE[6] == 1419
        assert EXPECTED_BODY_SIZE[7] == 1416
        assert EXPECTED_BODY_SIZE[8] == 1105
        assert EXPECTED_BODY_SIZE[9] == 1033
        assert EXPECTED_BODY_SIZE[10] == 1104
        assert EXPECTED_BODY_SIZE[11] == 1431
        assert EXPECTED_BODY_SIZE[12] == 202
        assert EXPECTED_BODY_SIZE[13] == 244
        assert EXPECTED_BODY_SIZE[14] == 75
        assert EXPECTED_BODY_SIZE[15] == 1202
        assert EXPECTED_BODY_SIZE[16] == 240
