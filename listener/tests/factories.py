"""
Builders for the packet dataclasses used in service tests.

These construct the *real* dataclasses rather than SimpleNamespace stand-ins,
so a field added to a packet shows up as a test failure in the parser suite
instead of silently leaving service tests exercising a shape the parser no
longer produces.
"""

import dataclasses
from typing import Any, TypeVar

from packets.car_damage import CarDamageData
from packets.car_setup import CarSetupData
from packets.car_status import CarStatusData
from packets.car_telemetry import CarTelemetryData
from packets.car_telemetry2 import CarTelemetry2Data
from packets.lap_data import LapData
from packets.packet_header import PacketHeader
from packets.participants import Participant
from packets.tyre_sets import TyreSetData

_T = TypeVar("_T")

# Field names whose value is a 4-element per-wheel tuple (RL, RR, FL, FR).
_WHEEL_TUPLE_DEFAULT = (0.0, 0.0, 0.0, 0.0)


def _default_for(field: dataclasses.Field) -> Any:
    annotation = field.type
    if annotation in (tuple, "tuple"):
        return _WHEEL_TUPLE_DEFAULT
    if annotation in (float, "float"):
        return 0.0
    if annotation in (str, "str"):
        return ""
    if annotation in (bool, "bool"):
        return False
    if isinstance(annotation, str) and annotation.startswith("list"):
        return []
    return 0


def build(cls: type[_T], **overrides) -> _T:
    """Construct a packet dataclass with zeroed fields, overridden by kwargs."""
    values = {f.name: _default_for(f) for f in dataclasses.fields(cls)}  # type: ignore[arg-type]
    unknown = set(overrides) - set(values)
    if unknown:
        raise TypeError(f"{cls.__name__} has no field(s): {sorted(unknown)}")
    values.update(overrides)
    return cls(**values)  # type: ignore[arg-type]


def make_header(**overrides) -> PacketHeader:
    defaults = dict(
        packet_format=2026, game_year=26, game_major_version=1, game_minor_version=0,
        packet_version=1, packet_id=0, session_uid=123, session_time=10.0,
        frame_identifier=1, overall_frame_identifier=1,
        player_car_index=0, secondary_player_car_index=255,
    )
    defaults.update(overrides)
    return PacketHeader(**defaults)


def make_motion(car_index: int = 0):
    from packets.motion import CarMotionData
    return build(CarMotionData, world_position_x=float(car_index))


def make_telemetry(car_index: int = 0) -> CarTelemetryData:
    return build(
        CarTelemetryData,
        speed=200 + car_index, throttle=1.0, gear=7, engine_rpm=11000,
        rev_lights_percent=50, engine_temperature=100,
        brakes_temperature=(400, 400, 400, 400),
        tyres_surface_temp=(100, 100, 100, 100),
        tyres_inner_temp=(95, 95, 95, 95),
        tyres_pressure=(23.5, 23.5, 22.0, 22.0),
        surface_type=(0, 0, 0, 0),
    )


def make_lap(
    car_position: int = 1,
    driver_status: int = 1,
    gap_to_car_ahead: int = 0,
    **overrides,
) -> LapData:
    defaults = dict(
        current_lap_num=1, lap_distance=1000.0, current_lap_time_in_ms=30000,
        car_position=car_position, driver_status=driver_status, result_status=2,
        delta_to_car_in_front_ms_part=gap_to_car_ahead,
        total_distance=1000.0, grid_position=car_position,
    )
    defaults.update(overrides)
    return build(LapData, **defaults)


def make_status(**overrides) -> CarStatusData:
    defaults = dict(
        drs_allowed=1, drs_activation_distance=100,
        actual_tyre_compound=20, visual_tyre_compound=16,
        tyres_age_laps=5, traction_control=1, anti_lock_brakes=1,
        max_rpm=13000, idle_rpm=4000, max_gears=8,
        front_brake_bias=58, fuel_mix=1, fuel_in_tank=50.0, fuel_capacity=110.0,
        fuel_remaining_laps=10.0, ers_store_energy=4000000.0, ers_deploy_mode=1,
        ers_deployed_this_lap=100000.0, ers_harvest_limit_per_lap=200000.0,
        ers_harvested_this_lap_mguk=50000.0, ers_harvested_this_lap_mguh=25000.0,
        engine_power_ice=560000.0, engine_power_mguk=350000.0,
    )
    defaults.update(overrides)
    return build(CarStatusData, **defaults)


def make_damage(**overrides) -> CarDamageData:
    defaults = dict(
        tyres_wear=(1.0, 1.0, 1.0, 1.0),
        tyres_damage=(0, 0, 0, 0),
        brakes_damage=(0, 0, 0, 0),
        tyre_blisters=(0, 0, 0, 0),
    )
    defaults.update(overrides)
    return build(CarDamageData, **defaults)


def make_telemetry2(regulations_2026: int = 1, **overrides) -> CarTelemetry2Data:
    defaults = dict(
        active_aero_mode=1, active_aero_available=1, active_aero_activation_distance=120,
        overtake_available=1, overtake_active=1, overtake_activation_distance=200,
        regulations_2026=regulations_2026, driving_wrong_way=0,
    )
    defaults.update(overrides)
    return build(CarTelemetry2Data, **defaults)


def make_participant(car_index: int = 0, **overrides) -> Participant:
    defaults = dict(
        driver_id=car_index, network_id=car_index, team_id=476,
        race_number=car_index + 1, nationality=1,
        name=f"Driver{car_index}", your_telemetry=1, show_online_names=1,
        platform=1, num_colours=4,
        livery_colours=[(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],
    )
    defaults.update(overrides)
    return build(Participant, **defaults)


def make_tyre_set(**overrides) -> TyreSetData:
    defaults = dict(
        actual_compound=16, visual_compound=16, wear=5, available=1,
        recommended_session=15, life_span=20, usable_life=18,
        lap_delta_time=0, fitted=0,
    )
    defaults.update(overrides)
    return build(TyreSetData, **defaults)


def make_car_setup(**overrides) -> CarSetupData:
    defaults = dict(
        front_wing=5, rear_wing=8, on_throttle=70, off_throttle=55,
        front_camber=-3.0, rear_camber=-1.5, front_toe=0.05, rear_toe=0.2,
        front_suspension=5, rear_suspension=6,
        front_anti_roll_bar=7, rear_anti_roll_bar=4,
        front_ride_height=3, rear_ride_height=6,
        brake_pressure=95, brake_bias=58, engine_braking=50,
        rear_left_tyre_pressure=22.0, rear_right_tyre_pressure=22.0,
        front_left_tyre_pressure=23.5, front_right_tyre_pressure=23.5,
        ballast=5, fuel_load=60.0,
    )
    defaults.update(overrides)
    return build(CarSetupData, **defaults)
