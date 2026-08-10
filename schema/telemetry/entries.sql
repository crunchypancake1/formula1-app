-- Entries table (driver roster per session)
CREATE TABLE IF NOT EXISTS telemetry.entries (
    session_uid VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    car_index SMALLINT NOT NULL,
    team_id SMALLINT NOT NULL REFERENCES telemetry.teams(team_id),
    race_number SMALLINT NOT NULL,
    telemetry_setting BOOLEAN NOT NULL,
    livery_colors SMALLINT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id),
    CONSTRAINT uq_entries_session_car UNIQUE (session_uid, car_index),
    CONSTRAINT ck_entries_car_index_valid CHECK (car_index >= 0 AND car_index < 22)
);

CREATE INDEX IF NOT EXISTS idx_entries_session_uid ON telemetry.entries(session_uid);
CREATE INDEX IF NOT EXISTS idx_entries_user_id ON telemetry.entries(user_id);
