"""Participants service for handling Participants packets (Packet 4)."""

import logging
from typing import Optional

from database.repositories import EntriesRepository
from utils.bounded_dict import BoundedDict

GENERIC_DRIVER_NAMES = {"player", ""}
EMPTY_SLOT_TEAM_ID = 255


class ParticipantsService:
    """
    Handles Participants packets (Packet 4).

    Only writes real human drivers to the entries table.
    Filters out AI drivers and empty lobby slots (team_id=255, race_number=0).
    Re-evaluates on every packet so mid-session joins are captured.
    """

    def __init__(
        self,
        entries_repo: EntriesRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._entries_repo = entries_repo
        self._logger = logger or logging.getLogger(__name__)
        # session_uid -> frozenset of human car_indices already written
        self._written_humans: BoundedDict = BoundedDict(200)
        self._user_map_cache: dict[str, dict[int, int]] = {}
        self._player_counter: int | None = None

    def _next_generic_name(self) -> str:
        """Generate the next sequential 'Player N' name, querying the DB on first call."""
        if self._player_counter is None:
            self._player_counter = self._entries_repo.max_player_number()
        self._player_counter += 1
        return f"Player {self._player_counter}"

    def handle_participants_packet(self, packet) -> dict[int, int]:
        """
        Process a Participants packet.

        Skips AI drivers entirely. Only inserts human players into entries.
        Re-evaluates every packet so humans joining mid-session are captured.

        Returns:
            car_index -> user_id mapping for human drivers in the session
        """
        session_uid = str(packet.header.session_uid)

        # Build list of real human drivers (skip AI and empty lobby slots)
        human_entries = []
        for i, participant in enumerate(packet.participants):
            if participant.ai_controlled:
                continue
            if participant.team_id == EMPTY_SLOT_TEAM_ID and participant.race_number == 0:
                continue

            driver_name = participant.name.replace("\x00", "").strip() if participant.name else ""
            if driver_name.lower() in GENERIC_DRIVER_NAMES:
                weekend_name = self._entries_repo.find_weekend_driver_name(
                    session_uid, participant.team_id, participant.race_number,
                )
                driver_name = weekend_name if weekend_name else self._next_generic_name()

            num_colours = getattr(participant, 'num_colours', 4)
            livery_colors = []
            for color_idx in range(min(num_colours, 4)):
                color_tuple = participant.livery_colours[color_idx]
                livery_colors.extend(color_tuple)

            human_entries.append({
                "session_uid": session_uid,
                "car_index": i,
                "driver_name": driver_name,
                "team_id": participant.team_id,
                "race_number": participant.race_number,
                "nationality": participant.nationality,
                "telemetry_setting": bool(participant.your_telemetry),
                "livery_colors": livery_colors,
            })

        current_humans = frozenset(e["car_index"] for e in human_entries)
        written = self._written_humans.get(session_uid, frozenset())

        # Fast path: same set of humans already written
        if current_humans == written:
            return self._user_map_cache.get(session_uid, {})

        # Find new humans that haven't been written yet
        new_entries = [e for e in human_entries if e["car_index"] not in written]

        if not new_entries:
            return self._user_map_cache.get(session_uid, {})

        self._logger.info(
            "Session %s: new human driver(s) detected: %s",
            session_uid,
            [e["driver_name"] for e in new_entries],
        )

        try:
            new_mappings = self._entries_repo.insert_entries_batch(new_entries)
            user_map = self._user_map_cache.get(session_uid, {})
            user_map = {**user_map, **new_mappings}
            self._user_map_cache[session_uid] = user_map
            if len(self._user_map_cache) > 100:
                oldest = next(iter(self._user_map_cache))
                del self._user_map_cache[oldest]
            self._written_humans[session_uid] = current_humans
            return user_map
        except Exception as e:
            self._logger.error(f"Failed to insert entries: {e}", exc_info=True)
            return self._user_map_cache.get(session_uid, {})
