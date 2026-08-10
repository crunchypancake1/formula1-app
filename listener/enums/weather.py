from enum import Enum


class WeatherIDs(Enum):
    UNKNOWN = 255
    CLEAR = 0
    LIGHT_CLOUD = 1
    OVERCAST = 2
    LIGHT_RAIN = 3
    HEAVY_RAIN = 4
    STORM = 5
