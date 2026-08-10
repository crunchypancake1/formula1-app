-- Retirement events (one row per retirement)
-- Covers: RTMT
CREATE TABLE IF NOT EXISTS telemetry.events_retirements (
    session_uid                 VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    user_id                   INTEGER NOT NULL REFERENCES identity.users(id),
    reason                      VARCHAR(50) NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_retirements_session ON telemetry.events_retirements(session_uid);
