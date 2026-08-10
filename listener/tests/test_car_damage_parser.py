"""Unit tests for the expanded CarDamageData parser (Packet ID 10)."""

import struct

from packets.car_damage import unpack_car_damage
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.header import build_header

_CAR_DAMAGE_FORMAT = '<4f4B4B4B18B'
_MAX_CARS = 22


def _build_car_damage_bytes(
    tyres_wear=(15.0, 14.0, 12.0, 13.0),
    tyres_damage=(5, 4, 3, 4),
    brakes_damage=(2, 2, 1, 1),
    tyre_blisters=(10, 8, 5, 7),
    front_left_wing_damage=3,
    front_right_wing_damage=4,
    rear_wing_damage=2,
    floor_damage=6,
    diffuser_damage=7,
    sidepod_damage=8,
    drs_fault=1,
    ers_fault=0,
    gearbox_damage=12,
    engine_damage=15,
    engine_mguh_wear=20,
    engine_es_wear=25,
    engine_ce_wear=30,
    engine_ice_wear=35,
    engine_mguk_wear=40,
    engine_tc_wear=45,
    engine_blown=0,
    engine_seized=1,
) -> bytes:
    """Build 46 bytes for a single car's damage data."""
    return struct.pack(
        _CAR_DAMAGE_FORMAT,
        *tyres_wear,
        *tyres_damage,
        *brakes_damage,
        *tyre_blisters,
        front_left_wing_damage,
        front_right_wing_damage,
        rear_wing_damage,
        floor_damage,
        diffuser_damage,
        sidepod_damage,
        drs_fault,
        ers_fault,
        gearbox_damage,
        engine_damage,
        engine_mguh_wear,
        engine_es_wear,
        engine_ce_wear,
        engine_ice_wear,
        engine_mguk_wear,
        engine_tc_wear,
        engine_blown,
        engine_seized,
    )


def _build_full_packet(**car0_kwargs) -> bytes:
    """Build a complete 22-car Car Damage packet with custom values for car 0."""
    header = build_header(
        packet_id=10,
        session_uid=123456789,
        session_time=10.0,
        frame_identifier=100,
        overall_frame_identifier=100,
    )
    body = _build_car_damage_bytes(**car0_kwargs)
    zero_car = struct.pack(_CAR_DAMAGE_FORMAT, *([0.0] * 4), *([0] * 30))
    body += zero_car * (_MAX_CARS - 1)
    return header + body


class TestCarDamageParser:
    """Verify all 22 fields are extracted from Car Damage packet."""

    def test_all_fields_extracted(self):
        packet_bytes = _build_full_packet()

        header = unpack_packet_header(packet_bytes[:PACKET_HEADER_FORMAT_SIZE])
        body = packet_bytes[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_damage(header, body)

        assert len(result.car_damage_data) == _MAX_CARS

        car = result.car_damage_data[0]

        assert car.tyres_wear == (15.0, 14.0, 12.0, 13.0)
        assert car.tyres_damage == (5, 4, 3, 4)
        assert car.brakes_damage == (2, 2, 1, 1)
        assert car.tyre_blisters == (10, 8, 5, 7)
        assert car.front_left_wing_damage == 3
        assert car.front_right_wing_damage == 4
        assert car.rear_wing_damage == 2
        assert car.floor_damage == 6
        assert car.diffuser_damage == 7
        assert car.sidepod_damage == 8
        assert car.drs_fault is True
        assert car.ers_fault is False
        assert car.gearbox_damage == 12
        assert car.engine_damage == 15
        assert car.engine_mguh_wear == 20
        assert car.engine_es_wear == 25
        assert car.engine_ce_wear == 30
        assert car.engine_ice_wear == 35
        assert car.engine_mguk_wear == 40
        assert car.engine_tc_wear == 45
        assert car.engine_blown is False
        assert car.engine_seized is True

    def test_zero_car_fields(self):
        """Verify a zeroed-out car has all fields at zero/False."""
        packet_bytes = _build_full_packet()

        header = unpack_packet_header(packet_bytes[:PACKET_HEADER_FORMAT_SIZE])
        body = packet_bytes[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_damage(header, body)

        car = result.car_damage_data[1]

        assert car.tyres_wear == (0.0, 0.0, 0.0, 0.0)
        assert car.tyres_damage == (0, 0, 0, 0)
        assert car.brakes_damage == (0, 0, 0, 0)
        assert car.tyre_blisters == (0, 0, 0, 0)
        assert car.front_left_wing_damage == 0
        assert car.drs_fault is False
        assert car.ers_fault is False
        assert car.engine_blown is False
        assert car.engine_seized is False

    def test_bool_fields_are_bool(self):
        """Ensure drs_fault, ers_fault, engine_blown, engine_seized are Python bool."""
        packet_bytes = _build_full_packet(
            drs_fault=1, ers_fault=1, engine_blown=1, engine_seized=0,
        )

        header = unpack_packet_header(packet_bytes[:PACKET_HEADER_FORMAT_SIZE])
        body = packet_bytes[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_damage(header, body)

        car = result.car_damage_data[0]
        assert type(car.drs_fault) is bool
        assert type(car.ers_fault) is bool
        assert type(car.engine_blown) is bool
        assert type(car.engine_seized) is bool
