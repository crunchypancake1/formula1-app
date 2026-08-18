import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

from packets.constants import MAX_CARS
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header
from packets.participants import _PARTICIPANT_FORMAT, unpack_participants

from .packet_builder.header import build_header
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

    def test_max_cars_participants_parsed(self):
        packet = build_participants_packet(
            session_uid=1, session_time=0.0, frame_id=0,
            num_drivers=20,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_participants(header, body)
        assert len(result.participants) == MAX_CARS

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
        for i in range(20, MAX_CARS):
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

    def test_widened_uint16_fields_round_trip(self):
        # driver_id/network_id/team_id are now uint16 -- pack a value (300)
        # that overflows a uint8 to prove the widths and field order are
        # correct and no index-shift corrupted a neighbouring field.
        header = build_header(
            packet_id=4, session_uid=1, session_time=0.0,
            frame_identifier=0, overall_frame_identifier=0,
        )
        name_bytes = b"SentinelDriver".ljust(32, b'\x00')
        participant_bytes = struct.pack(
            _PARTICIPANT_FORMAT,
            1,          # ai_controlled
            300,        # driver_id (uint16, overflows uint8)
            301,        # network_id (uint16, overflows uint8)
            302,        # team_id (uint16, overflows uint8)
            1,          # my_team
            44,         # race_number
            7,          # nationality
            name_bytes, # name
            1,          # your_telemetry
            0,          # show_online_names
            9999,       # tech_level
            3,          # platform
            4,          # num_colours
            *([1, 2, 3] * 4),  # livery_colours
        )
        body = struct.pack('<B', 1) + participant_bytes
        result = unpack_participants(header, body)
        participant = result.participants[0]
        assert participant.driver_id == 300
        assert participant.network_id == 301
        assert participant.team_id == 302
        assert participant.my_team == 1
        assert participant.race_number == 44
        assert participant.nationality == 7
        assert participant.name == "SentinelDriver"
        assert participant.tech_level == 9999
        assert participant.platform == 3
