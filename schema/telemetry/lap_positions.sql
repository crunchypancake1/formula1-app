-- Lap positions table (position order at end of each lap)
-- positions is INTEGER[] of driver_ids indexed by position
CREATE TABLE IF NOT EXISTS telemetry.lap_positions (
    session_uid VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    lap_number SMALLINT NOT NULL,
    positions INTEGER[] NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, lap_number),
    CONSTRAINT ck_lap_positions_lap_number_valid CHECK (lap_number >= 0)
);

-- No secondary index: the primary key leads with session_uid.
