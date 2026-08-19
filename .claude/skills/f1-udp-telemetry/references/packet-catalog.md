# Packet catalog

Field-by-field reference for every packet. Sizes and layouts are encoded
machine-readably in `scripts/f1_packets.py`; this document covers what the
fields *mean* and where each packet misleads you.

Sizes shown as `2025 / 2026`. The 29-byte header is included in all sizes.

Contents:
- [Header](#header)
- [0 Motion](#0-motion) · [1 Session](#1-session) · [2 Lap Data](#2-lap-data)
- [3 Event](#3-event) · [4 Participants](#4-participants) · [5 Car Setups](#5-car-setups)
- [6 Car Telemetry](#6-car-telemetry) · [7 Car Status](#7-car-status)
- [8 Final Classification](#8-final-classification) · [9 Lobby Info](#9-lobby-info)
- [10 Car Damage](#10-car-damage) · [11 Session History](#11-session-history)
- [12 Tyre Sets](#12-tyre-sets) · [13 Motion Ex](#13-motion-ex)
- [14 Time Trial](#14-time-trial) · [15 Lap Positions](#15-lap-positions)
- [16 Car Telemetry 2](#16-car-telemetry-2-2026-only)

---

## Header

29 bytes, prefixed to every packet, identical in both formats.

| Field | Type | Meaning |
|---|---|---|
| `m_packetFormat` | uint16 | 2025 or 2026. **Read this first and dispatch on it** - the layouts differ. |
| `m_gameYear` | uint8 | e.g. 25 |
| `m_gameMajorVersion` / `m_gameMinorVersion` | uint8 | Game build |
| `m_packetVersion` | uint8 | Version of this packet type |
| `m_packetId` | uint8 | See catalog below |
| `m_sessionUID` | uint64 | Changes when a new session starts. Reset accumulated state when it changes. |
| `m_sessionTime` | float | Seconds since session start |
| `m_frameIdentifier` | uint32 | Rewinds after a flashback |
| `m_overallFrameIdentifier` | uint32 | Never rewinds - use for ordering/logging |
| `m_playerCarIndex` | uint8 | Index of your car in every per-car array |
| `m_secondaryPlayerCarIndex` | uint8 | Splitscreen player, 255 if none |

Packets sharing a `m_sessionTime` were produced on the same frame. Packets
listed as "rate as specified in menus" always go out together on the same
frame, so you can safely join Lap Data, Motion, Telemetry, Status and Motion Ex
by frame identifier without interpolating.

---

## 0 Motion

**1349 / 1325 bytes** · rate from menus · array of 22/24 `CarMotionData`

Position, velocity, orientation and G-force per car. Only transmitted while the
player is in control, so it stops during replays and menus.

| Field | Notes |
|---|---|
| `m_worldPositionX/Y/Z` | Metres, world space. Y is vertical. |
| `m_worldVelocityX/Y/Z` | Metres/second |
| `m_worldForwardDirX/Y/Z`, `m_worldRightDirX/Y/Z` | int16 packed - **divide by 32767.0** for a unit vector |
| `m_gForceLateral/Longitudinal/Vertical` | **2025: float. 2026: int16, divide by 1000.0.** This is the trap when porting a 2025 app forward. |
| `m_yaw`, `m_pitch`, `m_roll` | Radians |

Use `normalise_dir()` and `gforce(value, packet_format)` from `f1_packets.py`
rather than hardcoding either convention.

For a track map, plot `m_worldPositionX` against `m_worldPositionZ` (X/Z is the
ground plane; Y is elevation).

---

## 1 Session

**753 / 926 bytes** · 2 per second

Track, weather, rules and every assist/difficulty setting. Mostly static within
a session, but weather and marshal flags update live.

Key fields:

| Field | Notes |
|---|---|
| `m_trackId` | -1 = unknown. Track 42 (Madrid) is 2026-only. |
| `m_trackLength` | Metres - the denominator for lap-progress percentages |
| `m_sessionType`, `m_sessionTimeLeft`, `m_sessionDuration` | Seconds remaining/total |
| `m_formula` | 13 = F1 26 in the 2026 format |
| `m_numMarshalZones` + `m_marshalZones[21]` | Only read the first `m_numMarshalZones`. `m_zoneStart` is a 0..1 lap fraction; `m_zoneFlag` is the live flag state, so this is your yellow-flag sector display. |
| `m_numWeatherForecastSamples` + `m_weatherForecastSamples[64]` | Again, only the first N are valid. `m_timeOffset` is minutes ahead; samples cover multiple session types, so filter by `m_sessionType` before charting a forecast. |
| `m_forecastAccuracy` | 0 = perfect, 1 = approximate. Worth surfacing - an approximate forecast should not drive a confident strategy call. |
| `m_safetyCarStatus` | 0 none, 1 full, 2 virtual, 3 formation lap |
| `m_sector2LapDistanceStart`, `m_sector3LapDistanceStart` | Metres around the lap. Combine with `m_lapDistance` to place a car in a sector without waiting for the sector to complete. |
| `m_weekendStructure[12]` | First `m_numSessionsInWeekend` entries are session type IDs |

### 2026 additions (session packet)

| Field | Notes |
|---|---|
| `m_activeAeroTrackStatus` | 0 = Full, 1 = Partial |
| `m_numActiveAeroZonesFull` + `m_activeAeroZonesFull[8]` | Zones as 0..1 lap fractions with start **and end** |
| `m_numActiveAeroZonesPartial` + `m_activeAeroZonesPartial[8]` | Used when the track is in partial mode |
| `m_numDRSZones` + `m_drsZones[4]` | DRS zones are now explicit in the feed - previously you had to infer them |
| `m_startReactionTime` | Seconds; 0.0 with assisted starts |
| `m_antiLockBrakesAssist`, `m_tractionControlAssist` | Assist state (TC: 0 off, 1 medium, 2 full) |
| `m_dynamicRacingLineHiVis`, `m_dynamicRacingLineColourBlind` | Accessibility settings (colourblind: 1 protanopia, 2 deuteranopia, 3 tritanopia) |
| `m_recurringRewindPrompt` | 0 off, 1 on |

---

## 2 Lap Data

**1285 / 1399 bytes** · rate from menus · array of 22/24 `LapData`

The workhorse packet for timing screens.

| Field | Notes |
|---|---|
| `m_lastLapTimeInMS`, `m_currentLapTimeInMS` | Milliseconds |
| `m_sector1TimeMSPart` + `m_sector1TimeMinutesPart` | **Split representation.** Total ms = minutes x 60000 + ms part. Same pattern for sector 2, delta to car in front, and delta to leader. Use `split_time_ms()`. |
| `m_lapDistance` | Metres around the current lap; **negative before the start line on the out lap** |
| `m_totalDistance` | Metres this session; also can be negative initially |
| `m_safetyCarDelta` | Seconds |
| `m_carPosition`, `m_gridPosition`, `m_currentLapNum` | |
| `m_pitStatus` | 0 none, 1 pitting, 2 in pit area |
| `m_sector` | 0-indexed: 0 = sector 1 |
| `m_currentLapInvalid` | 0 valid, 1 invalid |
| `m_penalties` | Accumulated seconds to be added |
| `m_totalWarnings`, `m_cornerCuttingWarnings` | |
| `m_numUnservedDriveThroughPens`, `m_numUnservedStopGoPens` | |
| `m_driverStatus` | 0 garage, 1 flying lap, 2 in lap, 3 out lap, 4 on track |
| `m_resultStatus` | 0 invalid, 1 inactive, 2 active, 3 finished, 4 DNF, 5 DSQ, 6 not classified, 7 retired. **Your active-car filter.** |
| `m_pitLaneTimerActive`, `m_pitLaneTimeInLaneInMS`, `m_pitStopTimerInMS` | Pit lane total vs stationary stop time |
| `m_speedTrapFastestSpeed`, `m_speedTrapFastestLap` | km/h; lap 255 = not set |

Packet-level: `m_timeTrialPBCarIdx`, `m_timeTrialRivalCarIdx` (255 = invalid).

There is no sector 3 field here - derive it as lap time minus sectors 1 and 2,
or read the Session History packet which reports all three.

---

## 3 Event

**45 bytes** · when the event occurs

A 4-char code plus a **union** of 12 bytes. Only the member matching the code is
meaningful; reading the wrong member gives plausible-looking garbage.
`parse_event_details()` handles the dispatch.

| Code | Event | Payload |
|---|---|---|
| `SSTA` | Session started | none |
| `SEND` | Session ended | none |
| `FTLP` | Fastest lap | `vehicleIdx`, `lapTime` (**seconds as float**, not ms) |
| `RTMT` | Retirement | `vehicleIdx`, `reason` |
| `DRSE` | DRS enabled | none |
| `DRSD` | DRS disabled | `reason` (0 wet, 1 safety car, 2 red flag, 3 min lap not reached) |
| `TMPT` | Team mate in pits | `vehicleIdx` |
| `CHQF` | Chequered flag | none |
| `RCWN` | Race winner | `vehicleIdx` |
| `PENA` | Penalty issued | `penaltyType`, `infringementType`, `vehicleIdx`, `otherVehicleIdx`, `time`, `lapNum`, `placesGained` |
| `SPTP` | Speed trap | `vehicleIdx`, `speed`, `isOverallFastestInSession`, `isDriverFastestInSession`, `fastestVehicleIdxInSession`, `fastestSpeedInSession` |
| `STLG` | Start lights | `numLights` |
| `LGOT` | Lights out | none |
| `DTSV` | Drive through served | `vehicleIdx` |
| `SGSV` | Stop go served | `vehicleIdx`, `stopTime` |
| `FLBK` | Flashback | `flashbackFrameIdentifier`, `flashbackSessionTime` |
| `BUTN` | Button status | `buttonStatus` bitmask |
| `RDFL` | Red flag | none |
| `OVTK` | Overtake | `overtakingVehicleIdx`, `beingOvertakenVehicleIdx` |
| `SCAR` | Safety car | `safetyCarType`, `eventType` |
| `COLL` | Collision | `vehicle1Idx`, `vehicle2Idx`, **+ `severity` in 2026** (0 low, 1 medium, 2 high) |

`FLBK` matters for data integrity: on a flashback the game rewinds, so any
lap/sector you recorded after `flashbackSessionTime` should be discarded.
`m_overallFrameIdentifier` keeps increasing so you can tell replayed frames
from new ones.

---

## 4 Participants

**1284 / 1470 bytes** · every 5 seconds

Names, teams and driver IDs, indexed by vehicle index. Arrives infrequently, so
cache it and expect it to be missing for the first few seconds.

| Field | 2025 | 2026 |
|---|---|---|
| `m_driverId` | uint8, 255 = network human | **uint16, 65535 = network human** |
| `m_networkId` | uint8 | **uint16** |
| `m_teamId` | uint8 | **uint16** |
| `m_aiControlled` | 1 = AI, 0 = human | same |
| `m_myTeam` | 1 = My Team entry | same |
| `m_name[32]` | UTF-8, null-terminated, truncated with U+2026 | same |
| `m_techLevel` | F1 World tech level | same |
| `m_platform` | 1 Steam, 3 PlayStation, 4 Xbox, 6 Origin, 255 unknown | same |
| `m_numColours` + `m_liveryColours[4]` | RGB triples; only the first `m_numColours` are valid | same |

Packet-level: `m_numActiveCars`.

Resolve display names as: if `m_driverId` is the network-human sentinel, use
`m_name`; otherwise prefer `m_name` and fall back to the driver ID table.

---

## 5 Car Setups

**1133 / 1233 bytes** · 2 per second

Wings, differential, camber/toe, suspension, ride height, brakes, tyre
pressures, ballast, fuel load. Plus packet-level `m_nextFrontWingValue`
(player only, value after the next pit stop).

**Online you only see your own setup**, and spectators see none - independent of
the "Your Telemetry" setting. See `data-visibility.md`.

---

## 6 Car Telemetry

**1352 / 1448 bytes** · rate from menus · array of 22/24 `CarTelemetryData`

| Field | Notes |
|---|---|
| `m_speed` | km/h (uint16) |
| `m_throttle`, `m_brake` | 0.0-1.0 |
| `m_steer` | -1.0 full left to 1.0 full right |
| `m_clutch` | 0-100 |
| `m_gear` | 1-8, 0 = N, -1 = R |
| `m_engineRPM` | |
| `m_drs` | 0 off, 1 on |
| `m_revLightsPercent`, `m_revLightsBitValue` | Bit 0 = leftmost LED, bit 14 = rightmost |
| `m_brakesTemperature[4]` | Celsius, uint16, **RL RR FL FR** |
| `m_tyresSurfaceTemperature[4]`, `m_tyresInnerTemperature[4]` | Celsius, uint8, RL RR FL FR |
| `m_engineTemperature` | **uint16 in 2025, uint8 in 2026** |
| `m_tyresPressure[4]` | PSI, RL RR FL FR |
| `m_surfaceType[4]` | Surface ID per wheel - detect off-track excursions |

Packet-level: `m_mfdPanelIndex`, `m_mfdPanelIndexSecondaryPlayer`,
`m_suggestedGear` (0 = none suggested). All player-only.

---

## 7 Car Status

**1239 / 1445 bytes** · rate from menus

Fuel, ERS, tyres, DRS availability, flags. Heavily affected by the "Your
Telemetry" restriction.

| Field | Notes |
|---|---|
| `m_tractionControl` | 0 off, 1 medium, 2 full |
| `m_fuelMix` | 0 lean, 1 standard, 2 rich, 3 max |
| `m_fuelInTank`, `m_fuelCapacity` | Mass |
| `m_fuelRemainingLaps` | Laps of fuel relative to target - **negative means under-fuelled**, this is the MFD delta, not an absolute count |
| `m_maxRPM`, `m_idleRPM`, `m_maxGears` | Constant per car - handy for rev-light scaling |
| `m_drsAllowed` | 0/1 |
| `m_drsActivationDistance` | Metres until DRS becomes available; 0 = not available |
| `m_actualTyreCompound` | C0-C6 etc. - see `f1_enums.ACTUAL_TYRE_COMPOUNDS`. C6 = 22. |
| `m_visualTyreCompound` | Soft/medium/hard as shown on the sidewall. The actual↔visual mapping changes per race. |
| `m_tyresAgeLaps` | |
| `m_vehicleFIAFlags` | -1 unknown, 0 none, 1 green, 2 blue, 3 yellow |
| `m_enginePowerICE`, `m_enginePowerMGUK` | Watts |
| `m_ersStoreEnergy` | Joules (max 4 MJ) |
| `m_ersDeployMode` | 0 none, 1 medium, 2 hotlap, 3 boost (called "overtake" in the 2025 docs - same value) |
| `m_ersHarvestedThisLapMGUK/MGUH`, `m_ersDeployedThisLap` | Joules |
| `m_ersHarvestLimitPerLap` | **2026 only** - the per-lap harvest cap, needed to show harvest as a percentage under 2026 regs |
| `m_networkPaused` | |

---

## 8 Final Classification

**1042 / 1134 bytes** · once at the end of a race

Positions, laps, points, pit stops, best lap, total race time (double,
seconds, excluding penalties), penalty totals, and up to 8 tyre stints with
`m_tyreStintsActual/Visual/EndLaps`.

`m_resultReason` (retired / terminal damage / black flagged / mechanical
failure / session simulated ...) explains a DNF - use it rather than inferring.

Only the first `m_numCars` entries are meaningful.

---

## 9 Lobby Info

**954 / 1062 bytes** · twice per second while in a lobby

Per player: AI flag, team, nationality, platform, name, car number, telemetry
setting, tech level and `m_readyStatus` (0 not ready, 1 ready, 2 spectating).
`m_teamId` is uint8 in 2025 (255 = none) and uint16 in 2026 (65535 = none).

---

## 10 Car Damage

**1041 / 1133 bytes** · 10 per second

`m_tyresWear[4]` is a float percentage; everything else is uint8 percentage or
a 0/1 fault flag. Wing damage is split front-left / front-right / rear. Engine
wear is broken out per component (MGU-H, ES, CE, ICE, MGU-K, TC) alongside
`m_engineBlown` and `m_engineSeized`. `m_tyreBlisters[4]` is separate from wear
and is what actually ends a stint early on aggressive setups.

All wheel arrays are RL RR FL FR. Restricted for other players.

---

## 11 Session History

**1460 bytes (both)** · 20 per second, **cycling one car per packet**

This packet does not describe all cars at once. Each transmission covers a
single `m_carIdx`, cycling through the field, so in a 20-car race you get each
car roughly once per second. Accumulate into a dict keyed by car index; do not
treat consecutive packets as the same car.

Contains up to 100 laps of `LapHistoryData` (lap time plus all three sector
times in the split minutes/ms form, and `m_lapValidBitFlags`) and up to 8 tyre
stints. `m_numLaps` includes the current partial lap - the last entry will have
zeros for sectors not yet completed.

`m_lapValidBitFlags`: 0x01 lap valid, 0x02 sector 1, 0x04 sector 2, 0x08
sector 3. Use `lap_valid_flags()`.

After the final classification packet, a bulk update of every car's history is
sent - the natural moment to write out a race report.

---

## 12 Tyre Sets

**231 bytes (both)** · 20 per second, cycling one car per packet

20 sets (13 dry + 7 wet) with compound, wear, availability, recommended
session, `m_lifeSpan` (laps left), `m_usableLife` (recommended max laps),
`m_lapDeltaTime` (ms versus the fitted set) and `m_fitted`. Packet-level
`m_fittedIdx` indexes the currently fitted set.

Entirely hidden for players with restricted telemetry.

---

## 13 Motion Ex

**273 bytes (both)** · rate from menus · **player car only**

Suspension position/velocity/acceleration, wheel speed, slip ratio, slip angle,
lateral/longitudinal/vertical forces, local and angular velocity and
acceleration, front wheels angle, front/rear aero (plank) heights, front/rear
roll angle, chassis yaw and pitch relative to the direction of motion, wheel
camber and camber gain.

Every 4-element array here is RL RR FL FR. This is the packet for motion rigs,
driver-coaching tools and understeer/oversteer analysis (compare front vs rear
slip angles).

---

## 14 Time Trial

**101 / 104 bytes** · 1 per second · **Time Trial mode only**

Three `TimeTrialDataSet` blocks: player session best, personal best, rival.
Each has car index, team, lap and sector times in ms, assist flags,
`m_equalCarPerformance`, `m_customSetup` and `m_valid`. `m_teamId` widened from
uint8 to uint16 in 2026.

Always check `m_valid` before displaying - an unset PB is not a 0.000 lap.

---

## 15 Lap Positions

**1131 / 1231 bytes** · 1 per second

`m_positionForVehicleIdx[50][cars]` - the position each car held at the start
of each lap, for building a position-change chart. `0` means no record.

Only 50 laps fit in one packet. Longer races send two packets with different
`m_lapStart` values; merge them on `m_lapStart` rather than overwriting, or you
will lose the first half of a 60-lap race.

---

## 16 Car Telemetry 2 (2026 only)

**269 bytes** · rate from menus · array of 24 `CarTelemetry2Data`

Split out because the original telemetry packet was growing too large.

| Field | Notes |
|---|---|
| `m_activeAeroMode` | 0 = corner mode, 1 = straight mode |
| `m_activeAeroAvailable` | 0/1 |
| `m_activeAeroActivationDistance` | Metres until available; 0 = not available |
| `m_overtakeAvailable` | 0/1 - the 2026 "Boost" replacement for DRS-style overtaking aid |
| `m_overtakeActive` | 0/1 |
| `m_overtakeActivationDistance` | Metres until available; 0 = not available |
| `m_2026Regulations` | 0 = pre-2026 car, 1 = 2026 regulations apply |
| `m_drivingWrongWay` | 0/1 |

`m_2026Regulations` is the reliable per-car test for whether active aero and
boost apply at all - a 2026-format stream can still contain classic cars.
