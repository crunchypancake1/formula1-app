"""Test fixtures: DB client, dispatcher wiring, cleanup."""

import logging
import os
import sys

import pytest

# Add listener root to sys.path so imports work like they do in production
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.client import PostgresClient
from database.repositories import (
    CarFrameDamageRepository,
    CarFrameMotionExRepository,
    CarFrameRepository,
    CarSetupsRepository,
    EntriesRepository,
    EventsButtonsRepository,
    EventsCollisionsRepository,
    EventsDriverActionsRepository,
    EventsFastestLapsRepository,
    EventsFlashbacksRepository,
    EventsOvertakesRepository,
    EventsPenaltiesRepository,
    EventsRaceControlRepository,
    EventsRetirementsRepository,
    EventsSpeedTrapsRepository,
    FinalClassificationRepository,
    LapPositionsRepository,
    LapSetupsRepository,
    LapsRepository,
    LobbyInfoRepository,
    SessionBestsRepository,
    SessionsRepository,
    SessionTimelineRepository,
    TyreSetsInventoryRepository,
    TyreStintsRepository,
)
from dispatcher import PacketDispatcher
from services import (
    CarFrameService,
    CarSetupService,
    EventsService,
    FinalClassificationService,
    LapHistoryService,
    LapPositionsService,
    LobbyInfoService,
    MotionExService,
    ParticipantsService,
    SessionService,
    TyreSetsService,
)

from .qualifying_scenario import QUALIFYING_SESSION_UID
from .scenario import SESSION_UID

_TEST_SESSION_UIDS = [str(SESSION_UID), str(QUALIFYING_SESSION_UID)]
_DRIVER_NAME_PREFIX = "SimTestDriver_"


@pytest.fixture(scope="session")
def logger():
    log = logging.getLogger("test_simulation")
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        log.addHandler(handler)
    return log


