import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from packets.events import (
    Collision,
    FastestLap,
    Overtake,
    Penalty,
    RaceWinner,
    SafetyCar,
    SpeedTrap,
    unpack_event_packet,
)
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.events import (
    build_event_chqf,
    build_event_coll,
    build_event_ftlp,
    build_event_ovtk,
    build_event_pena,
    build_event_rcwn,
    build_event_scar,
    build_event_send,
    build_event_sptp,
    build_event_ssta,
)


class TestEventsParser:

    def test_ssta_event(self):
        packet = build_event_ssta(session_uid=1, session_time=0.0, frame_id=0)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "SSTA"
        assert result.event is None

    def test_send_event(self):
        packet = build_event_send(session_uid=1, session_time=100.0, frame_id=500)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "SEND"

    def test_ovtk_event(self):
        packet = build_event_ovtk(
            session_uid=1, session_time=50.0, frame_id=300,
            overtaking_index=0, overtaken_index=1,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "OVTK"
        assert isinstance(result.event, Overtake)
        assert result.event.overtaking_vehicle_index == 0
        assert result.event.being_overtaken_vehicle_index == 1

    def test_ftlp_event(self):
        packet = build_event_ftlp(
            session_uid=1, session_time=60.0, frame_id=400,
            vehicle_index=3, lap_time=88.5,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "FTLP"
        assert isinstance(result.event, FastestLap)
        assert result.event.vehicle_index == 3
        assert result.event.lap_time == pytest.approx(88.5)

    def test_pena_event(self):
        packet = build_event_pena(
            session_uid=1, session_time=70.0, frame_id=450,
            vehicle_index=5, other_vehicle_index=8,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "PENA"
        assert isinstance(result.event, Penalty)
        assert result.event.penalty_type == 0
        assert result.event.infringement_type == 3
        assert result.event.vehicle_index == 5
        assert result.event.other_vehicle_index == 8
        assert result.event.time == 5
        assert result.event.lap_num == 1
        assert result.event.places_gained == 0

    def test_coll_event(self):
        packet = build_event_coll(
            session_uid=1, session_time=80.0, frame_id=500,
            vehicle_1_index=2, vehicle_2_index=7,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "COLL"
        assert isinstance(result.event, Collision)
        assert result.event.vehicle_1_index == 2
        assert result.event.vehicle_2_index == 7

    def test_sptp_event(self):
        packet = build_event_sptp(
            session_uid=1, session_time=90.0, frame_id=550,
            vehicle_index=4, speed=310.5,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "SPTP"
        assert isinstance(result.event, SpeedTrap)
        assert result.event.vehicle_index == 4
        assert result.event.speed == pytest.approx(310.5)

    def test_scar_event(self):
        packet = build_event_scar(
            session_uid=1, session_time=100.0, frame_id=600,
            safety_car_type=1, event_type=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "SCAR"
        assert isinstance(result.event, SafetyCar)
        assert result.event.safety_car_type == 1
        assert result.event.event_type == 0

    def test_rcwn_event(self):
        packet = build_event_rcwn(
            session_uid=1, session_time=110.0, frame_id=700,
            vehicle_index=0,
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "RCWN"
        assert isinstance(result.event, RaceWinner)
        assert result.event.vehicle_index == 0

    def test_chqf_event(self):
        packet = build_event_chqf(session_uid=1, session_time=120.0, frame_id=800)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_event_packet(header, body)
        assert result.event_string_code == "CHQF"
        assert result.event is None
