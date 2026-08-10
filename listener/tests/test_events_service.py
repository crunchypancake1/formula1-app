import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.events import EventsService

from .mock_repo import MockRepo


def _make_event_packet(session_uid=123, event_code="SSTA", event=None):
    header = SimpleNamespace(
        session_uid=session_uid, session_time=10.0,
        overall_frame_identifier=1, player_car_index=0,
    )
    return SimpleNamespace(header=header, event_string_code=event_code, event=event)


def _make_service():
    race_control_repo = MockRepo()
    overtakes_repo = MockRepo()
    collisions_repo = MockRepo()
    penalties_repo = MockRepo()
    fastest_laps_repo = MockRepo()
    retirements_repo = MockRepo()
    speed_traps_repo = MockRepo()
    driver_actions_repo = MockRepo()
    svc = EventsService(
        race_control_repo=race_control_repo,
        overtakes_repo=overtakes_repo,
        collisions_repo=collisions_repo,
        penalties_repo=penalties_repo,
        fastest_laps_repo=fastest_laps_repo,
        retirements_repo=retirements_repo,
        speed_traps_repo=speed_traps_repo,
        driver_actions_repo=driver_actions_repo,
    )
    return (svc, race_control_repo, overtakes_repo, collisions_repo,
            penalties_repo, fastest_laps_repo, retirements_repo,
            speed_traps_repo, driver_actions_repo)


def test_ssta_writes_race_control():
    svc, race_control_repo, *_ = _make_service()
    packet = _make_event_packet(event_code="SSTA")
    svc.handle_event_packet(packet, user_map={})
    assert race_control_repo.call_count("insert") == 1
    _, kwargs = race_control_repo.last_call("insert")
    assert kwargs["event_code"] == "SSTA"


def test_send_writes_race_control():
    svc, race_control_repo, *_ = _make_service()
    packet = _make_event_packet(event_code="SEND")
    svc.handle_event_packet(packet, user_map={})
    assert race_control_repo.call_count("insert") == 1


def test_overtake_writes_both_drivers():
    svc, _, overtakes_repo, *_ = _make_service()
    event = SimpleNamespace(overtaking_vehicle_index=0, being_overtaken_vehicle_index=1)
    packet = _make_event_packet(event_code="OVTK", event=event)
    svc.handle_event_packet(packet, user_map={0: 100, 1: 101})
    assert overtakes_repo.call_count("insert") == 1
    _, kwargs = overtakes_repo.last_call("insert")
    assert kwargs["overtaking_user_id"] == 100
    assert kwargs["overtaken_user_id"] == 101


def test_overtake_skipped_if_driver_missing():
    svc, _, overtakes_repo, *_ = _make_service()
    event = SimpleNamespace(overtaking_vehicle_index=0, being_overtaken_vehicle_index=5)
    packet = _make_event_packet(event_code="OVTK", event=event)
    svc.handle_event_packet(packet, user_map={0: 100})
    assert overtakes_repo.call_count("insert") == 0


def test_collision_requires_both_drivers():
    svc, _, _, collisions_repo, *_ = _make_service()
    event = SimpleNamespace(vehicle_1_index=0, vehicle_2_index=5)
    packet = _make_event_packet(event_code="COLL", event=event)
    svc.handle_event_packet(packet, user_map={0: 100})
    assert collisions_repo.call_count("insert") == 0


def test_penalty_255_other_vehicle_is_none():
    svc, _, _, _, penalties_repo, *_ = _make_service()
    event = SimpleNamespace(
        vehicle_index=0, other_vehicle_index=255,
        penalty_type=0, infringement_type=0,
        time=5, lap_num=3, places_gained=0,
    )
    packet = _make_event_packet(event_code="PENA", event=event)
    svc.handle_event_packet(packet, user_map={0: 100})
    assert penalties_repo.call_count("insert") == 1
    _, kwargs = penalties_repo.last_call("insert")
    assert kwargs["other_user_id"] is None


def test_fastest_lap_writes():
    svc, _, _, _, _, fastest_laps_repo, *_ = _make_service()
    event = SimpleNamespace(vehicle_index=0, lap_time=85.123)
    packet = _make_event_packet(event_code="FTLP", event=event)
    svc.handle_event_packet(packet, user_map={0: 100})
    assert fastest_laps_repo.call_count("insert") == 1


def test_retirement_writes():
    svc, _, _, _, _, _, retirements_repo, *_ = _make_service()
    event = SimpleNamespace(vehicle_index=0, reason=0)
    packet = _make_event_packet(event_code="RTMT", event=event)
    svc.handle_event_packet(packet, user_map={0: 100})
    assert retirements_repo.call_count("insert") == 1


def test_speed_trap_writes():
    svc, _, _, _, _, _, _, speed_traps_repo, _ = _make_service()
    event = SimpleNamespace(
        vehicle_index=0, speed=320.5,
        is_overall_fastest_in_session=0,
        is_driver_fastest_in_session=1,
        fastest_vehicle_index_in_session=0,
        fastest_speed_in_session=321.0,
    )
    packet = _make_event_packet(event_code="SPTP", event=event)
    svc.handle_event_packet(packet, user_map={0: 100})
    assert speed_traps_repo.call_count("insert") == 1
    _, kwargs = speed_traps_repo.last_call("insert")
    assert kwargs["speed"] == 320.5


def test_rcwn_driver_action():
    svc, _, _, _, _, _, _, _, driver_actions_repo = _make_service()
    event = SimpleNamespace(vehicle_index=0)
    packet = _make_event_packet(event_code="RCWN", event=event)
    svc.handle_event_packet(packet, user_map={0: 100})
    assert driver_actions_repo.call_count("insert") == 1
