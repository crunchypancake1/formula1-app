-- Lobby snapshot (source: Lobby Info packet, Packet 9)
--
-- One row per session, overwritten as the lobby changes. session_uid is
-- VARCHAR here to match every other table, so it joins to telemetry.sessions
-- without a cast — the lobby packet arrives before the session row exists, so
-- there is deliberately no foreign key.
CREATE TABLE IF NOT EXISTS telemetry.lobby_info (
    session_uid VARCHAR(20) PRIMARY KEY,
    num_players SMALLINT NOT NULL,
    players JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
