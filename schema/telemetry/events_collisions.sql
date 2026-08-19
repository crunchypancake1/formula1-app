-- Collision events (one row per collision)
-- Covers: COLL
CREATE TABLE IF NOT EXISTS telemetry.events_collisions (
    session_uid                 VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    user1_id                  INTEGER NOT NULL REFERENCES identity.users(id),
    user2_id                  INTEGER NOT NULL REFERENCES identity.users(id),
    severity                    SMALLINT,   -- 0 = low, 1 = medium, 2 = high
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, user1_id)
);

-- No secondary index: session_uid is a prefix of the primary key.
