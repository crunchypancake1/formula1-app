from enum import Enum


class SafetyCarEventType(Enum):
    DEPLOYED = 0
    RETURNING = 1
    RETURNED = 2
    RESUME_RACE = 3
