import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from services.final_classification import FinalClassificationService

from .mock_repo import MockRepo


class MockSessionService:
    def __init__(self, session_type=15):
        self._session_type = session_type

    def get_session_type(self, session_uid):
        return self._session_type


def _make_classification(position=1, num_of_laps=3, grid_position=1, points=25,
                         num_pit_stops=1, result_status=3, result_reason=2,
                         best_lap_time_in_ms=88000, total_race_time=270.5,
                         penalties_time=0, num_of_penalties=0, num_of_tyre_stints=2):
    return SimpleNamespace(
        position=position,
        num_of_laps=num_of_laps,
        grid_position=grid_position,
        points=points,
        num_pit_stops=num_pit_stops,
        result_status=result_status,
        result_reason=result_reason,
        best_lap_time_in_ms=best_lap_time_in_ms,
        total_race_time=total_race_time,
        penalties_time=penalties_time,
        num_of_penalties=num_of_penalties,
        num_of_tyre_stints=num_of_tyre_stints,
        tyre_stints_actual=[20, 18, 0, 0, 0, 0, 0, 0],
        tyre_stints_visual=[16, 17, 0, 0, 0, 0, 0, 0],
        tyre_stints_end_laps=[15, 255, 0, 0, 0, 0, 0, 0],
    )


def _make_classification_packet(session_uid=123, classifications=None):
    if classifications is None:
        classifications = [_make_classification()]
    return SimpleNamespace(
        header=SimpleNamespace(session_uid=session_uid),
        num_cars=len(classifications),
        final_classifications=classifications,
    )


def test_race_classification_written():
    repo = MockRepo()
    session_svc = MockSessionService(session_type=15)
    svc = FinalClassificationService(repo, session_svc)
    packet = _make_classification_packet()
    svc.handle_final_classification_packet(packet, user_map={0: 100})
    assert repo.call_count("insert_race_classification_batch") == 1


def test_qualifying_classification_written():
    repo = MockRepo()
    session_svc = MockSessionService(session_type=10)
    svc = FinalClassificationService(repo, session_svc)
    packet = _make_classification_packet()
    svc.handle_final_classification_packet(packet, user_map={0: 100})
    assert repo.call_count("insert_qualifying_classification_batch") == 1


def test_duplicate_ignored():
    repo = MockRepo()
    session_svc = MockSessionService(session_type=15)
    svc = FinalClassificationService(repo, session_svc)
    packet = _make_classification_packet()
    svc.handle_final_classification_packet(packet, user_map={0: 100})
    svc.handle_final_classification_packet(packet, user_map={0: 100})
    assert repo.call_count("insert_race_classification_batch") == 1


def test_result_status_zero_filtered():
    repo = MockRepo()
    session_svc = MockSessionService(session_type=15)
    svc = FinalClassificationService(repo, session_svc)
    classifications = [
        _make_classification(result_status=0),
        _make_classification(position=2, result_status=3),
    ]
    packet = _make_classification_packet(classifications=classifications)
    svc.handle_final_classification_packet(packet, user_map={0: 100, 1: 101})
    args, _ = repo.last_call("insert_race_classification_batch")
    batch = args[0]
    assert len(batch) == 1
    assert batch[0]["user_id"] == 101


def test_race_includes_tyre_stints():
    repo = MockRepo()
    session_svc = MockSessionService(session_type=15)
    svc = FinalClassificationService(repo, session_svc)
    packet = _make_classification_packet()
    svc.handle_final_classification_packet(packet, user_map={0: 100})
    args, _ = repo.last_call("insert_race_classification_batch")
    classification = args[0][0]
    assert "tyre_stints_actual" in classification
    assert "tyre_stints_visual" in classification


def test_dead_letter_on_failure(tmp_path):
    repo = MockRepo()
    # Make the repo raise on insert
    original_getattr = MockRepo.__getattr__

    class FailingRepo(MockRepo):
        def __getattr__(self, name):
            if name == "insert_race_classification_batch":
                def fail(*args, **kwargs):
                    raise Exception("DB down")
                return fail
            return original_getattr(self, name)

    failing_repo = FailingRepo()
    session_svc = MockSessionService(session_type=15)
    dead_letter_dir = str(tmp_path / "dead-letters")
    svc = FinalClassificationService(failing_repo, session_svc, dead_letter_dir=dead_letter_dir)
    packet = _make_classification_packet()
    svc.handle_final_classification_packet(packet, user_map={0: 100})

    # Verify dead letter file was written
    dead_letter_files = list(tmp_path.joinpath("dead-letters").glob("*.json"))
    assert len(dead_letter_files) == 1
