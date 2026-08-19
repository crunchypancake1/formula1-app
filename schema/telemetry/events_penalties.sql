-- Penalty events (one row per penalty)
-- Covers: PENA
CREATE TABLE IF NOT EXISTS telemetry.events_penalties (
    session_uid                 VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    user_id                   INTEGER NOT NULL REFERENCES identity.users(id),
    other_user_id             INTEGER REFERENCES identity.users(id),
    penalty_type                VARCHAR(50) NOT NULL,
    infringement_type           VARCHAR(50) NOT NULL,
    time_seconds                SMALLINT,   -- NULL when the game sends the 255 sentinel
    lap_num                     SMALLINT,
    places_gained               SMALLINT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, user_id, penalty_type)
);

-- session_uid is a prefix of the primary key, so the feed read needs no index
-- of its own. user_id does: it is the one cross-session lookup here ("every
-- penalty this driver has taken") and, as an FK column, it also keeps a
-- cascading delete of a user off a sequential scan.
CREATE INDEX IF NOT EXISTS idx_events_penalties_driver ON telemetry.events_penalties(user_id);
