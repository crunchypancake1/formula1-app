import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from packets.constants import MAX_CARS
from packets.lap_data import unpack_lap_data
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.lap_data import build_lap_data_packet


class TestLapDataParser:

    def test_22_cars_parsed(self):
        packet = build_lap_data_packet(
            session_uid=1, session_time=0.0, frame_id=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lap_data(header, body)
        assert len(result.lap_data) == MAX_CARS

    def test_lap_number_and_distance(self):
        packet = build_lap_data_packet(
            session_uid=1, session_time=10.0, frame_id=100,
            current_lap_num=3, lap_distance=1500.0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lap_data(header, body)
        car = result.lap_data[0]
        assert car.current_lap_num == 3
        assert car.lap_distance == pytest.approx(1500.0)

    def test_position_values(self):
        positions = list(range(1, 21)) + [0, 0]
        packet = build_lap_data_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            num_drivers=20, positions=positions,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lap_data(header, body)
        assert result.lap_data[0].car_position == 1
        assert result.lap_data[4].car_position == 5
        assert result.lap_data[19].car_position == 20

    def test_time_trial_indices(self):
        packet = build_lap_data_packet(
            session_uid=1, session_time=0.0, frame_id=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_lap_data(header, body)
        assert result.time_trial_pb_car_idx == 255
        assert result.time_trial_rival_car_idx == 255
