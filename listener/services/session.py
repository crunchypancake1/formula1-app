"""Session service for handling Session packets (Packet 1)."""

import logging
from typing import Optional

from database.repositories import SessionsRepository, SessionTimelineRepository
from utils.bounded_dict import BoundedDict
from utils.bounded_set import BoundedSet

_SPRINT_SHOOTOUT_IDS = {10, 11, 12, 13, 14}
_RACE_IDS = {15, 16, 17}
_SPRINT_RACE_ID = 100


def _resolve_session_type(packet) -> int:
    """Return the effective session type, remapping RACE to SPRINT_RACE on sprint weekends."""
    session_type = packet.session_type
    num_sessions = getattr(packet, "num_sessions_in_weekend", 0)
    weekend_structure = getattr(packet, "weekend_structure", [])
    weekend_sessions = set(weekend_structure[:num_sessions])
    has_sprint_quali = bool(weekend_sessions & _SPRINT_SHOOTOUT_IDS)
    num_races = len(weekend_sessions & _RACE_IDS)
    if has_sprint_quali and num_races >= 2 and session_type == 15:
        return _SPRINT_RACE_ID
    return session_type


class SessionService:
    """
    Handles Session packets (Packet 1).

    Writes to:
    - sessions table (first packet only)
    - session_timeline hypertable (every packet)
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
        self._last_forecast_hash: BoundedDict = BoundedDict(200)
        self._session_types: BoundedDict = BoundedDict(200)
        self._track_ids: BoundedDict = BoundedDict(200)


    def handle_session_packet(self, packet):
        """
        Process a Session packet.

        Args:
            packet: SessionPacket from packets.unpack_session()
        """
        session_uid = str(packet.header.session_uid)

        # Determine effective session type (remap RACE to SPRINT_RACE on sprint weekends)
        session_type = _resolve_session_type(packet)

        # Track session type for classification routing
        self._session_types[session_uid] = session_type
        self._track_ids[session_uid] = packet.track_id

        # Insert into sessions table (first packet only)
        if session_uid not in self._seen_sessions:
            self._insert_session(packet, session_type)
            self._seen_sessions.add(session_uid)

        # Insert into session_timeline hypertable (every packet)
        self._insert_timeline(packet)

        # Update weather forecast (every packet - upserts to keep latest)
        self._update_weather_forecast(packet)

    def get_session_type(self, session_uid: str) -> Optional[int]:
        """
        Get the session type for a given session UID.

        Args:
            session_uid: Session identifier

        Returns:
            Session type ID, or None if session not seen
        """
        return self._session_types.get(session_uid)

    def get_track_id(self, session_uid: str) -> Optional[int]:
        """Get the track_id for a session, if known."""
        return self._track_ids.get(session_uid)

    def _insert_session(self, packet, session_type: int):
        """Insert session record on first Session packet."""
        try:
            session_uid_str = str(packet.header.session_uid)
            weekend_link_val = getattr(packet, "weekend_link_identifier", 0)
            session_link_val = getattr(packet, "session_link_identifier", 0)

            # Update technical track data (track must already exist)
            self._sessions_repo.update_track_technical_data(
                track_id=packet.track_id,
                track_length=packet.track_length,
                sector2_start=packet.sector_2_lap_distance_start,
                sector3_start=packet.sector_3_lap_distance_start,
                marshal_zones=getattr(packet, 'marshal_zones', []),
                pit_speed_limit=packet.pit_speed_limit,
            )

            self._sessions_repo.insert_session(
                session_uid=session_uid_str,
                weekend_link=str(weekend_link_val) if weekend_link_val else session_uid_str,
                session_link=str(session_link_val) if session_link_val else session_uid_str,
                track_id=packet.track_id,
                session_type=session_type,
                formula=packet.formula_type,
                game_mode=packet.game_mode,
                ruleset=packet.rule_set,
                total_laps=packet.total_laps,
                session_duration=packet.session_duration,
                num_sessions_in_weekend=packet.num_sessions_in_weekend,
                time_of_day=packet.time_of_day,
                session_length=packet.session_length,
            )

        except Exception as e:
            self._logger.error(f"Failed to insert session: {e}", exc_info=True)

    def _insert_timeline(self, packet):
        """Insert session timeline record."""
        try:
            total_laps = 0
            if hasattr(packet, "total_laps") and packet.total_laps > 0:
                total_laps = packet.total_laps

            self._session_timeline_repo.insert_timeline_entry(
                session_uid=str(packet.header.session_uid),
                session_time=packet.header.session_time,
                overall_frame_identifier=packet.header.overall_frame_identifier,
                session_time_left=packet.session_time_left,
                total_laps=total_laps,
                safety_car_status=packet.safety_car_status,
                weather_track_temp=packet.track_temperature,
                weather_air_temp=packet.air_temperature,
                weather_state=packet.weather,
            )
        except Exception as e:
            self._logger.error(f"Failed to insert session timeline: {e}", exc_info=True)

    def _update_weather_forecast(self, packet):
        """Update weather forecast samples (upserts latest forecast, skips if unchanged)."""
        try:
            if not hasattr(packet, 'weather_forecast_samples') or not packet.weather_forecast_samples:
                return

            session_uid = str(packet.header.session_uid)

            forecast_key = tuple(
                (s.session_type, s.time_offset, s.weather,
                 s.track_temperature, s.track_temperature_change,
                 s.air_temperature, s.air_temperature_change,
                 s.rain_percentage)
                for s in packet.weather_forecast_samples
            )
            forecast_hash = hash(forecast_key)

            if self._last_forecast_hash.get(session_uid) == forecast_hash:
                return

            self._sessions_repo.upsert_weather_forecast(
                session_uid=session_uid,
                overall_frame_identifier=packet.header.overall_frame_identifier,
                forecast_samples=packet.weather_forecast_samples,
            )
            self._last_forecast_hash[session_uid] = forecast_hash

        except Exception as e:
            self._logger.error(f"Failed to update weather forecast: {e}", exc_info=True)
