"""Repository for events_race_control table."""

import logging
from typing import Optional

from database.client import PostgresClient
from database.repositories.base import RepositoryBase


class EventsRaceControlRepository(RepositoryBase):
    """Manages events_race_control table — session-level events (no driver)."""

    TABLE_NAME = "telemetry.events_race_control"

    def __init__(self, postgres_client: PostgresClient, logger: Optional[logging.Logger] = None):
        super().__init__(postgres_client, logger)

    def insert(
        self,
        session_uid: str,
        overall_frame_identifier: int,
        event_code: str,
        session_time: float,
        safety_car_type: Optional[str] = None,
        safety_car_event_type: Optional[str] = None,
        num_lights: Optional[int] = None,
        drs_disabled_reason: Optional[str] = None,
    ):
        sql = """
            INSERT INTO telemetry.events_race_control (
                session_uid, overall_frame_identifier, event_code, session_time,
                safety_car_type, safety_car_event_type, num_lights, drs_disabled_reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_uid, overall_frame_identifier, event_code) DO NOTHING
        """
        self._execute(
            sql,
            (session_uid, overall_frame_identifier, event_code, session_time,
             safety_car_type, safety_car_event_type, num_lights, drs_disabled_reason),
            table_name=self.TABLE_NAME,
        )
