"""Main entry point for F1 telemetry listener."""

import signal
import sys

from config import (
    get_dead_letter_dir,
    get_listen_ip,
    get_listen_port,
    get_log_level,
    get_log_path,
    get_postgres_pool_max,
    get_postgres_pool_min,
    get_postgres_uri,
)
from database.client import PostgresClient
from database.repositories import (
    CarFrameDamageRepository,
    CarFrameMotionExRepository,
    CarFrameRepository,
    CarSetupsRepository,
    EntriesRepository,
    EventsCollisionsRepository,
    EventsDriverActionsRepository,
    EventsFastestLapsRepository,
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
    SessionsRepository,
    SessionTimelineRepository,
    TyreSetsInventoryRepository,
    TyreStintsRepository,
)
from dispatcher import PacketDispatcher
from logging_config import configure_logging
from server import start_udp_server
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


def main():
    """Initialize and start the F1 telemetry listener."""
    # Configure logging
    logger = configure_logging(get_log_level(), get_log_path())
    logger.info("Starting F1 telemetry listener")

    # Initialize PostgreSQL connection pool
    postgres_client = PostgresClient(
        connection_string=get_postgres_uri(),
        pool_min=get_postgres_pool_min(),
        pool_max=get_postgres_pool_max(),
        logger=logger,
    )

    # Initialize repositories
    sessions_repo = SessionsRepository(postgres_client, logger)
    entries_repo = EntriesRepository(postgres_client, logger)
    laps_repo = LapsRepository(postgres_client, logger)
    car_frame_repo = CarFrameRepository(postgres_client, logger)
    events_race_control_repo = EventsRaceControlRepository(postgres_client, logger)
    events_overtakes_repo = EventsOvertakesRepository(postgres_client, logger)
    events_collisions_repo = EventsCollisionsRepository(postgres_client, logger)
    events_penalties_repo = EventsPenaltiesRepository(postgres_client, logger)
    events_fastest_laps_repo = EventsFastestLapsRepository(postgres_client, logger)
    events_retirements_repo = EventsRetirementsRepository(postgres_client, logger)
    events_speed_traps_repo = EventsSpeedTrapsRepository(postgres_client, logger)
    events_driver_actions_repo = EventsDriverActionsRepository(postgres_client, logger)
    final_classification_repo = FinalClassificationRepository(postgres_client, logger)
    session_timeline_repo = SessionTimelineRepository(postgres_client, logger)
    lap_positions_repo = LapPositionsRepository(postgres_client, logger)
    tyre_stints_repo = TyreStintsRepository(postgres_client, logger)
    car_setups_repo = CarSetupsRepository(postgres_client, logger)
    lap_setups_repo = LapSetupsRepository(postgres_client, logger)
    tyre_sets_inventory_repo = TyreSetsInventoryRepository(postgres_client, logger)
    car_frame_damage_repo = CarFrameDamageRepository(postgres_client, logger)
    car_frame_motion_ex_repo = CarFrameMotionExRepository(postgres_client, logger)
    lobby_info_repo = LobbyInfoRepository(postgres_client, logger)

    # Initialize services
    session_service = SessionService(sessions_repo, session_timeline_repo, logger)
    participants_service = ParticipantsService(entries_repo, logger)
    car_frame_service = CarFrameService(
        car_frame_repo,
        car_frame_damage_repo=car_frame_damage_repo,
        logger=logger,
    )
    lap_history_service = LapHistoryService(laps_repo, tyre_stints_repo, logger)
    events_service = EventsService(
        race_control_repo=events_race_control_repo,
        overtakes_repo=events_overtakes_repo,
        collisions_repo=events_collisions_repo,
        penalties_repo=events_penalties_repo,
        fastest_laps_repo=events_fastest_laps_repo,
        retirements_repo=events_retirements_repo,
        speed_traps_repo=events_speed_traps_repo,
        driver_actions_repo=events_driver_actions_repo,
        logger=logger,
    )
    final_classification_service = FinalClassificationService(
        final_classification_repo,
        session_service,
        logger,
        dead_letter_dir=get_dead_letter_dir(),
    )
    lap_positions_service = LapPositionsService(lap_positions_repo, logger)
    car_setup_service = CarSetupService(car_setups_repo, lap_setups_repo, logger)
    tyre_sets_service = TyreSetsService(tyre_sets_inventory_repo, logger)
    motion_ex_service = MotionExService(car_frame_motion_ex_repo, logger)
    lobby_info_service = LobbyInfoService(lobby_info_repo, logger)

    # Initialize dispatcher
    dispatcher = PacketDispatcher(
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

    # Replay any dead-letter files from previous runs
    final_classification_service.replay_dead_letters()

    # Set up graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, closing connection pool")
        postgres_client.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start UDP server
    def packet_handler(data: bytes):
        dispatcher.handle_packet(data)

    logger.info(
        f"Listening on {get_listen_ip()}:{get_listen_port()} "
        f"(PostgreSQL: {'enabled' if postgres_client.enabled else 'disabled'})"
    )

    try:
        start_udp_server(get_listen_ip(), get_listen_port(), packet_handler, logger)
    except Exception as e:
        logger.error(f"UDP server error: {e}", exc_info=True)
        postgres_client.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
