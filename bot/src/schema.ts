/**
 * Row models for the F1 26 telemetry schema (`schema/*.sql`).
 *
 * Two conventions the listener enforces, which these types deliberately encode:
 *
 * 1. **NULL means withheld, never zero.** Fields that are player-only, or hidden
 *    by a driver's telemetry privacy setting, are written as NULL — the listener
 *    never stores a zero-filled stand-in. A `null` here must render as "—", not 0.
 * 2. **BIGINT arrives as a string.** `db.ts` sets `fetch_types: false` (Hyperdrive
 *    cannot cache postgres.js's type-introspection query), so int8 columns come
 *    back as strings. Use `parseMs` rather than coercing at each call site.
 */

import type {
  ActualTyreCompound,
  FlagStatus,
  Formula,
  GameMode,
  Platform,
  ResultReason,
  ResultStatus,
  Ruleset,
  SafetyCarStatus,
  SessionType,
  VisualTyreCompound,
  Weather,
} from "./enums";

/** F1 26 grid size. Matches `ck_entries_car_index_valid` and listener/packets/constants.py. */
export const MAX_CARS = 24;

/**
 * `m_teamId` is uint16 on the wire and 65535 is the "no team selected" sentinel.
 * `EntriesRepository.ensure_teams` inserts any unseen id on sight, so team_id is a
 * plain number — never assume the seeded list in `schema/telemetry/teams.sql` is closed.
 */
export const NO_TEAM = 65535;

// ---------------------------------------------------------------------------
// identity
// ---------------------------------------------------------------------------

/** identity.users — every participant seen in telemetry. Discord fields NULL = unlinked. */
export interface UserRow {
  id: number;
  driver_name: string;
  nationality: string | null;
  discord_id: string | null;
  discord_username: string | null;
  discord_nickname: string | null;
  discord_email: string | null;
  discord_avatar: string | null;
  created_at: Date;
  updated_at: Date;
}

// ---------------------------------------------------------------------------
// telemetry — session
// ---------------------------------------------------------------------------

/**
 * telemetry.sessions — the session's *static* configuration.
 *
 * `session_start_utc` is the wall-clock anchor, written once as NOW() - m_sessionTime
 * and never moved; every frame table derives its timestamp from it. It is the correct
 * ordering key for "most recent session", not `created_at` (which is row-insert time).
 */
export interface SessionRow {
  session_uid: string;
  weekend_link: string;
  session_link: string;
  season_link: string | null;
  session_start_utc: Date;
  track_id: number;
  session_type: SessionType;
  formula: Formula;
  game_mode: GameMode;
  ruleset: Ruleset;
  total_laps: number;
  session_duration: number;
  num_sessions_in_weekend: number;
  weekend_structure: SessionType[] | null;
  time_of_day: number | null;
  session_length: number | null;

  /** NULL until a non-zero value is seen — stays 0.0 while starts are assisted. */
  start_reaction_time: number | null;

  network_game: boolean | null;
  ai_difficulty: number | null;
  forecast_accuracy: number | null;
  equal_car_performance: boolean | null;
  sli_pro_native_support: boolean | null;

  assist_steering: number | null;
  assist_braking: number | null;
  assist_gearbox: number | null;
  assist_pit: number | null;
  assist_pit_release: number | null;
  assist_ers: number | null;
  assist_drs: number | null;
  assist_anti_lock_brakes: number | null;
  assist_traction_control: number | null;
  dynamic_racing_line: number | null;
  dynamic_racing_line_type: number | null;
  dynamic_racing_line_hi_vis: number | null;
  dynamic_racing_line_colour_blind: number | null;

