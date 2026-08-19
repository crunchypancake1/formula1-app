"""Combines the same-tick packets (Motion, Lap Data, Telemetry, Status, Damage, Telemetry 2) into car_frame rows."""

import logging
from datetime import datetime, timedelta, timezone
from typing import AbstractSet, Optional

from database.repositories import CarFrameDamageRepository, CarFrameRepository
from database.repositories.base import safe_enum_name
from database.repositories.car_frame import COLUMN_INDEX
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
from packets.constants import MAX_CARS

# Sentinel used by the game for "not set" on these uint8 fields.
_NOT_SET = 255

# Field positions used by the gap-to-car-behind pass. Resolved from the
# repository's column list rather than hand-counted, so they cannot drift.
_IDX_POSITION = COLUMN_INDEX["position"]
_IDX_GAP_AHEAD = COLUMN_INDEX["gap_to_car_ahead_ms"]
_IDX_GAP_BEHIND = COLUMN_INDEX["gap_to_car_behind_ms"]


def _split_time_ms(minutes_part: int, ms_part: int) -> int:
    """Recombine the game's split minute/millisecond time fields into plain ms."""
    return minutes_part * 60000 + ms_part


def _build_motion_fields(motion) -> tuple:
    if motion is None:
        return (None,) * 18
    return (
        motion.world_position_x,
        motion.world_position_y,
        motion.world_position_z,
        motion.world_velocity_x,
        motion.world_velocity_y,
        motion.world_velocity_z,
        motion.world_forward_dir_x,
        motion.world_forward_dir_y,
        motion.world_forward_dir_z,
        motion.world_right_dir_x,
        motion.world_right_dir_y,
        motion.world_right_dir_z,
        motion.g_force_lateral,
        motion.g_force_longitudinal,
        motion.g_force_vertical,
        motion.yaw,
        motion.pitch,
        motion.roll,
    )


def _build_telemetry_fields(telemetry, logger: logging.Logger) -> tuple:
    """Telemetry is never restricted — every field here is populated for every car."""
    if telemetry is None:
        return (None,) * 31
    return (
        telemetry.speed,
        telemetry.throttle,
        telemetry.steer,
        telemetry.brake,
        telemetry.clutch,
        telemetry.gear,
        telemetry.engine_rpm,
        bool(telemetry.drs),
        telemetry.rev_lights_percent,
        telemetry.rev_lights_bit_value,
        telemetry.engine_temperature,
        # Per-wheel, in the game's RL, RR, FL, FR order
        *telemetry.brakes_temperature,
        *telemetry.tyres_surface_temp,
        *telemetry.tyres_inner_temp,
        *telemetry.tyres_pressure,
        *(safe_enum_name(SurfaceType, s, logger) for s in telemetry.surface_type),
    )


def _build_player_telemetry_fields(telemetry_packet, is_player: bool) -> tuple:
    """
    The three Car Telemetry fields that sit outside the per-car array.

    They describe the local player alone — there is no equivalent for any other
    car — so every other driver's row leaves them NULL.
    """
    if telemetry_packet is None or not is_player:
        return (None,) * 3
    return (
        telemetry_packet.mfd_panel_index,
        telemetry_packet.mfd_panel_index_secondary_player,
        telemetry_packet.suggested_gear,
    )


def _build_lap_fields(lap, logger: logging.Logger) -> tuple:
    if lap is None:
        return (None,) * 30
    return (
        lap.last_lap_time_in_ms or None,
        lap.current_lap_time_in_ms,
        _split_time_ms(lap.sector1_time_minutes_part, lap.sector1_time_ms_part) or None,
        _split_time_ms(lap.sector2_time_minutes_part, lap.sector2_time_ms_part) or None,
        lap.lap_distance,
        lap.total_distance,
        lap.safety_car_delta,
        lap.car_position if lap.car_position != _NOT_SET else None,
        lap.grid_position if lap.grid_position else None,
        lap.current_lap_num,
        safe_enum_name(Sector, lap.sector, logger),
        safe_enum_name(PitStatus, lap.pit_status, logger),
        safe_enum_name(DriverStatus, lap.driver_status, logger),
        safe_enum_name(ResultStatus, lap.result_status, logger),
        bool(lap.current_lap_invalid),
        _split_time_ms(lap.delta_to_race_leader_minutes_part, lap.delta_to_race_leader_ms_part),
        _split_time_ms(lap.delta_to_car_in_front_minutes_part, lap.delta_to_car_in_front_ms_part),
        None,  # gap_to_car_behind_ms — filled by the second pass in write_frame()
        lap.num_pit_stops,
        bool(lap.pit_lane_timer_active),
        lap.pit_lane_time_in_lane_in_ms,
        lap.pit_stop_timer_in_ms,
        bool(lap.pit_stop_should_serve_pen),
        lap.penalties,
        lap.total_warnings,
        lap.corner_cutting_warnings,
        lap.num_unserved_drive_through_pens,
        lap.num_unserved_stop_go_pens,
        lap.speed_trap_fastest_speed or None,
        lap.speed_trap_fastest_lap if lap.speed_trap_fastest_lap != _NOT_SET else None,
    )


