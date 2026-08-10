CREATE TABLE IF NOT EXISTS telemetry.lobby_info (
    session_uid BIGINT PRIMARY KEY,
    players JSONB NOT NULL,
    num_players SMALLINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
