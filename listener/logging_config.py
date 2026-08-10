import logging
import os


def configure_logging(log_level: str, log_path: str) -> logging.Logger:
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handlers = [logging.StreamHandler(), logging.FileHandler(log_path)]
    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
    return logging.getLogger("telemetry.listener")
