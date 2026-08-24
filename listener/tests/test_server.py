"""Tests for the UDP receive loop (server.py)."""

import logging
import queue
import socket
import threading
import time

import pytest

from server import (
    _configure_receive_buffer,
    _kernel_rcvbuf_errors,
    _process_packets,
    start_udp_server,
)

logger = logging.getLogger("test")


def _free_udp_port() -> int:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class TestProcessPackets:
    def test_hands_every_packet_to_the_handler_in_order(self):
        seen = []
        packets: queue.Queue = queue.Queue()
        for i in range(5):
            packets.put(bytes([i]))
        packets.put(None)

        _process_packets(packets, seen.append, logger)

        assert seen == [bytes([i]) for i in range(5)]

    def test_a_failing_handler_does_not_stop_the_worker(self):
        seen = []

        def handler(data: bytes):
            if data == b"boom":
                raise ValueError("handler exploded")
            seen.append(data)

        packets: queue.Queue = queue.Queue()
        for item in (b"a", b"boom", b"b", None):
            packets.put(item)

        _process_packets(packets, handler, logger)

        assert seen == [b"a", b"b"]


class TestKernelRcvbufErrors:
    def test_reads_the_counter_without_raising(self):
        # Linux exposes /proc/net/snmp; elsewhere the helper degrades to 0.
        assert _kernel_rcvbuf_errors() >= 0

    def test_parses_the_column_by_name(self, tmp_path, monkeypatch):
        snmp = tmp_path / "snmp"
        snmp.write_text(
            "Ip: Forwarding DefaultTTL\nIp: 2 64\n"
            "Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors\n"
            "Udp: 100 1 2 3 4242\n"
        )
        real_open = open
        monkeypatch.setattr(
            "builtins.open",
            lambda path, *a, **kw: real_open(snmp, *a, **kw)
            if path == "/proc/net/snmp"
            else real_open(path, *a, **kw),
        )

        assert _kernel_rcvbuf_errors() == 4242


class TestConfigureReceiveBuffer:
    def test_returns_the_granted_size(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            granted = _configure_receive_buffer(sock, logger)
        finally:
            sock.close()

        # The kernel caps the request at net.core.rmem_max rather than failing.
        assert granted > 0


class TestStartUdpServer:
    @pytest.fixture
    def running_server(self):
        received: list[bytes] = []
        gate = threading.Event()
        port = _free_udp_port()

        def handler(data: bytes):
            gate.wait(timeout=5.0)
            received.append(data)

        thread = threading.Thread(
            target=start_udp_server,
            args=("127.0.0.1", port, handler, logger),
            daemon=True,
        )
        thread.start()
        time.sleep(0.2)  # let the socket bind before anything is sent

        yield port, received, gate
        gate.set()

    def test_delivers_received_packets_to_the_handler(self, running_server):
        port, received, gate = running_server
        gate.set()

        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(20):
            client.sendto(bytes([i]) * 100, ("127.0.0.1", port))
        client.close()

        assert _wait_for(lambda: len(received) == 20)

    def test_keeps_receiving_while_the_handler_is_blocked(self, running_server):
        """A stalled write must delay packets, not lose them to the socket."""
        port, received, gate = running_server

        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(50):
            client.sendto(bytes([i % 256]) * 200, ("127.0.0.1", port))
        client.close()

        # The handler is still blocked on the gate, so nothing has been processed
        # yet — but the receive loop has taken all 50 off the socket.
        time.sleep(0.3)
        assert received == []

        gate.set()
        assert _wait_for(lambda: len(received) == 50)


class TestQueueOverflow:
    def test_drops_rather_than_blocking_when_the_queue_is_full(self):
        """Once the backlog is full the receive loop sheds packets and keeps going."""
        port = _free_udp_port()
        gate = threading.Event()
        received: list[bytes] = []

        def handler(data: bytes):
            gate.wait(timeout=5.0)
            received.append(data)

        thread = threading.Thread(
            target=start_udp_server,
            args=("127.0.0.1", port, handler, logger),
            kwargs={"queue_size": 4},
            daemon=True,
        )
        thread.start()
        time.sleep(0.2)

        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for i in range(40):
                client.sendto(bytes([i % 256]) * 100, ("127.0.0.1", port))
            client.close()

            time.sleep(0.3)
            gate.set()

            # Far fewer than 40 survive, but the loop never wedged: it is still
            # alive and delivering what did fit.
            assert _wait_for(lambda: len(received) > 0)
            assert len(received) <= 6
            assert thread.is_alive()
        finally:
            gate.set()
