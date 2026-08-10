import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import struct

import pytest

from packets.car_status import unpack_car_status
from packets.packet_header import PACKET_HEADER_FORMAT_SIZE, unpack_packet_header

from .packet_builder.header import build_header

_CAR_STATUS_FORMAT = '<5B3fHHBBHBBBb3fB3fB'
_MAX_CARS = 22


def _build_car_status_bytes(
    traction_control=0, anti_lock=0, fuel_mix=0, front_brake_bias=55, pit_limiter=0,
    fuel_in_tank=50.0, fuel_capacity=110.0, fuel_remaining_laps=20.0,
    max_rpm=12000, idle_rpm=4000,
    max_gears=8, drs_allowed=1,
    drs_activation_distance=100,
    actual_tyre_compound=18, visual_tyre_compound=16, tyres_age_laps=5,
    vehicle_fia_flags=0,
    engine_power_ice=750.0, engine_power_mguk=120.0, ers_store_energy=4000000.0,
    ers_deploy_mode=2,
    ers_harvested_mguk=200000.0, ers_harvested_mguh=300000.0, ers_deployed_this_lap=100000.0,
    network_paused=0,
):
    return struct.pack(
        _CAR_STATUS_FORMAT,
        traction_control, anti_lock, fuel_mix, front_brake_bias, pit_limiter,
        fuel_in_tank, fuel_capacity, fuel_remaining_laps,
        max_rpm, idle_rpm,
        max_gears, drs_allowed,
        drs_activation_distance,
        actual_tyre_compound, visual_tyre_compound, tyres_age_laps,
        vehicle_fia_flags,
        engine_power_ice, engine_power_mguk, ers_store_energy,
        ers_deploy_mode,
        ers_harvested_mguk, ers_harvested_mguh, ers_deployed_this_lap,
        network_paused,
    )


def _build_full_packet(**car0_kwargs):
    header = build_header(
        packet_id=7,
        session_uid=100,
        session_time=1.0,
        frame_identifier=1,
        overall_frame_identifier=1,
    )
    body = _build_car_status_bytes(**car0_kwargs)
    zero_car = _build_car_status_bytes(
        front_brake_bias=0, fuel_in_tank=0.0, fuel_capacity=0.0,
        fuel_remaining_laps=0.0, max_rpm=0, idle_rpm=0, max_gears=0,
        drs_allowed=0, drs_activation_distance=0,
        actual_tyre_compound=0, visual_tyre_compound=0, tyres_age_laps=0,
        engine_power_ice=0.0, engine_power_mguk=0.0, ers_store_energy=0.0,
        ers_deploy_mode=0,
        ers_harvested_mguk=0.0, ers_harvested_mguh=0.0, ers_deployed_this_lap=0.0,
    )
    body += zero_car * (_MAX_CARS - 1)
    return header + body


class TestCarStatusParser:

    def test_22_cars_parsed(self):
        packet = _build_full_packet()
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_status(header, body)
        assert len(result.car_status_data) == 22

    def test_fuel_and_brake_bias(self):
        packet = _build_full_packet(fuel_in_tank=50.0, front_brake_bias=58)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_status(header, body)
        car = result.car_status_data[0]
        assert car.fuel_in_tank == pytest.approx(50.0)
        assert car.front_brake_bias == 58

    def test_tyre_compound_fields(self):
        packet = _build_full_packet(actual_tyre_compound=20, visual_tyre_compound=18)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_status(header, body)
        car = result.car_status_data[0]
        assert car.actual_tyre_compound == 20
        assert car.visual_tyre_compound == 18

    def test_ers_fields(self):
        packet = _build_full_packet(ers_store_energy=4000000.0)
        header = unpack_packet_header(packet[:PACKET_HEADER_FORMAT_SIZE])
        body = packet[PACKET_HEADER_FORMAT_SIZE:]
        result = unpack_car_status(header, body)
        car = result.car_status_data[0]
        assert car.ers_store_energy == pytest.approx(4000000.0)
