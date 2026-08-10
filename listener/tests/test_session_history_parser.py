import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header
from packets.session_history import unpack_session_history

from .packet_builder.session_history import build_session_history_packet


class TestSessionHistoryParser:

    def test_car_index(self):
        packet = build_session_history_packet(
            session_uid=1, session_time=100.0, frame_id=500,
            car_index=5,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session_history(header, body)
        assert result.car_index == 5

    def test_num_laps(self):
        packet = build_session_history_packet(
            session_uid=1, session_time=100.0, frame_id=500,
            car_index=0, num_laps=3,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session_history(header, body)
        assert result.num_laps == 3

    def test_lap_time_values(self):
        lap_times = [88000, 87500, 88200]
        packet = build_session_history_packet(
            session_uid=1, session_time=100.0, frame_id=500,
            car_index=0, num_laps=3, lap_times_ms=lap_times,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session_history(header, body)
        for i in range(3):
            assert result.lap_history_list[i].lap_time_in_ms > 0
        assert result.lap_history_list[0].lap_time_in_ms == 88000

    def test_validity_bit_flags(self):
        packet = build_session_history_packet(
            session_uid=1, session_time=100.0, frame_id=500,
            car_index=0, num_laps=3,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session_history(header, body)
        assert result.lap_history_list[0].lap_valid_bit_flags == 0x0F
