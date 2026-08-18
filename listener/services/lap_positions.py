"""Lap positions service for handling Lap Positions packets (Packet 15)."""

import logging
from typing import Optional

from database.repositories import LapPositionsRepository
from packets.constants import MAX_CARS


class LapPositionsService:
    """
    Handles Lap Positions packets (Packet 15).

    Writes to lap_positions table. Translates car_index positions to user_id positions.
    The positions array stores user_ids indexed by position.
    """

    def __init__(
        self,
        lap_positions_repo: LapPositionsRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._lap_positions_repo = lap_positions_repo
        self._logger = logger or logging.getLogger(__name__)

    def handle_lap_positions_packet(self, packet, user_map: dict[int, int]):
        """
        Process a Lap Positions packet.

        Args:
            packet: LapPositionsPacket from packets.unpack_lap_positions()
            user_map: car_index -> user_id mapping for the session
        """
        session_uid = str(packet.header.session_uid)

        for lap_index in range(packet.num_laps):
            actual_lap_number = packet.lap_start + lap_index + 1

            # Build positions array indexed by position: positions[pos-1] = user_id
            # The game gives positions[car_index] = position, we invert to position -> user_id
            positions_array = [0] * MAX_CARS
            for car_index in range(MAX_CARS):
                position = packet.positions[lap_index][car_index]
                if position == 0:
                    continue
                user_id = user_map.get(car_index)
                if user_id is None:
                    continue
                positions_array[position - 1] = user_id

            # Trim trailing zeros
            while positions_array and positions_array[-1] == 0:
                positions_array.pop()

            try:
                self._lap_positions_repo.upsert_lap_positions(
                    session_uid=session_uid,
                    lap_number=actual_lap_number,
                    positions=positions_array,
                )
            except Exception as e:
                self._logger.error(
                    f"Failed to upsert lap positions for lap {actual_lap_number}: {e}",
                    exc_info=True,
                )