def _build_status_public_fields(status, logger: logging.Logger) -> tuple:
    """The Car Status fields the game sends for every car regardless of privacy setting."""
    if status is None:
        return (None,) * 13
    return (
        bool(status.pit_limiter),
        bool(status.drs_allowed),
        status.drs_activation_distance,
        safe_enum_name(ActualTyreCompound, status.actual_tyre_compound, logger),
        safe_enum_name(VisualTyreCompound, status.visual_tyre_compound, logger),
        status.tyres_age_laps if status.tyres_age_laps != _NOT_SET else None,
        safe_enum_name(FlagStatus, status.vehicle_fia_flags, logger),
        bool(status.network_paused),
        status.traction_control,
        bool(status.anti_lock_brakes),
        status.max_rpm,
        status.idle_rpm,
        status.max_gears,
    )


def _build_status_restricted_fields(status, is_restricted: bool) -> tuple:
    """
    The Car Status fields the game zeroes for a Restricted driver's car.

    Fuel, ERS and brake bias arrive as 0 for any *other* driver whose Your
    Telemetry setting is Restricted. Storing those zeroes would be indis-
    tinguishable from a real reading, so this returns NULLs instead.
    """
    if status is None or is_restricted:
        return (None,) * 13
    return (
        status.front_brake_bias,
        status.fuel_mix,
        status.fuel_in_tank,
        status.fuel_capacity,
        status.fuel_remaining_laps,
        status.ers_store_energy,
        status.ers_deploy_mode,
        status.ers_deployed_this_lap,
        status.ers_harvest_limit_per_lap,
        status.ers_harvested_this_lap_mguk,
        status.ers_harvested_this_lap_mguh,
        status.engine_power_ice,
        status.engine_power_mguk,
    )


def _build_damage_fields(damage) -> tuple:
    """Extract the 34 damage/wear fields from a CarDamageData object."""
    if damage is None:
        return (None,) * 34
    return (
        *damage.tyres_wear,
        *damage.tyres_damage,
        *damage.brakes_damage,
        *damage.tyre_blisters,
        damage.front_left_wing_damage,
        damage.front_right_wing_damage,
        damage.rear_wing_damage,
        damage.floor_damage,
        damage.diffuser_damage,
        damage.sidepod_damage,
        bool(damage.drs_fault),
        bool(damage.ers_fault),
        damage.gearbox_damage,
        damage.engine_damage,
        damage.engine_mguh_wear,
        damage.engine_es_wear,
        damage.engine_ce_wear,
        damage.engine_ice_wear,
        damage.engine_mguk_wear,
        damage.engine_tc_wear,
        bool(damage.engine_blown),
        bool(damage.engine_seized),
    )


def _build_telemetry2_fields(telemetry2) -> tuple:
    """
    The 8 Car Telemetry 2 (packet 16) fields.

    Active aero and boost only exist under 2026 regulations; on a classic or F2
    car they are legitimately zero and stored as NULL. is_2026_regulations
    itself is a fact we know either way, so it is stored as a real boolean —
    NULL there means "packet 16 never arrived", not "pre-2026 car".
    driving_wrong_way is meaningful on any car.
    """
    if telemetry2 is None:
        return (None,) * 8
    if not telemetry2.regulations_2026:
        return (None,) * 6 + (False, bool(telemetry2.driving_wrong_way))
    return (
        telemetry2.active_aero_mode,
        bool(telemetry2.active_aero_available),
        telemetry2.active_aero_activation_distance,
        bool(telemetry2.overtake_available),
        bool(telemetry2.overtake_active),
        telemetry2.overtake_activation_distance,
        True,
        bool(telemetry2.driving_wrong_way),
    )


