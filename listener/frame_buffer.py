"""Frame buffer for collecting car_frame packets (0, 2, 6, 7, 10) and flushing combined."""

import logging
import time
from typing import Any, Callable, Optional


class FrameBuffer:
    """
    Collects car_frame packets (0, 2, 6, 7, 10) by (session_uid, frame_identifier)
    and flushes them as a combined write when the next frame arrives.

    All other packet types are processed immediately by the dispatcher.
    """

    FLUSH_INTERVAL_MS = 100

    def __init__(
        self,
        flush_callback: Callable[[str, int, dict[int, Any]], None],
        logger: Optional[logging.Logger] = None,
    ):
        self._flush_callback = flush_callback
        self._logger = logger or logging.getLogger(__name__)
        # {session_uid: {frame_id: {packet_id: (header, body) or list[(header, body)]}}}
        self._frames: dict[str, dict[int, dict[int, Any]]] = {}
        # {session_uid: current_frame_id}
        self._current_frame: dict[str, int] = {}
        self._last_flush_time: float = time.monotonic()

    def add(self, session_uid: str, frame_identifier: int, packet_id: int, header, body: bytes):
        """
        Add a packet to the buffer.

        When a higher frame_identifier arrives for the same session, flushes the previous frame.
        """
        current = self._current_frame.get(session_uid)

        if current is not None and frame_identifier > current:
            self._flush_frame(session_uid, current)

        self._current_frame[session_uid] = frame_identifier

        if session_uid not in self._frames:
            self._frames[session_uid] = {}
        if frame_identifier not in self._frames[session_uid]:
            self._frames[session_uid][frame_identifier] = {}

        # Event packets (ID 3) can have multiple per frame — collect in a list
        if packet_id == 3:
            self._frames[session_uid][frame_identifier].setdefault(3, [])
            self._frames[session_uid][frame_identifier][3].append((header, body))
        else:
            self._frames[session_uid][frame_identifier][packet_id] = (header, body)

    def check_periodic_flush(self):
        """Flush stale frames if enough time has passed (for session-end scenarios)."""
        now = time.monotonic()
        if (now - self._last_flush_time) * 1000 < self.FLUSH_INTERVAL_MS:
            return

        self._last_flush_time = now

        stale = []
        for session_uid, frames in list(self._frames.items()):
            current = self._current_frame.get(session_uid)
            for frame_id in list(frames.keys()):
                if frame_id != current:
                    stale.append((session_uid, frame_id))

        for session_uid, frame_id in stale:
            self._flush_frame(session_uid, frame_id)

    def flush_session(self, session_uid: str):
        """Flush all pending frames for a session (used on session end)."""
        if session_uid not in self._frames:
            return

        for frame_id in sorted(self._frames[session_uid].keys()):
            self._flush_frame(session_uid, frame_id)

        self._frames.pop(session_uid, None)
        self._current_frame.pop(session_uid, None)

    def _flush_frame(self, session_uid: str, frame_id: int):
        """Flush a single frame's packets via the callback."""
        packets = self._frames.get(session_uid, {}).pop(frame_id, None)
        if not packets:
            return

        # Clean up empty session entry
        if session_uid in self._frames and not self._frames[session_uid]:
            del self._frames[session_uid]

        try:
            self._flush_callback(session_uid, frame_id, packets)
        except Exception as e:
            self._logger.error(
                f"Error flushing frame {frame_id} for session {session_uid}: {e}",
                exc_info=True,
            )