@pytest.fixture(scope="session")
def db_client(logger):
    """Create a PostgresClient connected to the Docker PostgreSQL."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "7005")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db = os.getenv("POSTGRES_DB", "f1_app")

    uri = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    client = PostgresClient(uri, pool_min=2, pool_max=5, logger=logger)

    if not client.enabled:
        pytest.skip("PostgreSQL not available — is Docker running?")

    yield client
    client.close()


@pytest.fixture(scope="session")
def dispatcher(db_client, logger):
    """Wire up the full dispatcher with all services and repositories."""
    sessions_repo = SessionsRepository(db_client, logger)
    entries_repo = EntriesRepository(db_client, logger)
    laps_repo = LapsRepository(db_client, logger)
    car_frame_repo = CarFrameRepository(db_client, logger)
    car_frame_damage_repo = CarFrameDamageRepository(db_client, logger)
    events_race_control_repo = EventsRaceControlRepository(db_client, logger)
    events_overtakes_repo = EventsOvertakesRepository(db_client, logger)
    events_collisions_repo = EventsCollisionsRepository(db_client, logger)
    events_penalties_repo = EventsPenaltiesRepository(db_client, logger)
    events_fastest_laps_repo = EventsFastestLapsRepository(db_client, logger)
    events_retirements_repo = EventsRetirementsRepository(db_client, logger)
    events_speed_traps_repo = EventsSpeedTrapsRepository(db_client, logger)
    events_driver_actions_repo = EventsDriverActionsRepository(db_client, logger)
    final_classification_repo = FinalClassificationRepository(db_client, logger)
    session_timeline_repo = SessionTimelineRepository(db_client, logger)
    lap_positions_repo = LapPositionsRepository(db_client, logger)
    events_flashbacks_repo = EventsFlashbacksRepository(db_client, logger)
    events_buttons_repo = EventsButtonsRepository(db_client, logger)
    session_bests_repo = SessionBestsRepository(db_client, logger)
    car_setups_repo = CarSetupsRepository(db_client, logger)
    lap_setups_repo = LapSetupsRepository(db_client, logger)
    tyre_sets_inventory_repo = TyreSetsInventoryRepository(db_client, logger)
    car_frame_motion_ex_repo = CarFrameMotionExRepository(db_client, logger)
    lobby_info_repo = LobbyInfoRepository(db_client, logger)

    session_service = SessionService(sessions_repo, session_timeline_repo, logger)
    participants_service = ParticipantsService(entries_repo, logger)
    car_frame_service = CarFrameService(car_frame_repo, car_frame_damage_repo=car_frame_damage_repo, logger=logger)
    tyre_stints_repo = TyreStintsRepository(db_client, logger)
    lap_history_service = LapHistoryService(
        laps_repo, tyre_stints_repo, session_bests_repo, logger
    )
    events_service = EventsService(
        race_control_repo=events_race_control_repo,
        overtakes_repo=events_overtakes_repo,
        collisions_repo=events_collisions_repo,
        penalties_repo=events_penalties_repo,
        fastest_laps_repo=events_fastest_laps_repo,
        retirements_repo=events_retirements_repo,
        speed_traps_repo=events_speed_traps_repo,
        driver_actions_repo=events_driver_actions_repo,
        flashbacks_repo=events_flashbacks_repo,
        buttons_repo=events_buttons_repo,
        logger=logger,
    )
    final_classification_service = FinalClassificationService(
        final_classification_repo,
        session_service,
        logger,
        dead_letter_dir=None,
    )
    lap_positions_service = LapPositionsService(lap_positions_repo, logger)
    car_setup_service = CarSetupService(car_setups_repo, lap_setups_repo, logger)
    tyre_sets_service = TyreSetsService(tyre_sets_inventory_repo, logger)
    motion_ex_service = MotionExService(car_frame_motion_ex_repo, logger)
    lobby_info_service = LobbyInfoService(lobby_info_repo, logger)

    # Wire every service, so packets 5, 9, 12, 13 and 16 are exercised through
    # the real dispatcher rather than silently no-oping.
    return PacketDispatcher(
        session_service=session_service,
        participants_service=participants_service,
        car_frame_service=car_frame_service,
        lap_history_service=lap_history_service,
        events_service=events_service,
        final_classification_service=final_classification_service,
        lap_positions_service=lap_positions_service,
        car_setup_service=car_setup_service,
        tyre_sets_service=tyre_sets_service,
        motion_ex_service=motion_ex_service,
        lobby_info_service=lobby_info_service,
        logger=logger,
    )


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data(db_client, logger):
    """Delete all test data after the test session completes."""
    yield

    logger.info("Cleaning up test data for session_uids=%s", _TEST_SESSION_UIDS)

    tables_to_clean = [
        "telemetry.lap_setups",
        "telemetry.car_setups",
        "telemetry.tyre_sets",
        "telemetry.session_bests",
        "telemetry.events_flashbacks",
        "telemetry.events_buttons",
        "telemetry.car_frame_motion_ex",
        "telemetry.lobby_info",
        "telemetry.race_classification",
        "telemetry.qualifying_classification",
        "telemetry.lap_positions",
        "telemetry.tyre_stints",
        "telemetry.laps",
        "telemetry.car_frame_damage",
        "telemetry.car_frame",
        "telemetry.events_race_control",
        "telemetry.events_overtakes",
        "telemetry.events_collisions",
        "telemetry.events_penalties",
        "telemetry.events_fastest_laps",
        "telemetry.events_retirements",
        "telemetry.events_speed_traps",
        "telemetry.events_driver_actions",
        "telemetry.session_timeline",
        "telemetry.weather_forecast",
        "telemetry.entries",
        "telemetry.sessions",
    ]

    with db_client.connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            for table in tables_to_clean:
                for session_uid in _TEST_SESSION_UIDS:
                    try:
                        cur.execute(
                            f"DELETE FROM {table} WHERE session_uid = %s",
                            (session_uid,),
                        )
                    except Exception as e:
                        logger.warning("Failed to clean %s: %s", table, e)
                        conn.rollback()
                        continue

            # Clean up test drivers
            try:
                cur.execute(
                    "DELETE FROM identity.users WHERE driver_name LIKE %s",
                    (f"{_DRIVER_NAME_PREFIX}%",),
                )
            except Exception as e:
                logger.warning("Failed to clean identity.users: %s", e)
                conn.rollback()

            conn.commit()

    logger.info("Test data cleanup complete")
