-- Speed trap events (one row per speed trap trigger)
-- Covers: SPTP
CREATE TABLE IF NOT EXISTS telemetry.events_speed_traps (
    session_uid                 VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    user_id                   INTEGER NOT NULL REFERENCES identity.users(id),
    speed                       REAL NOT NULL,
    is_overall_fastest          BOOLEAN NOT NULL,
    is_driver_fastest           BOOLEAN NOT NULL,
    fastest_user_id           INTEGER REFERENCES identity.users(id),
    fastest_speed               REAL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_speed_traps_session ON telemetry.events_speed_traps(session_uid);
