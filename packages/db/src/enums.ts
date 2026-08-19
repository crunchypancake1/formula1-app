/**
 * Enum-valued columns as TypeScript types.
 *
 * Two storage forms reach this module, and both end up as the same `Enum<T>`
 * string so callers never have to care which they came from:
 *
 * - **Names.** Most tables store the resolved name, written by `safe_enum_name`
 *   (listener/database/repositories/base.py), which degrades a value it does not
 *   recognise to `UNKNOWN_<value>` rather than failing the write — an enum member
 *   added by a game patch must never stop collection.
 * - **Codes.** `telemetry.car_frame` stores the game's raw integer instead, in a
 *   SMALLINT. It is the one table where eleven text columns are worth ~66 bytes a
 *   row, and it is read exclusively through this package. `enumFromCode` below
 *   applies the identical `UNKNOWN_<n>` degradation at read time.
 *
 * Either way every union carries the `UNKNOWN_<n>` escape hatch and callers must
 * handle it — `displayEnum` is the usual way.
 */

/** A known enum member name, or the `UNKNOWN_<value>` fallback for an unrecognised code. */
export type Enum<T extends string> = T | `UNKNOWN_${number}`;

/** Maps a game enum's integer values to their member names. */
export type EnumCodes<T extends string> = Readonly<Record<number, T>>;

/**
 * Resolve a raw enum code from `telemetry.car_frame` to its member name.
 *
 * A code with no entry in the table degrades to `UNKNOWN_<n>` rather than
 * throwing, which is what lets the listener store whatever the game sends —
 * including a member added by a patch this build predates.
 */
export function enumFromCode<T extends string>(
  codes: EnumCodes<T>,
  code: number | null | undefined
): Enum<T> | null {
  if (code === null || code === undefined) return null;
  return codes[code] ?? (`UNKNOWN_${code}` as Enum<T>);
}

export type SessionType = Enum<
  | "UNKNOWN"
  | "PRACTICE_1"
  | "PRACTICE_2"
  | "PRACTICE_3"
  | "SHORT_PRACTICE"
  | "QUALIFYING_1"
  | "QUALIFYING_2"
  | "QUALIFYING_3"
  | "SHORT_QUALIFYING"
  | "ONE_SHOT_QUALIFYING"
  | "SPRINT_SHOOTOUT_1"
  | "SPRINT_SHOOTOUT_2"
  | "SPRINT_SHOOTOUT_3"
  | "SHORT_SPRINT_SHOOTOUT"
  | "ONE_SHOT_SPRINT_SHOOTOUT"
  | "RACE"
  | "RACE_2"
  | "RACE_3"
  | "TIME_TRIAL"
  | "SPRINT_RACE"
>;

export type ResultStatus = Enum<
  | "INVALID"
  | "INACTIVE"
  | "ACTIVE"
  | "FINISHED"
  | "DID_NOT_FINISH"
  | "DISQUALIFIED"
  | "NOT_CLASSIFIED"
  | "RETIRED"
>;

export type ResultReason = Enum<
  | "INVALID"
  | "RETIRED"
  | "FINISHED"
  | "TERMINAL_DAMAGE"
  | "INACTIVE"
  | "NOT_ENOUGH_LAPS"
  | "BLACK_FLAGGED"
  | "RED_FLAGGED"
  | "MECHANICAL_FAILURE"
  | "SESSION_SKIPPED"
  | "SESSION_SIMULATED"
>;

export type Platform = Enum<
  "NONE" | "STEAM" | "PLAYSTATION" | "XBOX" | "ORIGIN" | "UNKNOWN"
>;

export type ActualTyreCompound = Enum<
  | "NONE"
  | "INTER"
  | "WET"
  | "CLASSIC_DRY"
  | "CLASSIC_WET"
  | "F2_SUPER_SOFT"
  | "F2_SOFT"
  | "F2_MEDIUM"
  | "F2_HARD"
  | "F2_WET"
  | "C5"
  | "C4"
  | "C3"
  | "C2"
  | "C1"
  | "C0"
  | "C6"
>;

