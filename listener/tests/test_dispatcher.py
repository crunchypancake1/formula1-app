import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import logging

from dispatcher import PacketDispatcher
from services import (
    CarFrameService,
    EventsService,
    FinalClassificationService,
    LapHistoryService,
    LapPositionsService,
    ParticipantsService,
    SessionService,
)

from .mock_repo import MockRepo
from .packet_builder import (
    build_event_scar,
    build_event_ssta,
    build_final_classification_packet,
    build_lap_data_packet,
    build_motion_packet,
    build_participants_packet,
    build_session_packet,
)

SESSION_UID = 1234567890
_DRIVER_MAP = {i: 100 + i for i in range(20)}


def _make_dispatcher():
    """Build a PacketDispatcher wired to mock repositories."""
    logger = logging.getLogger("test_dispatcher")

    sessions_repo = MockRepo()
    session_timeline_repo = MockRepo()
    entries_repo = MockRepo(
        insert_entries_batch=_DRIVER_MAP,
        max_player_number=0,
    )
    car_frame_repo = MockRepo()
    car_frame_damage_repo = MockRepo()
    laps_repo = MockRepo()
    tyre_stints_repo = MockRepo()
    final_classification_repo = MockRepo()
    lap_positions_repo = MockRepo()
    race_control_repo = MockRepo()
    overtakes_repo = MockRepo()
    collisions_repo = MockRepo()
    penalties_repo = MockRepo()
    fastest_laps_repo = MockRepo()
    retirements_repo = MockRepo()
    speed_traps_repo = MockRepo()
    driver_actions_repo = MockRepo()

    session_service = SessionService(sessions_repo, session_timeline_repo, logger)
    participants_service = ParticipantsService(entries_repo, logger)
    car_frame_service = CarFrameService(
        car_frame_repo, car_frame_damage_repo=car_frame_damage_repo, logger=logger,
    )
    lap_history_service = LapHistoryService(laps_repo, tyre_stints_repo, logger)
    events_service = EventsService(
        race_control_repo=race_control_repo,
        overtakes_repo=overtakes_repo,
        collisions_repo=collisions_repo,
        penalties_repo=penalties_repo,
        fastest_laps_repo=fastest_laps_repo,
        retirements_repo=retirements_repo,
        speed_traps_repo=speed_traps_repo,
        driver_actions_repo=driver_actions_repo,
        logger=logger,
    )
    final_classification_service = FinalClassificationService(
        final_classification_repo, session_service, logger, dead_letter_dir=None,
    )
    lap_positions_service = LapPositionsService(lap_positions_repo, logger)

    dispatcher = PacketDispatcher(
        session_service=session_service,
        participants_service=participants_service,
        car_frame_service=car_frame_service,
        lap_history_service=lap_history_service,
        events_service=events_service,
        final_classification_service=final_classification_service,
        lap_positions_service=lap_positions_service,
        logger=logger,
    )

    return (
        dispatcher,
        sessions_repo,
        entries_repo,
        car_frame_repo,
        race_control_repo,
        final_classification_repo,
    )


def _send_session(dispatcher, session_type=15):
    """Send a session packet (race by default)."""
    data = build_session_packet(
        session_uid=SESSION_UID,
        session_time=1.0,
        frame_id=1,
        session_type=session_type,
    )
    dispatcher.handle_packet(data)


def _send_participants(dispatcher):
    """Send a participants packet."""
    data = build_participants_packet(
        session_uid=SESSION_UID,
        session_time=1.5,
        frame_id=2,
    )
    dispatcher.handle_packet(data)


class TestSessionPacketCreatesKnownSession:
    def test_session_packet_creates_known_session(self):
        dispatcher, *_ = _make_dispatcher()
        _send_session(dispatcher)
        assert str(SESSION_UID) in dispatcher._known_sessions


class TestUnknownSessionRejected:
    def test_unknown_session_rejected(self):
        dispatcher, _, entries_repo, *_ = _make_dispatcher()
        # Send lap_data without a prior session packet
        data = build_lap_data_packet(
            session_uid=SESSION_UID,
            session_time=1.0,
            frame_id=1,
        )
        dispatcher.handle_packet(data)
        # Participants should never have been called
        assert entries_repo.call_count("insert_entries_batch") == 0


class TestExcludedSessionTypeFiltered:
    def test_excluded_session_type_filtered(self):
        dispatcher, *_ = _make_dispatcher()
        # session_type=0 is "unknown" — excluded
        _send_session(dispatcher, session_type=0)
        assert str(SESSION_UID) in dispatcher._excluded_sessions
        assert str(SESSION_UID) not in dispatcher._known_sessions
        # Subsequent packets for this session should be dropped
        data = build_participants_packet(
            session_uid=SESSION_UID,
            session_time=2.0,
            frame_id=2,
        )
        dispatcher.handle_packet(data)
        # Should not reach participants service
        assert str(SESSION_UID) not in dispatcher._user_maps


