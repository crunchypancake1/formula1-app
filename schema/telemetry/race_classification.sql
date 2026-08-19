-- Race classification (source: Final Classification packet, Packet 8)
-- League points are calculated dynamically from position; game_points is what
-- the game itself awarded, kept for reference.
CREATE TABLE IF NOT EXISTS telemetry.race_classification (
    session_uid VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    position SMALLINT NOT NULL,
    num_laps SMALLINT NOT NULL,
    grid_position SMALLINT NOT NULL,
    num_pit_stops SMALLINT NOT NULL,
    result_status VARCHAR(50) NOT NULL,
    result_reason VARCHAR(50),
    best_lap_time_ms INTEGER,
    game_points SMALLINT,
    total_race_time FLOAT NOT NULL,
    penalties_time SMALLINT NOT NULL,
    num_penalties SMALLINT NOT NULL,
    num_tyre_stints SMALLINT NOT NULL,
    tyre_stints_actual SMALLINT[] NOT NULL,
    tyre_stints_visual SMALLINT[] NOT NULL,
    tyre_stints_end_laps SMALLINT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id),
    CONSTRAINT ck_race_class_position_valid CHECK (position >= 0)
);

-- Classification is read as "the whole field for one session, in finishing
-- order", which this index serves end to end. A bare session_uid index would
-- be a prefix of the primary key and of this one; an INCLUDE (user_id) variant
-- cannot produce an index-only scan either, because every caller selects the
-- full row.
CREATE INDEX IF NOT EXISTS idx_race_class_position ON telemetry.race_classification(session_uid, position);
