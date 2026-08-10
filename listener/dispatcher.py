"""Packet dispatcher for routing UDP packets to appropriate services."""

import logging
import threading
from typing import Any, Optional, Set

from frame_buffer import FrameBuffer
from packets import (
    PACKET_HEADER_FORMAT_SIZE,
    SafetyCar,
    packet_header,
    unpack_car_damage,
    unpack_car_setup,
    unpack_car_status,
    unpack_car_telemetry,
    unpack_event_packet,
    unpack_final_classification,
    unpack_lap_data,
    unpack_lap_positions,
    unpack_lobby_info,
    unpack_motion,
    unpack_motion_ex,
    unpack_participants,
    unpack_session,
    unpack_session_history,
    unpack_tyre_sets,
)
from packets.packet_header import PacketValidationError, validate_packet_header
from services import (
    CarFrameService,
    CarSetupService,
    EventsService,
    FinalClassificationService,
    LapHistoryService,
    LapPositionsService,
    LobbyInfoService,
    MotionExService,
    ParticipantsService,
    SessionService,
    TyreSetsService,
)
from utils.bounded_dict import BoundedDict
from utils.bounded_set import BoundedSet

# Session types to exclude from collection (unknown and time trial only)
EXCLUDED_SESSION_TYPES: Set[int] = {0, 18}

# Race session types where lap positions are meaningful
RACE_SESSION_TYPES: Set[int] = {15, 16, 17, 100}

# Packet IDs that combine into a single car_frame row (buffered)
CAR_FRAME_PACKET_IDS: Set[int] = {0, 2, 6, 7, 10}

# Session-level event codes that don't require a user_map
_SESSION_LEVEL_EVENT_CODES: Set[str] = {
    "SSTA", "SEND", "LGOT", "CHQF", "RDFL", "DRSE", "DRSD", "STLG", "SCAR",
}