class TestParticipantsBuildsUserMap:
    def test_participants_builds_user_map(self):
        dispatcher, _, entries_repo, _, race_control_repo, _ = _make_dispatcher()
        _send_session(dispatcher)
        _send_participants(dispatcher)
        session_key = str(SESSION_UID)
        assert session_key in dispatcher._user_maps
        # Send an SSTA event to verify user_map exists and events process
        data = build_event_ssta(
            session_uid=SESSION_UID,
            session_time=2.0,
            frame_id=3,
        )
        dispatcher.handle_packet(data)
        assert race_control_repo.call_count("insert") >= 1


class TestPacketsWithoutUserMapDropped:
    def test_packets_without_user_map_dropped(self):
        dispatcher, _, _, car_frame_repo, *_ = _make_dispatcher()
        _send_session(dispatcher)
        # Send lap_data without participants — should be dropped (no user_map)
        data = build_lap_data_packet(
            session_uid=SESSION_UID,
            session_time=2.0,
            frame_id=2,
        )
        dispatcher.handle_packet(data)
        # Car frame write should not happen
        assert car_frame_repo.call_count("insert_batch") == 0


class TestScarFormationLapSetsRaceStarted:
    def test_scar_formation_lap_sets_race_started(self):
        dispatcher, *_ = _make_dispatcher()
        _send_session(dispatcher, session_type=15)
        _send_participants(dispatcher)
        session_key = str(SESSION_UID)
        # Race sessions start with race_started=False
        assert dispatcher._race_started.get(session_key) is False
        # SCAR with safety_car_type=3, event_type=3 signals formation lap end
        data = build_event_scar(
            session_uid=SESSION_UID,
            session_time=3.0,
            frame_id=4,
            safety_car_type=3,
            event_type=3,
        )
        dispatcher.handle_packet(data)
        assert dispatcher._race_started[session_key] is True


class TestSessionLevelEventsBypassUserMap:
    def test_session_level_events_bypass_user_map(self):
        dispatcher, _, _, _, race_control_repo, _ = _make_dispatcher()
        _send_session(dispatcher)
        # No participants sent — no user_map
        data = build_event_ssta(
            session_uid=SESSION_UID,
            session_time=2.0,
            frame_id=3,
        )
        dispatcher.handle_packet(data)
        # SSTA is session-level and should be processed without user_map
        assert race_control_repo.call_count("insert") >= 1


class TestClassificationMarksSession:
    def test_classification_marks_session(self):
        dispatcher, *_ = _make_dispatcher()
        _send_session(dispatcher)
        _send_participants(dispatcher)
        data = build_final_classification_packet(
            session_uid=SESSION_UID,
            session_time=300.0,
            frame_id=100,
        )
        dispatcher.handle_packet(data)
        assert str(SESSION_UID) in dispatcher._classification_received


class TestInvalidHeaderRejected:
    def test_invalid_header_rejected(self):
        dispatcher, _, entries_repo, *_ = _make_dispatcher()
        # Build a header with packet_format=2024 (invalid — expects 2025)
        import struct
        bad_header = struct.pack(
            '<HBBBBBQfIIBB',
            2024, 24, 1, 0, 1, 1,
            SESSION_UID, 1.0, 1, 1, 0, 255,
        )
        body = b'\x00' * 200
        dispatcher.handle_packet(bad_header + body)
        assert str(SESSION_UID) not in dispatcher._known_sessions


class TestPacketTooShort:
    def test_packet_too_short(self):
        dispatcher, *_ = _make_dispatcher()
        dispatcher.handle_packet(b'\x00' * 10)
        # Should not crash, no sessions created
        assert len(dispatcher._known_sessions._data) == 0


class TestCarFramePacketsBuffered:
    def test_car_frame_packets_buffered(self):
        dispatcher, _, _, car_frame_repo, *_ = _make_dispatcher()
        _send_session(dispatcher)
        _send_participants(dispatcher)
        # Send a motion packet (id=0) — should go through frame buffer, not direct write
        data = build_motion_packet(
            session_uid=SESSION_UID,
            session_time=5.0,
            frame_id=10,
        )
        dispatcher.handle_packet(data)
        # write_frame on the service should NOT have been called directly
        # (it only gets called when the buffer flushes, which requires a new frame)
        assert car_frame_repo.call_count("insert_batch") == 0
