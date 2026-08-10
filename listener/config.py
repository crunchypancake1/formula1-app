import os
from urllib.parse import quote_plus

# PostgreSQL configuration defaults
_DEFAULT_POSTGRES_HOST = "localhost"
_DEFAULT_POSTGRES_PORT = "5432"
_DEFAULT_POSTGRES_USER = "postgres"
_DEFAULT_POSTGRES_PASSWORD = "postgres"
_DEFAULT_POSTGRES_DB = "f1_app"
_DEFAULT_POSTGRES_POOL_MIN = 5
_DEFAULT_POSTGRES_POOL_MAX = 20

# UDP server configuration
_DEFAULT_PORT = 20777
_DEFAULT_IP = "0.0.0.0"

# Logging configuration
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_LOG_PATH = "/var/log/f1-listener/listener.log"

_DEFAULT_DEAD_LETTER_DIR = "/var/log/f1-listener/dead-letter"


def get_postgres_uri() -> str:
    """Build PostgreSQL URI from component environment variables."""
    host = os.getenv("POSTGRES_HOST", _DEFAULT_POSTGRES_HOST)
    port = os.getenv("POSTGRES_PORT", _DEFAULT_POSTGRES_PORT)
    user = os.getenv("POSTGRES_USER", _DEFAULT_POSTGRES_USER)
    password = os.getenv("POSTGRES_PASSWORD", _DEFAULT_POSTGRES_PASSWORD)
    db = os.getenv("POSTGRES_DB", _DEFAULT_POSTGRES_DB)

    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


def get_postgres_pool_min() -> int:
    return int(os.getenv("POSTGRES_POOL_MIN", _DEFAULT_POSTGRES_POOL_MIN))


def get_postgres_pool_max() -> int:
    return int(os.getenv("POSTGRES_POOL_MAX", _DEFAULT_POSTGRES_POOL_MAX))


def get_listen_port() -> int:
    return int(os.getenv("LISTEN_PORT", _DEFAULT_PORT))


def get_listen_ip() -> str:
    return os.getenv("LISTEN_IP", _DEFAULT_IP)


def get_log_level() -> str:
    return os.getenv("LOG_LEVEL", _DEFAULT_LOG_LEVEL).upper()


def get_log_path() -> str:
    return os.getenv("LOG_PATH", _DEFAULT_LOG_PATH)


def get_dead_letter_dir() -> str:
    return os.getenv("DEAD_LETTER_DIR", _DEFAULT_DEAD_LETTER_DIR)
