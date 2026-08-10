import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

import pytest

from packets.motion import unpack_motion
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.header import build_header

_CAR_MOTION_FORMAT = '<6f6h6f'
_MAX_CARS = 22


def _build_car_motion_bytes(
    pos_x=0.0, pos_y=0.0, pos_z=0.0,
    vel_x=0.0, vel_y=0.0, vel_z=0.0,
    fwd_x=0, fwd_y=0, fwd_z=0,
    right_x=0, right_y=0, right_z=0,
    g_lat=0.0, g_long=0.0, g_vert=0.0,
    yaw=0.0, pitch=0.0, roll=0.0,
):
    return struct.pack(
        _CAR_MOTION_FORMAT,
        pos_x, pos_y, pos_z,
        vel_x, vel_y, vel_z,
        fwd_x, fwd_y, fwd_z,
        right_x, right_y, right_z,
        g_lat, g_long, g_vert,
        yaw, pitch, roll,
    )


def _build_full_packet(**car0_kwargs):
    header = build_header(
        packet_id=0,
        session_uid=100,
        session_time=1.0,
        frame_identifier=1,
        overall_frame_identifier=1,
    )
    body = _build_car_motion_bytes(**car0_kwargs)
    zero_car = _build_car_motion_bytes()
    body += zero_car * (_MAX_CARS - 1)
    return header + body


class TestMotionParser:

    def test_22_cars_parsed(self):
        packet = _build_full_packet()
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion(header, body)
        assert len(result.car_motion_data) == 22

    def test_direction_normalization(self):
        packet = _build_full_packet(fwd_x=16383)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion(header, body)
        assert result.car_motion_data[0].world_forward_dir_x == pytest.approx(0.5, abs=0.01)

    def test_world_position_fields(self):
        packet = _build_full_packet(pos_x=100.5, pos_y=20.0, pos_z=-50.3)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion(header, body)
        car = result.car_motion_data[0]
        assert car.world_position_x == pytest.approx(100.5)
        assert car.world_position_y == pytest.approx(20.0)
        assert car.world_position_z == pytest.approx(-50.3)

    def test_g_force_fields(self):
        packet = _build_full_packet(g_lat=1.5, g_long=-0.8, g_vert=9.81)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion(header, body)
        car = result.car_motion_data[0]
        assert car.g_force_lateral == pytest.approx(1.5)
        assert car.g_force_longitudinal == pytest.approx(-0.8)
        assert car.g_force_vertical == pytest.approx(9.81)
