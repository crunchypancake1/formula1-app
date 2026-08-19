-- Qualifying classification (source: Final Classification packet, Packet 8)
-- League points are calculated dynamically from position; game_points is what
-- the game itself awarded, kept for reference.
CREATE TABLE IF NOT EXISTS telemetry.qualifying_classification (
    session_uid VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    position SMALLINT NOT NULL,
    num_laps SMALLINT NOT NULL,
    best_lap_time_ms INTEGER,
    result_status VARCHAR(50) NOT NULL,
    result_reason VARCHAR(50),
    game_points SMALLINT,
    penalties_time SMALLINT,
    num_penalties SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id),
    CONSTRAINT ck_quali_class_position_valid CHECK (position >= 0)
);

-- session_uid alone is a prefix of the primary key; this covers the ordered read.
CREATE INDEX IF NOT EXISTS idx_quali_class_position ON telemetry.qualifying_classification(session_uid, position);
