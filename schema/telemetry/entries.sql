-- Entries table (driver roster per session)
CREATE TABLE IF NOT EXISTS telemetry.entries (
    session_uid VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    car_index SMALLINT NOT NULL,
    team_id INTEGER NOT NULL REFERENCES telemetry.teams(team_id),
    race_number SMALLINT NOT NULL,
    telemetry_setting BOOLEAN NOT NULL,
    livery_colors SMALLINT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id),
    CONSTRAINT uq_entries_session_car UNIQUE (session_uid, car_index),
    CONSTRAINT ck_entries_car_index_valid CHECK (car_index >= 0 AND car_index < 24)
);

CREATE INDEX IF NOT EXISTS idx_entries_session_uid ON telemetry.entries(session_uid);
CREATE INDEX IF NOT EXISTS idx_entries_user_id ON telemetry.entries(user_id);

-- 2026 Season Pack: 24 cars (was 22), and team_id can exceed SMALLINT range
-- (sentinel 65535). Idempotent upgrade path for pre-existing deployments.
ALTER TABLE telemetry.entries ALTER COLUMN team_id TYPE INTEGER;
ALTER TABLE telemetry.entries DROP CONSTRAINT IF EXISTS ck_entries_car_index_valid;
ALTER TABLE telemetry.entries ADD CONSTRAINT ck_entries_car_index_valid CHECK (car_index >= 0 AND car_index < 24);
