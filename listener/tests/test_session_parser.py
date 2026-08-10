import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header
from packets.session import unpack_session

from .packet_builder.session import build_session_packet


class TestSessionParser:

    def test_track_id_and_session_type(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            track_id=11, session_type=15,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert result.track_id == 11
        assert result.session_type == 15

    def test_weather_fields(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            weather=2, track_temperature=35, air_temperature=28,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert result.weather == 2
        assert result.track_temperature == 35
        assert result.air_temperature == 28

    def test_total_laps_and_track_length(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            total_laps=50, track_length=5793,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert result.total_laps == 50
        assert result.track_length == 5793

    def test_marshal_zones_count(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert len(result.marshal_zones) == 21

    def test_weather_forecast_samples_count(self):
        packet = build_session_packet(
            session_uid=1, session_time=0.0, frame_id=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_session(header, body)
        assert len(result.weather_forecast_samples) == 64
