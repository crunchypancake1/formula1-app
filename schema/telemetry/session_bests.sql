-- Per-driver session bests (source: Session History packet, Packet 11)
--
-- The packet reports which lap each best was set on rather than the time
-- itself; join back to telemetry.laps on (session_uid, user_id, lap_number)
-- for the times. 0 means "no best set yet" and is stored as NULL.
CREATE TABLE IF NOT EXISTS telemetry.session_bests (
    session_uid         VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id             INTEGER NOT NULL REFERENCES identity.users(id),
    best_lap_num        SMALLINT,
    best_sector1_lap_num SMALLINT,
    best_sector2_lap_num SMALLINT,
    best_sector3_lap_num SMALLINT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, user_id)
);

CREATE INDEX IF NOT EXISTS idx_session_bests_session ON telemetry.session_bests(session_uid);
