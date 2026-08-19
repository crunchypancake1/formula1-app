"""Car setup service — caches setups, writes them on lap completion."""

import hashlib
import logging
import struct
from typing import Optional

from database.repositories.car_setups import CarSetupsRepository
from database.repositories.lap_setups import LapSetupsRepository
from utils.bounded_dict import BoundedDict


class CarSetupService:
    """
    Handles Car Setup packets (Packet 5).

    Online you only ever receive your own setup: other players' entries arrive
    as all zeroes regardless of their telemetry setting, and spectators get
    none at all. A blank setup is therefore never persisted — a row of zeroes
    would read as a real (and absurd) setup rather than as missing data.

    Real setups are deduplicated into a library by hash + track + driver, and
    each completed lap is linked to the setup it was driven on.
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
        # (session_uid, user_id) -> (setup_hash, setup_fields, next_front_wing_value)
        self._cached_setup: BoundedDict[tuple[str, int], tuple] = BoundedDict(500)

    @staticmethod
    def _is_real_setup(fields: tuple) -> bool:
        """An all-zero setup is the game withholding data, not a setup."""
        return any(v != 0 for v in fields)

    def handle_car_setup_packet(self, packet, session_uid: str, user_map: dict[int, int]):
        """Cache each known driver's setup from a Car Setup packet."""
        num_cars = len(packet.car_setups)
        player_index = packet.header.player_car_index

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

            if not self._is_real_setup(fields):
                continue

            setup_hash = hashlib.sha256(struct.pack(self._HASH_FORMAT, *fields)).digest()

            # m_nextFrontWingValue is packet-level and describes the local
            # player only, so it is meaningless for anyone else.
            next_front_wing = (
                packet.next_front_wing_value if car_index == player_index else None
            )

            self._cached_setup[(session_uid, user_id)] = (setup_hash, fields, next_front_wing)

    def on_lap_complete(self, session_uid: str, user_id: int, lap_number: int, track_id: int):
        """Persist the cached setup (deduplicated) and link the completed lap to it."""
        cached = self._cached_setup.get((session_uid, user_id))
        if cached is None:
            return

        setup_hash, fields, next_front_wing = cached

        setup_id = self._car_setups_repo.upsert_setup(
            setup_hash, track_id, fields,
            user_id=user_id,
            session_uid=session_uid,
        )
        if setup_id is None:
            self._logger.warning(
                "Failed to get setup_id for session %s user %d lap %d",
                session_uid, user_id, lap_number,
            )
            return

        self._lap_setups_repo.insert_lap_setup(
            session_uid, user_id, lap_number, setup_id, next_front_wing
        )
        self._logger.debug(
            "Linked lap %d to setup_id %d (session %s, user %d)",
            lap_number, setup_id, session_uid, user_id,
        )
