"""Tyre sets service — caches available tyre sets per car, writes on lap completion."""

import logging
from typing import Optional

from database.repositories.base import safe_enum_name
from database.repositories.tyre_sets import TyreSetsInventoryRepository
from enums import ActualTyreCompound, VisualTyreCompound
from utils.bounded_dict import BoundedDict


class TyreSetsService:
    """
    Handles Tyre Sets packets (Packet 12).

    Caches available tyre sets per car in memory. On lap completion,
    writes a snapshot of all available sets for that driver.
    """

    def __init__(
        self,
        tyre_sets_repo: TyreSetsInventoryRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._tyre_sets_repo = tyre_sets_repo
        self._logger = logger or logging.getLogger(__name__)
        # (session_uid, car_index) -> list of available set tuples
        self._cached_sets: BoundedDict = BoundedDict(500)

    def handle_tyre_sets_packet(self, packet, user_map: dict[int, int]):
        """
        Cache available tyre sets from a Tyre Sets packet.
        Called at 20Hz cycling through cars. Only caches sets where available == 1.
        """
        session_uid = str(packet.header.session_uid)
        car_idx = packet.car_idx

        if car_idx not in user_map:
            return

        available_sets = []
        for tyre_set in packet.tyre_set_data:
            if tyre_set.available != 1:
                continue

            actual = safe_enum_name(ActualTyreCompound, tyre_set.actual_compound, self._logger)
            visual = safe_enum_name(VisualTyreCompound, tyre_set.visual_compound, self._logger)

            available_sets.append((
                actual,
                visual,
                tyre_set.wear,
                tyre_set.life_span,
                tyre_set.usable_life,
                tyre_set.lap_delta_time,
                bool(tyre_set.fitted),
            ))

        self._cached_sets[(session_uid, car_idx)] = available_sets

    def on_lap_complete(
        self,
        session_uid: str,
        user_id: int,
        car_index: int,
        lap_number: int,
    ):
        """
        Called when a lap is completed. Writes the cached available tyre sets
        snapshot to the database.
        """
        cached = self._cached_sets.get((session_uid, car_index))
        if not cached:
            return

        rows = []
        for actual, visual, wear, life_span, usable_life, delta, fitted in cached:
            rows.append((
                session_uid, user_id, lap_number,
                actual, visual, wear, life_span, usable_life, delta, fitted,
            ))

        if rows:
            self._tyre_sets_repo.insert_snapshot(rows)
            self._logger.debug(
                "Wrote %d tyre sets for user %d lap %d (session %s)",
                len(rows), user_id, lap_number, session_uid,
            )
