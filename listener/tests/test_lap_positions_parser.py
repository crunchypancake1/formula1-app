import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.constants import MAX_CARS
from packets.lap_positions import unpack_lap_positions
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.lap_positions import build_lap_positions_packet


class TestLapPositionsParser:

    def test_num_laps_and_start(self):
        lap_positions = {
            0: [1, 2, 3] + [0] * 19,
            1: [2, 1, 3] + [0] * 19,
        }
        packet = build_lap_positions_packet(
            session_uid=1, session_time=100.0, frame_id=500,
            lap_positions=lap_positions, lap_start=5,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lap_positions(header, body)
        assert result.num_laps == 2
        assert result.lap_start == 5

    def test_positions_grid_shape(self):
        lap_positions = {0: [1] + [0] * (MAX_CARS - 1)}
        packet = build_lap_positions_packet(
            session_uid=1, session_time=100.0, frame_id=500,
            lap_positions=lap_positions,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lap_positions(header, body)
        assert len(result.positions) == 50
        for row in result.positions:
            assert len(row) == MAX_CARS

    def test_position_values(self):
        lap_positions = {
            0: [1, 2, 3, 4, 5] + [0] * 17,
        }
        packet = build_lap_positions_packet(
            session_uid=1, session_time=100.0, frame_id=500,
            lap_positions=lap_positions,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lap_positions(header, body)
        assert result.positions[0][0] == 1
        assert result.positions[0][1] == 2
        assert result.positions[0][4] == 5
        assert result.positions[1][0] == 0