  recovery_mode: number | null;
  flashback_limit: number | null;
  recurring_rewind_prompt: number | null;
  surface_type: number | null;
  low_fuel_mode: number | null;
  race_starts: number | null;
  tyre_temperature: number | null;
  pit_lane_tyre_sim: number | null;
  car_damage: number | null;
  car_damage_rate: number | null;
  collisions: number | null;
  collisions_off_for_first_lap_only: number | null;
  mp_unsafe_pit_release: number | null;
  mp_off_for_griefing: number | null;
  corner_cutting_stringency: number | null;
  parc_ferme_rules: number | null;
  pit_stop_experience: number | null;
  safety_car: number | null;
  safety_car_experience: number | null;
  formation_lap: number | null;
  formation_lap_experience: number | null;
  red_flags: number | null;
  affects_licence_level_solo: number | null;
  affects_licence_level_mp: number | null;

  /** 0 = MPH/Celsius, 1 = KPH/Fahrenheit. */
  speed_units_lead_player: number | null;
  temperature_units_lead_player: number | null;
  speed_units_secondary_player: number | null;
  temperature_units_secondary_player: number | null;

  created_at: Date;
}

/** telemetry.session_timeline — the live half of session state, sampled at packet rate. */
export interface SessionTimelineRow {
  timestamp: Date;
  session_uid: string;
  session_time: number;
  overall_frame_identifier: number;
  session_time_left: number;
  total_laps: number | null;

  weather_state: Weather;
  weather_track_temp: number;
  weather_air_temp: number;

  safety_car_status: SafetyCarStatus;
  marshal_zone_flags: FlagStatus[] | null;
  num_safety_car_periods: number | null;
  num_virtual_safety_car_periods: number | null;
  num_red_flag_periods: number | null;

  game_paused: boolean | null;
  is_spectating: boolean | null;
  spectator_car_index: number | null;

  /** Player-only pit strategy window. NULL when not applicable. */
  pit_stop_window_ideal_lap: number | null;
  pit_stop_window_latest_lap: number | null;
  pit_stop_rejoin_position: number | null;
}

/** telemetry.tracks — track-static data only. Marshal zone *flags* live on the timeline. */
export interface TrackRow {
  track_id: number;
  name: string;
  display_name: string;
  country: string;
  track_length: number | null;
  sector2_start: number | null;
  sector3_start: number | null;
  marshal_zones: unknown;
  pit_speed_limit: number | null;
  active_aero_track_status: number | null;
  active_aero_zones_full: unknown;
  active_aero_zones_partial: unknown;
  drs_zones: unknown;
}

/** telemetry.teams — seeded, but the listener upserts unseen ids, so treat as open. */
export interface TeamRow {
  team_id: number;
  name: string;
  display_name: string;
}

// ---------------------------------------------------------------------------
// telemetry — roster
// ---------------------------------------------------------------------------

/**
 * telemetry.entries — the driver roster for one session.
 *
 * `telemetry_public` mirrors m_yourTelemetry: false = Restricted, meaning the game
 * zeroes fuel/ERS/damage for this car in everyone else's stream and the listener
 * stores NULL rather than those zeroes. Renderers must consult this before
 * presenting a missing value as a real one.
 */
export interface EntryRow {
  session_uid: string;
  user_id: number;
  car_index: number;
  team_id: number;
  race_number: number;
  driver_id: number | null;
  network_id: number | null;
  my_team: boolean | null;
  platform: Platform | null;
  tech_level: number | null;
  show_online_names: boolean | null;
  telemetry_public: boolean;
  num_livery_colors: number | null;
  livery_colors: number[];
  created_at: Date;
}

/** A roster entry joined to its driver identity and team name. */
export interface RosterEntry extends EntryRow {
  driver_name: string;
  discord_id: string | null;
  team_name: string;
  team_display_name: string;
}

// ---------------------------------------------------------------------------
// telemetry — results
// ---------------------------------------------------------------------------

/** telemetry.race_classification. `game_points` is what the game awarded, for reference. */
export interface RaceClassificationRow {
  session_uid: string;
  user_id: number;
  position: number;
  num_laps: number;
  grid_position: number;
  num_pit_stops: number;
  result_status: ResultStatus;
  result_reason: ResultReason | null;
  /** BIGINT — string, or null when no valid lap was set. */
  best_lap_time_ms: string | null;
  game_points: number | null;
  total_race_time: number;
  penalties_time: number;
  num_penalties: number;
  num_tyre_stints: number;
  tyre_stints_actual: number[];
  tyre_stints_visual: number[];
  tyre_stints_end_laps: number[];
  created_at: Date;
}

