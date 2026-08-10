"""Unit tests for the MotionEx parser (Packet ID 13)."""

import struct

from pytest import approx

from packets.motion_ex import unpack_motion_ex
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.header import build_header

_MOTION_EX_FORMAT = '<61f'


def _build_motion_ex_payload() -> bytes:
    """Build 244 bytes (61 floats) of Motion Ex data with known values."""
    floats = [
        # suspension_position[4]
        1.0, 2.0, 3.0, 4.0,
        # suspension_velocity[4]
        5.0, 6.0, 7.0, 8.0,
        # suspension_acceleration[4]
        9.0, 10.0, 11.0, 12.0,
        # wheel_speed[4]
        80.0, 81.0, 82.0, 83.0,
        # wheel_slip_ratio[4]
        0.01, 0.02, 0.03, 0.04,
        # wheel_slip_angle[4]
        0.1, 0.2, 0.3, 0.4,
        # wheel_lat_force[4]
        100.0, 200.0, 300.0, 400.0,
        # wheel_long_force[4]
        500.0, 600.0, 700.0, 800.0,
        # height_of_cog_above_ground
        0.35,
        # local_velocity x/y/z
        55.0, 0.5, -1.0,
        # angular_velocity x/y/z
        0.01, 0.02, 0.03,
        # angular_acceleration x/y/z
        0.04, 0.05, 0.06,
        # front_wheels_angle
        0.12,
        # wheel_vert_force[4]
        3000.0, 3100.0, 3200.0, 3300.0,
        # front_aero_height, rear_aero_height
        0.05, 0.08,
        # front_roll_angle, rear_roll_angle
        0.003, 0.004,
        # chassis_yaw, chassis_pitch
        1.57, 0.01,
        # wheel_camber[4]
        -3.5, -3.4, -3.3, -3.2,
        # wheel_camber_gain[4]
        0.5, 0.6, 0.7, 0.8,
    ]
    assert len(floats) == 61
    return struct.pack(_MOTION_EX_FORMAT, *floats)


def _build_full_packet() -> bytes:
    """Build a complete Motion Ex packet with header + body."""
    header = build_header(
        packet_id=13,
        session_uid=987654321,
        session_time=42.5,
        frame_identifier=500,
        overall_frame_identifier=500,
    )
    return header + _build_motion_ex_payload()


class TestMotionExParser:
    """Verify key fields are extracted from Motion Ex packet."""

    def test_suspension_position_is_tuple4(self):
        raw = _build_full_packet()
        header = unpack_packet_header(raw[:PACKET_HEADER_FORMAT_SIZE])
        body = raw[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion_ex(header, body)

        assert len(result.motion_ex_data.suspension_position) == 4
        assert result.motion_ex_data.suspension_position == (1.0, 2.0, 3.0, 4.0)

    def test_wheel_speed_is_tuple4(self):
        raw = _build_full_packet()
        header = unpack_packet_header(raw[:PACKET_HEADER_FORMAT_SIZE])
        body = raw[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion_ex(header, body)

        assert len(result.motion_ex_data.wheel_speed) == 4
        assert result.motion_ex_data.wheel_speed == (80.0, 81.0, 82.0, 83.0)

    def test_wheel_slip_ratio_is_tuple4(self):
        raw = _build_full_packet()
        header = unpack_packet_header(raw[:PACKET_HEADER_FORMAT_SIZE])
        body = raw[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion_ex(header, body)

        assert len(result.motion_ex_data.wheel_slip_ratio) == 4
        assert result.motion_ex_data.wheel_slip_ratio == approx((0.01, 0.02, 0.03, 0.04))

    def test_scalar_fields(self):
        raw = _build_full_packet()
        header = unpack_packet_header(raw[:PACKET_HEADER_FORMAT_SIZE])
        body = raw[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion_ex(header, body)

        data = result.motion_ex_data
        assert abs(data.height_of_cog_above_ground - 0.35) < 1e-5
        assert abs(data.front_wheels_angle - 0.12) < 1e-5

    def test_chassis_yaw_and_pitch(self):
        raw = _build_full_packet()
        header = unpack_packet_header(raw[:PACKET_HEADER_FORMAT_SIZE])
        body = raw[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion_ex(header, body)

        data = result.motion_ex_data
        assert abs(data.chassis_yaw - 1.57) < 1e-5
        assert abs(data.chassis_pitch - 0.01) < 1e-5

    def test_wheel_camber_is_tuple4(self):
        raw = _build_full_packet()
        header = unpack_packet_header(raw[:PACKET_HEADER_FORMAT_SIZE])
        body = raw[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion_ex(header, body)

        assert len(result.motion_ex_data.wheel_camber) == 4
        assert result.motion_ex_data.wheel_camber[0] == -3.5

    def test_header_packet_id(self):
        raw = _build_full_packet()
        header = unpack_packet_header(raw[:PACKET_HEADER_FORMAT_SIZE])
        body = raw[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_motion_ex(header, body)

        assert result.header.packet_id == 13
