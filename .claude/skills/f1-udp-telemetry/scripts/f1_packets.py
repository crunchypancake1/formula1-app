"""
f1_packets.py - Packet layouts and parser for the EA SPORTS F1 UDP telemetry feed.

Supports two wire formats:
  * 2025  -> F1 25 base game            (22 cars, header m_packetFormat == 2025)
  * 2026  -> F1 25: 2026 Season Pack    (24 cars, header m_packetFormat == 2026)

Everything is little-endian and tightly packed (no padding), which is why every
format string below starts with "<".

Layouts are declared as data, not hand-written struct strings. That keeps them
readable and lets verify_sizes.py prove each packet matches the byte size EA
documents - a wrong layout is caught immediately instead of silently producing
garbage floats 900 bytes into the packet.

Usage:
    from f1_packets import parse_packet
    header, body = parse_packet(datagram)
    if header["m_packetId"] == 6:
        print(body["m_carTelemetryData"][header["m_playerCarIndex"]]["m_speed"])

Field names match EA's documentation exactly (m_ prefix) so you can read the
spec PDF and the code side by side.
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Tuple

# --------------------------------------------------------------------------
# Primitive types
# --------------------------------------------------------------------------

PRIM = {
    "u8": "B",
    "i8": "b",
    "u16": "H",
    "i16": "h",
    "u32": "I",
    "u64": "Q",
    "f32": "f",
    "f64": "d",
}

# --------------------------------------------------------------------------
# Packet header - identical in both formats (29 bytes)
# --------------------------------------------------------------------------

HEADER_FIELDS = [
    ("m_packetFormat", "u16"),            # 2025 or 2026 - dispatch on this
    ("m_gameYear", "u8"),
    ("m_gameMajorVersion", "u8"),
    ("m_gameMinorVersion", "u8"),
    ("m_packetVersion", "u8"),
    ("m_packetId", "u8"),
    ("m_sessionUID", "u64"),              # changes => new session, reset state
    ("m_sessionTime", "f32"),
    ("m_frameIdentifier", "u32"),         # rewinds on a flashback
    ("m_overallFrameIdentifier", "u32"),  # never rewinds
    ("m_playerCarIndex", "u8"),
    ("m_secondaryPlayerCarIndex", "u8"),  # 255 if no splitscreen player
]

HEADER_FMT = "<" + "".join(PRIM[t] for _, t in HEADER_FIELDS)
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 29

# --------------------------------------------------------------------------
# Packet IDs
# --------------------------------------------------------------------------

PACKET_NAMES = {
    0: "Motion",
    1: "Session",
    2: "LapData",
    3: "Event",
    4: "Participants",
    5: "CarSetups",
    6: "CarTelemetry",
    7: "CarStatus",
    8: "FinalClassification",
    9: "LobbyInfo",
    10: "CarDamage",
    11: "SessionHistory",
    12: "TyreSets",
    13: "MotionEx",
    14: "TimeTrial",
    15: "LapPositions",
    16: "CarTelemetry2",  # 2026 only
}

# --------------------------------------------------------------------------
# Shared sub-structs (identical across both formats)
# --------------------------------------------------------------------------

_MARSHAL_ZONE = [("m_zoneStart", "f32"), ("m_zoneFlag", "i8")]

_WEATHER_SAMPLE = [
    ("m_sessionType", "u8"),
    ("m_timeOffset", "u8"),
    ("m_weather", "u8"),
    ("m_trackTemperature", "i8"),
    ("m_trackTemperatureChange", "i8"),
    ("m_airTemperature", "i8"),
    ("m_airTemperatureChange", "i8"),
    ("m_rainPercentage", "u8"),
]

_LIVERY_COLOUR = [("red", "u8"), ("green", "u8"), ("blue", "u8")]

_LAP_HISTORY = [
    ("m_lapTimeInMS", "u32"),
    ("m_sector1TimeMSPart", "u16"),
    ("m_sector1TimeMinutesPart", "u8"),
    ("m_sector2TimeMSPart", "u16"),
    ("m_sector2TimeMinutesPart", "u8"),
    ("m_sector3TimeMSPart", "u16"),
    ("m_sector3TimeMinutesPart", "u8"),
    ("m_lapValidBitFlags", "u8"),  # 0x01 lap, 0x02 s1, 0x04 s2, 0x08 s3
]

_TYRE_STINT_HISTORY = [
    ("m_endLap", "u8"),
    ("m_tyreActualCompound", "u8"),
    ("m_tyreVisualCompound", "u8"),
]

_TYRE_SET = [
    ("m_actualTyreCompound", "u8"),
    ("m_visualTyreCompound", "u8"),
    ("m_wear", "u8"),
    ("m_available", "u8"),
    ("m_recommendedSession", "u8"),
    ("m_lifeSpan", "u8"),
    ("m_usableLife", "u8"),
    ("m_lapDeltaTime", "i16"),
    ("m_fitted", "u8"),
]

_CAR_SETUP = [
    ("m_frontWing", "u8"),
    ("m_rearWing", "u8"),
    ("m_onThrottle", "u8"),
    ("m_offThrottle", "u8"),
    ("m_frontCamber", "f32"),
    ("m_rearCamber", "f32"),
    ("m_frontToe", "f32"),
    ("m_rearToe", "f32"),
    ("m_frontSuspension", "u8"),
    ("m_rearSuspension", "u8"),
    ("m_frontAntiRollBar", "u8"),
    ("m_rearAntiRollBar", "u8"),
    ("m_frontSuspensionHeight", "u8"),
    ("m_rearSuspensionHeight", "u8"),
    ("m_brakePressure", "u8"),
    ("m_brakeBias", "u8"),
    ("m_engineBraking", "u8"),
    ("m_rearLeftTyrePressure", "f32"),
    ("m_rearRightTyrePressure", "f32"),
    ("m_frontLeftTyrePressure", "f32"),
    ("m_frontRightTyrePressure", "f32"),
    ("m_ballast", "u8"),
    ("m_fuelLoad", "f32"),
]

_CAR_DAMAGE = [
    ("m_tyresWear", "f32", 4),
    ("m_tyresDamage", "u8", 4),
    ("m_brakesDamage", "u8", 4),
    ("m_tyreBlisters", "u8", 4),
    ("m_frontLeftWingDamage", "u8"),
    ("m_frontRightWingDamage", "u8"),
    ("m_rearWingDamage", "u8"),
    ("m_floorDamage", "u8"),
    ("m_diffuserDamage", "u8"),
    ("m_sidepodDamage", "u8"),
    ("m_drsFault", "u8"),
    ("m_ersFault", "u8"),
    ("m_gearBoxDamage", "u8"),
    ("m_engineDamage", "u8"),
    ("m_engineMGUHWear", "u8"),
    ("m_engineESWear", "u8"),
    ("m_engineCEWear", "u8"),
    ("m_engineICEWear", "u8"),
    ("m_engineMGUKWear", "u8"),
    ("m_engineTCWear", "u8"),
    ("m_engineBlown", "u8"),
    ("m_engineSeized", "u8"),
]

_LAP_DATA = [
    ("m_lastLapTimeInMS", "u32"),
    ("m_currentLapTimeInMS", "u32"),
    ("m_sector1TimeMSPart", "u16"),
    ("m_sector1TimeMinutesPart", "u8"),
    ("m_sector2TimeMSPart", "u16"),
    ("m_sector2TimeMinutesPart", "u8"),
    ("m_deltaToCarInFrontMSPart", "u16"),
    ("m_deltaToCarInFrontMinutesPart", "u8"),
    ("m_deltaToRaceLeaderMSPart", "u16"),
    ("m_deltaToRaceLeaderMinutesPart", "u8"),
    ("m_lapDistance", "f32"),
    ("m_totalDistance", "f32"),
    ("m_safetyCarDelta", "f32"),
    ("m_carPosition", "u8"),
    ("m_currentLapNum", "u8"),
    ("m_pitStatus", "u8"),
    ("m_numPitStops", "u8"),
    ("m_sector", "u8"),
    ("m_currentLapInvalid", "u8"),
    ("m_penalties", "u8"),
    ("m_totalWarnings", "u8"),
    ("m_cornerCuttingWarnings", "u8"),
    ("m_numUnservedDriveThroughPens", "u8"),
    ("m_numUnservedStopGoPens", "u8"),
    ("m_gridPosition", "u8"),
    ("m_driverStatus", "u8"),
    ("m_resultStatus", "u8"),
    ("m_pitLaneTimerActive", "u8"),
    ("m_pitLaneTimeInLaneInMS", "u16"),
    ("m_pitStopTimerInMS", "u16"),
    ("m_pitStopShouldServePen", "u8"),
    ("m_speedTrapFastestSpeed", "f32"),
    ("m_speedTrapFastestLap", "u8"),
]

_FINAL_CLASSIFICATION = [
    ("m_position", "u8"),
    ("m_numLaps", "u8"),
    ("m_gridPosition", "u8"),
    ("m_points", "u8"),
    ("m_numPitStops", "u8"),
    ("m_resultStatus", "u8"),
    ("m_resultReason", "u8"),
    ("m_bestLapTimeInMS", "u32"),
    ("m_totalRaceTime", "f64"),
    ("m_penaltiesTime", "u8"),
    ("m_numPenalties", "u8"),
    ("m_numTyreStints", "u8"),
    ("m_tyreStintsActual", "u8", 8),
    ("m_tyreStintsVisual", "u8", 8),
    ("m_tyreStintsEndLaps", "u8", 8),
]

_MOTION_EX = [
    # Wheel arrays are ordered RL, RR, FL, FR - see WHEEL_ORDER below.
    ("m_suspensionPosition", "f32", 4),
    ("m_suspensionVelocity", "f32", 4),
    ("m_suspensionAcceleration", "f32", 4),
    ("m_wheelSpeed", "f32", 4),
    ("m_wheelSlipRatio", "f32", 4),
    ("m_wheelSlipAngle", "f32", 4),
    ("m_wheelLatForce", "f32", 4),
    ("m_wheelLongForce", "f32", 4),
    ("m_heightOfCOGAboveGround", "f32"),
    ("m_localVelocityX", "f32"),
    ("m_localVelocityY", "f32"),
    ("m_localVelocityZ", "f32"),
    ("m_angularVelocityX", "f32"),
    ("m_angularVelocityY", "f32"),
    ("m_angularVelocityZ", "f32"),
    ("m_angularAccelerationX", "f32"),
    ("m_angularAccelerationY", "f32"),
    ("m_angularAccelerationZ", "f32"),
    ("m_frontWheelsAngle", "f32"),
    ("m_wheelVertForce", "f32", 4),
    ("m_frontAeroHeight", "f32"),
    ("m_rearAeroHeight", "f32"),
    ("m_frontRollAngle", "f32"),
    ("m_rearRollAngle", "f32"),
    ("m_chassisYaw", "f32"),
    ("m_chassisPitch", "f32"),
    ("m_wheelCamber", "f32", 4),
    ("m_wheelCamberGain", "f32", 4),
]

_SESSION_HISTORY = [
    ("m_carIdx", "u8"),
    ("m_numLaps", "u8"),
    ("m_numTyreStints", "u8"),
    ("m_bestLapTimeLapNum", "u8"),
    ("m_bestSector1LapNum", "u8"),
    ("m_bestSector2LapNum", "u8"),
    ("m_bestSector3LapNum", "u8"),
    ("m_lapHistoryData", "LapHistoryData", 100),
    ("m_tyreStintsHistoryData", "TyreStintHistoryData", 8),
]

# Session settings block shared by both formats, up to sector3LapDistanceStart.
_SESSION_COMMON = [
    ("m_weather", "u8"),
    ("m_trackTemperature", "i8"),
    ("m_airTemperature", "i8"),
    ("m_totalLaps", "u8"),
    ("m_trackLength", "u16"),
    ("m_sessionType", "u8"),
    ("m_trackId", "i8"),
    ("m_formula", "u8"),
    ("m_sessionTimeLeft", "u16"),
    ("m_sessionDuration", "u16"),
    ("m_pitSpeedLimit", "u8"),
    ("m_gamePaused", "u8"),
    ("m_isSpectating", "u8"),
    ("m_spectatorCarIndex", "u8"),
    ("m_sliProNativeSupport", "u8"),
    ("m_numMarshalZones", "u8"),
    ("m_marshalZones", "MarshalZone", 21),
    ("m_safetyCarStatus", "u8"),
    ("m_networkGame", "u8"),
    ("m_numWeatherForecastSamples", "u8"),
    ("m_weatherForecastSamples", "WeatherForecastSample", 64),
    ("m_forecastAccuracy", "u8"),
    ("m_aiDifficulty", "u8"),
    ("m_seasonLinkIdentifier", "u32"),
    ("m_weekendLinkIdentifier", "u32"),
    ("m_sessionLinkIdentifier", "u32"),
    ("m_pitStopWindowIdealLap", "u8"),
    ("m_pitStopWindowLatestLap", "u8"),
    ("m_pitStopRejoinPosition", "u8"),
    ("m_steeringAssist", "u8"),
    ("m_brakingAssist", "u8"),
    ("m_gearboxAssist", "u8"),
    ("m_pitAssist", "u8"),
    ("m_pitReleaseAssist", "u8"),
    ("m_ERSAssist", "u8"),
    ("m_DRSAssist", "u8"),
    ("m_dynamicRacingLine", "u8"),
    ("m_dynamicRacingLineType", "u8"),
    ("m_gameMode", "u8"),
    ("m_ruleSet", "u8"),
    ("m_timeOfDay", "u32"),
    ("m_sessionLength", "u8"),
    ("m_speedUnitsLeadPlayer", "u8"),
    ("m_temperatureUnitsLeadPlayer", "u8"),
    ("m_speedUnitsSecondaryPlayer", "u8"),
    ("m_temperatureUnitsSecondaryPlayer", "u8"),
    ("m_numSafetyCarPeriods", "u8"),
    ("m_numVirtualSafetyCarPeriods", "u8"),
    ("m_numRedFlagPeriods", "u8"),
    ("m_equalCarPerformance", "u8"),
    ("m_recoveryMode", "u8"),
    ("m_flashbackLimit", "u8"),
    ("m_surfaceType", "u8"),
    ("m_lowFuelMode", "u8"),
    ("m_raceStarts", "u8"),
    ("m_tyreTemperature", "u8"),
    ("m_pitLaneTyreSim", "u8"),
    ("m_carDamage", "u8"),
    ("m_carDamageRate", "u8"),
    ("m_collisions", "u8"),
    ("m_collisionsOffForFirstLapOnly", "u8"),
    ("m_mpUnsafePitRelease", "u8"),
    ("m_mpOffForGriefing", "u8"),
    ("m_cornerCuttingStringency", "u8"),
    ("m_parcFermeRules", "u8"),
    ("m_pitStopExperience", "u8"),
    ("m_safetyCar", "u8"),
    ("m_safetyCarExperience", "u8"),
    ("m_formationLap", "u8"),
    ("m_formationLapExperience", "u8"),
    ("m_redFlags", "u8"),
    ("m_affectsLicenceLevelSolo", "u8"),
    ("m_affectsLicenceLevelMP", "u8"),
    ("m_numSessionsInWeekend", "u8"),
    ("m_weekendStructure", "u8", 12),
    ("m_sector2LapDistanceStart", "f32"),
    ("m_sector3LapDistanceStart", "f32"),
]

_CAR_STATUS_COMMON_HEAD = [
    ("m_tractionControl", "u8"),
    ("m_antiLockBrakes", "u8"),
    ("m_fuelMix", "u8"),
    ("m_frontBrakeBias", "u8"),
    ("m_pitLimiterStatus", "u8"),
    ("m_fuelInTank", "f32"),
    ("m_fuelCapacity", "f32"),
    ("m_fuelRemainingLaps", "f32"),
    ("m_maxRPM", "u16"),
    ("m_idleRPM", "u16"),
    ("m_maxGears", "u8"),
    ("m_drsAllowed", "u8"),
    ("m_drsActivationDistance", "u16"),
    ("m_actualTyreCompound", "u8"),
    ("m_visualTyreCompound", "u8"),
    ("m_tyresAgeLaps", "u8"),
    ("m_vehicleFIAFlags", "i8"),
    ("m_enginePowerICE", "f32"),
    ("m_enginePowerMGUK", "f32"),
    ("m_ersStoreEnergy", "f32"),
    ("m_ersDeployMode", "u8"),
    ("m_ersHarvestedThisLapMGUK", "f32"),
    ("m_ersHarvestedThisLapMGUH", "f32"),
]

# ==========================================================================
# 2025 format (F1 25 base game) - 22 cars
# ==========================================================================

MAX_CARS_2025 = 22

STRUCTS_2025: Dict[str, List[tuple]] = {
    "MarshalZone": _MARSHAL_ZONE,
    "WeatherForecastSample": _WEATHER_SAMPLE,
    "LiveryColour": _LIVERY_COLOUR,
    "LapHistoryData": _LAP_HISTORY,
    "TyreStintHistoryData": _TYRE_STINT_HISTORY,
    "TyreSetData": _TYRE_SET,
    "CarSetupData": _CAR_SETUP,
    "CarDamageData": _CAR_DAMAGE,
    "LapData": _LAP_DATA,
    "FinalClassificationData": _FINAL_CLASSIFICATION,
    "CarMotionData": [
        ("m_worldPositionX", "f32"),
        ("m_worldPositionY", "f32"),
        ("m_worldPositionZ", "f32"),
        ("m_worldVelocityX", "f32"),
        ("m_worldVelocityY", "f32"),
        ("m_worldVelocityZ", "f32"),
        ("m_worldForwardDirX", "i16"),
        ("m_worldForwardDirY", "i16"),
        ("m_worldForwardDirZ", "i16"),
        ("m_worldRightDirX", "i16"),
        ("m_worldRightDirY", "i16"),
        ("m_worldRightDirZ", "i16"),
        ("m_gForceLateral", "f32"),        # plain float in 2025
        ("m_gForceLongitudinal", "f32"),
        ("m_gForceVertical", "f32"),
        ("m_yaw", "f32"),
        ("m_pitch", "f32"),
        ("m_roll", "f32"),
    ],
    "ParticipantData": [
        ("m_aiControlled", "u8"),
        ("m_driverId", "u8"),      # 255 = network human
        ("m_networkId", "u8"),
        ("m_teamId", "u8"),
        ("m_myTeam", "u8"),
        ("m_raceNumber", "u8"),
        ("m_nationality", "u8"),
        ("m_name", "char", 32),
        ("m_yourTelemetry", "u8"),
        ("m_showOnlineNames", "u8"),
        ("m_techLevel", "u16"),
        ("m_platform", "u8"),
        ("m_numColours", "u8"),
        ("m_liveryColours", "LiveryColour", 4),
    ],
    "CarTelemetryData": [
        ("m_speed", "u16"),
        ("m_throttle", "f32"),
        ("m_steer", "f32"),
        ("m_brake", "f32"),
        ("m_clutch", "u8"),
        ("m_gear", "i8"),
        ("m_engineRPM", "u16"),
        ("m_drs", "u8"),
        ("m_revLightsPercent", "u8"),
        ("m_revLightsBitValue", "u16"),
        ("m_brakesTemperature", "u16", 4),
        ("m_tyresSurfaceTemperature", "u8", 4),
        ("m_tyresInnerTemperature", "u8", 4),
        ("m_engineTemperature", "u16"),    # u16 in 2025, u8 in 2026
        ("m_tyresPressure", "f32", 4),
        ("m_surfaceType", "u8", 4),
    ],
    "CarStatusData": _CAR_STATUS_COMMON_HEAD + [
        ("m_ersDeployedThisLap", "f32"),
        ("m_networkPaused", "u8"),
    ],
    "LobbyInfoData": [
        ("m_aiControlled", "u8"),
        ("m_teamId", "u8"),        # 255 = no team selected
        ("m_nationality", "u8"),
        ("m_platform", "u8"),
        ("m_name", "char", 32),
        ("m_carNumber", "u8"),
        ("m_yourTelemetry", "u8"),
        ("m_showOnlineNames", "u8"),
        ("m_techLevel", "u16"),
        ("m_readyStatus", "u8"),
    ],
    "TimeTrialDataSet": [
        ("m_carIdx", "u8"),
        ("m_teamId", "u8"),
        ("m_lapTimeInMS", "u32"),
        ("m_sector1TimeInMS", "u32"),
        ("m_sector2TimeInMS", "u32"),
        ("m_sector3TimeInMS", "u32"),
        ("m_tractionControl", "u8"),
        ("m_gearboxAssist", "u8"),
        ("m_antiLockBrakes", "u8"),
        ("m_equalCarPerformance", "u8"),
        ("m_customSetup", "u8"),
        ("m_valid", "u8"),
    ],
}

PACKETS_2025: Dict[int, Tuple[str, List[tuple]]] = {
    0: ("PacketMotionData", [("m_carMotionData", "CarMotionData", MAX_CARS_2025)]),
    1: ("PacketSessionData", _SESSION_COMMON),
    2: ("PacketLapData", [
        ("m_lapData", "LapData", MAX_CARS_2025),
        ("m_timeTrialPBCarIdx", "u8"),
        ("m_timeTrialRivalCarIdx", "u8"),
    ]),
    3: ("PacketEventData", [
        ("m_eventStringCode", "char", 4),
        ("m_eventDetailsRaw", "bytes", 12),
    ]),
    4: ("PacketParticipantsData", [
        ("m_numActiveCars", "u8"),
        ("m_participants", "ParticipantData", MAX_CARS_2025),
    ]),
    5: ("PacketCarSetupData", [
        ("m_carSetups", "CarSetupData", MAX_CARS_2025),
        ("m_nextFrontWingValue", "f32"),
    ]),
    6: ("PacketCarTelemetryData", [
        ("m_carTelemetryData", "CarTelemetryData", MAX_CARS_2025),
        ("m_mfdPanelIndex", "u8"),
        ("m_mfdPanelIndexSecondaryPlayer", "u8"),
        ("m_suggestedGear", "i8"),
    ]),
    7: ("PacketCarStatusData", [("m_carStatusData", "CarStatusData", MAX_CARS_2025)]),
    8: ("PacketFinalClassificationData", [
        ("m_numCars", "u8"),
        ("m_classificationData", "FinalClassificationData", MAX_CARS_2025),
    ]),
    9: ("PacketLobbyInfoData", [
        ("m_numPlayers", "u8"),
        ("m_lobbyPlayers", "LobbyInfoData", MAX_CARS_2025),
    ]),
    10: ("PacketCarDamageData", [("m_carDamageData", "CarDamageData", MAX_CARS_2025)]),
    11: ("PacketSessionHistoryData", _SESSION_HISTORY),
    12: ("PacketTyreSetsData", [
        ("m_carIdx", "u8"),
        ("m_tyreSetData", "TyreSetData", 20),
        ("m_fittedIdx", "u8"),
    ]),
    13: ("PacketMotionExData", _MOTION_EX),
    14: ("PacketTimeTrialData", [
        ("m_playerSessionBestDataSet", "TimeTrialDataSet"),
        ("m_personalBestDataSet", "TimeTrialDataSet"),
        ("m_rivalDataSet", "TimeTrialDataSet"),
    ]),
    15: ("PacketLapPositionsData", [
        ("m_numLaps", "u8"),
        ("m_lapStart", "u8"),
        ("m_positionForVehicleIdx", "u8", 50 * MAX_CARS_2025),
    ]),
}

# ==========================================================================
# 2026 format (F1 25: 2026 Season Pack) - 24 cars
# ==========================================================================

MAX_CARS_2026 = 24

STRUCTS_2026: Dict[str, List[tuple]] = {
    "MarshalZone": _MARSHAL_ZONE,
    "WeatherForecastSample": _WEATHER_SAMPLE,
    "LiveryColour": _LIVERY_COLOUR,
    "LapHistoryData": _LAP_HISTORY,
    "TyreStintHistoryData": _TYRE_STINT_HISTORY,
    "TyreSetData": _TYRE_SET,
    "CarSetupData": _CAR_SETUP,
    "CarDamageData": _CAR_DAMAGE,
    "LapData": _LAP_DATA,
    "FinalClassificationData": _FINAL_CLASSIFICATION,
    "ActiveAeroZone": [("m_zoneStart", "f32"), ("m_zoneEnd", "f32")],
    "DRSZone": [("m_zoneStart", "f32"), ("m_zoneEnd", "f32")],
    "CarMotionData": [
        ("m_worldPositionX", "f32"),
        ("m_worldPositionY", "f32"),
        ("m_worldPositionZ", "f32"),
        ("m_worldVelocityX", "f32"),
        ("m_worldVelocityY", "f32"),
        ("m_worldVelocityZ", "f32"),
        ("m_worldForwardDirX", "i16"),
        ("m_worldForwardDirY", "i16"),
        ("m_worldForwardDirZ", "i16"),
        ("m_worldRightDirX", "i16"),
        ("m_worldRightDirY", "i16"),
        ("m_worldRightDirZ", "i16"),
        ("m_gForceLateral", "i16"),        # quantised: divide by 1000.0
        ("m_gForceLongitudinal", "i16"),
        ("m_gForceVertical", "i16"),
        ("m_yaw", "f32"),
        ("m_pitch", "f32"),
        ("m_roll", "f32"),
    ],
    "ParticipantData": [
        ("m_aiControlled", "u8"),
        ("m_driverId", "u16"),     # widened; 65535 = network human
        ("m_networkId", "u16"),
        ("m_teamId", "u16"),
        ("m_myTeam", "u8"),
        ("m_raceNumber", "u8"),
        ("m_nationality", "u8"),
        ("m_name", "char", 32),
        ("m_yourTelemetry", "u8"),
        ("m_showOnlineNames", "u8"),
        ("m_techLevel", "u16"),
        ("m_platform", "u8"),
        ("m_numColours", "u8"),
        ("m_liveryColours", "LiveryColour", 4),
    ],
    "CarTelemetryData": [
        ("m_speed", "u16"),
        ("m_throttle", "f32"),
        ("m_steer", "f32"),
        ("m_brake", "f32"),
        ("m_clutch", "u8"),
        ("m_gear", "i8"),
        ("m_engineRPM", "u16"),
        ("m_drs", "u8"),
        ("m_revLightsPercent", "u8"),
        ("m_revLightsBitValue", "u16"),
        ("m_brakesTemperature", "u16", 4),
        ("m_tyresSurfaceTemperature", "u8", 4),
        ("m_tyresInnerTemperature", "u8", 4),
        ("m_engineTemperature", "u8"),     # narrowed from u16 in 2025
        ("m_tyresPressure", "f32", 4),
        ("m_surfaceType", "u8", 4),
    ],
    "CarTelemetry2Data": [
        ("m_activeAeroMode", "u8"),               # 0 = corner, 1 = straight
        ("m_activeAeroAvailable", "u8"),
        ("m_activeAeroActivationDistance", "u16"),
        ("m_overtakeAvailable", "u8"),
        ("m_overtakeActive", "u8"),
        ("m_overtakeActivationDistance", "u16"),
        ("m_2026Regulations", "u8"),
        ("m_drivingWrongWay", "u8"),
    ],
    "CarStatusData": _CAR_STATUS_COMMON_HEAD + [
        ("m_ersHarvestLimitPerLap", "f32"),     # new in 2026
        ("m_ersDeployedThisLap", "f32"),
        ("m_networkPaused", "u8"),
    ],
    "LobbyInfoData": [
        ("m_aiControlled", "u8"),
        ("m_teamId", "u16"),       # 65535 = no team selected
        ("m_nationality", "u8"),
        ("m_platform", "u8"),
        ("m_name", "char", 32),
        ("m_carNumber", "u8"),
        ("m_yourTelemetry", "u8"),
        ("m_showOnlineNames", "u8"),
        ("m_techLevel", "u16"),
        ("m_readyStatus", "u8"),
    ],
    "TimeTrialDataSet": [
        ("m_carIdx", "u8"),
        ("m_teamId", "u16"),       # widened
        ("m_lapTimeInMS", "u32"),
        ("m_sector1TimeInMS", "u32"),
        ("m_sector2TimeInMS", "u32"),
        ("m_sector3TimeInMS", "u32"),
        ("m_tractionControl", "u8"),
        ("m_gearboxAssist", "u8"),
        ("m_antiLockBrakes", "u8"),
        ("m_equalCarPerformance", "u8"),
        ("m_customSetup", "u8"),
        ("m_valid", "u8"),
    ],
}

PACKETS_2026: Dict[int, Tuple[str, List[tuple]]] = {
    0: ("PacketMotionData", [("m_carMotionData", "CarMotionData", MAX_CARS_2026)]),
    1: ("PacketSessionData", _SESSION_COMMON + [
        ("m_activeAeroTrackStatus", "u8"),        # 0 = Full, 1 = Partial
        ("m_numActiveAeroZonesFull", "u8"),
        ("m_activeAeroZonesFull", "ActiveAeroZone", 8),
        ("m_numActiveAeroZonesPartial", "u8"),
        ("m_activeAeroZonesPartial", "ActiveAeroZone", 8),
        ("m_numDRSZones", "u8"),
        ("m_drsZones", "DRSZone", 4),
        ("m_startReactionTime", "f32"),
        ("m_antiLockBrakesAssist", "u8"),
        ("m_tractionControlAssist", "u8"),
        ("m_dynamicRacingLineHiVis", "u8"),
        ("m_dynamicRacingLineColourBlind", "u8"),
        ("m_recurringRewindPrompt", "u8"),
    ]),
    2: ("PacketLapData", [
        ("m_lapData", "LapData", MAX_CARS_2026),
        ("m_timeTrialPBCarIdx", "u8"),
        ("m_timeTrialRivalCarIdx", "u8"),
    ]),
    3: ("PacketEventData", [
        ("m_eventStringCode", "char", 4),
        ("m_eventDetailsRaw", "bytes", 12),
    ]),
    4: ("PacketParticipantsData", [
        ("m_numActiveCars", "u8"),
        ("m_participants", "ParticipantData", MAX_CARS_2026),
    ]),
    5: ("PacketCarSetupData", [
        ("m_carSetups", "CarSetupData", MAX_CARS_2026),
        ("m_nextFrontWingValue", "f32"),
    ]),
    6: ("PacketCarTelemetryData", [
        ("m_carTelemetryData", "CarTelemetryData", MAX_CARS_2026),
        ("m_mfdPanelIndex", "u8"),
        ("m_mfdPanelIndexSecondaryPlayer", "u8"),
        ("m_suggestedGear", "i8"),
    ]),
    7: ("PacketCarStatusData", [("m_carStatusData", "CarStatusData", MAX_CARS_2026)]),
    8: ("PacketFinalClassificationData", [
        ("m_numCars", "u8"),
        ("m_classificationData", "FinalClassificationData", MAX_CARS_2026),
    ]),
    9: ("PacketLobbyInfoData", [
        ("m_numPlayers", "u8"),
        ("m_lobbyPlayers", "LobbyInfoData", MAX_CARS_2026),
    ]),
    10: ("PacketCarDamageData", [("m_carDamageData", "CarDamageData", MAX_CARS_2026)]),
    11: ("PacketSessionHistoryData", _SESSION_HISTORY),
    12: ("PacketTyreSetsData", [
        ("m_carIdx", "u8"),
        ("m_tyreSetData", "TyreSetData", 20),
        ("m_fittedIdx", "u8"),
    ]),
    13: ("PacketMotionExData", _MOTION_EX),
    14: ("PacketTimeTrialData", [
        ("m_playerSessionBestDataSet", "TimeTrialDataSet"),
        ("m_personalBestDataSet", "TimeTrialDataSet"),
        ("m_rivalDataSet", "TimeTrialDataSet"),
    ]),
    15: ("PacketLapPositionsData", [
        ("m_numLaps", "u8"),
        ("m_lapStart", "u8"),
        ("m_positionForVehicleIdx", "u8", 50 * MAX_CARS_2026),
    ]),
    16: ("PacketCarTelemetry2Data", [
        ("m_carTelemetry2Data", "CarTelemetry2Data", MAX_CARS_2026),
    ]),
}

FORMATS = {
    2025: {"structs": STRUCTS_2025, "packets": PACKETS_2025, "max_cars": MAX_CARS_2025},
    2026: {"structs": STRUCTS_2026, "packets": PACKETS_2026, "max_cars": MAX_CARS_2026},
}

# Documented byte sizes straight from the EA spec. verify_sizes.py checks the
# compiled layouts against these.
DOCUMENTED_SIZES = {
    2025: {0: 1349, 1: 753, 2: 1285, 3: 45, 4: 1284, 5: 1133, 6: 1352, 7: 1239,
           8: 1042, 9: 954, 10: 1041, 11: 1460, 12: 231, 13: 273, 14: 101, 15: 1131},
    2026: {0: 1325, 1: 926, 2: 1399, 3: 45, 4: 1470, 5: 1233, 6: 1448, 7: 1445,
           8: 1134, 9: 1062, 10: 1133, 11: 1460, 12: 231, 13: 273, 14: 104,
           15: 1231, 16: 269},
}

# --------------------------------------------------------------------------
# Layout compiler
# --------------------------------------------------------------------------


def _compile(structs: Dict[str, List[tuple]], fields: List[tuple]):
    """Turn a field list into (format_string_without_prefix, plan, value_count)."""
    fmt = ""
    plan = []
    total = 0
    for entry in fields:
        name, typ = entry[0], entry[1]
        count = entry[2] if len(entry) > 2 else 1
        if typ == "char":
            fmt += f"{count}s"
            plan.append((name, "str", 1))
            total += 1
        elif typ == "bytes":
            fmt += f"{count}s"
            plan.append((name, "bytes", 1))
            total += 1
        elif typ in PRIM:
            fmt += PRIM[typ] * count
            plan.append((name, "array" if len(entry) > 2 else "scalar", count))
            total += count
        else:
            sub_fmt, sub_plan, sub_n = _compile(structs, structs[typ])
            fmt += sub_fmt * count
            kind = "struct_array" if len(entry) > 2 else "struct"
            plan.append((name, kind, (count, sub_plan, sub_n)))
            total += sub_n * count
    return fmt, plan, total


def _apply(plan, values, pos: int):
    out: Dict[str, Any] = {}
    for name, kind, info in plan:
        if kind == "scalar":
            out[name] = values[pos]
            pos += 1
        elif kind == "array":
            out[name] = list(values[pos:pos + info])
            pos += info
        elif kind == "str":
            raw = values[pos]
            pos += 1
            out[name] = raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        elif kind == "bytes":
            out[name] = values[pos]
            pos += 1
        elif kind == "struct":
            _count, sub_plan, sub_n = info
            out[name], pos = _apply(sub_plan, values, pos)
        elif kind == "struct_array":
            count, sub_plan, sub_n = info
            items = []
            for _ in range(count):
                item, pos = _apply(sub_plan, values, pos)
                items.append(item)
            out[name] = items
    return out, pos


class _Layout:
    __slots__ = ("name", "fmt", "plan", "size")

    def __init__(self, name, structs, fields):
        body, plan, _n = _compile(structs, fields)
        self.name = name
        self.fmt = "<" + body
        self.plan = plan
        self.size = HEADER_SIZE + struct.calcsize(self.fmt)

    def parse(self, payload: bytes) -> Dict[str, Any]:
        values = struct.unpack(self.fmt, payload[:struct.calcsize(self.fmt)])
        body, _ = _apply(self.plan, values, 0)
        return body


_LAYOUT_CACHE: Dict[Tuple[int, int], _Layout] = {}


def get_layout(packet_format: int, packet_id: int) -> _Layout:
    key = (packet_format, packet_id)
    if key not in _LAYOUT_CACHE:
        spec = FORMATS[packet_format]
        name, fields = spec["packets"][packet_id]
        _LAYOUT_CACHE[key] = _Layout(name, spec["structs"], fields)
    return _LAYOUT_CACHE[key]


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


class UnsupportedPacket(Exception):
    """Raised for a packet format or id this module does not know about."""


def parse_header(data: bytes) -> Dict[str, Any]:
    values = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    return {name: value for (name, _t), value in zip(HEADER_FIELDS, values)}


def parse_packet(data: bytes) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Parse one UDP datagram into (header, body).

    Raises UnsupportedPacket for formats/ids we do not model, so callers can
    skip a 2024-format stream loudly rather than misreading it silently.
    """
    if len(data) < HEADER_SIZE:
        raise UnsupportedPacket(f"datagram too short: {len(data)} bytes")
    header = parse_header(data)
    fmt = header["m_packetFormat"]
    pid = header["m_packetId"]
    if fmt not in FORMATS:
        raise UnsupportedPacket(f"packet format {fmt} not supported (expected 2025 or 2026)")
    if pid not in FORMATS[fmt]["packets"]:
        raise UnsupportedPacket(f"packet id {pid} not valid for format {fmt}")
    layout = get_layout(fmt, pid)
    body = layout.parse(data[HEADER_SIZE:])
    if pid == 3:
        body["m_eventDetails"] = parse_event_details(
            body["m_eventStringCode"], body["m_eventDetailsRaw"], fmt
        )
    return header, body


