"""Packet dispatcher for routing UDP packets to the appropriate services."""

import logging
import threading
from typing import Any, Optional, Set

from frame_buffer import FrameBuffer
from packets import (
    PACKET_HEADER_FORMAT_SIZE,
    Flashback,
    SafetyCar,
    packet_header,
    unpack_car_damage,
    unpack_car_setup,
    unpack_car_status,
    unpack_car_telemetry,
    unpack_car_telemetry2,
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
from packets.packet_header import (
    EXPECTED_BODY_SIZE,
    VARIABLE_LENGTH_PACKET_IDS,
    PacketValidationError,
    validate_packet_header,
)
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

# Session types never collected: unknown, and time trial (which has its own
# packet 14 and no meaningful multi-car data).
EXCLUDED_SESSION_TYPES: Set[int] = {0, 18}

# Race session types where lap positions are meaningful
RACE_SESSION_TYPES: Set[int] = {15, 16, 17, 100}

# Packet IDs that describe the same simulation tick and combine into one
# car_frame row.
CAR_FRAME_PACKET_IDS: Set[int] = {0, 2, 6, 7, 10, 16}

# Session-level event codes that don't require a user_map
_SESSION_LEVEL_EVENT_CODES: Set[str] = {
    "SSTA", "SEND", "LGOT", "CHQF", "RDFL", "DRSE", "DRSD", "STLG", "SCAR", "FLBK", "BUTN",
}

# Safety car type 3 (formation lap) + event type 3 (resume race) is the game
# telling us the formation lap is over.
_FORMATION_LAP_SAFETY_CAR = 3
_RESUME_RACE = 3

# A car reporting this lap number cannot still be on the formation lap. Used as
# a backstop so a missed start event can never cost a whole race's telemetry.
_RACING_LAP_NUM = 2


class PacketDispatcher:
    """
    Routes UDP packets to the appropriate service handlers.

    Independent packets (session, participants, events, classification, history,
    lap positions, setups, tyre sets, motion ex, lobby) are processed on arrival.
    Only the car_frame packets (0, 2, 6, 7, 10, 16) are buffered, so that the
    packets describing one simulation tick become a single row.
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
        # session_uid -> bool (True = race under way, or a non-race session)
        self._race_started: BoundedDict[str, bool] = BoundedDict(200)
        # Sessions where final classification (Packet 8) has been received.
        # Tyre stints are only written from the bulk Session History update
        # that the game sends after classification.
        self._classification_received = BoundedSet(max_size=100)
        # (session_uid, user_id) -> last seen lap number, for lap completion detection
        self._last_lap_nums: BoundedDict[tuple, int] = BoundedDict(500)

        self._frame_buffer = FrameBuffer(
            flush_callback=self._flush_frame,
            logger=self._logger,
        )
        self._lock = threading.Lock()
        # (session_uid, packet_id) pairs already logged for a body-size
        # mismatch, so a persistently wrong packet logs once per session
        # instead of once per packet (same rate-limit pattern as
        # packet_header.py's format rejection logging).
        self._logged_size_mismatches = BoundedSet(max_size=200)

    def _validate_body_size(self, header, body: bytes) -> bool:
        """
        Validate a packet body's length against EXPECTED_BODY_SIZE.

        Variable-length packets (8, 9, 11) are validated as an upper bound;
        all others must match exactly. Returns False (and logs, rate-limited
        per (session_uid, packet_id)) on mismatch.
        """
        expected = EXPECTED_BODY_SIZE.get(header.packet_id)
        if expected is None:
            return True

        if header.packet_id in VARIABLE_LENGTH_PACKET_IDS:
            ok = len(body) <= expected
        else:
            ok = len(body) == expected

        if not ok:
            key = (header.session_uid, header.packet_id)
            if key not in self._logged_size_mismatches:
                self._logged_size_mismatches.add(key)
                self._logger.warning(
                    "Dropping packet_id=%s for session %s — body size %d "
                    "doesn't match expected %s%d",
                    header.packet_id,
                    header.session_uid,
                    len(body),
                    "<= " if header.packet_id in VARIABLE_LENGTH_PACKET_IDS else "",
                    expected,
                )
        return ok

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

                if not self._validate_body_size(header, body):
                    return

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
                    # Non-race sessions are "started" from the first packet;
                    # races wait for lights out or the end of the formation lap.
                    if session_uid not in self._race_started:
                        self._race_started[session_uid] = (
                            packet.session_type not in RACE_SESSION_TYPES
                        )
                    return

                # Lobby Info packet (9) — process before the known-session gate,
                # since a lobby exists before any session packet arrives
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

                # Events packet (3) — session-level events bypass the user_map gate
                if header.packet_id == 3:
                    packet = unpack_event_packet(header, body)
                    event_code = str(packet.event_string_code).strip()[:10]

                    if event_code in _SESSION_LEVEL_EVENT_CODES:
                        user_map = self._user_maps.get(session_uid) or {}
                        self._events_service.handle_event_packet(packet, user_map)
                        if event_code == "SEND":
                            self._frame_buffer.flush_session(session_uid)
                        elif event_code == "FLBK":
                            self._handle_flashback(session_uid, packet)
                        elif event_code == "LGOT":
                            # Lights out: the race is definitively under way.
                            self._mark_race_started(session_uid, "lights out")
                        elif event_code == "SCAR" and isinstance(packet.event, SafetyCar):
                            if (packet.event.safety_car_type == _FORMATION_LAP_SAFETY_CAR
                                    and packet.event.event_type == _RESUME_RACE):
                                self._mark_race_started(session_uid, "formation lap complete")
                        return

                    # Driver-specific events require a user_map
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

                # Car Setup packet (5) — cache every driver's setup
                if header.packet_id == 5:
                    if self._car_setup_service is not None:
                        packet = unpack_car_setup(header, body)
                        self._car_setup_service.handle_car_setup_packet(
                            packet, session_uid, user_map,
                        )
                    return

                # Tyre Sets packet (12) — cache the available sets for one car
                if header.packet_id == 12:
                    if self._tyre_sets_service is not None:
                        packet = unpack_tyre_sets(header, body)
                        self._tyre_sets_service.handle_tyre_sets_packet(
                            packet,
                            user_map,
                            self._participants_service.get_restricted_indices(session_uid),
                        )
                    return

                # Motion Ex packet (13) — player-only, written immediately (not buffered)
                if header.packet_id == 13:
                    if self._motion_ex_service is not None:
                        packet = unpack_motion_ex(header, body)
                        self._motion_ex_service.write_motion_ex(
                            packet,
                            user_map,
                            self._session_service.get_session_start(session_uid),
                        )
                    return

                # Final Classification packet (8) — process immediately
                if header.packet_id == 8:
                    packet = unpack_final_classification(header, body)
                    self._final_classification_service.handle_final_classification_packet(
                        packet, user_map
                    )
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

                # Lap Positions packet (15) — race sessions only
                if header.packet_id == 15:
                    session_type = self._session_service.get_session_type(session_uid)
                    if session_type in RACE_SESSION_TYPES:
                        packet = unpack_lap_positions(header, body)
                        self._lap_positions_service.handle_lap_positions_packet(packet, user_map)
                    return

                # Car frame packets (0, 2, 6, 7, 10, 16) — buffer for a combined write
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

    def _mark_race_started(self, session_uid: str, reason: str) -> None:
        """Flip a race session out of formation-lap mode, once."""
        if self._race_started.get(session_uid):
            return
        self._race_started[session_uid] = True
        self._logger.info("Race start detected for session %s (%s)", session_uid, reason)

    def _handle_flashback(self, session_uid: str, packet) -> None:
        """
        Discard the telemetry a flashback undid, and record that it happened.

        A flashback rewinds m_sessionTime and m_frameIdentifier but not
        m_overallFrameIdentifier, so without this the rows recorded during the
        rewound-over stretch would sit in the database as if that run really
        happened — producing duplicate laps at different times.
        """
        event = packet.event
        if not isinstance(event, Flashback):
            return

        rewind_to = event.flashback_session_time
        self._frame_buffer.discard_session(session_uid)

        # The session anchor turns the DELETEs' session_time bound into a
        # `timestamp` bound as well, which is the frame hypertables'
        # partitioning column — without it each flashback scans every chunk of
        # every session ever recorded.
        session_start = self._session_service.get_session_start(session_uid)

        discarded = self._car_frame_service.discard_after(
            session_uid, rewind_to, session_start
        )
        if self._motion_ex_service is not None:
            self._motion_ex_service.discard_after(session_uid, rewind_to, session_start)

        # Lap-completion detection tracks the highest lap number seen; after a
        # rewind those counters are ahead of reality.
        for key in [k for k in self._last_lap_nums.keys() if k[0] == session_uid]:
            self._last_lap_nums[key] = 0

        self._events_service.record_flashback(
            session_uid,
            packet.header.overall_frame_identifier,
            packet.header.session_time,
            event,
            discarded,
        )
        self._logger.info(
            "Flashback in session %s to session_time %.3f — discarded %s frame row(s)",
            session_uid, rewind_to, discarded,
        )

    def _flush_frame(self, session_uid: str, frame_id: int, packets: dict[int, Any]):
        """Flush one frame's buffered packets (0, 2, 6, 7, 10, 16) as a combined write."""
        user_map = self._user_maps.get(session_uid) or {}
        if not user_map:
            self._logger.debug(
                f"Skipping frame {frame_id} for session {session_uid} — no user_map yet"
            )
            return

        motion_data = None
        telemetry_packet = None
        telemetry_data = None
        lap_data_list = None
        car_status_data = None
        car_damage_data = None
        car_telemetry2_data = None

        # Every packet in the frame carries the same session_time; take it from
        # whichever one is present.
        first_header = next(iter(packets.values()))[0]
        session_time = first_header.session_time

        if session_time < 1.0:
            return

        if 0 in packets:
            header, body = packets[0]
            motion_data = unpack_motion(header, body).car_motion_data

        if 6 in packets:
            header, body = packets[6]
            telemetry_packet = unpack_car_telemetry(header, body)
            telemetry_data = telemetry_packet.car_telemetry_data

        if 2 in packets:
            header, body = packets[2]
            lap_data_list = unpack_lap_data(header, body).lap_data

        if 7 in packets:
            header, body = packets[7]
            car_status_data = unpack_car_status(header, body).car_status_data

        if 10 in packets:
            header, body = packets[10]
            car_damage_data = unpack_car_damage(header, body).car_damage_data

        if 16 in packets:
            header, body = packets[16]
            car_telemetry2_data = unpack_car_telemetry2(header, body).car_telemetry2_data

        # Backstop for a missed start event: nobody is on lap 2 during a
        # formation lap, so seeing one means the race is running.
        if lap_data_list and not self._race_started.get(session_uid):
            if any(
                lap.current_lap_num >= _RACING_LAP_NUM
                for car_index, lap in enumerate(lap_data_list)
                if car_index in user_map
            ):
                self._mark_race_started(session_uid, "car on a racing lap")

        race_started = bool(self._race_started.get(session_uid, True))
        restricted_indices = self._participants_service.get_restricted_indices(session_uid)

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
                car_telemetry2_data=car_telemetry2_data,
                telemetry_packet=telemetry_packet,
                player_car_index=first_header.player_car_index,
                restricted_indices=restricted_indices,
                session_start=self._session_service.get_session_start(session_uid),
                race_started=race_started,
            )

        if lap_data_list and race_started:
            self._check_lap_completions(session_uid, user_map, lap_data_list)

    def _check_lap_completions(
        self,
        session_uid: str,
        user_map: dict[int, int],
        lap_data_list,
    ):
        """Detect lap completions and notify the setup and tyre-set services."""
        for car_index, lap_data in enumerate(lap_data_list):
            user_id = user_map.get(car_index)
            if user_id is None:
                continue

            # Only count laps completed while actually driving (flying lap or on track).
            if lap_data.driver_status not in (1, 4):
                continue

            key = (session_uid, user_id)
            current_lap = lap_data.current_lap_num
            last_lap: int = self._last_lap_nums.get(key) or 0

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
