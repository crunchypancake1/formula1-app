---
name: f1-udp-telemetry
description: Authoritative reference for the EA SPORTS F1 25 / F1 25 2026 Season Pack UDP telemetry data structures - byte-exact packet layouts for formats 2025 and 2026, ID lookup tables, and the rules governing which fields are available for all cars, only for the player, or hidden by a driver's telemetry privacy setting. Use this skill whenever the user is reading, parsing, modelling, or debugging F1 game telemetry data - if they mention packet formats 2025/2026, packet IDs, PacketHeader/CarTelemetryData/PacketSessionData/MotionEx or any m_ field name, tyre compound or team or driver IDs, restricted telemetry, or are working on an F1 dashboard, timing screen, strategy tool, logger or overlay - even when they don't say "UDP" or name a packet explicitly.
---

# F1 UDP telemetry data structures

The F1 games broadcast game state as UDP datagrams: 16 packet types in the
2025 format, 17 in the 2026 Season Pack. Each is a packed C struct with no
padding, so parsing is fast but unforgiving - one wrong field width shifts
everything after it and produces plausible-looking garbage rather than an
error.

This skill is a reference for those structures and the rules about which data
is actually populated. It is not an app scaffold: assume the user already has a
working project and needs accurate answers about layouts, field semantics and
availability while they change it.

## Bundled files

| File | Use it for |
|---|---|
| `references/packet-catalog.md` | Every packet: fields, units, meanings, per-packet traps |
| `references/data-visibility.md` | Public vs restricted vs player-only data, in prose |
| `scripts/f1_packets.py` | All 33 layouts as data + a parser, decoding helpers |
| `scripts/f1_visibility.py` | The same availability rules, machine-readable |
| `scripts/f1_enums.py` | Team, driver, track, nationality, compound, penalty, button tables |
| `scripts/verify_sizes.py` | Self-test proving every layout matches the documented size |

Read `packet-catalog.md` whenever field semantics matter beyond names - it
covers units, sentinel values and the specific way each packet misleads you.
Read `data-visibility.md` for anything involving multiplayer or other cars.

The scripts are usable two ways: import them, or read them as a precise
statement of the layout when checking someone else's parser. They are standard
library only, no dependencies.

## Verifying layouts

`scripts/verify_sizes.py` compiles every layout and compares it against the
byte size EA documents for that packet. Because the structs are packed, a size
match is strong evidence the whole field sequence is right, and a mismatch
localises the error to one packet.

```
python scripts/verify_sizes.py        # all 33 layouts, both formats
python scripts/verify_sizes.py -v     # also round-trips a synthetic packet
```

This is the fastest way to check a hand-written parser too: compare its struct
format string's `calcsize` against `DOCUMENTED_SIZES` in `f1_packets.py`. If a
user reports fields going wrong partway through a packet, that is nearly always
a width error earlier in the same struct, and this finds it.

## Availability rules

Three independent mechanisms leave fields empty, and they stack - a field can
be zero for more than one reason at once. This is the most common source of
"works offline, broken online" confusion.

**Player-only.** Motion Ex (13) and Time Trial (14) describe the player's car
alone, in every session type. Motion (0) covers all cars but is only sent while
the player is in control. Some individual fields are player-only inside
otherwise-public packets - the pit window fields in Session, `m_suggestedGear`
and the MFD panel indices in Car Telemetry, `m_nextFrontWingValue` in Car
Setups.

**Car Setups (5) is a special case.** Online you see only your own setup, and
spectators see none, regardless of anyone's privacy setting. A rival
setup-comparison feature is not possible online.

**The "Your Telemetry" restriction.** Each driver chooses Restricted (the
default) or Public. For a restricted driver, other players receive zeros for
fuel, ERS, engine power and brake bias in Car Status; all damage and wear
fields in Car Damage; and the entire Tyre Sets packet. Speed, throttle, brake,
steering, gear, RPM, DRS, tyre temperatures and pressures, lap and sector
times, positions, penalties, and tyre compound and age are never restricted -
so live timing and pace comparison work online, while rival fuel and strategy
modelling do not. The setting can change mid-session, so treat visibility as a
per-packet property rather than something fixed.

