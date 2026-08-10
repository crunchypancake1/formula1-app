#!/bin/bash
set -e

# Database initialization script for schema-based separation
# Creates single app database with telemetry and webapp schemas

APP_DB="${APP_DB:-f1_app}"

echo "Creating F1 database with schemas..."

# Create app database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE "$APP_DB";
EOSQL

# Enable TimescaleDB and create schemas
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$APP_DB" <<-EOSQL
    -- Enable TimescaleDB extension
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    -- Enable pg_trgm extension for trigram indexes (fuzzy search)
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- Create identity schema (user identity hub, shared across services)
    CREATE SCHEMA IF NOT EXISTS identity;

    -- Create telemetry schema (immutable game data, written by listener)
    CREATE SCHEMA IF NOT EXISTS telemetry;

    -- Create webapp schema (mutable app data, managed by API)
    CREATE SCHEMA IF NOT EXISTS webapp;

    -- Create ml schema (derived/computed ML data)
    CREATE SCHEMA IF NOT EXISTS ml;

    -- Grant permissions (default user has full access)
    GRANT ALL PRIVILEGES ON SCHEMA identity TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON SCHEMA telemetry TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON SCHEMA webapp TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON SCHEMA ml TO "$POSTGRES_USER";
EOSQL

echo "F1 database initialized: $APP_DB (with TimescaleDB, identity, telemetry, webapp, and ml schemas)"
