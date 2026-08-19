-- Driver action events (simple single-driver events)
-- Covers: RCWN, TMPT, DTSV, SGSV
CREATE TABLE IF NOT EXISTS telemetry.events_driver_actions (
    session_uid                 VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    event_code                  VARCHAR(10) NOT NULL,
    session_time                FLOAT NOT NULL,
    user_id                   INTEGER NOT NULL REFERENCES identity.users(id),
    stop_time                   REAL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, event_code, user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_driver_actions_session ON telemetry.events_driver_actions(session_uid);
CREATE INDEX IF NOT EXISTS idx_events_driver_actions_code ON telemetry.events_driver_actions(event_code);
