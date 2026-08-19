-- One row per session-card message the bot has posted. `finalized` gates the
-- scheduled handler: once true the session's card is never touched again, so
-- a finished weekend's messages stop costing a Discord API call every tick.
CREATE TABLE IF NOT EXISTS bot.discord_session_messages (
    session_uid VARCHAR(20) PRIMARY KEY REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    channel_id  VARCHAR(50) NOT NULL,
    message_id  VARCHAR(50) NOT NULL,
    finalized   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Backs "is this session already tracked" (primary key) and the scheduled
-- handler's sweep for unfinalized cards to check on every tick.
CREATE INDEX IF NOT EXISTS idx_discord_session_messages_pending
ON bot.discord_session_messages(session_uid)
WHERE NOT finalized;
