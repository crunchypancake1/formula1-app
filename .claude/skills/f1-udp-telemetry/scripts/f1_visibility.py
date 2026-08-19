"""
f1_visibility.py - Which fields actually hold data, for which cars.

Three independent mechanisms leave fields empty in the F1 UDP feed:

  1. Player-only packets and fields - never sent for other cars, in any mode.
  2. The "Your Telemetry" privacy setting - a driver set to Restricted has
     certain fields zeroed in everyone else's stream.
  3. Unused array slots - car arrays are always full length (22 or 24)
     regardless of how many cars are in the session.

None of these are flagged in the wire data; restricted fields simply arrive as
zero. That makes them indistinguishable from a legitimate zero on any single
field, which is why the helpers below reason over field *groups* and over
constants that can never legitimately be zero on a running car.

The tables here mirror references/data-visibility.md. Keeping them in code as
well as prose means an app can decide at runtime whether to render a value or
an explicit "hidden" marker, instead of showing a rival with 0% tyre wear.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

# --------------------------------------------------------------------------
# 1. Player-only data
# --------------------------------------------------------------------------

# Packets that describe the player's car only, whatever the session type.
PLAYER_ONLY_PACKETS: Dict[int, str] = {
    13: "Motion Ex - suspension, slip, wheel forces, chassis attitude",
    14: "Time Trial - only sent in Time Trial mode at all",
}

# Packets sent for all cars, but only while the player is in control
# (they stop during replays, cutscenes and menus).
PLAYER_CONTROL_GATED_PACKETS: Dict[int, str] = {
    0: "Motion",
}

# Individual fields that are meaningful only for the player, inside packets
# that otherwise describe every car.
PLAYER_ONLY_FIELDS: Dict[int, Set[str]] = {
    1: {  # Session
        "m_pitStopWindowIdealLap",
        "m_pitStopWindowLatestLap",
        "m_pitStopRejoinPosition",
        "m_startReactionTime",  # 2026; also 0.0 when assisted starts are on
    },
    5: {  # Car Setups
        "m_nextFrontWingValue",
    },
    6: {  # Car Telemetry
        "m_mfdPanelIndex",
        "m_mfdPanelIndexSecondaryPlayer",
        "m_suggestedGear",
    },
}

# Car Setups is a special case: online you see only your own setup, and
# spectators see none - independent of anyone's "Your Telemetry" setting.
SETUP_PACKET_ID = 5

# --------------------------------------------------------------------------
# 2. The "Your Telemetry" restriction
# --------------------------------------------------------------------------
# Fields zeroed for a car whose driver has telemetry set to Restricted (the
# default). Your own car is always complete regardless of your own setting.
# The setting can change mid-session, so treat visibility as a per-packet
# property rather than something fixed for the session.

RESTRICTED_FIELDS: Dict[int, Set[str]] = {
    7: {  # Car Status
        "m_fuelInTank", "m_fuelCapacity", "m_fuelMix", "m_fuelRemainingLaps",
        "m_frontBrakeBias", "m_ersDeployMode", "m_ersStoreEnergy",
        "m_ersDeployedThisLap", "m_ersHarvestedThisLapMGUK",
        "m_ersHarvestedThisLapMGUH", "m_enginePowerICE", "m_enginePowerMGUK",
    },
    10: {  # Car Damage
        "m_frontLeftWingDamage", "m_frontRightWingDamage", "m_rearWingDamage",
        "m_floorDamage", "m_diffuserDamage", "m_sidepodDamage",
        "m_engineDamage", "m_gearBoxDamage", "m_tyresWear", "m_tyresDamage",
        "m_brakesDamage", "m_drsFault", "m_engineMGUHWear", "m_engineESWear",
        "m_engineCEWear", "m_engineICEWear", "m_engineMGUKWear",
        "m_engineTCWear",
    },
    12: "ALL",  # Tyre Sets - the entire packet is withheld for that car
}

# Explicitly NOT restricted, so rival-facing features built on these work
# online: speed, throttle, brake, steer, gear, RPM, DRS, tyre temperatures and
# pressures, lap and sector times, positions, penalties, tyre compound and age,
# and constants such as m_maxRPM.

# Names are a separate control: participants and lobby entries only carry real
# online IDs when that player enabled "show online ID". m_showOnlineNames says
# which case you are in. Xbox always reports the driver name.


def is_player_only(packet_id: int, field: Optional[str] = None) -> bool:
    """True if this packet, or this field within it, only ever has player data."""
    if packet_id in PLAYER_ONLY_PACKETS:
        return True
    if field is None:
        return False
    return field in PLAYER_ONLY_FIELDS.get(packet_id, set())


def is_restricted_field(packet_id: int, field: str) -> bool:
    """True if this field is hidden for drivers with restricted telemetry."""
    entry = RESTRICTED_FIELDS.get(packet_id)
    if entry is None:
        return False
    if entry == "ALL":
        return True
    return field in entry


def describe_availability(packet_id: int, field: str) -> str:
    """One-line explanation of who you can read this field for.

    Useful when surfacing a field in a UI builder, or when explaining to a user
    why a value is empty.
    """
    if is_player_only(packet_id, field):
        return "player's car only"
    if packet_id == SETUP_PACKET_ID:
        return "player's car only online; all cars offline; none when spectating"
    if is_restricted_field(packet_id, field):
        return "all cars, but zeroed for drivers with restricted telemetry"
    return "all active cars"


# --------------------------------------------------------------------------
# 3. Detecting withheld data at runtime
# --------------------------------------------------------------------------
# Restricted fields arrive as 0, so detection means finding a value that cannot
# legitimately be zero. Judge the group, not the individual field.


def fuel_hidden(car_status: Dict[str, Any]) -> bool:
    """Tank capacity is a constant of the car - zero means withheld."""
    return car_status.get("m_fuelCapacity", 0.0) == 0.0


def ers_hidden(car_status: Dict[str, Any]) -> bool:
    """A running car always has some stored or harvested energy."""
    return (
        car_status.get("m_ersStoreEnergy", 0.0) == 0.0
        and car_status.get("m_ersHarvestedThisLapMGUK", 0.0) == 0.0
        and car_status.get("m_ersHarvestedThisLapMGUH", 0.0) == 0.0
    )


def damage_hidden(car_damage: Dict[str, Any],
                  car_status: Optional[Dict[str, Any]] = None,
                  laps_completed: int = 0) -> bool:
    """Ambiguous alone - an undamaged car on lap 1 also reads all zeroes.

    Two ways to disambiguate, in order of reliability:
      * Cross-check the fuel group, which is withheld by the same setting.
      * Tyre wear on a car that has completed a flying lap is never exactly
        0.0 on all four corners.
    """
    all_zero = list(car_damage.get("m_tyresWear", [0.0] * 4)) == [0.0] * 4
    if not all_zero:
        return False
    if car_status is not None:
        return fuel_hidden(car_status)
    return laps_completed >= 1


def tyre_sets_hidden(tyre_sets_body: Dict[str, Any]) -> bool:
    """The whole packet is withheld, so every set reads as empty."""
    sets = tyre_sets_body.get("m_tyreSetData", [])
    return all(s.get("m_lifeSpan", 0) == 0 and s.get("m_actualTyreCompound", 0) == 0
               for s in sets)


def visibility_report(car_idx: int, player_idx: int,
                      car_status: Optional[Dict[str, Any]] = None,
                      car_damage: Optional[Dict[str, Any]] = None,
                      laps_completed: int = 0) -> Dict[str, bool]:
    """Summarise which field groups are readable for one car.

    Your own car is always complete, so short-circuit on the player index
    rather than running the heuristics against it.
    """
    if car_idx == player_idx:
        return {"fuel": True, "ers": True, "damage": True, "is_player": True}
    return {
        "fuel": not (car_status is None or fuel_hidden(car_status)),
        "ers": not (car_status is None or ers_hidden(car_status)),
        "damage": not (car_damage is None
                       or damage_hidden(car_damage, car_status, laps_completed)),
        "is_player": False,
    }


# --------------------------------------------------------------------------
# 4. Unused array slots
# --------------------------------------------------------------------------
# See active_car_indices() in f1_packets.py. Result status 0 (invalid) and
# 1 (inactive) mark slots that carry no usable data; every other value,
# including finished, DNF and disqualified, is a real car.

EMPTY_SLOT_RESULT_STATUSES = (0, 1)


__all__ = [
    "PLAYER_ONLY_PACKETS", "PLAYER_CONTROL_GATED_PACKETS", "PLAYER_ONLY_FIELDS",
    "RESTRICTED_FIELDS", "EMPTY_SLOT_RESULT_STATUSES", "SETUP_PACKET_ID",
    "is_player_only", "is_restricted_field", "describe_availability",
    "fuel_hidden", "ers_hidden", "damage_hidden", "tyre_sets_hidden",
    "visibility_report",
]
