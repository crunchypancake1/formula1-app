-- Sessions table
CREATE TABLE IF NOT EXISTS telemetry.sessions (
    session_uid VARCHAR(255) PRIMARY KEY,
    weekend_link VARCHAR(255) NOT NULL,
    session_link VARCHAR(255) NOT NULL,
    track_id SMALLINT NOT NULL REFERENCES telemetry.tracks(track_id),
    session_type VARCHAR(50) NOT NULL,
    formula VARCHAR(50) NOT NULL,
    game_mode VARCHAR(50) NOT NULL,
    ruleset VARCHAR(50) NOT NULL,
    total_laps SMALLINT NOT NULL,
    session_duration INTEGER NOT NULL,
    num_sessions_in_weekend SMALLINT NOT NULL,
    time_of_day SMALLINT,
    session_length SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_sessions_session_uid_not_empty CHECK (length(session_uid) > 0),
    CONSTRAINT uk_sessions_weekend_session UNIQUE (weekend_link, session_link)
);

CREATE INDEX IF NOT EXISTS idx_sessions_track ON telemetry.sessions(track_id, session_type);

-- Critical for standings JOIN (races.weekend_link -> sessions.weekend_link)
CREATE INDEX IF NOT EXISTS idx_sessions_weekend_link ON telemetry.sessions(weekend_link);
