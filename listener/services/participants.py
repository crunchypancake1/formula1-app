"""Participants service for handling Participants packets (Packet 4)."""

import logging
from typing import Optional

from database.repositories import EntriesRepository
from utils.bounded_dict import BoundedDict

GENERIC_DRIVER_NAMES = {"player", ""}

# m_teamId sentinel for a lobby slot with no team selected (uint16 in F1 26).
EMPTY_SLOT_TEAM_ID = 65535


class ParticipantsService:
    """
    Handles Participants packets (Packet 4).

    Only writes real human drivers to the entries table; AI drivers and empty
    lobby slots are skipped. Re-evaluates on every packet so drivers joining
    mid-session are captured.
    """

    def __init__(
        self,
        entries_repo: EntriesRepository,
        logger: Optional[logging.Logger] = None,
    ):
        self._entries_repo = entries_repo
        self._logger = logger or logging.getLogger(__name__)
        # session_uid -> frozenset of human car_indices confirmed written
        self._written_humans: BoundedDict[str, frozenset[int]] = BoundedDict(200)
        self._user_map_cache: BoundedDict[str, dict[int, int]] = BoundedDict(200)
        self._player_counter: int | None = None
        # session_uid -> frozenset of car_indices with your_telemetry == 0
        # (Restricted), excluding the local player's own car. Rebuilt on every
        # Participants packet, since a driver can change the setting mid-session.
        self._restricted_indices: BoundedDict[str, frozenset[int]] = BoundedDict(200)

    def get_restricted_indices(self, session_uid: str) -> frozenset[int]:
        """Car indices currently Restricted (your_telemetry == 0) for a session."""
        return self._restricted_indices.get(session_uid) or frozenset()

    def get_user_map(self, session_uid: str) -> dict[int, int]:
        """The confirmed car_index -> user_id mapping for a session."""
        return self._user_map_cache.get(session_uid) or {}

    def _next_generic_name(self) -> str:
        """Generate the next sequential 'Player N' name, querying the DB on first call."""
        if self._player_counter is None:
            self._player_counter = self._entries_repo.max_player_number()
        self._player_counter += 1
        return f"Player {self._player_counter}"

    def handle_participants_packet(self, packet) -> dict[int, int]:
        """
        Process a Participants packet.

        Returns:
            car_index -> user_id mapping for the human drivers whose entries
            rows are known to exist.
        """
        session_uid = str(packet.header.session_uid)

        # The local player always sees their own car in full, whatever their own
        # telemetry setting says, so exclude it from the restricted set.
        self._restricted_indices[session_uid] = frozenset(
            i for i, p in enumerate(packet.participants) if p.your_telemetry == 0
        ) - {packet.header.player_car_index}

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

            num_colours = min(participant.num_colours, 4)
            livery_colors = []
            for color_idx in range(num_colours):
                livery_colors.extend(participant.livery_colours[color_idx])

            human_entries.append({
                "session_uid": session_uid,
                "car_index": i,
                "driver_name": driver_name,
                "team_id": participant.team_id,
                "race_number": participant.race_number,
                "nationality": participant.nationality,
                "driver_id": participant.driver_id,
                "network_id": participant.network_id,
                "my_team": bool(participant.my_team),
                "platform": participant.platform,
                "tech_level": participant.tech_level,
                "show_online_names": bool(participant.show_online_names),
                "telemetry_public": bool(participant.your_telemetry),
                "num_livery_colors": num_colours,
                "livery_colors": livery_colors,
            })

        current_humans = frozenset(e["car_index"] for e in human_entries)
        written = self._written_humans.get(session_uid) or frozenset()

        # Fast path: every human on track already has a confirmed entries row.
        if current_humans == written:
            return self.get_user_map(session_uid)

        new_entries = [e for e in human_entries if e["car_index"] not in written]
        if not new_entries:
            return self.get_user_map(session_uid)

        self._logger.info(
            "Session %s: new human driver(s) detected: %s",
            session_uid,
            [e["driver_name"] for e in new_entries],
        )

        new_mappings = self._entries_repo.insert_entries_batch(new_entries)
        if not new_mappings:
            # The write failed. Leave _written_humans alone so the next
            # Participants packet retries instead of running the whole session
            # against a roster that was never recorded.
            self._logger.warning(
                "Session %s: entries write failed for %d driver(s) — will retry",
                session_uid, len(new_entries),
            )
            return self.get_user_map(session_uid)

        user_map = {**self.get_user_map(session_uid), **new_mappings}
        self._user_map_cache[session_uid] = user_map
        self._written_humans[session_uid] = written | frozenset(new_mappings)
        return user_map
