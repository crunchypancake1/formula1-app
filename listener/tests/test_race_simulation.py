"""End-to-end race simulation test.

Feeds constructed binary packets through the dispatcher and verifies
data landed correctly in the database.
"""

import pytest

from .scenario import (
    NUM_DRIVERS,
    RESTRICTED_CAR_INDICES,
    SESSION_UID,
    TOTAL_LAPS,
    generate_race_scenario,
)

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

    def test_car_frame_enums_stored_as_codes(self, db_client):
        """
        car_frame's enum columns hold the game's raw integer, not a resolved name.

        Resolution moved to the query layer (@f1/db) because eleven text columns
        cost ~66 bytes a row here. The codes below are what the scenario feeds in
        (see tests/factories.py), so this pins the contract the TypeScript
        `*_CODES` tables are written against — a listener change that started
        writing names again would still satisfy the column type, but not this.
        """
        row = self._query_one(
            db_client,
            """
            SELECT array_agg(DISTINCT sector),
                   array_agg(DISTINCT pit_status),
                   array_agg(DISTINCT driver_status),
                   array_agg(DISTINCT result_status),
                   array_agg(DISTINCT actual_tyre_compound),
                   array_agg(DISTINCT visual_tyre_compound),
                   array_agg(DISTINCT surface_type_rl)
            FROM telemetry.car_frame
            WHERE session_uid = %s AND driver_status IS NOT NULL
            """,
            (_SESSION_UID,),
        )
        sector, pit, driver, result, actual, visual, surface = row
        assert driver, "No car_frame rows with enum columns populated"

        # Every value is an integer inside its enum's declared range. A resolved
        # name could not survive the SMALLINT column, and the game's 255 "not
        # set" sentinel would fall outside every range below.
        valid = {
            "Sector": (sector, range(0, 3)),
            "PitStatus": (pit, range(0, 3)),
            "DriverStatus": (driver, range(0, 5)),
            "ResultStatus": (result, range(0, 8)),
            "ActualTyreCompound": (actual, range(0, 23)),
            "VisualTyreCompound": (visual, range(0, 23)),
            "SurfaceType": (surface, range(0, 12)),
        }
        for name, (values, allowed) in valid.items():
            assert all(isinstance(v, int) for v in values), f"{name}: not integers — {values}"
            assert all(v in allowed for v in values), f"{name}: out of range — {values}"

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

    # --- Restricted telemetry -------------------------------------------------

    def _restricted_user_ids(self, db_client):
        rows = self._query_all(
            db_client,
            """
            SELECT user_id FROM telemetry.entries
            WHERE session_uid = %s AND car_index = ANY(%s)
            """,
            (_SESSION_UID, sorted(RESTRICTED_CAR_INDICES)),
        )
        return [r[0] for r in rows]

    def test_restricted_drivers_recorded_as_restricted(self, db_client):
        """The roster records who had Your Telemetry set to Restricted."""
        restricted = self._restricted_user_ids(db_client)
        assert len(restricted) == len(RESTRICTED_CAR_INDICES)

        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM telemetry.entries
            WHERE session_uid = %s AND telemetry_public = false
            """,
            (_SESSION_UID,),
        )
        assert row[0] == len(RESTRICTED_CAR_INDICES)

    def test_restricted_car_status_is_null_not_zero(self, db_client):
        """
        A Restricted driver's fuel and ERS arrive zeroed from the game. Those
        must be stored as NULL — a 0.0 fuel load is indistinguishable from a
        real reading and would be believed.
        """
        restricted = self._restricted_user_ids(db_client)
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.car_frame
            WHERE session_uid = %s AND user_id = ANY(%s)
              AND (fuel_in_tank IS NOT NULL OR fuel_capacity IS NOT NULL
                   OR ers_store_energy IS NOT NULL OR front_brake_bias IS NOT NULL
                   OR ers_harvested_this_lap_mguk IS NOT NULL
                   OR engine_power_ice IS NOT NULL)
            """,
            (_SESSION_UID, restricted),
        )
        assert row[0] == 0, "Restricted driver has non-NULL withheld car status data"

    def test_public_car_status_is_populated(self, db_client):
        """Public drivers keep every Car Status field, including the new ones."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*)
            FROM telemetry.car_frame
            WHERE session_uid = %s AND user_id <> ALL(%s)
              AND fuel_in_tank IS NOT NULL AND fuel_capacity IS NOT NULL
              AND ers_harvested_this_lap_mguk IS NOT NULL
              AND ers_harvested_this_lap_mguh IS NOT NULL
              AND engine_power_ice IS NOT NULL AND engine_power_mguk IS NOT NULL
              AND max_rpm IS NOT NULL
            """,
            (_SESSION_UID, self._restricted_user_ids(db_client)),
        )
        assert row[0] > 0, "No public driver has fully populated car status"

    def test_restricted_drivers_have_no_damage_rows(self, db_client):
        """
        The whole Car Damage packet is withheld for a Restricted driver, so the
        row is omitted entirely rather than written as ~30 zeroes.
        """
        restricted = self._restricted_user_ids(db_client)
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM telemetry.car_frame_damage
            WHERE session_uid = %s AND user_id = ANY(%s)
            """,
            (_SESSION_UID, restricted),
        )
        assert row[0] == 0, "Restricted driver has car_frame_damage rows"

        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM telemetry.car_frame_damage
            WHERE session_uid = %s AND user_id <> ALL(%s)
            """,
            (_SESSION_UID, restricted),
        )
        assert row[0] > 0, "No damage rows for the public drivers either"

    # --- Packet 16 ------------------------------------------------------------

    def test_car_telemetry2_stored(self, db_client):
        """Packet 16 lands, aero and boost included."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(is_2026_regulations), COUNT(active_aero_mode),
                   COUNT(overtake_activation_distance)
            FROM telemetry.car_frame
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        regs, aero, overtake = row
        assert regs > 0, "is_2026_regulations never stored"
        assert aero > 0 and overtake > 0, "Packet 16 aero/boost fields never stored"

    def test_regulations_flag_null_only_without_packet_16(self, db_client):
        """
        NULL in is_2026_regulations must mean "packet 16 never arrived for this
        frame" and nothing else — a car we did hear from always gets a real
        true/false, so a classic car reads False rather than unknown.
        """
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM telemetry.car_frame
            WHERE session_uid = %s
              AND is_2026_regulations IS NULL
              AND (active_aero_mode IS NOT NULL OR driving_wrong_way IS NOT NULL)
            """,
            (_SESSION_UID,),
        )
        assert row[0] == 0, "Rows carry packet-16 data but no regulations flag"

    # --- Lap Data coverage ----------------------------------------------------

    def test_lap_data_extras_stored(self, db_client):
        """Warnings, penalties and lap validity live only in Lap Data."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(current_lap_invalid), COUNT(total_warnings),
                   COUNT(corner_cutting_warnings), COUNT(grid_position),
                   COUNT(last_lap_time_ms)
            FROM telemetry.car_frame
            WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        invalid, warnings, corner_cuts, grid, last_lap = row
        assert invalid > 0 and warnings > 0 and corner_cuts > 0
        assert grid > 0, "grid_position never stored"

    # --- Frame identity -------------------------------------------------------

    def test_frames_are_deduplicated(self, db_client):
        """
        The frame key is (timestamp, session_uid, user_id, frame) with a derived
        timestamp, so one frame can only ever produce one row per driver.
        """
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM (
                SELECT session_uid, user_id, overall_frame_identifier
                FROM telemetry.car_frame
                WHERE session_uid = %s
                GROUP BY 1, 2, 3
                HAVING COUNT(*) > 1
            ) duplicates
            """,
            (_SESSION_UID,),
        )
        assert row[0] == 0, "Duplicate (session, driver, frame) rows in car_frame"

    def test_session_start_anchor_recorded(self, db_client):
        """Frame timestamps are derived from this anchor, so it must exist."""
        row = self._query_one(
            db_client,
            "SELECT session_start_utc FROM telemetry.sessions WHERE session_uid = %s",
            (_SESSION_UID,),
        )
        assert row is not None and row[0] is not None

    # --- Session packet coverage ----------------------------------------------

    def test_session_settings_stored(self, db_client):
        """The session's rules and assists are recorded, not just its identity."""
        row = self._query_one(
            db_client,
            """
            SELECT equal_car_performance, parc_ferme_rules, corner_cutting_stringency,
                   safety_car, formation_lap, ai_difficulty, weekend_structure
            FROM telemetry.sessions WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row is not None
        assert all(v is not None for v in row), f"Unset session settings: {row}"
        assert len(row[6]) > 0, "weekend_structure not stored"

    def test_timeline_records_live_state(self, db_client):
        """Race-control state that changes during the session lands on the timeline."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*), COUNT(marshal_zone_flags), COUNT(num_safety_car_periods)
            FROM telemetry.session_timeline WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        total, flags, sc_periods = row
        assert total > 0
        assert flags == total and sc_periods == total

    def test_session_bests_recorded(self, db_client):
        """Session History reports which lap each best was set on."""
        row = self._query_one(
            db_client,
            "SELECT COUNT(*) FROM telemetry.session_bests WHERE session_uid = %s",
            (_SESSION_UID,),
        )
        assert row[0] > 0, "No session_bests rows"

    def test_weather_forecast_keeps_target_session(self, db_client):
        """A forecast sample says which session it predicts for."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*), COUNT(forecast_session_type)
            FROM telemetry.weather_forecast WHERE session_uid = %s
            """,
            (_SESSION_UID,),
        )
        assert row[0] > 0 and row[1] == row[0]

    # --- Participants coverage ------------------------------------------------

    def test_entry_identity_fields_stored(self, db_client):
        """Platform and network identity come only from the Participants packet."""
        row = self._query_one(
            db_client,
            """
            SELECT COUNT(*) FROM telemetry.entries
            WHERE session_uid = %s
              AND platform IS NOT NULL AND driver_id IS NOT NULL
              AND network_id IS NOT NULL AND show_online_names IS NOT NULL
              AND num_livery_colors IS NOT NULL
            """,
            (_SESSION_UID,),
        )
        assert row[0] == NUM_DRIVERS
