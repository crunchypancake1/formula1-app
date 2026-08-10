"""Car frame service for combined Motion + Telemetry + Lap Data + Car Status + Car Damage writes."""

import logging
from typing import Optional

from database.repositories import CarFrameDamageRepository, CarFrameRepository
from database.repositories.base import safe_enum_name
from enums import (
    ActualTyreCompound,
    DriverStatus,
    FlagStatus,
    PitStatus,
    ResultStatus,
    Sector,
    SurfaceType,
    VisualTyreCompound,
)


def _build_motion_fields(motion) -> tuple:
    if motion is None:
        return (None,) * 12
    return (
        motion.world_position_x,
        motion.world_position_y,
        motion.world_position_z,
        motion.world_velocity_x,
        motion.world_velocity_y,
        motion.world_velocity_z,
        motion.g_force_lateral,
        motion.g_force_longitudinal,
        motion.g_force_vertical,
        motion.yaw,
        motion.pitch,
        motion.roll,
    )


def _build_telemetry_fields(telemetry, logger: logging.Logger) -> tuple:
    if telemetry is None:
        return (None,) * 29
    return (
        telemetry.speed,
        telemetry.throttle,
        telemetry.steer,
        telemetry.brake,
        telemetry.clutch,
        telemetry.gear,
        telemetry.engine_rpm,
        bool(telemetry.drs),
        telemetry.engine_temperature,
        # Per-wheel brakes temp (RL=0, RR=1, FL=2, FR=3)
        telemetry.brakes_temperature[0],
        telemetry.brakes_temperature[1],
        telemetry.brakes_temperature[2],
        telemetry.brakes_temperature[3],
        # Per-wheel tyres surface temp
        telemetry.tyres_surface_temp[0],
        telemetry.tyres_surface_temp[1],
        telemetry.tyres_surface_temp[2],
        telemetry.tyres_surface_temp[3],
        # Per-wheel tyres inner temp
        telemetry.tyres_inner_temp[0],
        telemetry.tyres_inner_temp[1],
        telemetry.tyres_inner_temp[2],
        telemetry.tyres_inner_temp[3],
        # Per-wheel tyres pressure
        telemetry.tyres_pressure[0],
        telemetry.tyres_pressure[1],
        telemetry.tyres_pressure[2],
        telemetry.tyres_pressure[3],
        # Per-wheel surface type (enum resolved)
        safe_enum_name(SurfaceType, telemetry.surface_type[0], logger),
        safe_enum_name(SurfaceType, telemetry.surface_type[1], logger),
        safe_enum_name(SurfaceType, telemetry.surface_type[2], logger),
        safe_enum_name(SurfaceType, telemetry.surface_type[3], logger),
    )


def _build_lap_fields(lap, logger: logging.Logger) -> tuple:
    if lap is None:
        return (None,) * 18
    gap_to_leader_ms = (
        lap.delta_to_race_leader_minutes_part * 60000 + lap.delta_to_race_leader_ms_part
    )
    gap_to_car_ahead_ms = (
        lap.delta_to_car_in_front_minutes_part * 60000 + lap.delta_to_car_in_front_ms_part
    )
    return (
        lap.current_lap_num,
        lap.lap_distance,
        lap.current_lap_time_in_ms,
        lap.car_position if lap.car_position != 255 else None,
        safe_enum_name(Sector, lap.sector, logger),
        safe_enum_name(PitStatus, lap.pit_status, logger),
        safe_enum_name(DriverStatus, lap.driver_status, logger),
        safe_enum_name(ResultStatus, lap.result_status, logger),
        gap_to_leader_ms,
        gap_to_car_ahead_ms,
        None,  # gap_to_car_behind_ms — filled in write_frame()
        lap.total_distance,
        lap.safety_car_delta,
        lap.num_pit_stops,
        bool(lap.pit_lane_timer_active),
        lap.pit_lane_time_in_lane_in_ms,
        lap.pit_stop_timer_in_ms,
        bool(lap.pit_stop_should_serve_pen),
    )


def _build_status_fields(status, logger: logging.Logger) -> tuple:
    if status is None:
        return (None,) * 8
    return (
        bool(status.pit_limiter),
        bool(status.drs_allowed),
        status.drs_activation_distance,
        safe_enum_name(ActualTyreCompound, status.actual_tyre_compound, logger),
        safe_enum_name(VisualTyreCompound, status.visual_tyre_compound, logger),
        status.tyres_age_laps if status.tyres_age_laps != 255 else None,
        safe_enum_name(FlagStatus, status.vehicle_fia_flags, logger),
        bool(status.network_paused),
    )


