from enum import Enum


class TrackIDs(Enum):
    """
    Track IDs from the F1 26 (2026 Season Pack) UDP spec.

    This enum is required for parsing UDP packets. Display names and countries
    are stored in the telemetry.tracks database table.
    """

    UNKNOWN = 255
    MELBOURNE = 0
    SHANGHAI = 2
    SAKHIR_BAHRAIN = 3
    CATALUNYA = 4
    MONACO = 5
    MONTREAL = 6
    SILVERSTONE = 7
    HUNGARORING = 9
    SPA = 10
    MONZA = 11
    SINGAPORE = 12
    SUZUKA = 13
    ABU_DHABI = 14
    TEXAS = 15
    BRAZIL = 16
    AUSTRIA = 17
    MEXICO = 19
    BAKU_AZERBAIJAN = 20
    ZANDVOORT = 26
    IMOLA = 27
    JEDDAH = 29
    MIAMI = 30
    LAS_VEGAS = 31
    LOSAIL = 32
    SILVERSTONE_REVERSE = 39
    AUSTRIA_REVERSE = 40
    ZANDVOORT_REVERSE = 41
    MADRID = 42
