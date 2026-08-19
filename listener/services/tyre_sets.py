"""Tyre sets service — caches a car's available sets, writes a snapshot on lap completion."""

import logging
from typing import AbstractSet, Optional

from database.repositories.base import safe_enum_name
from database.repositories.tyre_sets import TyreSetsInventoryRepository
from enums import ActualTyreCompound, SessionTypeIDs, VisualTyreCompound
from utils.bounded_dict import BoundedDict


class TyreSetsService:
    """
    Handles Tyre Sets packets (Packet 12).

    The packet cycles one car at a time, so sets are cached per car and written
    as a snapshot when that driver completes a lap.

    The whole packet is withheld for a driver whose Your Telemetry setting is
    Restricted — it arrives zero-filled. Those cars are skipped explicitly
    rather than relying on the zeroes filtering themselves out, so no snapshot
    row can ever claim a restricted driver has no tyres left.
    """

    def __init__(
        self,
        tyre_sets_repo: TyreSetsInventoryRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._tyre_sets_repo = tyre_sets_repo
        self._logger = logger or logging.getLogger(__name__)
        # (session_uid, car_index) -> list of available set tuples
        self._cached_sets: BoundedDict[tuple, list] = BoundedDict(500)

    def handle_tyre_sets_packet(
        self,
        packet,
        user_map: dict[int, int],
        restricted_indices: Optional[AbstractSet[int]] = None,
    ):
        """Cache the available tyre sets for the car this packet describes."""
        session_uid = str(packet.header.session_uid)
        car_idx = packet.car_idx

        if car_idx not in user_map:
            return

        if restricted_indices and car_idx in restricted_indices:
            return

        available_sets = []
        for set_index, tyre_set in enumerate(packet.tyre_set_data):
            if tyre_set.available != 1:
                continue

            available_sets.append((
                set_index,
                safe_enum_name(ActualTyreCompound, tyre_set.actual_compound, self._logger),
                safe_enum_name(VisualTyreCompound, tyre_set.visual_compound, self._logger),
                tyre_set.wear,
                tyre_set.life_span,
                tyre_set.usable_life,
                safe_enum_name(SessionTypeIDs, tyre_set.recommended_session, self._logger),
                tyre_set.lap_delta_time,
                set_index == packet.fitted_idx,
            ))

        self._cached_sets[(session_uid, car_idx)] = available_sets

    def on_lap_complete(
        self,
        session_uid: str,
        user_id: int,
        car_index: int,
        lap_number: int,
    ):
        """Write the cached snapshot of available sets for a completed lap."""
        cached = self._cached_sets.get((session_uid, car_index))
        if not cached:
            return

        rows = [
            (session_uid, user_id, lap_number, *fields)
            for fields in cached
        ]

        if rows:
            self._tyre_sets_repo.insert_snapshot(rows)
            self._logger.debug(
                "Wrote %d tyre sets for user %d lap %d (session %s)",
                len(rows), user_id, lap_number, session_uid,
            )
