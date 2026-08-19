CREATE SCHEMA IF NOT EXISTS bot;

-- Tracks which Discord channel the bot is currently posting a weekend's
-- session cards into. weekend_link is telemetry.sessions.weekend_link, but
-- carries no FK there: a weekend is a group of sessions, not a row, and the
-- first session of a new weekend needs a channel to be created for it before
-- that session even reaches the sessions table's usual read patterns.
CREATE TABLE IF NOT EXISTS bot.discord_weekends (
    weekend_link VARCHAR(255) PRIMARY KEY,
    channel_id   VARCHAR(50) NOT NULL,
    archived     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- No secondary index: the scheduled handler's only reads are "does this
-- weekend_link have a row" (primary key) and "the not-yet-archived one"
-- (below), both cheap over a table that gains one row per race weekend.
CREATE INDEX IF NOT EXISTS idx_discord_weekends_active
ON bot.discord_weekends(weekend_link)
WHERE NOT archived;
