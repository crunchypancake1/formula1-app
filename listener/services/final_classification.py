"""Final classification service for handling Final Classification packets (Packet 8)."""

import json
import logging
import os
import time
from typing import Optional

from database.repositories import FinalClassificationRepository
from enums.session_types import SessionTypeIDs
from utils.bounded_set import BoundedSet

# Session types that are races (including sprints)
RACE_SESSION_TYPES = {
    SessionTypeIDs.RACE.value,
    SessionTypeIDs.RACE_2.value,
    SessionTypeIDs.RACE_3.value,
    SessionTypeIDs.SPRINT_RACE.value,
}


class FinalClassificationService:
    """
    Handles Final Classification packets (Packet 8).

    Writes to race_classification or qualifying_classification table based on session type,
    then closes the session. Falls back to dead-letter queue on DB failure.
    Uses user_id (resolved from user_map) instead of car_index.
    """

    def __init__(
        self,
        final_classification_repo: FinalClassificationRepository,
        session_service,
        logger: Optional[logging.Logger] = None,
        dead_letter_dir: Optional[str] = None,
    ):
        self._final_classification_repo = final_classification_repo
        self._session_service = session_service
        self._logger = logger or logging.getLogger(__name__)
        self._processed_sessions = BoundedSet(max_size=100)
        self._dead_letter_dir = dead_letter_dir

    def handle_final_classification_packet(self, packet, user_map: dict[int, int]):
        """
        Process a Final Classification packet.

        Args:
            packet: FinalClassificationPacket from packets.unpack_final_classification()
            user_map: car_index -> user_id mapping for the session
        """
        session_uid = str(packet.header.session_uid)

        status_counts = {}
        for fc in packet.final_classifications:
            status_counts[fc.result_status] = status_counts.get(fc.result_status, 0) + 1
        self._logger.info(
            f"Session {session_uid}: FinalClassification packet received, "
            f"result_status distribution: {status_counts}"
        )

        if session_uid in self._processed_sessions:
            self._logger.debug(
                f"Session {session_uid}: Ignoring duplicate Final Classification packet"
            )
            return

        session_type = self._session_service.get_session_type(session_uid)
        if session_type is None:
            self._logger.error(
                f"Session {session_uid}: Session type unknown, cannot process final classification"
            )
            return

        is_race = session_type in RACE_SESSION_TYPES

        classifications = []
        for car_index, fc in enumerate(packet.final_classifications):
            if fc.result_status == 0:
                continue

            user_id = user_map.get(car_index)
            if user_id is None:
                self._logger.warning(
                    f"Session {session_uid}: Cannot resolve car_index {car_index} to user_id for classification"
                )
                continue

            classification = {
                "session_uid": session_uid,
                "user_id": user_id,
                "position": fc.position,
                "num_laps": fc.num_of_laps,
                "result_status": fc.result_status,
                "result_reason": fc.result_reason,
                "best_lap_time_ms": fc.best_lap_time_in_ms if fc.best_lap_time_in_ms > 0 else None,
                # What the game itself awarded. League points are derived from
                # position separately; this is kept as the raw record.
                "game_points": fc.points,
                "penalties_time": fc.penalties_time if fc.penalties_time != 255 else 0,
                "num_penalties": fc.num_of_penalties,
            }

            if is_race:
                num_stints = fc.num_of_tyre_stints
                end_laps = [
                    lap if lap != 255 else None
                    for lap in fc.tyre_stints_end_laps[:num_stints]
                ]
                classification.update({
                    "grid_position": fc.grid_position,
                    "num_pit_stops": fc.num_pit_stops,
                    "total_race_time": fc.total_race_time,
                    "num_tyre_stints": num_stints,
                    "tyre_stints_actual": fc.tyre_stints_actual[:num_stints],
                    "tyre_stints_visual": fc.tyre_stints_visual[:num_stints],
                    "tyre_stints_end_laps": end_laps,
                })

            classifications.append(classification)

        if not classifications:
            self._processed_sessions.add(session_uid)
            return

        try:
            if is_race:
                self._final_classification_repo.insert_race_classification_batch(classifications)
                self._logger.info(
                    f"Session {session_uid}: Inserted {len(classifications)} race classification records"
                )
            else:
                self._final_classification_repo.insert_qualifying_classification_batch(classifications)
                self._logger.info(
                    f"Session {session_uid}: Inserted {len(classifications)} qualifying classification records"
                )
        except Exception as e:
            self._logger.error(
                f"Session {session_uid}: DB write failed, writing dead letter: {e}",
                exc_info=True,
            )
            self._write_dead_letter(session_uid, classifications, is_race)
            return

        self._logger.info(f"Session {session_uid} completed (Final Classification received)")
        self._processed_sessions.add(session_uid)

    def _write_dead_letter(self, session_uid: str, classifications: list, is_race: bool):
        if not self._dead_letter_dir:
            self._logger.error("No dead-letter directory configured, data lost for session %s", session_uid)
            return

        try:
            os.makedirs(self._dead_letter_dir, exist_ok=True)
            filename = f"{session_uid}_{int(time.time())}.json"
            filepath = os.path.join(self._dead_letter_dir, filename)
            with open(filepath, "w") as f:
                json.dump({
                    "session_uid": session_uid,
                    "classifications": classifications,
                    "is_race": is_race
                }, f)
            self._logger.info("Dead letter written: %s", filepath)
        except Exception as e:
            self._logger.error("Failed to write dead letter for session %s: %s", session_uid, e)

    def replay_dead_letters(self):
        if not self._dead_letter_dir or not os.path.isdir(self._dead_letter_dir):
            return

        files = sorted(f for f in os.listdir(self._dead_letter_dir) if f.endswith(".json"))
        if not files:
            return

        self._logger.info("Replaying %d dead-letter file(s)", len(files))
        for filename in files:
            filepath = os.path.join(self._dead_letter_dir, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                is_race = data["is_race"]
                if is_race:
                    self._final_classification_repo.insert_race_classification_batch(data["classifications"])
                else:
                    self._final_classification_repo.insert_qualifying_classification_batch(data["classifications"])

                session_uid = data["session_uid"]
                os.remove(filepath)
                self._logger.info("Replayed dead letter: %s (session %s)", filename, session_uid)
            except Exception as e:
                self._logger.error("Failed to replay dead letter %s: %s", filename, e)
