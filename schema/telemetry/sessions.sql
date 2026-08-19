-- Sessions table (source: Session packet, Packet 1).
--
-- Holds the session's *static* configuration: everything the game fixes when
-- the session is created. Live state that changes while the session runs
-- (weather, safety car, period counters, pit window) lives in
-- telemetry.session_timeline.
--
-- session_start_utc is the wall-clock anchor for the whole session. It is
-- written once, on the first Session packet, as NOW() - m_sessionTime, and is
-- never updated. Every frame table derives its timestamp from it
-- (session_start_utc + session_time), which is what makes those rows
-- deterministic and de-duplicable across listener restarts.
CREATE TABLE IF NOT EXISTS telemetry.sessions (
    session_uid VARCHAR(20) PRIMARY KEY,
    weekend_link VARCHAR(255) NOT NULL,
    session_link VARCHAR(255) NOT NULL,
    season_link VARCHAR(255),
    session_start_utc TIMESTAMPTZ NOT NULL,
    track_id SMALLINT NOT NULL REFERENCES telemetry.tracks(track_id),
    session_type VARCHAR(50) NOT NULL,
    formula VARCHAR(50) NOT NULL,
    game_mode VARCHAR(50) NOT NULL,
    ruleset VARCHAR(50) NOT NULL,
    total_laps SMALLINT NOT NULL,
    session_duration INTEGER NOT NULL,
    num_sessions_in_weekend SMALLINT NOT NULL,
    weekend_structure VARCHAR(50)[],
    time_of_day INTEGER,
    session_length SMALLINT,

    -- Local player's start reaction time; NULL until a non-zero value is seen
    -- (it stays 0.0 for as long as starts are assisted).
    start_reaction_time REAL,

    -- Lobby / difficulty
    network_game BOOLEAN,
    ai_difficulty SMALLINT,
    forecast_accuracy SMALLINT,
    equal_car_performance BOOLEAN,
    sli_pro_native_support BOOLEAN,

    -- Driver assists
    assist_steering SMALLINT,
    assist_braking SMALLINT,
    assist_gearbox SMALLINT,
    assist_pit SMALLINT,
    assist_pit_release SMALLINT,
    assist_ers SMALLINT,
    assist_drs SMALLINT,
    assist_anti_lock_brakes SMALLINT,
    assist_traction_control SMALLINT,
    dynamic_racing_line SMALLINT,
    dynamic_racing_line_type SMALLINT,
    dynamic_racing_line_hi_vis SMALLINT,
    dynamic_racing_line_colour_blind SMALLINT,

    -- Simulation / rules settings
    recovery_mode SMALLINT,
    flashback_limit SMALLINT,
    recurring_rewind_prompt SMALLINT,
    surface_type SMALLINT,
    low_fuel_mode SMALLINT,
    race_starts SMALLINT,
    tyre_temperature SMALLINT,
    pit_lane_tyre_sim SMALLINT,
    car_damage SMALLINT,
    car_damage_rate SMALLINT,
    collisions SMALLINT,
    collisions_off_for_first_lap_only SMALLINT,
    mp_unsafe_pit_release SMALLINT,
    mp_off_for_griefing SMALLINT,
    corner_cutting_stringency SMALLINT,
    parc_ferme_rules SMALLINT,
    pit_stop_experience SMALLINT,
    safety_car SMALLINT,
    safety_car_experience SMALLINT,
    formation_lap SMALLINT,
    formation_lap_experience SMALLINT,
    red_flags SMALLINT,
    affects_licence_level_solo SMALLINT,
    affects_licence_level_mp SMALLINT,

    -- Lead/secondary player display units (0 = MPH/Celsius, 1 = KPH/Fahrenheit)
    speed_units_lead_player SMALLINT,
    temperature_units_lead_player SMALLINT,
    speed_units_secondary_player SMALLINT,
    temperature_units_secondary_player SMALLINT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_sessions_session_uid_not_empty CHECK (length(session_uid) > 0),
    CONSTRAINT uk_sessions_weekend_session UNIQUE (weekend_link, session_link)
);

CREATE INDEX IF NOT EXISTS idx_sessions_track ON telemetry.sessions(track_id, session_type);

-- Critical for standings JOIN (races.weekend_link -> sessions.weekend_link)
CREATE INDEX IF NOT EXISTS idx_sessions_weekend_link ON telemetry.sessions(weekend_link);

-- "Most recently run session" — ORDER BY session_start_utc DESC LIMIT n. Both
-- Workers open on this query and the dashboard re-runs it on every poll, so it
-- is the single hottest read in the app; without this index it is a seq scan
-- plus a sort over every session ever recorded.
CREATE INDEX IF NOT EXISTS idx_sessions_start_utc
ON telemetry.sessions(session_start_utc DESC);