class PacketDispatcher:
    """
    Routes UDP packets to appropriate service handlers.

    Independent packets (session, participants, events, classification, history,
    lap positions) are processed immediately on arrival. Only car_frame packets
    (0, 2, 6, 7, 10) are buffered to be combined into a single write.
    """

    def __init__(
        self,
        session_service: SessionService,
        participants_service: ParticipantsService,
        car_frame_service: CarFrameService,
        lap_history_service: LapHistoryService,
        events_service: EventsService,
        final_classification_service: FinalClassificationService,
        lap_positions_service: LapPositionsService,
        car_setup_service: Optional[CarSetupService] = None,
        tyre_sets_service: Optional[TyreSetsService] = None,
        motion_ex_service: Optional[MotionExService] = None,
        lobby_info_service: Optional[LobbyInfoService] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._session_service = session_service
        self._participants_service = participants_service
        self._car_frame_service = car_frame_service
        self._lap_history_service = lap_history_service
        self._events_service = events_service
        self._final_classification_service = final_classification_service
        self._lap_positions_service = lap_positions_service
        self._car_setup_service = car_setup_service
        self._tyre_sets_service = tyre_sets_service
        self._motion_ex_service = motion_ex_service
        self._lobby_info_service = lobby_info_service
        self._logger = logger or logging.getLogger(__name__)

        self._known_sessions = BoundedSet(max_size=100)
        self._excluded_sessions = BoundedSet(max_size=100)
        # session_uid -> {car_index: user_id}
        self._user_maps: BoundedDict[str, dict[int, int]] = BoundedDict(200)
        # session_uid -> bool (True = race started or non-race session)
        self._race_started: BoundedDict[str, bool] = BoundedDict(200)
        # Sessions where final classification (Packet 8) has been received.
        # Tyre stints are only written from the bulk Session History update
        # that the game sends after classification.
        self._classification_received = BoundedSet(max_size=100)
        # (session_uid, user_id) -> last seen lap number for lap completion detection
        self._last_lap_nums: BoundedDict[tuple, int] = BoundedDict(500)

        self._frame_buffer = FrameBuffer(
            flush_callback=self._flush_frame,
            logger=self._logger,
        )
        self._lock = threading.Lock()

    def handle_packet(self, data: bytes):
        """Parse a UDP packet and route it to the appropriate handler."""
        with self._lock:
            try:
                if len(data) < PACKET_HEADER_FORMAT_SIZE:
                    self._logger.warning(f"Packet too short: {len(data)} bytes")
                    return

                header = packet_header.unpack_packet_header(data[:PACKET_HEADER_FORMAT_SIZE])

                try:
                    validate_packet_header(header)
                except PacketValidationError:
                    return

                body = data[PACKET_HEADER_FORMAT_SIZE:]
                session_uid = str(header.session_uid)

                if session_uid in self._excluded_sessions:
                    return

                # Session packet (1) — process immediately
                if header.packet_id == 1:
                    packet = unpack_session(header, body)
                    if packet.session_type in EXCLUDED_SESSION_TYPES:
                        self._excluded_sessions.add(session_uid)
                        self._logger.debug(
                            f"Excluding session {session_uid} (type={packet.session_type})"
                        )
                        return
                    self._known_sessions.add(session_uid)
                    self._session_service.handle_session_packet(packet)
                    # Set race_started default: True for non-race, False for race
                    if session_uid not in self._race_started:
                        self._race_started[session_uid] = packet.session_type not in RACE_SESSION_TYPES
                    return

                # Lobby Info packet (9) — process before known-session gate
                if header.packet_id == 9:
                    if self._lobby_info_service:
                        packet = unpack_lobby_info(header, body)
                        self._lobby_info_service.handle_lobby_info_packet(packet)
                    return

                # Gate non-Session packets on known sessions
                if session_uid not in self._known_sessions:
                    self._logger.debug(
                        f"Skipping packet (ID={header.packet_id}) for unknown session {session_uid}"
                    )
                    return

                # Participants packet (4) — process immediately, builds user_map
                if header.packet_id == 4:
                    packet = unpack_participants(header, body)
                    new_map = self._participants_service.handle_participants_packet(packet)
                    if new_map:
                        self._user_maps[session_uid] = new_map
                    return

                # Events packet (3) — session-level events bypass user_map gate
                if header.packet_id == 3:
                    packet = unpack_event_packet(header, body)
                    event_code = str(packet.event_string_code).strip()[:10]

                    if event_code in _SESSION_LEVEL_EVENT_CODES:
                        user_map = self._user_maps.get(session_uid, {}) or {}
                        self._events_service.handle_event_packet(packet, user_map)
                        if event_code == "SEND":
                            self._frame_buffer.flush_session(session_uid)
                        # Detect formation lap end → race start
                        elif event_code == "SCAR" and isinstance(packet.event, SafetyCar):
                            if packet.event.safety_car_type == 3 and packet.event.event_type == 3:
                                self._race_started[session_uid] = True
                                self._logger.info(
                                    f"Race start detected for session {session_uid} (formation lap complete)"
                                )
                        return

                    # Driver-specific events require user_map
                    user_map = self._user_maps.get(session_uid)
                    if not user_map:
                        self._logger.debug(
                            f"Skipping event {event_code} for session {session_uid} — no user_map yet"
                        )
                        return
                    self._events_service.handle_event_packet(packet, user_map)
                    return

                # All remaining packets require a user_map
                user_map = self._user_maps.get(session_uid)
                if not user_map:
                    self._logger.debug(
                        f"Skipping packet (ID={header.packet_id}) for session {session_uid} — no user_map yet"
                    )
                    return

                # Car Setup packet (5) — cache all driver setups
                if header.packet_id == 5:
                    if self._car_setup_service is not None:
                        packet = unpack_car_setup(header, body)
                        self._car_setup_service.handle_car_setup_packet(
                            packet, session_uid, self._user_maps.get(session_uid, {}) or {},
                        )
                    return

                # Tyre Sets packet (12) — cache available tyre sets
                if header.packet_id == 12:
                    if self._tyre_sets_service is not None:
                        packet = unpack_tyre_sets(header, body)
                        self._tyre_sets_service.handle_tyre_sets_packet(packet, user_map)
                    return

                # Motion Ex packet (13) — player-only, NOT buffered, write immediately
                if header.packet_id == 13:
                    if self._motion_ex_service is not None:
                        packet = unpack_motion_ex(header, body)
                        self._motion_ex_service.write_motion_ex(packet, user_map)
                    return

                # Final Classification packet (8) — process immediately
                if header.packet_id == 8:
                    packet = unpack_final_classification(header, body)
                    self._final_classification_service.handle_final_classification_packet(packet, user_map)
                    self._classification_received.add(session_uid)
                    self._logger.info(
                        "Final classification received for session %s — "
                        "tyre stints will be captured from bulk session history update",
                        session_uid,
                    )
                    return

                # Session History packet (11) — laps always, tyre stints only after classification
                if header.packet_id == 11:
                    packet = unpack_session_history(header, body)
                    self._lap_history_service.handle_session_history_packet(packet, user_map)
                    if session_uid in self._classification_received:
                        self._lap_history_service.handle_tyre_stints(packet, user_map)
                    return

                # Lap Positions packet (15) — process immediately (race sessions only)
                if header.packet_id == 15:
                    session_type = self._session_service.get_session_type(session_uid)
                    if session_type in RACE_SESSION_TYPES:
                        packet = unpack_lap_positions(header, body)
                        self._lap_positions_service.handle_lap_positions_packet(packet, user_map)
                    return

                # Car frame packets (0, 2, 6, 7, 10) — buffer for combined write
                if header.packet_id in CAR_FRAME_PACKET_IDS:
                    self._frame_buffer.add(
                        session_uid=session_uid,
                        frame_identifier=header.overall_frame_identifier,
                        packet_id=header.packet_id,
                        header=header,
                        body=body,
                    )
                    self._frame_buffer.check_periodic_flush()

            except Exception as e:
                self._logger.error(f"Error handling packet: {e}", exc_info=True)

    def _flush_frame(self, session_uid: str, frame_id: int, packets: dict[int, Any]):
        """
        Flush a frame's car_frame packets (0+2+6+7+10) as a combined write.
        """
        user_map = self._user_maps.get(session_uid, {}) or {}
        if not user_map:
            self._logger.debug(
                f"Skipping frame {frame_id} for session {session_uid} — no user_map yet"
            )
            return

        motion_data = None
        telemetry_data = None
        lap_data_list = None
        car_status_data = None
        car_damage_data = None
        session_time = 0.0

        # Determine session_time from whichever packet is available
        for pid in (0, 6, 2):
            if pid in packets:
                header, _ = packets[pid]
                session_time = header.session_time
                break

        if session_time < 1.0:
            return

        if 0 in packets:
            header, body = packets[0]
            motion_packet = unpack_motion(header, body)
            motion_data = motion_packet.car_motion_data
            session_time = header.session_time

        if 6 in packets:
            header, body = packets[6]
            telemetry_packet = unpack_car_telemetry(header, body)
            telemetry_data = telemetry_packet.car_telemetry_data
            session_time = header.session_time

        if 2 in packets:
            header, body = packets[2]
            lap_data_packet = unpack_lap_data(header, body)
            lap_data_list = lap_data_packet.lap_data
            session_time = header.session_time

        if 7 in packets:
            header, body = packets[7]
            packet = unpack_car_status(header, body)
            car_status_data = packet.car_status_data

        if 10 in packets:
            header, body = packets[10]
            damage_packet = unpack_car_damage(header, body)
            car_damage_data = damage_packet.car_damage_data

        race_started_val = self._race_started.get(session_uid, True)
        race_started = race_started_val if race_started_val is not None else True

        if motion_data or telemetry_data or lap_data_list or car_status_data:
            self._car_frame_service.write_frame(
                session_uid=session_uid,
                session_time=session_time,
                overall_frame_identifier=frame_id,
                user_map=user_map,
                motion_data=motion_data,
                telemetry_data=telemetry_data,
                lap_data_list=lap_data_list,
                car_status_data=car_status_data,
                car_damage_data=car_damage_data,
                race_started=race_started,
            )

        # Detect lap completions for setup + tyre set writes
        if lap_data_list:
            self._check_lap_completions(session_uid, user_map, lap_data_list)

    def _check_lap_completions(
        self,
        session_uid: str,
        user_map: dict[int, int],
        lap_data_list,
    ):
        """Detect lap completions and notify setup/tyre services."""
        for car_index, lap_data in enumerate(lap_data_list):
            user_id = user_map.get(car_index)
            if user_id is None:
                continue

            if lap_data.driver_status not in (1, 4):
                continue

            key = (session_uid, user_id)
            current_lap = lap_data.current_lap_num
            last_lap: int = self._last_lap_nums.get(key, 0) or 0

            if current_lap > last_lap and last_lap > 0:
                completed_lap = last_lap
                track_id = self._session_service.get_track_id(session_uid)

                if track_id is not None and self._car_setup_service is not None:
                    self._car_setup_service.on_lap_complete(
                        session_uid, user_id, completed_lap, track_id,
                    )
                if self._tyre_sets_service is not None:
                    self._tyre_sets_service.on_lap_complete(
                        session_uid, user_id, car_index, completed_lap,
                    )

            self._last_lap_nums[key] = current_lap
