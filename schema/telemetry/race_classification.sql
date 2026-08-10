-- Race classification table
-- Stores final race results including tire stints and penalties
-- Points are calculated dynamically from position using league settings
CREATE TABLE IF NOT EXISTS telemetry.race_classification (
    session_uid VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    position SMALLINT NOT NULL,
    num_laps SMALLINT NOT NULL,
    grid_position SMALLINT NOT NULL,
    num_pit_stops SMALLINT NOT NULL,
    result_status VARCHAR(50) NOT NULL,
    result_reason VARCHAR(50),
    best_lap_time_ms BIGINT,
    total_race_time FLOAT NOT NULL,
    penalties_time SMALLINT NOT NULL,
    num_penalties SMALLINT NOT NULL,
    num_tyre_stints SMALLINT NOT NULL,
    tyre_stints_actual SMALLINT[] NOT NULL,
    tyre_stints_visual SMALLINT[] NOT NULL,
    tyre_stints_end_laps SMALLINT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id),
    CONSTRAINT ck_race_class_position_valid CHECK (position >= 0)
);

CREATE INDEX IF NOT EXISTS idx_race_class_session ON telemetry.race_classification(session_uid);
CREATE INDEX IF NOT EXISTS idx_race_class_position ON telemetry.race_classification(session_uid, position);

-- Covering index for standings queries (direct user_id join, no entries needed)
CREATE INDEX IF NOT EXISTS idx_race_class_standings ON telemetry.race_classification(session_uid, position) INCLUDE (user_id);
