CREATE SCHEMA IF NOT EXISTS identity;

-- Required by the gin_trgm_ops indexes below. scripts/init_databases.sh also
-- creates it, but declaring it here keeps this file runnable against a database
-- that was not built by docker compose.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Unified identity table: every participant (Discord-linked or not) is a row.
-- Discord fields NULL = driver seen in telemetry but not linked to a Discord account.
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

-- Case-insensitive uniqueness. This is the index every name lookup actually
-- uses — get_or_create_driver and the bot's driverByName both match on
-- lower(driver_name) — and it is strictly stronger than uq_users_driver_name,
-- which is kept only as a declared constraint.
--
-- A plain btree on driver_name is deliberately absent: uq_users_driver_name
-- already provides one, and nothing queries the column case-sensitively.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_driver_name_lower
ON identity.users(lower(driver_name));

-- Fuzzy search (bot: searchDrivers)
CREATE INDEX IF NOT EXISTS idx_users_driver_name_trgm
ON identity.users USING gin (driver_name gin_trgm_ops);

-- Fuzzy search on discord_username. Partial because most rows are drivers seen
-- in telemetry with no linked Discord account.
--
-- No plain btree on discord_id or discord_username: the UNIQUE constraints on
-- both columns already create one, and an extra partial index over the same
-- column only adds write cost.
CREATE INDEX IF NOT EXISTS idx_users_discord_username_trgm
ON identity.users USING gin (discord_username gin_trgm_ops)
WHERE discord_username IS NOT NULL;
