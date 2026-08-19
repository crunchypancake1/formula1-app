#!/usr/bin/env python3
"""SQL schema runner. Applies .sql files in FK-dependency order."""

import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import psycopg

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# FK dependency chain:
#   1. identity.users (no deps)
#   2. telemetry tables (entries references identity.users)
SCHEMA_EXECUTION_ORDER = {
    "identity": [
        "users.sql",
        "get_or_create_driver.sql",
    ],
    "telemetry": [
        "tracks.sql",
        "teams.sql",
        "sessions.sql",
        "entries.sql",
        "laps.sql",
        "events_race_control.sql",
        "events_overtakes.sql",
        "events_collisions.sql",
        "events_penalties.sql",
        "events_fastest_laps.sql",
        "events_retirements.sql",
        "events_speed_traps.sql",
        "events_driver_actions.sql",
        "events_flashbacks.sql",
        "events_buttons.sql",
        "race_classification.sql",
        "qualifying_classification.sql",
        "weather_forecast.sql",
        "lap_positions.sql",
        "session_timeline.sql",
        "session_bests.sql",
        "car_frame.sql",
        "car_frame_damage.sql",
        "car_frame_motion_ex.sql",
        "tyre_stints.sql",
        "car_setups.sql",
        "lap_setups.sql",
        "tyre_sets.sql",
        "lobby_info.sql",
    ],
}


def get_database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    db = os.environ.get("POSTGRES_DB", "f1_app")
    # Percent-encode the credentials, as listener/config.py does: a password
    # containing @ : / or # is otherwise parsed as URI structure and the
    # connection fails somewhere unhelpful.
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


def run_schema() -> None:
    schema_dir = Path(__file__).parent

    logger.info("Connecting to database...")
    with psycopg.connect(get_database_url(), autocommit=False) as conn:
        for schema_name, file_order in SCHEMA_EXECUTION_ORDER.items():
            schema_path = schema_dir / schema_name
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema directory missing: {schema_path}")

            for filename in file_order:
                sql_file = schema_path / filename
                if not sql_file.exists():
                    raise FileNotFoundError(f"Schema file missing: {sql_file}")

                logger.info("Running %s/%s...", schema_name, filename)
                sql = sql_file.read_text()

                try:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                    conn.commit()
                except (psycopg.errors.DuplicateTable, psycopg.errors.DuplicateObject):
                    # Rollback discards the whole file, not just the duplicate
                    # statement — anything declared after it (a newly added
                    # index, a compression policy) silently does not run. Every
                    # statement here uses IF NOT EXISTS, so reaching this means
                    # one of them does not, and it is worth seeing.
                    conn.rollback()
                    logger.warning(
                        "  %s/%s: object already exists — rest of file skipped",
                        schema_name,
                        filename,
                    )
                except Exception:
                    conn.rollback()
                    logger.exception("  failed: %s/%s", schema_name, filename)
                    raise

    logger.info("Schema setup complete!")


if __name__ == "__main__":
    try:
        run_schema()
    except Exception:
        logger.exception("Schema setup failed")
        sys.exit(1)
