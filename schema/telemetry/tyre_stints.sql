-- Tyre stint history from Session History packets (Packet 11)
CREATE TABLE IF NOT EXISTS telemetry.tyre_stints (
    session_uid VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    stint_number SMALLINT NOT NULL,
    end_lap SMALLINT,
    actual_compound VARCHAR(30) NOT NULL,
    visual_compound VARCHAR(30) NOT NULL,
    PRIMARY KEY (session_uid, user_id, stint_number)
);

-- No secondary index: (session_uid, user_id) is a prefix of the primary key,
-- which also supplies the ORDER BY stint_number the bot reads with.
