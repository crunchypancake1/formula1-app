import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header
from packets.participants import unpack_participants

from .packet_builder.participants import build_participants_packet


class TestParticipantsParser:

    def test_num_active_cars(self):
        packet = build_participants_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            num_drivers=20,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_participants(header, body)
        assert result.num_active_cars == 20

    def test_22_participants_parsed(self):
        packet = build_participants_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            num_drivers=20,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_participants(header, body)
        assert len(result.participants) == 22

    def test_human_driver_names(self):
        packet = build_participants_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            num_drivers=20,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_participants(header, body)
        assert result.participants[0].name.startswith("SimTestDriver_")

    def test_ai_drivers_flagged(self):
        packet = build_participants_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            num_drivers=20,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_participants(header, body)
        for i in range(20):
            assert result.participants[i].ai_controlled == 0
        for i in range(20, 22):
            assert result.participants[i].ai_controlled == 1

    def test_livery_colours_grouping(self):
        packet = build_participants_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            num_drivers=20,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_participants(header, body)
        colours = result.participants[0].livery_colours
        assert len(colours) == 4
        for colour in colours:
            assert isinstance(colour, tuple)
            assert len(colour) == 3
            for component in colour:
                assert isinstance(component, int)
