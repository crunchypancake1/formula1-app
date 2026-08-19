-- Entries table (driver roster per session, source: Participants packet, Packet 4)
--
-- telemetry_public mirrors m_yourTelemetry: false = Restricted (the game zeroes
-- fuel/ERS/damage for this car in everyone else's stream), true = Public.
CREATE TABLE IF NOT EXISTS telemetry.entries (
    session_uid VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    car_index SMALLINT NOT NULL,
    team_id INTEGER NOT NULL REFERENCES telemetry.teams(team_id),
    race_number SMALLINT NOT NULL,
    driver_id INTEGER,
    network_id INTEGER,
    my_team BOOLEAN,
    platform VARCHAR(20),
    tech_level SMALLINT,
    show_online_names BOOLEAN,
    telemetry_public BOOLEAN NOT NULL,
    num_livery_colors SMALLINT,
    livery_colors SMALLINT[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id),
    CONSTRAINT uq_entries_session_car UNIQUE (session_uid, car_index),
    CONSTRAINT ck_entries_car_index_valid CHECK (car_index >= 0 AND car_index < 24)
);

-- No index on session_uid alone: the primary key (session_uid, user_id) leads
-- with it, so roster lookups already have one.
-- user_id is the other direction — "every session this driver entered".
CREATE INDEX IF NOT EXISTS idx_entries_user_id ON telemetry.entries(user_id);
