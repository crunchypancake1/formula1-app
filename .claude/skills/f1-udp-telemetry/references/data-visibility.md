# Data visibility: what you can actually read for each car

Three separate mechanisms decide whether a field holds real data. They stack,
so a field can be zero for more than one reason. Getting this wrong is the
single most common cause of "my app works in single player but shows nothing
online" bug reports.

The same rules are encoded in `scripts/f1_visibility.py` if you want to query
them at runtime - `describe_availability(packet_id, field)` answers "who can I
read this for?", and the `*_hidden()` helpers implement the detection
heuristics from section 4.

Contents:
1. Player-only packets
2. The "Your Telemetry" restriction (other players' cars)
3. Unused array slots
4. Practical detection strategy

---

## 1. Player-only packets

Some packets carry data for exactly one car regardless of session type. There
is no setting that changes this - the game simply never sends the other cars'
values.

| Packet | Scope | Notes |
|---|---|---|
| Motion Ex (13) | Player's car only | Suspension, slip, wheel forces, camber, chassis attitude. Intended for motion rigs. No car index field - it is implicitly the player. |
| Time Trial (14) | Player, player's PB, rival | Only sent in Time Trial mode; absent everywhere else. |
| Motion (0) | All cars, but only sent while the player is in control | Stops during replays/cutscenes. |

Player-only **fields** inside otherwise-public packets:

| Field | Packet |
|---|---|
| `m_pitStopWindowIdealLap`, `m_pitStopWindowLatestLap`, `m_pitStopRejoinPosition` | Session (1) |
| `m_nextFrontWingValue` | Car Setups (5) |
| `m_mfdPanelIndex`, `m_mfdPanelIndexSecondaryPlayer`, `m_suggestedGear` | Car Telemetry (6) |
| `m_startReactionTime` (2026) | Session (1) - 0.0 if assisted starts are on |

**Car Setups (5) is a special case.** In multiplayer you only ever see your own
setup. Other players' entries are blank *regardless of their "Your Telemetry"
setting*, and spectators see no setups at all. Do not build a setup-comparison
feature that assumes rival data is obtainable online - it is not.

---

## 2. The "Your Telemetry" restriction

Each player chooses Restricted (the default) or Public in the game's telemetry
options. When a driver is Restricted, the fields below arrive as **zero** for
that driver's car in everyone else's UDP stream. You always see your own data
in full, whatever your own setting says.

Because the restricted values are zeroes rather than a flag, there is no
explicit "this is hidden" marker on the field itself - see section 4 for how to
tell hidden from genuinely zero.

### Car Status packet (7)
`m_fuelInTank`, `m_fuelCapacity`, `m_fuelMix`, `m_fuelRemainingLaps`,
`m_frontBrakeBias`, `m_ersDeployMode`, `m_ersStoreEnergy`,
`m_ersDeployedThisLap`, `m_ersHarvestedThisLapMGUK`,
`m_ersHarvestedThisLapMGUH`, `m_enginePowerICE`, `m_enginePowerMGUK`

### Car Damage packet (10)
`m_frontLeftWingDamage`, `m_frontRightWingDamage`, `m_rearWingDamage`,
`m_floorDamage`, `m_diffuserDamage`, `m_sidepodDamage`, `m_engineDamage`,
`m_gearBoxDamage`, `m_tyresWear` (all four), `m_tyresDamage` (all four),
`m_brakesDamage` (all four), `m_drsFault`, `m_engineMGUHWear`,
`m_engineESWear`, `m_engineCEWear`, `m_engineICEWear`, `m_engineMGUKWear`,
`m_engineTCWear`

### Tyre Sets packet (12)
**All** data in the packet, for the restricted player's car.

### What is NOT restricted
Speed, throttle, brake, steering, gear, RPM, DRS, tyre temperatures and
pressures, lap times, sector times, positions, penalties, tyre compound and
age, damage-free status fields like `m_maxRPM`. So a live timing board or a
rival-pace tool works fine online; a fuel/ERS strategy tool for rivals does not.

The restriction can be toggled mid-session and takes effect immediately, so a
car's fuel data can appear or vanish between packets. Treat visibility as a
per-packet property, not a session-level one.

### Names
Player names in Participants (4) and Lobby Info (9) only show real online IDs
if that player enabled "Show online ID / gamertags". Otherwise you get the
driver name. On Xbox names are always the driver name; on PlayStation the LAN
name is used only in LAN games.

`m_showOnlineNames` on each participant tells you which case you are in.

---

## 3. Unused array slots

Every per-car array is sent at full length - 22 entries in the 2025 format, 24
in 2026 - no matter how many cars are actually in the session. The unused tail
is not cleared to anything meaningful.

Filter with two checks, in this order:

1. `m_numActiveCars` from the Participants packet (4) bounds the array.
2. Per car, `m_resultStatus` in Lap Data (2): values 0 (invalid) and 1
   (inactive) mean that index carries no usable data. Anything else - active,
   finished, DNF, disqualified, not classified, retired - is real.

`active_car_indices()` in `scripts/f1_packets.py` implements exactly this.

Skipping step 2 is what produces leaderboards with phantom cars sitting in P0
with a 0.000 lap time.

---

## 4. Practical detection strategy

You cannot distinguish "restricted" from "genuinely zero" from a single field
in a single packet, because both look like `0`. Use context instead:

**Whole-group heuristic.** The restriction hides fields in groups. Real fuel
data is never `m_fuelInTank == 0 and m_fuelCapacity == 0 and
m_fuelRemainingLaps == 0` on a running car - a car with no fuel capacity is not
physically possible. Judge the group, not one field:

```python
def fuel_hidden(car_status):
    # Capacity is a constant of the car; zero means the value was withheld.
    return car_status["m_fuelCapacity"] == 0.0

def ers_hidden(car_status):
    # An F1 car's ERS store is never exactly zero with no harvest at all.
    return (car_status["m_ersStoreEnergy"] == 0.0
            and car_status["m_ersHarvestedThisLapMGUK"] == 0.0
            and car_status["m_ersHarvestedThisLapMGUH"] == 0.0)

def damage_hidden(car_damage, car_status):
    # Ambiguous by itself: an undamaged car legitimately reads all zeroes.
    # Cross-check against a field that is never zero when data is flowing.
    return car_damage["m_tyresWear"] == [0.0, 0.0, 0.0, 0.0] and fuel_hidden(car_status)
```

Damage is the awkward one: a clean car on lap 1 really does read zero
everywhere. If you need certainty, watch over time - tyre wear on a moving car
climbs within a lap, so a car that has completed a flying lap with exactly
0.0 wear on all four corners is restricted.

**Design guidance.** Show "—" or "hidden" rather than "0%" when a group looks
withheld. Users reading a timing screen will trust a zero and conclude a rival
has no tyre wear; an explicit hidden marker is honest and costs nothing.

**Your own car is always complete.** `m_playerCarIndex` in the header points at
it. Features that need full data (fuel calculators, ERS deployment planners,
setup analysis) should be built player-first and treat rival data as a bonus
that may not arrive.
