-- Overtake events (one row per overtake)
-- Covers: OVTK
CREATE TABLE IF NOT EXISTS telemetry.events_overtakes (
    session_uid                 VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    overtaking_user_id        INTEGER NOT NULL REFERENCES identity.users(id),
    overtaken_user_id         INTEGER NOT NULL REFERENCES identity.users(id),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, overtaking_user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_overtakes_session ON telemetry.events_overtakes(session_uid);
