from enum import Enum


class SafetyCarStatus(Enum):
    NONE = 0
    FULL = 1
    VIRTUAL = 2
    FORMATION_LAP = 3
