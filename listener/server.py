import logging
import queue
import socket
import threading
import time
from typing import Callable

# Largest F1 26 packet is 1470 bytes; 4096 leaves comfortable headroom
_DEFAULT_BUFFER_SIZE = 4096

# Datagrams held between the receive loop and the worker. The game sends ~700 a
# second with a full grid, so this is ~30s of slack for a slow write to pass.
_DEFAULT_QUEUE_SIZE = 20000

# The kernel discards datagrams the moment its own receive buffer fills, and the
# default (208 KB, ~150 packets) is a fraction of a second at the game's send
# rate. net.core.rmem_max caps a plain SO_RCVBUF request; SO_RCVBUFFORCE ignores
# that cap but needs CAP_NET_ADMIN, so it is tried first.
_DESIRED_RCVBUF = 16 * 1024 * 1024

# Linux-only, and CPython does not export it.
_SO_RCVBUFFORCE = 33

_REPORT_INTERVAL_S = 5.0


def _configure_receive_buffer(sock: socket.socket, logger: logging.Logger) -> int:
    """Ask the kernel for a large receive buffer and report what it granted."""
    for option in (_SO_RCVBUFFORCE, socket.SO_RCVBUF):
        try:
            sock.setsockopt(socket.SOL_SOCKET, option, _DESIRED_RCVBUF)
            break
        except OSError:
            continue

    # Linux reports back double what it granted; half is bookkeeping overhead.
    granted = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF) // 2
    if granted < _DESIRED_RCVBUF:
        logger.info(
            "UDP receive buffer is %d bytes, capped below the %d requested by "
            "net.core.rmem_max",
            granted,
            _DESIRED_RCVBUF,
        )
    else:
        logger.info("UDP receive buffer set to %d bytes", granted)
    return granted


def _kernel_rcvbuf_errors() -> int:
    """
    Cumulative datagrams the kernel dropped because a receive buffer was full.

    These never reach recvfrom, so this counter is the only way the listener can
    see them. The container has its own network namespace, where the telemetry
    socket is the only meaningful UDP traffic.
    """
    try:
        with open("/proc/net/snmp", encoding="ascii") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return 0

    for header, values in zip(lines, lines[1:]):
        if header.startswith("Udp:") and values.startswith("Udp:"):
            fields = header.split()
            if "RcvbufErrors" in fields:
                return int(values.split()[fields.index("RcvbufErrors")])
    return 0


def _process_packets(
    packets: "queue.Queue[bytes | None]",
    packet_handler: Callable[[bytes], None],
    logger: logging.Logger,
) -> None:
    """Hand queued datagrams to the handler until the sentinel arrives."""
    while True:
        data = packets.get()
        if data is None:
            return
        try:
            packet_handler(data)
        except Exception as e:
            logger.error("Packet handler failed: %s", e, exc_info=True)


def start_udp_server(
    ip: str,
    port: int,
    packet_handler,
    logger,
    queue_size: int = _DEFAULT_QUEUE_SIZE,
):
    """
    Start UDP server to receive telemetry packets.

    The receive loop does nothing but move datagrams onto a queue; a worker
    thread runs packet_handler. Parsing and the database writes it triggers take
    long enough that doing them inline lets the socket's receive buffer overflow,
    which costs whole packets rather than delaying them.

    Args:
        ip: IP address to bind to
        port: UDP port to listen on
        packet_handler: Callback function to process received packets
        logger: Logger instance for logging
        queue_size: Datagrams to hold while the handler catches up
    """
    sock = None
    packets: "queue.Queue[bytes | None]" = queue.Queue(maxsize=queue_size)
    worker = threading.Thread(
        target=_process_packets,
        args=(packets, packet_handler, logger),
        name="packet-handler",
        daemon=True,
    )

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rcvbuf = _configure_receive_buffer(sock, logger)
        sock.bind((ip, port))
        worker.start()
        logger.info("Listening for UDP packets on %s:%s", ip, port)

        dropped = 0
        backlog_peak = 0
        last_report = time.monotonic()
        last_kernel_drops = _kernel_rcvbuf_errors()

        while True:
            try:
                data, _ = sock.recvfrom(_DEFAULT_BUFFER_SIZE)
            except OSError as e:
                logger.error("Socket receive error: %s", e)
                # Continue listening after receive errors
                continue

            try:
                packets.put_nowait(data)
            except queue.Full:
                dropped += 1

            backlog_peak = max(backlog_peak, packets.qsize())

            now = time.monotonic()
            if now - last_report >= _REPORT_INTERVAL_S:
                kernel_drops = _kernel_rcvbuf_errors()
                if kernel_drops > last_kernel_drops:
                    logger.warning(
                        "Kernel dropped %d datagram(s) in the last %.0fs — the "
                        "receive buffer (%d bytes) overflowed; raise "
                        "net.core.rmem_max on the host",
                        kernel_drops - last_kernel_drops,
                        now - last_report,
                        rcvbuf,
                    )
                if dropped:
                    logger.warning(
                        "Dropped %d packet(s) in the last %.0fs — the handler is "
                        "not keeping up with the game's send rate",
                        dropped,
                        now - last_report,
                    )
                elif backlog_peak >= queue_size // 2:
                    logger.warning(
                        "Packet backlog peaked at %d of %d — the handler is "
                        "falling behind",
                        backlog_peak,
                        queue_size,
                    )
                dropped = 0
                backlog_peak = 0
                last_kernel_drops = kernel_drops
                last_report = now

    except OSError as e:
        logger.error("Failed to bind UDP socket to %s:%s - %s", ip, port, e)
        raise
    except KeyboardInterrupt:
        logger.info("Shutting down UDP server")
    finally:
        try:
            packets.put_nowait(None)
        except queue.Full:
            pass
        if sock:
            sock.close()
            logger.info("UDP socket closed")