**Unused array slots.** Car arrays are always full length - 22 entries in 2025,
24 in 2026 - regardless of how many cars are present. Filter on
`m_numActiveCars` from Participants and per-car `m_resultStatus`, where 0
(invalid) and 1 (inactive) mark empty slots and every other value including
finished, DNF and disqualified is a real car.

There is no flag marking withheld data; restricted fields simply arrive as
zero, indistinguishable from a legitimate zero on any single field. Detection
means finding a value that cannot legitimately be zero on a running car -
`m_fuelCapacity` is a constant of the car, and a car that has completed a
flying lap never has exactly 0.0 wear on all four tyres. `f1_visibility.py`
implements these group heuristics, and `describe_availability(packet_id,
field)` answers the "who can I read this for?" question directly.

Where data is withheld, rendering "—" or "hidden" rather than "0%" matters:
a zero on a timing screen reads as fact, and users will conclude a rival has no
tyre wear.

## Structural traps

These are properties of the data itself, and they cause bugs that survive to
production because the wrong output still looks reasonable.

**Dispatch on `m_packetFormat`.** Both formats stream on the same port with an
identical 29-byte header, but the bodies differ. A parser assuming one format
reads the other as noise. Users can also select 2024 in game, which this skill
does not cover - detect it and say so plainly rather than guessing.

**Wheel arrays are ordered RL, RR, FL, FR.** Not front-left first. Every
4-element array uses this order - tyre temperatures, pressures, wear, brake
temperatures, suspension, slip, forces, camber. Assuming FL-first swaps the
axles and the data still looks plausible.

**Sector times and gaps are split** into a whole-minutes byte and a
milliseconds remainder: total ms = `minutes * 60000 + ms`. Applies to sector 1
and 2 in Lap Data, both delta fields, and all three sectors in Session History.
Ignoring the minutes part works at short circuits and breaks at Spa.

**The Event packet's details field is a union.** Only the member matching the
4-char code is valid; reading another member yields convincing nonsense. The
`FTLP` lap time is *seconds as a float*, unlike every other time field in the
feed, which is milliseconds.

**Session History (11) and Tyre Sets (12) cycle one car per packet** rather
than describing all cars at once. Key them by `m_carIdx`; consecutive packets
are different drivers.

**Lap Positions (15) holds only 50 laps.** Longer races send a second packet
with a different `m_lapStart`; merge on that field rather than overwriting.

**`m_sessionUID` changing means a new session.** Any accumulated state keyed to
the old session is stale.

**Flashbacks rewind `m_frameIdentifier`** but not `m_overallFrameIdentifier`.
The `FLBK` event carries the session time rewound to, which is what invalidates
anything recorded after it.

## 2025 to 2026 changes

The migration points for an existing F1 25 project. Full detail per packet is
in `packet-catalog.md`.

| Change | Impact |
|---|---|
| Max cars 22 → 24 (Audi and Cadillac join) | Nearly every packet size changed |
| G-forces became quantised `int16` | **Divide by 1000.0** - previously plain floats |
| `m_engineTemperature` uint16 → uint8 | Shifts every later field in Car Telemetry |
| `m_driverId`, `m_networkId`, `m_teamId` uint8 → uint16 | Network-human sentinel is **65535**, not 255; team IDs above 255 now exist (Audi 485, Cadillac 486) |
| New packet 16, Car Telemetry 2 | Active aero, boost/overtake, wrong-way flag, `m_2026Regulations` |
| Session packet gained aero and DRS zones | DRS zone boundaries are explicit at last; plus active aero zones and start reaction time |
| `m_ersHarvestLimitPerLap` added to Car Status | The per-lap harvest cap under 2026 regs |
| Collision event gained `severity` | 0 low, 1 medium, 2 high |
| New track Madrid (42), formula ID 13 = F1 26 | |
| ERS deploy mode 3 renamed Overtake → Boost | Same value, new official name |

A 2026-format stream can still contain classic cars, so gate any active-aero or
boost handling on per-car `m_2026Regulations` rather than on the packet format.

## Accuracy

Field names match EA's specification exactly, including the `m_` prefix, so the
official PDF can be read alongside this. When something isn't covered here - a
new ID after a game patch, an undocumented value - say so rather than inventing
a plausible mapping. Unknown IDs are normal: the lookup helpers in
`f1_enums.py` degrade to `"Team 512"` style placeholders instead of raising,
and app code should do the same.
