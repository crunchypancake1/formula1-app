-- Unified identity table: every participant (Discord-linked or not) is a row.
-- Discord fields NULL = unlinked driver (formerly "phantom").
CREATE TABLE IF NOT EXISTS identity.users (
    id SERIAL PRIMARY KEY,
    driver_name VARCHAR(255) NOT NULL,
    nationality VARCHAR(50),
    discord_id VARCHAR(100) UNIQUE,
    discord_username VARCHAR(255) UNIQUE,
    discord_nickname VARCHAR(255),
    discord_email VARCHAR(255),
    discord_avatar VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_driver_name UNIQUE (driver_name),
    CONSTRAINT ck_users_driver_name_not_empty CHECK (length(trim(driver_name)) > 0)
);

-- Case-insensitive uniqueness enforcement
DROP INDEX IF EXISTS identity.idx_users_driver_name_lower;
CREATE UNIQUE INDEX idx_users_driver_name_lower
ON identity.users(lower(driver_name));

-- Exact lookup
CREATE INDEX IF NOT EXISTS idx_users_driver_name
ON identity.users(driver_name);

-- Fuzzy search
CREATE INDEX IF NOT EXISTS idx_users_driver_name_trgm
ON identity.users USING gin (driver_name gin_trgm_ops);

-- Discord lookup (partial — only non-NULL)
CREATE INDEX IF NOT EXISTS idx_users_discord_id
ON identity.users(discord_id) WHERE discord_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_discord_username
ON identity.users(discord_username) WHERE discord_username IS NOT NULL;

-- Fuzzy search on discord_username
CREATE INDEX IF NOT EXISTS idx_users_discord_username_trgm
ON identity.users USING gin (discord_username gin_trgm_ops);