# --------------------------------------------------------------------------
# Event packet - the details field is a union, so it must be read per event code
# --------------------------------------------------------------------------

EVENT_DETAILS = {
    "FTLP": [("vehicleIdx", "u8"), ("lapTime", "f32")],
    "RTMT": [("vehicleIdx", "u8"), ("reason", "u8")],
    "DRSD": [("reason", "u8")],
    "TMPT": [("vehicleIdx", "u8")],
    "RCWN": [("vehicleIdx", "u8")],
    "PENA": [
        ("penaltyType", "u8"), ("infringementType", "u8"), ("vehicleIdx", "u8"),
        ("otherVehicleIdx", "u8"), ("time", "u8"), ("lapNum", "u8"),
        ("placesGained", "u8"),
    ],
    "SPTP": [
        ("vehicleIdx", "u8"), ("speed", "f32"), ("isOverallFastestInSession", "u8"),
        ("isDriverFastestInSession", "u8"), ("fastestVehicleIdxInSession", "u8"),
        ("fastestSpeedInSession", "f32"),
    ],
    "STLG": [("numLights", "u8")],
    "DTSV": [("vehicleIdx", "u8")],
    "SGSV": [("vehicleIdx", "u8"), ("stopTime", "f32")],
    "FLBK": [("flashbackFrameIdentifier", "u32"), ("flashbackSessionTime", "f32")],
    "BUTN": [("buttonStatus", "u32")],
    "OVTK": [("overtakingVehicleIdx", "u8"), ("beingOvertakenVehicleIdx", "u8")],
    "SCAR": [("safetyCarType", "u8"), ("eventType", "u8")],
    # Collision gained a severity byte in the 2026 format.
    "COLL": [("vehicle1Idx", "u8"), ("vehicle2Idx", "u8")],
    # SSTA, SEND, DRSE, CHQF, LGOT, RDFL carry no payload.
}

