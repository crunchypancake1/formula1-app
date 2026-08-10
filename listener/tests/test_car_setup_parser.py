import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

import pytest

from packets.car_setup import unpack_car_setup
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.header import build_header

_CAR_SETUP_FORMAT = '<4B4f6B3B4fBf'
_MAX_CARS = 22


def _build_car_setup_bytes(
    front_wing=5, rear_wing=7, on_throttle=50, off_throttle=50,
    front_camber=-3.0, rear_camber=-1.5, front_toe=0.05, rear_toe=0.2,
    front_suspension=5, rear_suspension=5, front_arb=5, rear_arb=5,
    front_height=3, rear_height=5,
    brake_pressure=90, brake_bias=55, engine_braking=50,
    rl_pressure=23.5, rr_pressure=23.5, fl_pressure=22.0, fr_pressure=22.0,
    ballast=0, fuel_load=50.0,
):
    return struct.pack(
        _CAR_SETUP_FORMAT,
        front_wing, rear_wing, on_throttle, off_throttle,
        front_camber, rear_camber, front_toe, rear_toe,
        front_suspension, rear_suspension, front_arb, rear_arb,
        front_height, rear_height,
        brake_pressure, brake_bias, engine_braking,
        rl_pressure, rr_pressure, fl_pressure, fr_pressure,
        ballast, fuel_load,
    )


def _build_full_packet(next_front_wing=5.0, **car0_kwargs):
    header = build_header(
        packet_id=5,
        session_uid=100,
        session_time=1.0,
        frame_identifier=1,
        overall_frame_identifier=1,
    )
    body = _build_car_setup_bytes(**car0_kwargs)
    zero_car = _build_car_setup_bytes(
        front_wing=0, rear_wing=0, on_throttle=0, off_throttle=0,
        front_camber=0.0, rear_camber=0.0, front_toe=0.0, rear_toe=0.0,
        front_suspension=0, rear_suspension=0, front_arb=0, rear_arb=0,
        front_height=0, rear_height=0,
        brake_pressure=0, brake_bias=0, engine_braking=0,
        rl_pressure=0.0, rr_pressure=0.0, fl_pressure=0.0, fr_pressure=0.0,
        ballast=0, fuel_load=0.0,
    )
    body += zero_car * (_MAX_CARS - 1)
    body += struct.pack('<f', next_front_wing)
    return header + body


class TestCarSetupParser:

    def test_22_setups_parsed(self):
        packet = _build_full_packet()
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_setup(header, body)
        assert len(result.car_setups) == 22

    def test_setup_fields(self):
        packet = _build_full_packet(front_wing=10, rear_wing=8)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_setup(header, body)
        car = result.car_setups[0]
        assert car.front_wing == 10
        assert car.rear_wing == 8

    def test_next_front_wing_value(self):
        packet = _build_full_packet(next_front_wing=12.5)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_setup(header, body)
        assert result.next_front_wing_value == pytest.approx(12.5)
