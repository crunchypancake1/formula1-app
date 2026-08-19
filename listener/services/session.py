"""Session service for handling Session packets (Packet 1)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from database.repositories import SessionsRepository, SessionTimelineRepository
from database.repositories.base import safe_enum_name
from database.repositories.sessions import resolve_session_enums
from enums import FlagStatus, SafetyCarStatus, SessionTypeIDs, WeatherIDs
from utils.bounded_dict import BoundedDict
from utils.bounded_set import BoundedSet

_SPRINT_SHOOTOUT_IDS = {10, 11, 12, 13, 14}
_RACE_IDS = {15, 16, 17}
_SPRINT_RACE_ID = 100


def _resolve_session_type(packet) -> int:
    """Return the effective session type, remapping RACE to SPRINT_RACE on sprint weekends."""
    session_type = packet.session_type
    num_sessions = packet.num_sessions_in_weekend
    weekend_sessions = set(packet.weekend_structure[:num_sessions])
    has_sprint_quali = bool(weekend_sessions & _SPRINT_SHOOTOUT_IDS)
    num_races = len(weekend_sessions & _RACE_IDS)
    if has_sprint_quali and num_races >= 2 and session_type == 15:
        return _SPRINT_RACE_ID
    return session_type


class SessionService:
    """
    Handles Session packets (Packet 1).

    Writes to:
    - sessions (static configuration, first packet only)
    - tracks (track-static geometry)
    - session_timeline (live state, every packet)
    - weather_forecast (upserted when the forecast changes)
    """

    def __init__(
        self,
        sessions_repo: SessionsRepository,
        session_timeline_repo: SessionTimelineRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._sessions_repo = sessions_repo
        self._session_timeline_repo = session_timeline_repo
        self._logger = logger or logging.getLogger(__name__)
        self._seen_sessions = BoundedSet(max_size=100)
        self._last_forecast_hash: BoundedDict[str, int] = BoundedDict(200)
        self._session_types: BoundedDict[str, int] = BoundedDict(200)
        self._track_ids: BoundedDict[str, int] = BoundedDict(200)
        # session_uid -> wall-clock anchor for session_time == 0. Every frame
        # table derives its timestamp from this.
        self._session_starts: BoundedDict[str, datetime] = BoundedDict(200)
        # Sessions where a non-zero start_reaction_time has already been
        # captured, so we stop issuing the (cheap but pointless) UPDATE.
        self._start_reaction_captured = BoundedSet(max_size=100)

    def handle_session_packet(self, packet):
        """Process a Session packet."""
        session_uid = str(packet.header.session_uid)
        session_type = _resolve_session_type(packet)

        self._session_types[session_uid] = session_type
        self._track_ids[session_uid] = packet.track_id

        if session_uid not in self._seen_sessions:
            self._insert_session(packet, session_type)
            self._seen_sessions.add(session_uid)

        # Capture start_reaction_time the first time it is non-zero (it stays
        # 0.0 while starts are assisted).
        if packet.start_reaction_time and session_uid not in self._start_reaction_captured:
            try:
                self._sessions_repo.capture_start_reaction_time(
                    session_uid, packet.start_reaction_time
                )
                self._start_reaction_captured.add(session_uid)
            except Exception as e:
                self._logger.error(f"Failed to capture start_reaction_time: {e}", exc_info=True)

        self._insert_timeline(packet)
        self._update_weather_forecast(packet)

    def get_session_type(self, session_uid: str) -> Optional[int]:
        """Session type for a session UID, or None if the session is unknown."""
        return self._session_types.get(session_uid)

    def get_track_id(self, session_uid: str) -> Optional[int]:
        """Track id for a session, if known."""
        return self._track_ids.get(session_uid)

    def get_session_start(self, session_uid: str) -> Optional[datetime]:
        """
        Wall-clock time corresponding to session_time == 0 for this session.

        Frame timestamps are derived from this rather than from the clock at
        insert time, so a frame that arrives twice lands on one row.
        """
        return self._session_starts.get(session_uid)

    def _insert_session(self, packet, session_type: int):
        """Insert the session row and its track geometry on the first Session packet."""
        session_uid = str(packet.header.session_uid)
        try:
            # Anchor the session: the packet's own session_time tells us how
            # long ago session_time == 0 was.
            session_start = datetime.now(timezone.utc) - timedelta(
                seconds=packet.header.session_time
            )

            # Slice the fixed-size zone arrays down to their real counts so we
            # store the actual zones, not the 8/8/4-slot arrays padded with
            # zero-entries.
            aero_zones_full = packet.active_aero_zones_full[:packet.num_active_aero_zones_full]
            aero_zones_partial = packet.active_aero_zones_partial[:packet.num_active_aero_zones_partial]
            drs_zones = packet.drs_zones[:packet.num_drs_zones]

            self._sessions_repo.update_track_technical_data(
                track_id=packet.track_id,
                track_length=packet.track_length,
                sector2_start=packet.sector_2_lap_distance_start,
                sector3_start=packet.sector_3_lap_distance_start,
                marshal_zones=packet.marshal_zones[:packet.num_marshal_zones],
                pit_speed_limit=packet.pit_speed_limit,
                active_aero_track_status=packet.active_aero_track_status,
                active_aero_zones_full=aero_zones_full,
                active_aero_zones_partial=aero_zones_partial,
                drs_zones=drs_zones,
            )

            weekend_link = packet.weekend_link_identifier
            session_link = packet.session_link_identifier
            season_link = packet.season_link_identifier

            weekend_structure = [
                safe_enum_name(SessionTypeIDs, s, self._logger)
                for s in packet.weekend_structure[:packet.num_sessions_in_weekend]
            ]

            type_name, formula_name, mode_name, ruleset_name = resolve_session_enums(
                session_type, packet.formula_type, packet.game_mode,
                packet.rule_set, self._logger,
            )

            self._sessions_repo.insert_session((
                session_uid,
                str(weekend_link) if weekend_link else session_uid,
                str(session_link) if session_link else session_uid,
                str(season_link) if season_link else None,
                session_start,
                packet.track_id,
                type_name,
                formula_name,
                mode_name,
                ruleset_name,
                packet.total_laps,
                packet.session_duration,
                packet.num_sessions_in_weekend,
                weekend_structure,
                packet.time_of_day,
                packet.session_length,
                bool(packet.network_game),
                packet.ai_difficulty,
                packet.forecast_accuracy,
                bool(packet.equal_car_performance),
                bool(packet.sli_pro_native_support),
                packet.assist_steering,
                packet.assist_braking,
                packet.assist_gearbox,
                packet.assist_pit,
                packet.assist_pit_release,
                packet.assist_ers,
                packet.assist_drs,
                packet.anti_lock_brakes_assist,
                packet.traction_control_assist,
                packet.dynamic_racing_line,
                packet.dynamic_racing_line_type,
                packet.dynamic_racing_line_hi_vis,
                packet.dynamic_racing_line_colour_blind,
                packet.recovery_mode,
                packet.flashback_limit,
                packet.recurring_rewind_prompt,
                packet.surface_type,
                packet.low_fuel_mode,
                packet.race_starts,
                packet.tyre_temperature,
                packet.pit_lane_tyre_sim,
                packet.car_damage,
                packet.car_damage_rate,
                packet.collisions,
                packet.collisions_off_for_first_lap_only,
                packet.mp_unsafe_pit_release,
                packet.mp_off_for_griefing,
                packet.corner_cutting_stringency,
                packet.parc_ferme_rules,
                packet.pit_stop_experience,
                packet.safety_car,
                packet.safety_car_experience,
                packet.formation_lap,
                packet.formation_lap_experience,
                packet.red_flags,
                packet.affects_licence_level_solo,
                packet.affects_licence_level_mp,
                packet.speed_units_lead_player,
                packet.temperature_units_lead_player,
                packet.speed_units_secondary_player,
                packet.temperature_units_secondary_player,
            ))

            # Read the anchor back rather than trusting the local value: on a
            # listener restart mid-session the stored row already holds the
            # original anchor, and reusing it keeps frame keys stable.
            stored_start = self._sessions_repo.get_session_start(session_uid)
            self._session_starts[session_uid] = stored_start or session_start

        except Exception as e:
            self._logger.error(f"Failed to insert session: {e}", exc_info=True)

    def _insert_timeline(self, packet):
        """Insert one live-state sample for this Session packet."""
        try:
            marshal_zone_flags = [
                safe_enum_name(FlagStatus, zone.zone_flag, self._logger)
                for zone in packet.marshal_zones[:packet.num_marshal_zones]
            ]
            session_uid = str(packet.header.session_uid)
            session_start = self.get_session_start(session_uid)
            session_time = packet.header.session_time
            timestamp = (
                session_start + timedelta(seconds=session_time)
                if session_start is not None
                else datetime.now(timezone.utc)
            )

            self._session_timeline_repo.insert_timeline_entry((
                timestamp,
                session_uid,
                session_time,
                packet.header.overall_frame_identifier,
                packet.session_time_left,
                packet.total_laps if packet.total_laps > 0 else None,
                safe_enum_name(WeatherIDs, packet.weather, self._logger),
                packet.track_temperature,
                packet.air_temperature,
                safe_enum_name(SafetyCarStatus, packet.safety_car_status, self._logger),
                marshal_zone_flags,
                packet.num_safety_car_periods,
                packet.num_virtual_safety_car_periods,
                packet.num_red_flag_periods,
                bool(packet.game_paused),
                bool(packet.is_spectating),
                packet.spectator_car_index,
                packet.pit_stop_window_ideal_lap or None,
                packet.pit_stop_window_latest_lap or None,
                packet.pit_stop_rejoin_position or None,
            ))
        except Exception as e:
            self._logger.error(f"Failed to insert session timeline: {e}", exc_info=True)

    def _update_weather_forecast(self, packet):
        """Upsert the forecast, skipping the write when nothing changed."""
        try:
            samples = packet.weather_forecast_samples[:packet.num_weather_forecast_samples]
            if not samples:
                return

            session_uid = str(packet.header.session_uid)

            forecast_hash = hash(tuple(
                (s.session_type, s.time_offset, s.weather,
                 s.track_temperature, s.track_temperature_change,
                 s.air_temperature, s.air_temperature_change,
                 s.rain_percentage)
                for s in samples
            ))

            if self._last_forecast_hash.get(session_uid) == forecast_hash:
                return

            self._sessions_repo.upsert_weather_forecast(
                session_uid=session_uid,
                overall_frame_identifier=packet.header.overall_frame_identifier,
                forecast_samples=samples,
            )
            self._last_forecast_hash[session_uid] = forecast_hash

        except Exception as e:
            self._logger.error(f"Failed to update weather forecast: {e}", exc_info=True)