EVENT_NAMES = {
    "SSTA": "Session Started", "SEND": "Session Ended", "FTLP": "Fastest Lap",
    "RTMT": "Retirement", "DRSE": "DRS Enabled", "DRSD": "DRS Disabled",
    "TMPT": "Team Mate In Pits", "CHQF": "Chequered Flag", "RCWN": "Race Winner",
    "PENA": "Penalty Issued", "SPTP": "Speed Trap Triggered", "STLG": "Start Lights",
    "LGOT": "Lights Out", "DTSV": "Drive Through Served", "SGSV": "Stop Go Served",
    "FLBK": "Flashback", "BUTN": "Button Status", "RDFL": "Red Flag",
    "OVTK": "Overtake", "SCAR": "Safety Car", "COLL": "Collision",
}


def parse_event_details(code: str, raw: bytes, packet_format: int = 2026) -> Dict[str, Any]:
    fields = EVENT_DETAILS.get(code)
    if fields is None:
        return {}
    if code == "COLL" and packet_format >= 2026:
        fields = fields + [("severity", "u8")]  # 0 = low, 1 = medium, 2 = high
    fmt = "<" + "".join(PRIM[t] for _n, t in fields)
    size = struct.calcsize(fmt)
    values = struct.unpack(fmt, raw[:size])
    return {name: value for (name, _t), value in zip(fields, values)}


