"""Groups the packets describing one simulation tick so they become a single car_frame row."""

import logging
import time
from typing import Any, Callable, Optional

from utils.bounded_dict import BoundedDict


class FrameBuffer:
    """
    Collects car_frame packets (0, 2, 6, 7, 10, 16) by (session_uid, frame_identifier).

    A frame is flushed when the next frame arrives for that session, when the
    session ends, or by the periodic stale-frame sweep. Every other packet type
    is processed immediately by the dispatcher.
    """

    FLUSH_INTERVAL_MS = 100

    # Sessions tracked concurrently. Bounded so a session that never sends its
    # SEND event cannot pin its frames in memory forever.
    MAX_SESSIONS = 20

    def __init__(
        self,
        flush_callback: Callable[[str, int, dict[int, Any]], None],
        logger: Optional[logging.Logger] = None,
    ):
        self._flush_callback = flush_callback
        self._logger = logger or logging.getLogger(__name__)
        # session_uid -> {frame_id: {packet_id: (header, body)}}
        self._frames: BoundedDict[str, dict[int, dict[int, Any]]] = BoundedDict(self.MAX_SESSIONS)
        # session_uid -> current frame_id
        self._current_frame: BoundedDict[str, int] = BoundedDict(self.MAX_SESSIONS)
        self._last_flush_time: float = time.monotonic()

    def add(self, session_uid: str, frame_identifier: int, packet_id: int, header, body: bytes):
        """
        Add a packet to the buffer.

        When a higher frame_identifier arrives for the same session, the
        previous frame is complete and gets flushed.
        """
        current = self._current_frame.get(session_uid)

        if current is not None and frame_identifier > current:
            self._flush_frame(session_uid, current)

        self._current_frame[session_uid] = frame_identifier

        session_frames = self._frames.get(session_uid)
        if session_frames is None:
            session_frames = {}
            self._frames[session_uid] = session_frames
        session_frames.setdefault(frame_identifier, {})[packet_id] = (header, body)

    def check_periodic_flush(self):
        """Flush frames left behind by a session that stopped sending."""
        now = time.monotonic()
        if (now - self._last_flush_time) * 1000 < self.FLUSH_INTERVAL_MS:
            return

        self._last_flush_time = now

        stale = []
        for session_uid in self._frames.keys():
            current = self._current_frame.get(session_uid)
            frames = self._frames.get(session_uid) or {}
            for frame_id in list(frames.keys()):
                if frame_id != current:
                    stale.append((session_uid, frame_id))

        for session_uid, frame_id in stale:
            self._flush_frame(session_uid, frame_id)

    def flush_session(self, session_uid: str):
        """Flush every pending frame for a session, in order (used on session end)."""
        frames = self._frames.get(session_uid)
        if frames is None:
            return

        for frame_id in sorted(frames.keys()):
            self._flush_frame(session_uid, frame_id)

        self._frames.pop(session_uid)
        self._current_frame.pop(session_uid)

    def discard_session(self, session_uid: str):
        """
        Drop a session's pending frames without writing them.

        Used on a flashback: those frames describe a run the driver has just
        undone, so writing them would record telemetry for something that no
        longer happened.
        """
        self._frames.pop(session_uid)
        self._current_frame.pop(session_uid)

    def _flush_frame(self, session_uid: str, frame_id: int):
        """Flush a single frame's packets via the callback."""
        frames = self._frames.get(session_uid)
        if frames is None:
            return
        packets = frames.pop(frame_id, None)
        if not packets:
            return

        if not frames:
            self._frames.pop(session_uid)

        try:
            self._flush_callback(session_uid, frame_id, packets)
        except Exception as e:
            self._logger.error(
                f"Error flushing frame {frame_id} for session {session_uid}: {e}",
                exc_info=True,
            )
