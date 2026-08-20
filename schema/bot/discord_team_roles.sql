CREATE SCHEMA IF NOT EXISTS bot;

-- Maps a guild role the bot manages (one per F1 team, plus Reserve) to the
-- Discord role it created for it. role_key is not an FK to telemetry.teams:
-- Reserve isn't a real team, and this table only ever holds the current F1 26
-- grid's roles, not every historical team_id that table accepts.
CREATE TABLE IF NOT EXISTS bot.discord_team_roles (
    role_key   VARCHAR(50) PRIMARY KEY,
    role_id    VARCHAR(50) NOT NULL,
    role_name  VARCHAR(100) NOT NULL,
    color      INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