export type VisualTyreCompound = Enum<
  | "NONE"
  | "INTER"
  | "WET"
  | "F2_WET"
  | "SOFT"
  | "MEDIUM"
  | "HARD"
  | "F2_SUPER_SOFT"
  | "F2_SOFT"
  | "F2_MEDIUM"
  | "F2_HARD"
>;

export type SafetyCarStatus = Enum<"NONE" | "FULL" | "VIRTUAL" | "FORMATION_LAP">;

export type Weather = Enum<
  "UNKNOWN" | "CLEAR" | "LIGHT_CLOUD" | "OVERCAST" | "LIGHT_RAIN" | "HEAVY_RAIN" | "STORM"
>;

export type Formula = Enum<
  | "F1_MODERN"
  | "F1_CLASSIC"
  | "F2"
  | "F1_GENERIC"
  | "BETA"
  | "ESPORTS"
  | "F1_WORLD"
  | "F1_ELIMINATION"
  | "F1_26"
>;

export type GameMode = Enum<
  | "NONE"
  | "UNKNOWN"
  | "GRAND_PRIX_23"
  | "TIME_TRIAL"
  | "SPLITSCREEN"
  | "ONLINE_CUSTOM"
  | "ONLINE_WEEKLY_EVENT"
  | "STORY_MODE"
  | "MY_TEAM_CAREER_25"
  | "DRIVER_CAREER_25"
  | "CAREER_25_ONLINE"
  | "CHALLENGE_CAREER_25"
  | "STORY_MODE_APXGP"
  | "BENCHMARK"
>;

export type Ruleset = Enum<
  "UNKNOWN" | "PRACTICE_QUALIFYING" | "RACE" | "TIME_TRIAL" | "ELIMINATION"
>;

export type FlagStatus = Enum<"UNKNOWN" | "NONE" | "GREEN" | "BLUE" | "YELLOW">;

export type Sector = Enum<"SECTOR_1" | "SECTOR_2" | "SECTOR_3">;

export type PitStatus = Enum<"NONE" | "PITTING" | "IN_PIT_AREA">;

export type DriverStatus = Enum<
  "IN_GARAGE" | "FLYING_LAP" | "IN_LAP" | "OUT_LAP" | "ON_TRACK"
>;

export type SurfaceType = Enum<
  | "TARMAC"
  | "RUMBLE_STRIP"
  | "CONCRETE"
  | "ROCK"
  | "GRAVEL"
  | "MUD"
  | "SAND"
  | "GRASS"
  | "WATER"
  | "COBBLESTONE"
  | "METAL"
  | "RIDGED"
>;

// ---------------------------------------------------------------------------
// Code tables for telemetry.car_frame
//
// These mirror listener/enums/*.py exactly — the listener stores the integer,
// so these names are the only place the mapping exists on the read side. The
// gaps are the game's, not omissions: tyre compound ids jump from 0 to 7.
// ---------------------------------------------------------------------------

export const SECTOR_CODES: EnumCodes<"SECTOR_1" | "SECTOR_2" | "SECTOR_3"> = {
  0: "SECTOR_1",
  1: "SECTOR_2",
  2: "SECTOR_3",
};

export const PIT_STATUS_CODES: EnumCodes<"NONE" | "PITTING" | "IN_PIT_AREA"> = {
  0: "NONE",
  1: "PITTING",
  2: "IN_PIT_AREA",
};

export const DRIVER_STATUS_CODES: EnumCodes<
  "IN_GARAGE" | "FLYING_LAP" | "IN_LAP" | "OUT_LAP" | "ON_TRACK"
> = {
  0: "IN_GARAGE",
  1: "FLYING_LAP",
  2: "IN_LAP",
  3: "OUT_LAP",
  4: "ON_TRACK",
};

export const RESULT_STATUS_CODES: EnumCodes<
  | "INVALID"
  | "INACTIVE"
  | "ACTIVE"
  | "FINISHED"
  | "DID_NOT_FINISH"
  | "DISQUALIFIED"
  | "NOT_CLASSIFIED"
  | "RETIRED"
> = {
  0: "INVALID",
  1: "INACTIVE",
  2: "ACTIVE",
  3: "FINISHED",
  4: "DID_NOT_FINISH",
  5: "DISQUALIFIED",
  6: "NOT_CLASSIFIED",
  7: "RETIRED",
};

