import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
from dataclasses import dataclass

from frame_buffer import FrameBuffer


@dataclass
class FakeHeader:
    session_time: float = 10.0


class TestFrameBuffer:
    def test_add_stores_packet(self):
        calls = []
        buf = FrameBuffer(flush_callback=lambda s, f, p: calls.append((s, f, p)))
        buf.add(session_uid="S1", frame_identifier=1, packet_id=0, header=FakeHeader(), body=b'\x00')
        assert len(calls) == 0

    def test_new_frame_flushes_previous(self):
        calls = []
        buf = FrameBuffer(flush_callback=lambda s, f, p: calls.append((s, f, p)))
        buf.add(session_uid="S1", frame_identifier=1, packet_id=0, header=FakeHeader(), body=b'\x00')
        buf.add(session_uid="S1", frame_identifier=2, packet_id=0, header=FakeHeader(), body=b'\x01')
        assert len(calls) == 1
        session_uid, frame_id, packets = calls[0]
        assert session_uid == "S1"
        assert frame_id == 1
        assert 0 in packets

    def test_flush_session_flushes_all(self):
        calls = []
        buf = FrameBuffer(flush_callback=lambda s, f, p: calls.append((s, f, p)))
        buf.add(session_uid="S1", frame_identifier=1, packet_id=0, header=FakeHeader(), body=b'\x00')
        buf.add(session_uid="S1", frame_identifier=2, packet_id=0, header=FakeHeader(), body=b'\x01')
        # Frame 1 already flushed by frame 2 arrival; flush_session flushes frame 2
        calls.clear()
        buf.flush_session("S1")
        assert len(calls) == 1
        assert calls[0][1] == 2

    def test_flush_session_unknown_session_noop(self):
        calls = []
        buf = FrameBuffer(flush_callback=lambda s, f, p: calls.append((s, f, p)))
        buf.flush_session("UNKNOWN")
        assert len(calls) == 0

    def test_callback_error_caught(self):
        def bad_callback(_s, _f, _p):
            raise RuntimeError("boom")

        buf = FrameBuffer(flush_callback=bad_callback)
        buf.add(session_uid="S1", frame_identifier=1, packet_id=0, header=FakeHeader(), body=b'\x00')
        # Adding frame 2 triggers flush of frame 1 — callback raises, but should not crash
        buf.add(session_uid="S1", frame_identifier=2, packet_id=0, header=FakeHeader(), body=b'\x01')

    def test_flush_combines_packet_types(self):
        calls = []
        buf = FrameBuffer(flush_callback=lambda s, f, p: calls.append((s, f, p)))
        buf.add(session_uid="S1", frame_identifier=1, packet_id=0, header=FakeHeader(), body=b'\x00')
        buf.add(session_uid="S1", frame_identifier=1, packet_id=6, header=FakeHeader(), body=b'\x06')
        # Trigger flush by advancing frame
        buf.add(session_uid="S1", frame_identifier=2, packet_id=0, header=FakeHeader(), body=b'\x10')
        assert len(calls) == 1
        packets = calls[0][2]
        assert 0 in packets
        assert 6 in packets

    def test_periodic_flush_flushes_stale(self):
        calls = []
        buf = FrameBuffer(flush_callback=lambda s, f, p: calls.append((s, f, p)))
        buf.add(session_uid="S1", frame_identifier=1, packet_id=0, header=FakeHeader(), body=b'\x00')
        # Frame 1 is the current frame, so periodic flush won't touch it.
        # Advance to frame 2 so frame 1 becomes non-current but NOT yet flushed via new-frame path.
        # Actually, adding frame 2 will flush frame 1 via the normal path.
        # Instead: directly manipulate the buffer to have a stale (non-current) frame.
        buf._frames["S1"] = {1: {0: (FakeHeader(), b'\x00')}}
        buf._current_frame["S1"] = 2
        buf._last_flush_time = time.monotonic() - 1.0  # well past FLUSH_INTERVAL_MS
        buf.check_periodic_flush()
        assert len(calls) == 1
        assert calls[0][1] == 1

    def test_empty_flush_noop(self):
        calls = []
        buf = FrameBuffer(flush_callback=lambda s, f, p: calls.append((s, f, p)))
        buf.flush_session("S1")
        assert len(calls) == 0
