-- Laps table (source: Session History packet, Packet 11)
CREATE TABLE IF NOT EXISTS telemetry.laps (
    session_uid VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES identity.users(id),
    lap_number SMALLINT NOT NULL,
    lap_time_ms INTEGER,
    sector1_time_ms INTEGER,
    sector2_time_ms INTEGER,
    sector3_time_ms INTEGER,
    is_valid BOOLEAN NOT NULL,
    sector1_valid BOOLEAN NOT NULL,
    sector2_valid BOOLEAN NOT NULL,
    sector3_valid BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id, lap_number),
    CONSTRAINT ck_laps_lap_number_valid CHECK (lap_number >= 0),
    CONSTRAINT ck_laps_lap_time_valid CHECK (lap_time_ms IS NULL OR lap_time_ms >= 0)
);

-- The primary key (session_uid, user_id, lap_number) already serves every
-- per-session and per-driver lookup, including the four joins sessionBests
-- makes back into this table. The only query it does not serve is "fastest
-- valid lap in this session", which gets the partial index below.
CREATE INDEX IF NOT EXISTS idx_laps_fastest_valid
ON telemetry.laps(session_uid, lap_time_ms)
WHERE is_valid = true AND lap_time_ms IS NOT NULL;
