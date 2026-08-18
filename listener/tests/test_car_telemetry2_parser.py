import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.car_telemetry2 import unpack_car_telemetry2
from packets.constants import MAX_CARS
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.car_telemetry2 import build_car_telemetry2_packet


class TestCarTelemetry2Parser:

    def test_packet_total_size_is_269_bytes(self):
        packet = build_car_telemetry2_packet(
            session_uid=100, session_time=1.0, frame_id=1, num_drivers=MAX_CARS,
        )
        assert len(packet) == 269

    def test_max_cars_parsed(self):
        packet = build_car_telemetry2_packet(
            session_uid=100, session_time=1.0, frame_id=1, num_drivers=MAX_CARS,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_telemetry2(header, body)
        assert len(result.car_telemetry2_data) == MAX_CARS

    def test_round_trip_sentinel_values_car_0_and_car_23(self):
        packet = build_car_telemetry2_packet(
            session_uid=100, session_time=1.0, frame_id=1, num_drivers=MAX_CARS,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_telemetry2(header, body)

        # car 0 -- builder emits: active_aero_mode=i%2, active_aero_available=1,
        # active_aero_activation_distance=100+i, overtake_available=1,
        # overtake_active=i%2, overtake_activation_distance=200+i,
        # regulations_2026=1, driving_wrong_way=i%2
        car0 = result.car_telemetry2_data[0]
        assert car0.active_aero_mode == 0
        assert car0.active_aero_available == 1
        assert car0.active_aero_activation_distance == 100
        assert car0.overtake_available == 1
        assert car0.overtake_active == 0
        assert car0.overtake_activation_distance == 200
        assert car0.regulations_2026 == 1
        assert car0.driving_wrong_way == 0

        # car 23 -- catches a MAX_CARS slicing bug
        car23 = result.car_telemetry2_data[23]
        assert car23.active_aero_mode == 23 % 2
        assert car23.active_aero_available == 1
        assert car23.active_aero_activation_distance == 100 + 23
        assert car23.overtake_available == 1
        assert car23.overtake_active == 23 % 2
        assert car23.overtake_activation_distance == 200 + 23
        assert car23.regulations_2026 == 1
        assert car23.driving_wrong_way == 23 % 2

    def test_beyond_num_drivers_is_zero_filled(self):
        packet = build_car_telemetry2_packet(
            session_uid=100, session_time=1.0, frame_id=1, num_drivers=20,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_telemetry2(header, body)
        car20 = result.car_telemetry2_data[20]
        assert car20.active_aero_mode == 0
        assert car20.active_aero_available == 0
        assert car20.active_aero_activation_distance == 0
        assert car20.overtake_available == 0
        assert car20.overtake_active == 0
        assert car20.overtake_activation_distance == 0
        assert car20.regulations_2026 == 0
        assert car20.driving_wrong_way == 0
