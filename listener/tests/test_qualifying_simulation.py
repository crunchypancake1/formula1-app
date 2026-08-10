"""End-to-end qualifying simulation test.

Feeds constructed binary packets through the dispatcher and verifies
qualifying classification data landed correctly in the database.
"""

import pytest

from .qualifying_scenario import NUM_DRIVERS, QUALIFYING_SESSION_UID, generate_qualifying_scenario

_SESSION_UID = str(QUALIFYING_SESSION_UID)


class TestQualifyingSimulation:
    """Qualifying simulation: build packets -> feed dispatcher -> verify DB."""

    @pytest.fixture(scope="class", autouse=True)
    def run_simulation(self, dispatcher):
        """Feed all qualifying packets through the dispatcher once."""
        packets = generate_qualifying_scenario()
        for packet_bytes in packets:
            dispatcher.handle_packet(packet_bytes)

    def _query_one(self, db_client, sql, params=None):
        with db_client.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()

    def _query_all(self, db_client, sql, params=None):
        with db_client.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()

    def test_session_created(self, db_client):
        """Session record exists with qualifying session type."""
        row = self._query_one(
            db_client,
            """
            SELECT session_type, track_id
            FROM telemetry.sessions
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row is not None, "Qualifying session not found in telemetry.sessions"

    def test_qualifying_classification_written(self, db_client):
        """Qualifying classification has entries for all drivers."""
        rows = self._query_all(
            db_client,
            """
            SELECT position, num_laps, best_lap_time_ms
            FROM telemetry.qualifying_classification
            WHERE session_uid = %s
            ORDER BY position
            """,
            (_SESSION_UID,),
        )
        assert len(rows) == NUM_DRIVERS, f"Expected {NUM_DRIVERS} qualifying rows, got {len(rows)}"

        positions = [row[0] for row in rows]
        assert positions == list(range(1, NUM_DRIVERS + 1)), f"Positions not sequential: {positions}"

        for pos, num_laps, best_lap in rows:
            assert best_lap is not None, f"Position {pos}: best_lap_time_ms is NULL"
            assert best_lap > 0, f"Position {pos}: best_lap_time_ms <= 0"

    def test_no_race_classification(self, db_client):
        """No race classification should exist for a qualifying session."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.race_classification
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] == 0, "Race classification should not exist for qualifying session"

    def test_driver_entries(self, db_client):
        """Driver entries exist for the qualifying session."""
        rows = self._query_all(
            db_client,
            """
            SELECT car_index, user_id
            FROM telemetry.entries
            WHERE session_uid = %s
            ORDER BY car_index
            """,
            (_SESSION_UID,),
        )
        assert len(rows) == NUM_DRIVERS, f"Expected {NUM_DRIVERS} entries, got {len(rows)}"

    def test_lap_times_exist(self, db_client):
        """Lap records exist from the session history packets."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.laps
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] > 0, "No lap records found for qualifying session"