/** telemetry.qualifying_classification. */
export interface QualifyingClassificationRow {
  session_uid: string;
  user_id: number;
  position: number;
  num_laps: number;
  /** BIGINT — string, or null when no valid lap was set. */
  best_lap_time_ms: string | null;
  result_status: ResultStatus;
  result_reason: ResultReason | null;
  game_points: number | null;
  penalties_time: number | null;
  num_penalties: number | null;
  created_at: Date;
}

/** A classification row joined to its driver identity. */
export type ClassifiedDriver<T> = T & {
  driver_name: string;
  discord_id: string | null;
};

// ---------------------------------------------------------------------------
// telemetry — laps
// ---------------------------------------------------------------------------

/** telemetry.laps — per-lap timing from the Session History packet. */
export interface LapRow {
  session_uid: string;
  user_id: number;
  lap_number: number;
  /** BIGINT — string, or null when the lap has no recorded time. */
  lap_time_ms: string | null;
  sector1_time_ms: number | null;
  sector2_time_ms: number | null;
  sector3_time_ms: number | null;
  is_valid: boolean;
  sector1_valid: boolean;
  sector2_valid: boolean;
  sector3_valid: boolean;
  created_at: Date;
}

/**
 * telemetry.session_bests — which lap each personal best was set on, not the time.
 * Join back to telemetry.laps on (session_uid, user_id, lap_number) for the times.
 * NULL means no best has been set yet (the packet's 0 is stored as NULL).
 */
export interface SessionBestsRow {
  session_uid: string;
  user_id: number;
  best_lap_num: number | null;
  best_sector1_lap_num: number | null;
  best_sector2_lap_num: number | null;
  best_sector3_lap_num: number | null;
  updated_at: Date;
}

/** session_bests joined back to laps for the actual times. */
export interface SessionBest {
  user_id: number;
  driver_name: string;
  best_lap_num: number | null;
  /** BIGINT — string. Null when no best lap has been set. */
  best_lap_time_ms: string | null;
  best_sector1_lap_num: number | null;
  best_sector1_time_ms: number | null;
  best_sector2_lap_num: number | null;
  best_sector2_time_ms: number | null;
  best_sector3_lap_num: number | null;
  best_sector3_time_ms: number | null;
}

/** telemetry.tyre_stints — stint history from the Session History packet. */
export interface TyreStintRow {
  session_uid: string;
  user_id: number;
  stint_number: number;
  end_lap: number | null;
  actual_compound: ActualTyreCompound;
  visual_compound: VisualTyreCompound;
}

/** telemetry.lap_positions — `positions` is user_ids indexed by finishing position. */
export interface LapPositionsRow {
  session_uid: string;
  lap_number: number;
  positions: number[];
  created_at: Date;
}

// ---------------------------------------------------------------------------
// Value helpers
// ---------------------------------------------------------------------------

/**
 * Decode a BIGINT column. postgres.js returns int8 as a string and `fetch_types:
 * false` leaves it that way; null passes through so a missing time stays missing
 * rather than collapsing to 0.
 */
export function parseMs(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const ms = typeof value === "number" ? value : Number(value);
  return Number.isFinite(ms) ? ms : null;
}

/**
 * Format a lap or sector time in milliseconds as `m:ss.mmm`, or `—` when the value
 * is absent. Absent is not zero: a driver with no valid lap must not read as 0:00.000.
 */
export function formatLapTime(value: string | number | null | undefined): string {
  const ms = parseMs(value);
  if (ms === null) return "—";

  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.floor((ms % 60_000) / 1000);
  const millis = Math.floor(ms % 1000);

  return `${minutes}:${seconds.toString().padStart(2, "0")}.${millis
    .toString()
    .padStart(3, "0")}`;
}
