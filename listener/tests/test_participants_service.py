import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.participants import ParticipantsService

from .mock_repo import MockRepo


def _make_participant(ai_controlled=0, name="Driver_0", team_id=0, race_number=1,
                      nationality=1, platform=1, your_telemetry=1):
    return SimpleNamespace(
        ai_controlled=ai_controlled,
        name=name,
        team_id=team_id,
        race_number=race_number,
        nationality=nationality,
        platform=platform,
        your_telemetry=your_telemetry,
        livery_colours=[(200, 100, 50)] * 4,
        num_colours=4,
    )


def _make_participants_packet(session_uid=123, participants=None):
    if participants is None:
        participants = [_make_participant()]
    return SimpleNamespace(
        header=SimpleNamespace(session_uid=session_uid),
        participants=participants,
        num_active_cars=len(participants),
    )


def _make_service(insert_return=None):
    if insert_return is None:
        insert_return = {0: 100}
    entries_repo = MockRepo(
        max_player_number=0,
        insert_entries_batch=insert_return,
    )
    svc = ParticipantsService(entries_repo)
    return svc, entries_repo


def test_filters_ai_drivers():
    svc, entries_repo = _make_service(insert_return={0: 100})
    participants = [
        _make_participant(ai_controlled=0, name="Human"),
        _make_participant(ai_controlled=1, name="AI_Bot"),
    ]
    packet = _make_participants_packet(participants=participants)
    svc.handle_participants_packet(packet)
    args, _ = entries_repo.last_call("insert_entries_batch")
    entries = args[0]
    assert all(e["driver_name"] != "AI_Bot" for e in entries)
    assert len(entries) == 1


def test_returns_user_map():
    svc, _ = _make_service(insert_return={0: 100})
    packet = _make_participants_packet()
    result = svc.handle_participants_packet(packet)
    assert result == {0: 100}


def test_generic_name_replaced():
    svc, entries_repo = _make_service()
    packet = _make_participants_packet(participants=[_make_participant(name="Player")])
    svc.handle_participants_packet(packet)
    args, _ = entries_repo.last_call("insert_entries_batch")
    entries = args[0]
    assert entries[0]["driver_name"] == "Player 1"


def test_empty_name_replaced():
    svc, entries_repo = _make_service()
    packet = _make_participants_packet(participants=[_make_participant(name="")])
    svc.handle_participants_packet(packet)
    args, _ = entries_repo.last_call("insert_entries_batch")
    entries = args[0]
    assert entries[0]["driver_name"].startswith("Player ")


def test_incremental_update_skips_known():
    svc, entries_repo = _make_service(insert_return={0: 100})
    packet = _make_participants_packet()
    svc.handle_participants_packet(packet)
    svc.handle_participants_packet(packet)
    assert entries_repo.call_count("insert_entries_batch") == 1


def test_mid_session_join():
    entries_repo = MockRepo(
        max_player_number=0,
        insert_entries_batch={0: 100, 1: 101},
    )
    svc = ParticipantsService(entries_repo)

    # First: 2 humans
    packet1 = _make_participants_packet(participants=[
        _make_participant(name="Driver_A"),
        _make_participant(name="Driver_B"),
    ])
    svc.handle_participants_packet(packet1)

    # Second: 3 humans (one new)
    entries_repo._return_values["insert_entries_batch"] = {2: 102}
    packet2 = _make_participants_packet(participants=[
        _make_participant(name="Driver_A"),
        _make_participant(name="Driver_B"),
        _make_participant(name="Driver_C"),
    ])
    svc.handle_participants_packet(packet2)

    # Second call should only insert the new driver
    second_call_args, _ = entries_repo.all_calls("insert_entries_batch")[1]
    new_entries = second_call_args[0]
    assert len(new_entries) == 1
    assert new_entries[0]["driver_name"] == "Driver_C"
