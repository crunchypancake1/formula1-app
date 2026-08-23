"""Events service for handling Event packets (Packet 3) with typed event tables."""

import logging
from typing import Optional
from database.repositories import (
    EventsButtonsRepository,
    EventsCollisionsRepository,
    EventsDriverActionsRepository,
    EventsFastestLapsRepository,
    EventsFlashbacksRepository,
    EventsOvertakesRepository,
    EventsPenaltiesRepository,
    EventsRaceControlRepository,
    EventsRetirementsRepository,
    EventsSpeedTrapsRepository,
)
from database.repositories.base import safe_enum_name
from enums import (
    ButtonFlags,
    DrsDisabledReason,
    InfringementType,
    PenaltyType,
    ResultReason,
    SafetyCarEventType,
    SafetyCarStatus,
)

# The game's "not set" sentinel on the uint8 fields of a penalty event.
_NOT_SET = 255

# Session-level event codes (no driver involved)
_RACE_CONTROL_CODES = {"SSTA", "SEND", "LGOT", "CHQF", "RDFL", "DRSE", "DRSD", "STLG", "SCAR"}

# Simple single-driver action codes
_DRIVER_ACTION_CODES = {"RCWN", "TMPT", "DTSV", "SGSV"}


class EventsService:
    """
    Handles Event packets (Packet 3).

    Routes each event_code to the appropriate typed repository.
    Translates vehicle_index -> user_id using the user_map.
    """

    def __init__(
        self,
        race_control_repo: EventsRaceControlRepository,
        overtakes_repo: EventsOvertakesRepository,
        collisions_repo: EventsCollisionsRepository,
        penalties_repo: EventsPenaltiesRepository,
        fastest_laps_repo: EventsFastestLapsRepository,
        retirements_repo: EventsRetirementsRepository,
        speed_traps_repo: EventsSpeedTrapsRepository,
        driver_actions_repo: EventsDriverActionsRepository,
        flashbacks_repo: Optional[EventsFlashbacksRepository] = None,
        buttons_repo: Optional[EventsButtonsRepository] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._race_control_repo = race_control_repo
        self._overtakes_repo = overtakes_repo
        self._collisions_repo = collisions_repo
        self._penalties_repo = penalties_repo
        self._fastest_laps_repo = fastest_laps_repo
        self._retirements_repo = retirements_repo
        self._speed_traps_repo = speed_traps_repo
        self._driver_actions_repo = driver_actions_repo
        self._flashbacks_repo = flashbacks_repo
        self._buttons_repo = buttons_repo
        self._logger = logger or logging.getLogger(__name__)

    def _resolve_driver(self, user_map: dict[int, int], vehicle_index: int) -> Optional[int]:
        """Resolve a vehicle_index to user_id. user_map holds only human drivers,
        so a miss means an AI car — not an error — and the event is skipped."""
        return user_map.get(vehicle_index)

    def handle_event_packet(self, packet, user_map: dict[int, int]):
        """
        Process an Event packet.

        Args:
            packet: EventPacket from packets.unpack_event()
            user_map: car_index -> user_id mapping for the session
        """
        session_uid = str(packet.header.session_uid)

        try:
            event_code = str(packet.event_string_code).strip()[:10]
            frame_id = packet.header.overall_frame_identifier
            session_time = packet.header.session_time
            event = getattr(packet, "event", None)

            if event_code in _RACE_CONTROL_CODES:
                self._handle_race_control(session_uid, frame_id, event_code, session_time, event)
                if event_code == "SEND":
                    self._logger.info(f"Session {session_uid} ended (SEND event received)")
                return

            if event_code == "OVTK":
                self._handle_overtake(session_uid, frame_id, session_time, event, user_map)
            elif event_code == "COLL":
                self._handle_collision(session_uid, frame_id, session_time, event, user_map)
            elif event_code == "PENA":
                self._handle_penalty(session_uid, frame_id, session_time, event, user_map)
            elif event_code == "FTLP":
                self._handle_fastest_lap(session_uid, frame_id, session_time, event, user_map)
            elif event_code == "RTMT":
                self._handle_retirement(session_uid, frame_id, session_time, event, user_map)
            elif event_code == "SPTP":
                self._handle_speed_trap(session_uid, frame_id, session_time, event, user_map)
            elif event_code == "BUTN":
                self._handle_buttons(session_uid, frame_id, session_time, event)
            elif event_code in _DRIVER_ACTION_CODES:
                self._handle_driver_action(session_uid, frame_id, event_code, session_time, event, user_map)

        except Exception as e:
            self._logger.error(f"Failed to process event: {e}", exc_info=True)

    def _handle_race_control(self, session_uid, frame_id, event_code, session_time, event):
        """Handle session-level race control events."""
        kwargs = {}
        if event_code == "SCAR" and event is not None:
            kwargs["safety_car_type"] = safe_enum_name(SafetyCarStatus, event.safety_car_type, self._logger)
            kwargs["safety_car_event_type"] = safe_enum_name(SafetyCarEventType, event.event_type, self._logger)
        elif event_code == "STLG" and event is not None:
            kwargs["num_lights"] = event.num_of_lights
        elif event_code == "DRSD" and event is not None:
            kwargs["drs_disabled_reason"] = safe_enum_name(DrsDisabledReason, event.reason, self._logger)

        self._race_control_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            event_code=event_code,
            session_time=session_time,
            **kwargs,
        )

    def _handle_overtake(self, session_uid, frame_id, session_time, event, user_map):
        if event is None:
            return
        overtaking = self._resolve_driver(user_map, event.overtaking_vehicle_index)
        overtaken = self._resolve_driver(user_map, event.being_overtaken_vehicle_index)
        if overtaking is None or overtaken is None:
            return
        self._overtakes_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            overtaking_user_id=overtaking,
            overtaken_user_id=overtaken,
        )

    def _handle_collision(self, session_uid, frame_id, session_time, event, user_map):
        if event is None:
            return
        driver1 = self._resolve_driver(user_map, event.vehicle_1_index)
        driver2 = self._resolve_driver(user_map, event.vehicle_2_index)
        if driver1 is None or driver2 is None:
            return
        self._collisions_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            user1_id=driver1,
            user2_id=driver2,
            severity=event.severity,
        )

    def _handle_penalty(self, session_uid, frame_id, session_time, event, user_map):
        if event is None:
            return
        user_id = self._resolve_driver(user_map, event.vehicle_index)
        if user_id is None:
            return
        other_user_id = (
            self._resolve_driver(user_map, event.other_vehicle_index)
            if event.other_vehicle_index != _NOT_SET else None
        )
        self._penalties_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            user_id=user_id,
            other_user_id=other_user_id,
            penalty_type=safe_enum_name(PenaltyType, event.penalty_type, self._logger),
            infringement_type=safe_enum_name(InfringementType, event.infringement_type, self._logger),
            time_seconds=event.time if event.time != _NOT_SET else None,
            lap_num=event.lap_num if event.lap_num != _NOT_SET else None,
            places_gained=event.places_gained if event.places_gained != _NOT_SET else None,
        )

    def _handle_fastest_lap(self, session_uid, frame_id, session_time, event, user_map):
        if event is None:
            return
        user_id = self._resolve_driver(user_map, event.vehicle_index)
        if user_id is None:
            return
        self._fastest_laps_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            user_id=user_id,
            lap_time=event.lap_time,
        )

    def _handle_retirement(self, session_uid, frame_id, session_time, event, user_map):
        if event is None:
            return
        user_id = self._resolve_driver(user_map, event.vehicle_index)
        if user_id is None:
            return
        self._retirements_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            user_id=user_id,
            reason=safe_enum_name(ResultReason, event.reason, self._logger),
        )

    def _handle_speed_trap(self, session_uid, frame_id, session_time, event, user_map):
        if event is None:
            return
        user_id = self._resolve_driver(user_map, event.vehicle_index)
        if user_id is None:
            return
        fastest_user_id = user_map.get(event.fastest_vehicle_index_in_session)
        self._speed_traps_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            user_id=user_id,
            speed=event.speed,
            is_overall_fastest=bool(event.is_overall_fastest_in_session),
            is_driver_fastest=bool(event.is_driver_fastest_in_session),
            fastest_user_id=fastest_user_id,
            fastest_speed=event.fastest_speed_in_session,
        )

    def _handle_driver_action(self, session_uid, frame_id, event_code, session_time, event, user_map):
        if event is None:
            return
        user_id = self._resolve_driver(user_map, event.vehicle_index)
        if user_id is None:
            return
        stop_time = getattr(event, "stop_time", None)
        self._driver_actions_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            event_code=event_code,
            session_time=session_time,
            user_id=user_id,
            stop_time=stop_time,
        )

    def _handle_buttons(self, session_uid, frame_id, session_time, event):
        """Record the local player's controller state."""
        if event is None or self._buttons_repo is None:
            return
        pressed = [
            flag.name for flag in ButtonFlags
            if flag.name is not None and flag.value & event.button_status
        ]
        self._buttons_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            button_status=event.button_status,
            buttons_pressed=pressed,
        )

    def record_flashback(self, session_uid, frame_id, session_time, event, rows_discarded):
        """
        Record a flashback and how many frame rows it invalidated.

        Called by the dispatcher rather than from handle_event_packet, because
        discarding the rewound-over rows is a dispatcher-level concern that
        spans three repositories.
        """
        if event is None or self._flashbacks_repo is None:
            return
        self._flashbacks_repo.insert(
            session_uid=session_uid,
            overall_frame_identifier=frame_id,
            session_time=session_time,
            flashback_frame_identifier=event.flashback_frame_identifier,
            flashback_session_time=event.flashback_session_time,
            rows_discarded=rows_discarded,
        )
