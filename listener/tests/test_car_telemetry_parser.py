import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

import pytest

from packets.car_telemetry import unpack_car_telemetry
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.header import build_header

_CAR_TELEMETRY_FORMAT = '<H3fBbHBBH4H4B4BH4f4B'
_MAX_CARS = 22


def _build_car_telemetry_bytes(
    speed=200, throttle=0.8, steer=0.0, brake=0.0,
    clutch=0, gear=6, rpm=10500, drs=0,
    brakes_temp=(400, 410, 380, 390),
    tyres_surface_temp=(100, 102, 98, 99),
    tyres_inner_temp=(105, 107, 103, 104),
    engine_temp=120,
    tyres_pressure=(23.5, 23.5, 22.0, 22.0),
    surface_type=(0, 0, 0, 0),
):
    return struct.pack(
        _CAR_TELEMETRY_FORMAT,
        speed, throttle, steer, brake,
        clutch, gear, rpm, drs,
        50, 0,
        *brakes_temp,
        *tyres_surface_temp,
        *tyres_inner_temp,
        engine_temp,
        *tyres_pressure,
        *surface_type,
    )


def _build_full_packet(**car0_kwargs):
    header = build_header(
        packet_id=6,
        session_uid=100,
        session_time=1.0,
        frame_identifier=1,
        overall_frame_identifier=1,
    )
    body = _build_car_telemetry_bytes(**car0_kwargs)
    zero_car = _build_car_telemetry_bytes(
        speed=0, throttle=0.0, gear=0, rpm=0,
        brakes_temp=(0, 0, 0, 0),
        tyres_surface_temp=(0, 0, 0, 0),
        tyres_inner_temp=(0, 0, 0, 0),
        engine_temp=0,
        tyres_pressure=(0.0, 0.0, 0.0, 0.0),
    )
    body += zero_car * (_MAX_CARS - 1)
    return header + body


class TestCarTelemetryParser:

    def test_22_cars_parsed(self):
        packet = _build_full_packet()
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_telemetry(header, body)
        assert len(result.car_telemetry_data) == 22

    def test_speed_and_throttle(self):
        packet = _build_full_packet(speed=200, throttle=0.8)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_telemetry(header, body)
        car = result.car_telemetry_data[0]
        assert car.speed == 200
        assert car.throttle == pytest.approx(0.8)

    def test_wheel_data_tuples(self):
        packet = _build_full_packet(
            brakes_temp=(400, 410, 380, 390),
            tyres_pressure=(23.5, 23.5, 22.0, 22.0),
        )
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_telemetry(header, body)
        car = result.car_telemetry_data[0]
        assert car.brakes_temperature == (400, 410, 380, 390)
        assert len(car.brakes_temperature) == 4
        assert car.tyres_pressure == pytest.approx((23.5, 23.5, 22.0, 22.0))
        assert len(car.tyres_pressure) == 4

    def test_surface_type_tuple(self):
        packet = _build_full_packet(surface_type=(1, 2, 3, 4))
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_telemetry(header, body)
        car = result.car_telemetry_data[0]
        assert car.surface_type == (1, 2, 3, 4)
        assert len(car.surface_type) == 4
