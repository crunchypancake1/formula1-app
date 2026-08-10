import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.final_classification import unpack_final_classification
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.final_classification import build_final_classification_packet


class TestFinalClassificationParser:

    def test_num_cars(self):
        packet = build_final_classification_packet(
            session_uid=1, session_time=300.0, frame_id=1000,
            num_drivers=20, total_laps=3,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_final_classification(header, body)
        assert result.num_cars == 20

    def test_position_and_laps(self):
        packet = build_final_classification_packet(
            session_uid=1, session_time=300.0, frame_id=1000,
            num_drivers=20, total_laps=3,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_final_classification(header, body)
        first = result.final_classifications[0]
        assert first.position == 1
        assert first.num_of_laps == 3

    def test_tyre_stints_arrays(self):
        packet = build_final_classification_packet(
            session_uid=1, session_time=300.0, frame_id=1000,
            num_drivers=20, total_laps=3,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_final_classification(header, body)
        first = result.final_classifications[0]
        assert isinstance(first.tyre_stints_actual, list)
        assert len(first.tyre_stints_actual) == 8
        assert isinstance(first.tyre_stints_visual, list)
        assert len(first.tyre_stints_visual) == 8
        assert isinstance(first.tyre_stints_end_laps, list)
        assert len(first.tyre_stints_end_laps) == 8

    def test_result_status_nonzero(self):
        packet = build_final_classification_packet(
            session_uid=1, session_time=300.0, frame_id=1000,
            num_drivers=20, total_laps=3,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_final_classification(header, body)
        for classification in result.final_classifications:
            assert classification.result_status > 0