# --------------------------------------------------------------------------
# Decoding helpers - the small conversions that are easy to get wrong
# --------------------------------------------------------------------------

# Every 4-element wheel array in this feed is ordered RL, RR, FL, FR.
# It is NOT front-left first; assuming otherwise silently swaps your axles.
WHEEL_ORDER = ("RL", "RR", "FL", "FR")
RL, RR, FL, FR = 0, 1, 2, 3


def wheels(values) -> Dict[str, Any]:
    """Label a 4-element wheel array: {'RL': .., 'RR': .., 'FL': .., 'FR': ..}."""
    return dict(zip(WHEEL_ORDER, values))


def normalise_dir(value: int) -> float:
    """Convert a packed int16 direction component to a float in [-1, 1]."""
    return value / 32767.0


def gforce(value, packet_format: int) -> float:
    """G-force is a float in 2025 but a quantised int16 (x1000) in 2026."""
    return value / 1000.0 if packet_format >= 2026 else float(value)


def split_time_ms(minutes_part: int, ms_part: int) -> int:
    """Recombine a split sector/delta time into total milliseconds.

    Sector times and deltas are sent as a whole-minutes byte plus a
    milliseconds remainder, so a 1:23.456 sector arrives as (1, 23456).
    """
    return minutes_part * 60_000 + ms_part


