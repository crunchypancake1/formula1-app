-- Driver action events (simple single-driver events)
-- Covers: RCWN, TMPT, DTSV, SGSV
CREATE TABLE IF NOT EXISTS telemetry.events_driver_actions (
    session_uid                 VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    event_code                  VARCHAR(10) NOT NULL,
    session_time                FLOAT NOT NULL,
    user_id                   INTEGER NOT NULL REFERENCES identity.users(id),
    stop_time                   REAL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, event_code, user_id)
);

-- No secondary indexes. session_uid is a prefix of the primary key, and a bare
-- event_code index would cover four distinct values across the whole table —
-- far too unselective for the planner to prefer over a scan, and nothing
-- queries by code without also naming a session.
