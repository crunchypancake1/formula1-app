-- Fastest lap events (one row per fastest lap)
-- Covers: FTLP
CREATE TABLE IF NOT EXISTS telemetry.events_fastest_laps (
    session_uid                 VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    user_id                   INTEGER NOT NULL REFERENCES identity.users(id),
    lap_time                    REAL NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_fastest_laps_session ON telemetry.events_fastest_laps(session_uid);
