import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packets.participants import ParticipantsPacket

from . import factories

from services.participants import ParticipantsService

from .mock_repo import MockRepo


def _make_participant(ai_controlled=0, name="Driver_0", team_id=476, race_number=1,
                      your_telemetry=1, nationality=1, num_colours=4):
    return factories.make_participant(
        ai_controlled=ai_controlled, name=name, team_id=team_id,
        race_number=race_number, your_telemetry=your_telemetry,
        nationality=nationality, num_colours=num_colours,
    )


def _make_participants_packet(session_uid=123, participants=None, player_car_index=0):
    if participants is None:
        participants = [_make_participant()]
    return ParticipantsPacket(
        header=factories.make_header(
            packet_id=4, session_uid=session_uid, player_car_index=player_car_index
        ),
        num_active_cars=len(participants),
        participants=participants,
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


def test_failed_entries_write_returns_no_user_map():
    """
    An entries write that fails must not be reported as a success.

    The returned map is what tells the dispatcher the roster exists; handing
    back drivers whose rows were rejected would run the whole session against a
    roster that is not in the database — telemetry, laps and classification all
    referencing drivers with no car index, team or race number.
    """
    svc, entries_repo = _make_service(insert_return={})
    packet = _make_participants_packet(
        participants=[_make_participant(name="Human")]
    )
    assert svc.handle_participants_packet(packet) == {}


def test_failed_entries_write_is_retried_on_the_next_packet():
    """
    A failed write must stay pending. Marking those drivers as written would
    make the failure permanent for the session — there is no other trigger that
    would ever insert them.
    """
    svc, entries_repo = _make_service(insert_return={})
    packet = _make_participants_packet(
        participants=[_make_participant(name="Human")]
    )
    svc.handle_participants_packet(packet)
    svc.handle_participants_packet(packet)
    assert entries_repo.call_count("insert_entries_batch") == 2


def test_restricted_drivers_exclude_the_local_player():
    """
    You always see your own car in full, whatever your own telemetry setting
    says — so the local player is never in the restricted set even when their
    own your_telemetry is 0.
    """
    svc, _ = _make_service(insert_return={0: 100, 1: 101})
    packet = _make_participants_packet(
        participants=[
            _make_participant(name="Me", your_telemetry=0),
            _make_participant(name="Rival", your_telemetry=0),
        ],
        player_car_index=0,
    )
    svc.handle_participants_packet(packet)
    assert svc.get_restricted_indices("123") == frozenset({1})


def test_telemetry_setting_tracked_per_driver():
    svc, entries_repo = _make_service(insert_return={0: 100, 1: 101})
    packet = _make_participants_packet(
        participants=[
            _make_participant(name="Public", your_telemetry=1),
            _make_participant(name="Restricted", your_telemetry=0),
        ],
        player_car_index=255,
    )
    svc.handle_participants_packet(packet)
    args, _ = entries_repo.last_call("insert_entries_batch")
    entries = {e["driver_name"]: e["telemetry_public"] for e in args[0]}
    assert entries == {"Public": True, "Restricted": False}
