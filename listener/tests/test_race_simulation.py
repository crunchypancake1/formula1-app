"""End-to-end race simulation test.

Feeds constructed binary packets through the dispatcher and verifies
data landed correctly in the database.
"""

import pytest

from .scenario import NUM_DRIVERS, SESSION_UID, TOTAL_LAPS, generate_race_scenario

_SESSION_UID = str(SESSION_UID)


class TestRaceSimulation:
    """Full race simulation: build packets → feed dispatcher → verify DB."""

    @pytest.fixture(scope="class", autouse=True)
    def run_simulation(self, dispatcher):
        """Feed all packets through the dispatcher once for the entire test class."""
        packets = generate_race_scenario()
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
        """Session record exists with correct metadata."""
        row = self._query_one(
            db_client,
            """
            SELECT session_type, track_id, total_laps
            FROM telemetry.sessions
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row is not None, "Session not found in telemetry.sessions"
        session_type, track_id, total_laps = row
        assert track_id == 11, f"Expected track_id=11, got {track_id}"
        assert total_laps == TOTAL_LAPS, f"Expected total_laps={TOTAL_LAPS}, got {total_laps}"

    def test_driver_entries(self, db_client):
        """Human driver entries exist with resolved user_ids (AI drivers excluded)."""
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
        for car_index, user_id in rows:
            assert user_id is not None, f"user_id is NULL for car_index={car_index}"

    def test_car_frame_data(self, db_client):
        """Car frame data was written with non-null speed values."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.car_frame
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        count = row[0]
        assert count > 0, "No car_frame rows found"

        # Spot-check: at least some frames have speed > 0
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.car_frame
            WHERE session_uid = %s AND speed > 0
            """,
            (_SESSION_UID,),
        )
        assert row[0] > 0, "No car_frame rows with speed > 0"

    def test_session_timeline(self, db_client):
        """Session timeline has multiple entries."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.session_timeline
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] > 0, "No session_timeline rows found"

    def test_weather_forecast(self, db_client):
        """Weather forecast was written."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.weather_forecast
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] >= 1, "No weather_forecast rows found"

    def test_overtake_events(self, db_client):
        """At least one overtake event was recorded."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.events_overtakes
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] >= 1, "No overtake events found"

    def test_speed_trap_events(self, db_client):
        """At least one speed trap event was recorded."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.events_speed_traps
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] >= 1, "No speed trap events found"

    def test_fastest_lap_events(self, db_client):
        """At least one fastest lap event was recorded."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.events_fastest_laps
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] >= 1, "No fastest lap events found"

    def test_penalty_events(self, db_client):
        """At least one penalty event was recorded."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.events_penalties
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] >= 1, "No penalty events found"

    def test_collision_events(self, db_client):
        """At least one collision event was recorded."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.events_collisions
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] >= 1, "No collision events found"

    def test_race_control_events(self, db_client):
        """SSTA and SEND race control events are present."""
        rows = self._query_all(
            db_client,
            """
            SELECT event_code
            FROM telemetry.events_race_control
            WHERE session_uid = %s
            ORDER BY event_code
            """,
            (_SESSION_UID,),
        )
        event_codes = {row[0] for row in rows}
        assert "SSTA" in event_codes, "SSTA event not found"
        assert "SEND" in event_codes, "SEND event not found"
        assert "CHQF" in event_codes, "CHQF event not found"

    def test_race_classification(self, db_client):
        """Race classification has entries for all drivers with valid positions."""
        rows = self._query_all(
            db_client,
            """
            SELECT position, num_laps, tyre_stints_actual
            FROM telemetry.race_classification
            WHERE session_uid = %s
            ORDER BY position
            """,
            (_SESSION_UID,),
        )
        assert len(rows) == NUM_DRIVERS, f"Expected {NUM_DRIVERS} classification rows, got {len(rows)}"

        positions = [row[0] for row in rows]
        assert positions == list(range(1, NUM_DRIVERS + 1)), f"Positions not sequential: {positions}"

        for pos, num_laps, tyre_stints in rows:
            assert num_laps == TOTAL_LAPS, f"Position {pos}: expected {TOTAL_LAPS} laps, got {num_laps}"
            assert tyre_stints is not None, f"Position {pos}: tyre_stints_actual is NULL"

    def test_lap_times(self, db_client):
        """Lap records exist with positive times."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.laps
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        count = row[0]
        # We should have at least some laps (3 laps × 20 drivers = 60, but incremental
        # upserts may produce fewer depending on timing)
        assert count >= 20, f"Expected at least 20 lap rows, got {count}"

        # Check positive times
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.laps
            WHERE session_uid = %s AND lap_time_ms > 0
            """,
            (_SESSION_UID,),
        )
        assert row[0] > 0, "No laps with positive lap_time_ms"

    def test_lap_positions(self, db_client):
        """Lap positions were recorded."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.lap_positions
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        count = row[0]
        assert count >= 1, f"Expected at least 1 lap_positions row, got {count}"

    def test_car_frame_damage_written(self, db_client):
        """Car damage data was written with non-zero wear values for multiple drivers."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.car_frame_damage
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        count = row[0]
        assert count > 0, "No car_frame_damage rows found"

        # Verify multiple drivers have damage data
        rows = self._query_all(
            db_client,
            """
            SELECT DISTINCT user_id
            FROM telemetry.car_frame_damage
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert len(rows) >= 2, f"Expected damage data for multiple drivers, got {len(rows)}"

        # Verify wear values are positive for at least some rows
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.car_frame_damage
            WHERE session_uid = %s AND tyres_wear_rl > 0
            """,
            (_SESSION_UID,),
        )
        assert row[0] > 0, "No car_frame_damage rows with tyres_wear_rl > 0"

    def test_driver_actions(self, db_client):
        """Race winner driver action event was recorded."""
        rows = self._query_all(
            db_client,
            """
            SELECT event_code
            FROM telemetry.events_driver_actions
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        event_codes = {row[0] for row in rows}
        assert "RCWN" in event_codes, "RCWN (race winner) event not found"
