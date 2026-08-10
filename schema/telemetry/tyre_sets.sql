-- Per-lap snapshot of available tyre sets (Packet 12)
-- Only available=true sets are stored. All rows sharing the same
-- (session_uid, user_id, lap_number) form one snapshot.
CREATE TABLE IF NOT EXISTS telemetry.tyre_sets (
    id                  SERIAL PRIMARY KEY,
    session_uid         VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL REFERENCES identity.users(id),
    lap_number          SMALLINT NOT NULL,
    actual_compound     VARCHAR(30) NOT NULL,
    visual_compound     VARCHAR(30) NOT NULL,
    wear                SMALLINT NOT NULL,
    life_span           SMALLINT NOT NULL,
    usable_life         SMALLINT NOT NULL,
    lap_delta_time_ms   SMALLINT NOT NULL,
    fitted              BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_tyre_sets_snapshot
    ON telemetry.tyre_sets(session_uid, user_id, lap_number);
