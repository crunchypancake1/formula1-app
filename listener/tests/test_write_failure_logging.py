"""A persistently failing write must not flood the log with one traceback per packet."""

import logging

import pytest

from database.repositories.base import RepositoryBase


class _Recorder(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class _FkViolation(Exception):
    sqlstate = "23503"


class _UniqueViolation(Exception):
    sqlstate = "23505"


@pytest.fixture
def repo():
    log = logging.getLogger("write_failure_test")
    log.setLevel(logging.ERROR)
    log.handlers.clear()
    recorder = _Recorder()
    log.addHandler(recorder)

    instance = RepositoryBase.__new__(RepositoryBase)
    RepositoryBase.__init__(instance, postgres_client=None, logger=log)  # type: ignore[arg-type]
    return instance, recorder


class TestWriteFailureLogging:
    def test_the_first_failure_logs_with_a_traceback(self, repo):
        instance, recorder = repo

        instance._log_write_failure("telemetry.session_timeline", _FkViolation("boom"))

        assert len(recorder.records) == 1
        assert recorder.records[0].exc_info is not None
        assert "telemetry.session_timeline" in recorder.records[0].getMessage()

    def test_repeats_of_the_same_failure_are_collapsed(self, repo):
        instance, recorder = repo

        for _ in range(500):
            instance._log_write_failure("telemetry.session_timeline", _FkViolation("boom"))

        # 62 tracebacks in 76 seconds was the observed incident; one is enough.
        assert len(recorder.records) == 1

    def test_a_different_failure_on_the_same_table_still_logs(self, repo):
        instance, recorder = repo

        instance._log_write_failure("telemetry.sessions", _FkViolation("boom"))
        instance._log_write_failure("telemetry.sessions", _UniqueViolation("dupe"))

        assert len(recorder.records) == 2

    def test_each_table_reports_its_own_first_failure(self, repo):
        instance, recorder = repo

        for table in ("telemetry.session_timeline", "telemetry.events_buttons"):
            for _ in range(50):
                instance._log_write_failure(table, _FkViolation("boom"))

        assert len(recorder.records) == 2
        assert {r.getMessage().split(" - ")[1].split(":")[0] for r in recorder.records} == {
            "telemetry.session_timeline",
            "telemetry.events_buttons",
        }

    def test_suppressed_failures_are_summarised_once_the_interval_passes(
        self, repo, monkeypatch
    ):
        instance, recorder = repo
        clock = [1000.0]
        monkeypatch.setattr(
            "database.repositories.base.time.monotonic", lambda: clock[0]
        )

        instance._log_write_failure("telemetry.car_frame", _FkViolation("boom"))
        for _ in range(9):
            instance._log_write_failure("telemetry.car_frame", _FkViolation("boom"))

        assert len(recorder.records) == 1

        clock[0] += 61.0
        instance._log_write_failure("telemetry.car_frame", _FkViolation("boom"))

        assert len(recorder.records) == 2
        summary = recorder.records[1].getMessage()
        assert "10 more in the last 61s" in summary
        # The summary is a one-liner; the traceback was already reported.
        assert recorder.records[1].exc_info is None

    def test_batch_and_single_failures_are_labelled_differently(self, repo):
        instance, recorder = repo

        instance._log_write_failure("telemetry.car_frame", _FkViolation("boom"), batch=True)

        assert "batch write failed" in recorder.records[0].getMessage()