export const SURFACE_TYPE_CODES: EnumCodes<
  | "TARMAC"
  | "RUMBLE_STRIP"
  | "CONCRETE"
  | "ROCK"
  | "GRAVEL"
  | "MUD"
  | "SAND"
  | "GRASS"
  | "WATER"
  | "COBBLESTONE"
  | "METAL"
  | "RIDGED"
> = {
  0: "TARMAC",
  1: "RUMBLE_STRIP",
  2: "CONCRETE",
  3: "ROCK",
  4: "GRAVEL",
  5: "MUD",
  6: "SAND",
  7: "GRASS",
  8: "WATER",
  9: "COBBLESTONE",
  10: "METAL",
  11: "RIDGED",
};

export const ACTUAL_TYRE_COMPOUND_CODES: EnumCodes<
  | "NONE"
  | "INTER"
  | "WET"
  | "CLASSIC_DRY"
  | "CLASSIC_WET"
  | "F2_SUPER_SOFT"
  | "F2_SOFT"
  | "F2_MEDIUM"
  | "F2_HARD"
  | "F2_WET"
  | "C5"
  | "C4"
  | "C3"
  | "C2"
  | "C1"
  | "C0"
  | "C6"
> = {
  0: "NONE",
  7: "INTER",
  8: "WET",
  9: "CLASSIC_DRY",
  10: "CLASSIC_WET",
  11: "F2_SUPER_SOFT",
  12: "F2_SOFT",
  13: "F2_MEDIUM",
  14: "F2_HARD",
  15: "F2_WET",
  16: "C5",
  17: "C4",
  18: "C3",
  19: "C2",
  20: "C1",
  21: "C0",
  22: "C6",
};

export const VISUAL_TYRE_COMPOUND_CODES: EnumCodes<
  | "NONE"
  | "INTER"
  | "WET"
  | "F2_WET"
  | "SOFT"
  | "MEDIUM"
  | "HARD"
  | "F2_SUPER_SOFT"
  | "F2_SOFT"
  | "F2_MEDIUM"
  | "F2_HARD"
> = {
  0: "NONE",
  7: "INTER",
  8: "WET",
  15: "F2_WET",
  16: "SOFT",
  17: "MEDIUM",
  18: "HARD",
  19: "F2_SUPER_SOFT",
  20: "F2_SOFT",
  21: "F2_MEDIUM",
  22: "F2_HARD",
};

/** -1 is the game's UNKNOWN, which is a *named* member here, not the fallback. */
export const FLAG_STATUS_CODES: EnumCodes<
  "UNKNOWN" | "NONE" | "GREEN" | "BLUE" | "YELLOW"
> = {
  [-1]: "UNKNOWN",
  0: "NONE",
  1: "GREEN",
  2: "BLUE",
  3: "YELLOW",
};

// Negative codes are reachable: FlagStatus uses -1, and an unrecognised signed
// value degrades to `UNKNOWN_-<n>`.
const UNKNOWN_PATTERN = /^UNKNOWN_(-?\d+)$/;

/**
 * False when the listener could not name the value — i.e. the game sent an enum
 * member this build does not know about.
 *
 * Note that a plain `"UNKNOWN"` is a *known* member of several of these enums
 * (Platform, Weather, GameMode, Ruleset, FlagStatus all define it), and is not
 * the same thing as the `UNKNOWN_<n>` fallback.
 */
export function isKnownEnum(value: string): boolean {
  return !UNKNOWN_PATTERN.test(value);
}

/** The raw integer behind an `UNKNOWN_<n>` value, or null for a known member. */
export function unknownEnumValue(value: string): number | null {
  const match = UNKNOWN_PATTERN.exec(value);
  return match ? Number(match[1]) : null;
}

/**
 * Render an enum column for display. Keeps unrecognised values legible instead of
 * leaking `UNKNOWN_37` into a Discord embed.
 */
export function displayEnum(value: string): string {
  const unknown = unknownEnumValue(value);
  if (unknown !== null) return `Unknown (${unknown})`;

  return value
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}
