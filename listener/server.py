import socket

# F1 25 max packet size is ~1460 bytes; 4096 provides comfortable headroom
_DEFAULT_BUFFER_SIZE = 4096


def start_udp_server(ip: str, port: int, packet_handler, logger):
    """
    Start UDP server to receive telemetry packets.

    Args:
        ip: IP address to bind to
        port: UDP port to listen on
        packet_handler: Callback function to process received packets
        logger: Logger instance for logging
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port))
        logger.info("Listening for UDP packets on %s:%s", ip, port)

        while True:
            try:
                data, _ = sock.recvfrom(_DEFAULT_BUFFER_SIZE)
                packet_handler(data)
            except OSError as e:
                logger.error("Socket receive error: %s", e)
                # Continue listening after receive errors
                continue

    except OSError as e:
        logger.error("Failed to bind UDP socket to %s:%s - %s", ip, port, e)
        raise
    except KeyboardInterrupt:
        logger.info("Shutting down UDP server")
    finally:
        if sock:
            sock.close()
            logger.info("UDP socket closed")