def _build_damage_fields(damage) -> tuple:
    """Extract 34 damage/wear fields from a CarDamageData object."""
    if damage is None:
        return (None,) * 34
    return (
        # Per-wheel tyre wear (RL=0, RR=1, FL=2, FR=3)
        damage.tyres_wear[0],
        damage.tyres_wear[1],
        damage.tyres_wear[2],
        damage.tyres_wear[3],
        # Per-wheel tyre damage
        damage.tyres_damage[0],
        damage.tyres_damage[1],
        damage.tyres_damage[2],
        damage.tyres_damage[3],
        # Per-wheel brakes damage
        damage.brakes_damage[0],
        damage.brakes_damage[1],
        damage.brakes_damage[2],
        damage.brakes_damage[3],
        # Per-wheel tyre blisters
        damage.tyre_blisters[0],
        damage.tyre_blisters[1],
        damage.tyre_blisters[2],
        damage.tyre_blisters[3],
        # Aero damage
        damage.front_left_wing_damage,
        damage.front_right_wing_damage,
        damage.rear_wing_damage,
        damage.floor_damage,
        damage.diffuser_damage,
        damage.sidepod_damage,
        # Faults
        bool(damage.drs_fault),
        bool(damage.ers_fault),
        # Mechanical damage
        damage.gearbox_damage,
        damage.engine_damage,
        # Engine component wear
        damage.engine_mguh_wear,
        damage.engine_es_wear,
        damage.engine_ce_wear,
        damage.engine_ice_wear,
        damage.engine_mguk_wear,
        damage.engine_tc_wear,
        # Engine critical faults
        bool(damage.engine_blown),
        bool(damage.engine_seized),
    )


def _build_car_status_extended_fields(status) -> tuple:
    """Extract 6 ERS/fuel/brake-bias fields from a CarStatusData object."""
    if status is None:
        return (None,) * 6
    return (
        status.front_brake_bias,
        status.fuel_in_tank,
        status.fuel_remaining_laps,
        status.ers_store_energy,
        status.ers_deploy_mode,
        status.ers_deployed_this_lap,
    )


class CarFrameService:
    """
    Handles combined frame data (Motion + Telemetry + Lap Data + Car Status).

    Receives pre-combined data for all 22 cars in a single frame and writes
    one batch INSERT of up to 22 rows to the car_frame hypertable.
    """

    def __init__(
        self,
        car_frame_repo: CarFrameRepository,
        car_frame_damage_repo: Optional[CarFrameDamageRepository] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._car_frame_repo = car_frame_repo
        self._car_frame_damage_repo = car_frame_damage_repo
        self._logger = logger or logging.getLogger(__name__)
        # Track whether we've already logged the formation lap drop per session
        self._formation_lap_logged: dict[str, bool] = {}

    def write_frame(
        self,
        session_uid: str,
        session_time: float,
        overall_frame_identifier: int,
        user_map: dict[int, int],
        motion_data,
        telemetry_data,
        lap_data_list,
        car_status_data=None,
        car_damage_data=None,
        race_started: bool = True,
    ):
        if not race_started:
            if not self._formation_lap_logged.get(session_uid):
                self._logger.debug(
                    f"Dropping car_frame for session {session_uid} — formation lap (race not started)"
                )
                self._formation_lap_logged[session_uid] = True
            return

        rows = []
        damage_rows = []
        for car_index in range(22):
            user_id = user_map.get(car_index)
            if user_id is None:
                continue

            motion = motion_data[car_index] if motion_data else None
            telemetry = telemetry_data[car_index] if telemetry_data else None
            lap = lap_data_list[car_index] if lap_data_list else None
            status = car_status_data[car_index] if car_status_data else None

            # Skip drivers sitting in the garage
            if lap is not None and lap.driver_status == 0:
                continue

            row = (
                (session_uid, user_id, session_time, overall_frame_identifier)
                + _build_motion_fields(motion)
                + _build_telemetry_fields(telemetry, self._logger)
                + _build_lap_fields(lap, self._logger)
                + _build_status_fields(status, self._logger)
                + _build_car_status_extended_fields(status)
            )
            rows.append(row)

            if car_damage_data is not None:
                damage = car_damage_data[car_index]
                damage_row = (
                    (session_uid, user_id, session_time, overall_frame_identifier)
                    + _build_damage_fields(damage)
                )
                damage_rows.append(damage_row)

        # Second pass: fill gap_to_car_behind_ms for each row.
        # Tuple layout: meta(4) + motion(12) + telemetry(29) + lap(18) + status(8) + status_ext(6)
        # position is at index 48, gap_to_car_ahead_ms at 54, gap_to_car_behind_ms at 55
        IDX_POSITION = 48
        IDX_GAP_BEHIND = 55
        IDX_GAP_AHEAD = 54
        position_to_gap_ahead: dict[int, int | None] = {}
        for row in rows:
            pos = row[IDX_POSITION]
            if pos is not None:
                position_to_gap_ahead[pos] = row[IDX_GAP_AHEAD]
        for i, row in enumerate(rows):
            pos = row[IDX_POSITION]
            if pos is not None:
                behind_gap = position_to_gap_ahead.get(pos + 1)
                if behind_gap is not None:
                    rows[i] = row[:IDX_GAP_BEHIND] + (behind_gap,) + row[IDX_GAP_BEHIND + 1:]

        if rows:
            try:
                self._car_frame_repo.insert_batch(rows)
            except Exception as e:
                self._logger.error(f"Failed to insert car frame batch: {e}", exc_info=True)

        if damage_rows and self._car_frame_damage_repo is not None:
            try:
                self._car_frame_damage_repo.insert_batch(damage_rows)
            except Exception as e:
                self._logger.error(f"Failed to insert car frame damage batch: {e}", exc_info=True)
