/**
 * Enum-valued columns as TypeScript types.
 *
 * The listener writes enum columns as VARCHAR via `safe_enum_name`
 * (listener/database/repositories/base.py), which degrades any value it does not
 * recognise to `UNKNOWN_<value>` rather than failing the write — an enum member
 * added by a game patch must never stop collection. Every enum-valued column can
 * therefore hold a string outside the known set, so every union below carries the
 * `UNKNOWN_<n>` escape hatch and callers must handle it.
 */

/** A known enum member name, or the `UNKNOWN_<value>` fallback the listener writes. */
export type Enum<T extends string> = T | `UNKNOWN_${number}`;

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

const UNKNOWN_PATTERN = /^UNKNOWN_(\d+)$/;

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
