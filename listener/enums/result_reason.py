from enum import Enum


class ResultReason(Enum):
    INVALID = 0
    RETIRED = 1
    FINISHED = 2
    TERMINAL_DAMAGE = 3
    INACTIVE = 4
    NOT_ENOUGH_LAPS = 5
    BLACK_FLAGGED = 6
    RED_FLAGGED = 7
    MECHANICAL_FAILURE = 8
    SESSION_SKIPPED = 9
    SESSION_SIMULATED = 10
