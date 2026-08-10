-- Qualifying classification table
-- Stores qualifying results with minimal fields needed for standings
-- Points are calculated dynamically from position using league settings
CREATE TABLE IF NOT EXISTS telemetry.qualifying_classification (
    session_uid VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    position SMALLINT NOT NULL,
    num_laps SMALLINT NOT NULL,
    best_lap_time_ms BIGINT,
    result_status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id),
    CONSTRAINT ck_quali_class_position_valid CHECK (position >= 0)
);

CREATE INDEX IF NOT EXISTS idx_quali_class_session ON telemetry.qualifying_classification(session_uid);
CREATE INDEX IF NOT EXISTS idx_quali_class_position ON telemetry.qualifying_classification(session_uid, position);
