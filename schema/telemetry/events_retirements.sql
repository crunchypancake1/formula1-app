-- Retirement events (one row per retirement)
-- Covers: RTMT
CREATE TABLE IF NOT EXISTS telemetry.events_retirements (
    session_uid                 VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    user_id                   INTEGER NOT NULL REFERENCES identity.users(id),
    reason                      VARCHAR(50) NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, user_id)
);

-- No secondary index: session_uid is a prefix of the primary key, which also
-- supplies the feed's ORDER BY overall_frame_identifier DESC.