def format_ms(total_ms: int) -> str:
    """1:23.456 style formatting for a millisecond duration."""
    if total_ms <= 0:
        return "--:--.---"
    minutes, rem = divmod(int(total_ms), 60_000)
    seconds, ms = divmod(rem, 1000)
    return f"{minutes}:{seconds:02d}.{ms:03d}"


def lap_valid_flags(bits: int) -> Dict[str, bool]:
    """Decode m_lapValidBitFlags from the session history packet."""
    return {
        "lap": bool(bits & 0x01),
        "sector1": bool(bits & 0x02),
        "sector2": bool(bits & 0x04),
        "sector3": bool(bits & 0x08),
    }


def active_car_indices(header, lap_data_body, participants_body=None) -> List[int]:
    """Indices whose data is real.

    The car arrays are always full length (22 or 24) regardless of how many
    cars are in the session, so iterating the whole array gives you phantom
    entries. Result status 0 (invalid) and 1 (inactive) mark unused slots.
    """
    n = len(lap_data_body["m_lapData"])
    if participants_body is not None:
        n = min(n, participants_body["m_numActiveCars"])
    return [i for i in range(n) if lap_data_body["m_lapData"][i]["m_resultStatus"] not in (0, 1)]


__all__ = [
    "parse_packet", "parse_header", "parse_event_details", "get_layout",
    "UnsupportedPacket", "HEADER_SIZE", "PACKET_NAMES", "EVENT_NAMES",
    "FORMATS", "DOCUMENTED_SIZES", "MAX_CARS_2025", "MAX_CARS_2026",
    "WHEEL_ORDER", "RL", "RR", "FL", "FR", "wheels", "normalise_dir",
    "gforce", "split_time_ms", "format_ms", "lap_valid_flags",
    "active_car_indices",
]
