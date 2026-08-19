#!/bin/bash
set -e

# Database initialization script.
# Creates the app database with the identity and telemetry schemas.
# run_schema.py creates the tables inside them.

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

    -- Grant permissions (default user has full access)
    GRANT ALL PRIVILEGES ON SCHEMA identity TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON SCHEMA telemetry TO "$POSTGRES_USER";
EOSQL

echo "F1 database initialized: $APP_DB (TimescaleDB, identity and telemetry schemas)"
