from enum import Enum


class DrsDisabledReason(Enum):
    WET_TRACK = 0
    SAFETY_CAR_DEPLOYED = 1
    RED_FLAG = 2
    MIN_LAP_NOT_REACHED = 3
