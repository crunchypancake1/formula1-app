import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header
from packets.tyre_sets import unpack_tyre_sets

from .packet_builder.header import build_header

_TYRE_SET_FORMAT = '<7BhB'
_NUM_SETS = 20


def _build_tyre_set_bytes(
    actual_compound=18, visual_compound=16, wear=10,
    available=1, recommended_session=0, life_span=20, usable_life=15,
    lap_delta_time=0, fitted=0,
):
    return struct.pack(
        _TYRE_SET_FORMAT,
        actual_compound, visual_compound, wear,
        available, recommended_session, life_span, usable_life,
        lap_delta_time, fitted,
    )


def _build_full_packet(car_idx=0, fitted_idx=0, **set0_kwargs):
    header = build_header(
        packet_id=12,
        session_uid=100,
        session_time=1.0,
        frame_identifier=1,
        overall_frame_identifier=1,
    )
    body = struct.pack('<B', car_idx)
    body += _build_tyre_set_bytes(**set0_kwargs)
    zero_set = _build_tyre_set_bytes(
        actual_compound=0, visual_compound=0, wear=0,
        available=0, recommended_session=0, life_span=0, usable_life=0,
    )
    body += zero_set * (_NUM_SETS - 1)
    body += struct.pack('<B', fitted_idx)
    return header + body


class TestTyreSetsParser:

    def test_20_sets_parsed(self):
        packet = _build_full_packet()
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_tyre_sets(header, body)
        assert len(result.tyre_set_data) == 20

    def test_set_fields(self):
        packet = _build_full_packet(actual_compound=20, wear=15)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_tyre_sets(header, body)
        first = result.tyre_set_data[0]
        assert first.actual_compound == 20
        assert first.wear == 15

    def test_signed_lap_delta(self):
        packet = _build_full_packet(lap_delta_time=-500)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_tyre_sets(header, body)
        assert result.tyre_set_data[0].lap_delta_time == -500
