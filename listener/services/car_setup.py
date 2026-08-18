"""Car setup service — caches setups for all drivers, writes on lap completion."""

import hashlib
import logging
import struct
from typing import Optional

from database.repositories.car_setups import CarSetupsRepository
from database.repositories.lap_setups import LapSetupsRepository


class CarSetupService:
    """
    Handles Car Setup packets (Packet 5).

    Caches every driver's current setup in memory. On lap completion,
    computes a hash and deduplicates against the car_setups library.
    Links the completed lap to the setup via lap_setups.
    """

    _HASH_FORMAT = '<4B4f6B3B4fBf'

    def __init__(
        self,
        car_setups_repo: CarSetupsRepository,
        lap_setups_repo: LapSetupsRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._car_setups_repo = car_setups_repo
        self._lap_setups_repo = lap_setups_repo
        self._logger = logger or logging.getLogger(__name__)
        # (session_uid, user_id) -> (setup_hash_bytes, setup_fields_tuple, telemetry_available)
        self._cached_setup: dict[tuple[str, int], tuple[bytes, tuple, bool]] = {}

    @staticmethod
    def _is_telemetry_available(fields: tuple) -> bool:
        return any(v != 0 for v in fields)

    def handle_car_setup_packet(self, packet, session_uid: str, user_map: dict[int, int]):
        """
        Cache every driver's setup from a Car Setup packet.
        Called at 2Hz. Loops all 22 car slots.
        """
        num_cars = len(packet.car_setups)

        for car_index, user_id in user_map.items():
            if car_index >= num_cars:
                continue

            setup = packet.car_setups[car_index]

            fields = (
                setup.front_wing, setup.rear_wing,
                setup.on_throttle, setup.off_throttle,
                setup.front_camber, setup.rear_camber,
                setup.front_toe, setup.rear_toe,
                setup.front_suspension, setup.rear_suspension,
                setup.front_anti_roll_bar, setup.rear_anti_roll_bar,
                setup.front_ride_height, setup.rear_ride_height,
                setup.brake_pressure, setup.brake_bias, setup.engine_braking,
                setup.front_left_tyre_pressure, setup.front_right_tyre_pressure,
                setup.rear_left_tyre_pressure, setup.rear_right_tyre_pressure,
                setup.ballast, setup.fuel_load,
            )

            packed = struct.pack(self._HASH_FORMAT, *fields)
            setup_hash = hashlib.sha256(packed).digest()
            telemetry_available = self._is_telemetry_available(fields)

            self._cached_setup[(session_uid, user_id)] = (setup_hash, fields, telemetry_available)

    def on_lap_complete(self, session_uid: str, user_id: int, lap_number: int, track_id: int):
        """
        Called when a lap is completed. Writes the cached setup to DB
        (deduplicated) and links the lap to it.
        """
        cached = self._cached_setup.get((session_uid, user_id))
        if cached is None:
            return

        setup_hash, fields, telemetry_available = cached

        # Restricted/blank setup (other players in MP, spectators): the
        # game sends an all-zeros setup that can never be a usable row —
        # skip persistence entirely rather than writing an unusable row.
        if not telemetry_available:
            return

        setup_id = self._car_setups_repo.upsert_setup(
            setup_hash, track_id, fields,
            user_id=user_id,
            session_uid=session_uid,
            telemetry_available=telemetry_available,
        )
        if setup_id is None:
            self._logger.warning(
                "Failed to get setup_id for session %s user %d lap %d",
                session_uid, user_id, lap_number,
            )
            return

        self._lap_setups_repo.insert_lap_setup(session_uid, user_id, lap_number, setup_id)
        self._logger.debug(
            "Linked lap %d to setup_id %d (session %s, user %d)",
            lap_number, setup_id, session_uid, user_id,
        )