class CarFrameService:
    """
    Writes one car_frame row per driver per simulation frame.

    Receives pre-combined data for up to MAX_CARS cars in a single frame and
    writes one batch INSERT to the car_frame hypertable, plus a second batch to
    car_frame_damage for the drivers whose damage data is actually visible.
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
        car_telemetry2_data=None,
        telemetry_packet=None,
        player_car_index: Optional[int] = None,
        restricted_indices: Optional[AbstractSet[int]] = None,
        session_start: Optional[datetime] = None,
        race_started: bool = True,
    ):
        # Formation-lap frames are deliberately not recorded. The dispatcher
        # decides when a race has started; see PacketDispatcher._mark_race_started.
        if not race_started:
            return

        restricted = restricted_indices or frozenset()

        # Derive the row timestamp from the session anchor so the same frame
        # always lands on the same key, even across a listener restart. Falling
        # back to wall clock keeps data flowing if the anchor is not known yet.
        if session_start is not None:
            timestamp = session_start + timedelta(seconds=session_time)
        else:
            timestamp = datetime.now(timezone.utc)

        meta = (timestamp, session_uid)

        rows = []
        damage_rows = []
        for car_index in range(MAX_CARS):
            user_id = user_map.get(car_index)
            if user_id is None:
                continue

            motion = motion_data[car_index] if motion_data else None
            telemetry = telemetry_data[car_index] if telemetry_data else None
            lap = lap_data_list[car_index] if lap_data_list else None
            status = car_status_data[car_index] if car_status_data else None
            telemetry2 = car_telemetry2_data[car_index] if car_telemetry2_data else None
            is_restricted = car_index in restricted

            # Skip drivers sitting in the garage — they produce no useful frame.
            if lap is not None and lap.driver_status == 0:
                continue

            rows.append(
                meta
                + (user_id, session_time, overall_frame_identifier)
                + _build_motion_fields(motion)
                + _build_telemetry_fields(telemetry, self._logger)
                + _build_player_telemetry_fields(telemetry_packet, car_index == player_car_index)
                + _build_lap_fields(lap, self._logger)
                + _build_status_public_fields(status, self._logger)
                + _build_status_restricted_fields(status, is_restricted)
                + _build_telemetry2_fields(telemetry2)
            )

            # Restricted drivers get no damage row at all. The game guarantees
            # ~30 of its 34 columns are zero for them, and this row is written
            # at 10 Hz for a whole race — an absent row says "withheld", a
            # zero-filled one would say "undamaged".
            if car_damage_data is not None and not is_restricted:
                damage_rows.append(
                    meta
                    + (user_id, session_time, overall_frame_identifier)
                    + _build_damage_fields(car_damage_data[car_index])
                )

        self._fill_gap_to_car_behind(rows)

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

    def discard_after(self, session_uid: str, session_time: float) -> int:
        """
        Delete frame rows recorded after a flashback's rewind point.

        Returns the number of car_frame rows removed; the damage and motion_ex
        rows for the same stretch go with them.
        """
        discarded = self._car_frame_repo.delete_after(session_uid, session_time)
        if self._car_frame_damage_repo is not None:
            self._car_frame_damage_repo.delete_after(session_uid, session_time)
        return discarded

    @staticmethod
    def _fill_gap_to_car_behind(rows: list[tuple]) -> None:
        """
        Derive each car's gap to the car behind.

        The game only reports a gap to the car *ahead*, so the car one position
        back is the one that knows this value — it reports it as its own
        gap-to-car-ahead.
        """
        gap_ahead_by_position = {
            row[_IDX_POSITION]: row[_IDX_GAP_AHEAD]
            for row in rows
            if row[_IDX_POSITION] is not None
        }
        for i, row in enumerate(rows):
            position = row[_IDX_POSITION]
            if position is None:
                continue
            behind_gap = gap_ahead_by_position.get(position + 1)
            if behind_gap is not None:
                rows[i] = row[:_IDX_GAP_BEHIND] + (behind_gap,) + row[_IDX_GAP_BEHIND + 1:]
