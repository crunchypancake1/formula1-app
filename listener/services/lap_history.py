"""Lap history service for handling Session History packets (Packet 11)."""

import logging
from typing import Optional

from database.repositories import LapsRepository, TyreStintsRepository
from database.repositories.base import safe_enum_name
from enums import ActualTyreCompound, VisualTyreCompound
from utils.bounded_dict import BoundedDict


class LapHistoryService:
    """
    Handles Session History packets (Packet 11).

    Writes to:
    - laps table (one record per lap)

    Uses user_id (resolved from user_map) instead of car_index.
    """

    def __init__(
        self,
        laps_repo: LapsRepository,
        tyre_stints_repo: TyreStintsRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._laps_repo = laps_repo
        self._tyre_stints_repo = tyre_stints_repo
        self._logger = logger or logging.getLogger(__name__)
        self._last_num_laps: BoundedDict[tuple, int] = BoundedDict(500)
        self._warned_car_indices: BoundedDict[tuple, bool] = BoundedDict(50)

    def handle_session_history_packet(self, packet, user_map: dict[int, int]):
        """
        Process lap data from a Session History packet.

        Tyre stints are NOT written here — they are handled separately by
        handle_tyre_stints() which is only called after final classification.
        """
        session_uid = str(packet.header.session_uid)
        car_index = packet.car_index
        user_id = user_map.get(car_index)
        if user_id is None:
            warn_key = (session_uid, car_index)
            if warn_key not in self._warned_car_indices:
                self._warned_car_indices[warn_key] = True
                self._logger.debug(
                    "Skipping car_index %d for session history (not in user_map, likely AI)",
                    car_index,
                )
            return

        self._upsert_laps(session_uid, user_id, packet)

    def handle_tyre_stints(self, packet, user_map: dict[int, int]):
        """
        Process tyre stint data from the post-classification bulk Session History update.

        Called only after final classification has been received for the session.
        """
        session_uid = str(packet.header.session_uid)
        car_index = packet.car_index
        user_id = user_map.get(car_index)
        if user_id is None:
            return

        self._upsert_tyre_stints(session_uid, user_id, packet)

    def _upsert_laps(self, session_uid: str, user_id: int, packet):
        """Upsert lap records from lap_history_list (incremental, batched)."""
        user_key = (session_uid, user_id)
        last_num_laps: int = self._last_num_laps.get(user_key, 0) or 0
        current_num_laps = packet.num_laps

        start_index = max(0, last_num_laps - 1)

        batch = []
        for lap_num, lap_history in enumerate(
            packet.lap_history_list[start_index:current_num_laps],
            start=start_index + 1,
        ):
            if lap_history.lap_time_in_ms == 0:
                continue

            try:
                sector1_time_ms = (lap_history.sector_1_time_minutes_part * 60000 +
                                   lap_history.sector_1_time_ms_part) if (lap_history.sector_1_time_ms_part > 0 or lap_history.sector_1_time_minutes_part > 0) else None
                sector2_time_ms = (lap_history.sector_2_time_minutes_part * 60000 +
                                   lap_history.sector_2_time_ms_part) if (lap_history.sector_2_time_ms_part > 0 or lap_history.sector_2_time_minutes_part > 0) else None
                sector3_time_ms = (lap_history.sector_3_time_minutes_part * 60000 +
                                   lap_history.sector_3_time_ms_part) if (lap_history.sector_3_time_ms_part > 0 or lap_history.sector_3_time_minutes_part > 0) else None

                is_valid = (lap_history.lap_valid_bit_flags & 0x01) == 0x01
                sector1_valid = (lap_history.lap_valid_bit_flags & 0x02) == 0x02
                sector2_valid = (lap_history.lap_valid_bit_flags & 0x04) == 0x04
                sector3_valid = (lap_history.lap_valid_bit_flags & 0x08) == 0x08

                batch.append((
                    session_uid,
                    user_id,
                    lap_num,
                    lap_history.lap_time_in_ms if lap_history.lap_time_in_ms > 0 else None,
                    sector1_time_ms,
                    sector2_time_ms,
                    sector3_time_ms,
                    is_valid,
                    sector1_valid,
                    sector2_valid,
                    sector3_valid,
                ))
            except Exception as e:
                self._logger.error(
                    f"Failed to build lap {lap_num} for user {user_id}: {e}",
                    exc_info=True,
                )

        if batch:
            self._laps_repo.upsert_laps_batch(batch)

        self._last_num_laps[user_key] = current_num_laps

    def _upsert_tyre_stints(self, session_uid: str, user_id: int, packet):
        """Upsert tyre stint records from tyre_stints_list."""
        batch = []
        for stint_idx, stint in enumerate(packet.tyre_stints_list[:packet.num_tyre_stints]):
            if stint.tyre_actual_compound == 0:
                continue

            actual = safe_enum_name(ActualTyreCompound, stint.tyre_actual_compound, self._logger)
            visual = safe_enum_name(VisualTyreCompound, stint.tyre_visual_compound, self._logger)

            batch.append((
                session_uid,
                user_id,
                stint_idx,
                stint.end_lap if stint.end_lap != 255 else None,
                actual,
                visual,
            ))

        if batch:
            self._tyre_stints_repo.upsert_stints_batch(batch)
