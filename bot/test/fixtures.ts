import type {
  DiscordSessionMessageRow,
  DiscordWeekendRow,
  QualifyingClassificationRow,
  RaceClassificationRow,
  RosterEntry,
  SessionBest,
  SessionRow,
  SessionTimelineRow,
  TrackRow,
  TyreStintRow,
  UserRow,
} from "@f1/db";
import type { FastestLap } from "../src/queries/laps";

/**
 * Partial builders. The row types mirror every column in `schema/*.sql`, but a
 * test only ever asserts on a handful, so each builder fills the identifying
 * fields and asserts the rest — hand-writing 55 session columns per test would
 * bury what is actually under test.
 */

export function sessionRow(overrides: Partial<SessionRow> = {}): SessionRow {
  return {
    session_uid: "1000000000000000001",
    weekend_link: "weekend-1",
    session_link: "session-1",
    session_start_utc: new Date("2026-08-19T18:00:00Z"),
    track_id: 10,
    session_type: "RACE",
    created_at: new Date("2026-08-19T18:05:00Z"),
    ...overrides,
  } as SessionRow;
}

export function rosterEntry(overrides: Partial<RosterEntry> = {}): RosterEntry {
  return {
    session_uid: "1000000000000000001",
    user_id: 1,
    car_index: 0,
    team_id: 2,
    race_number: 1,
    telemetry_public: true,
    livery_colors: [],
    driver_name: "Driver One",
    discord_id: null,
    team_name: "RED_BULL_RACING",
    team_display_name: "Red Bull Racing",
    ...overrides,
  } as RosterEntry;
}

export function raceResult(
  overrides: Partial<RaceClassificationRow & { driver_name: string; discord_id: string | null }> = {}
): RaceClassificationRow & { driver_name: string; discord_id: string | null } {
  return {
    session_uid: "1000000000000000001",
    user_id: 1,
    position: 1,
    num_laps: 44,
    grid_position: 1,
    num_pit_stops: 1,
    result_status: "FINISHED",
    result_reason: "FINISHED",
    best_lap_time_ms: 83456,
    game_points: 25,
    total_race_time: 5400.5,
    penalties_time: 0,
    num_penalties: 0,
    num_tyre_stints: 2,
    tyre_stints_actual: [16, 18],
    tyre_stints_visual: [16, 18],
    tyre_stints_end_laps: [20, 44],
    driver_name: "Driver One",
    discord_id: null,
    ...overrides,
  } as RaceClassificationRow & { driver_name: string; discord_id: string | null };
}

export function qualifyingResult(
  overrides: Partial<
    QualifyingClassificationRow & { driver_name: string; discord_id: string | null }
  > = {}
): QualifyingClassificationRow & { driver_name: string; discord_id: string | null } {
  return {
    session_uid: "1000000000000000001",
    user_id: 1,
    position: 1,
    num_laps: 12,
    best_lap_time_ms: "78123",
    result_status: "FINISHED",
    result_reason: null,
    game_points: null,
    penalties_time: null,
    num_penalties: null,
    driver_name: "Driver One",
    discord_id: null,
    ...overrides,
  } as QualifyingClassificationRow & { driver_name: string; discord_id: string | null };
}

export function fastestLap(overrides: Partial<FastestLap> = {}): FastestLap {
  return {
    user_id: 1,
    driver_name: "Driver One",
    lap_number: 12,
    lap_time_ms: 83456,
    ...overrides,
  };
}

export function sessionBest(overrides: Partial<SessionBest> = {}): SessionBest {
  return {
    user_id: 1,
    driver_name: "Driver One",
    best_lap_num: 12,
    best_lap_time_ms: 83456,
    best_sector1_lap_num: 12,
    best_sector1_time_ms: 28000,
    best_sector2_lap_num: 9,
    best_sector2_time_ms: 30000,
    best_sector3_lap_num: 12,
    best_sector3_time_ms: 25456,
    ...overrides,
  };
}

export function tyreStint(overrides: Partial<TyreStintRow> = {}): TyreStintRow {
  return {
    session_uid: "1000000000000000001",
    user_id: 1,
    stint_number: 1,
    end_lap: 20,
    actual_compound: "C3",
    visual_compound: "MEDIUM",
    ...overrides,
  };
}

export function timelineRow(overrides: Partial<SessionTimelineRow> = {}): SessionTimelineRow {
  return {
    timestamp: new Date("2026-08-19T18:10:00Z"),
    session_uid: "1000000000000000001",
    session_time: 600,
    overall_frame_identifier: 15000,
    session_time_left: 4800,
    total_laps: 44,
    weather_state: "CLEAR",
    weather_track_temp: 32,
    weather_air_temp: 24,
    safety_car_status: "NONE",
    marshal_zone_flags: null,
    num_safety_car_periods: null,
    num_virtual_safety_car_periods: null,
    num_red_flag_periods: null,
    game_paused: null,
    is_spectating: null,
    spectator_car_index: null,
    pit_stop_window_ideal_lap: null,
    pit_stop_window_latest_lap: null,
    pit_stop_rejoin_position: null,
    ...overrides,
  } as SessionTimelineRow;
}

export function trackRow(overrides: Partial<TrackRow> = {}): TrackRow {
  return {
    track_id: 10,
    name: "SILVERSTONE",
    display_name: "Silverstone",
    country: "United Kingdom",
    track_length: 5891,
    sector2_start: null,
    sector3_start: null,
    marshal_zones: null,
    pit_speed_limit: null,
    active_aero_track_status: null,
    active_aero_zones_full: null,
    active_aero_zones_partial: null,
    drs_zones: null,
    ...overrides,
  } as TrackRow;
}

export function discordWeekendRow(overrides: Partial<DiscordWeekendRow> = {}): DiscordWeekendRow {
  return {
    weekend_link: "weekend-1",
    channel_id: "channel-1",
    archived: false,
    created_at: new Date("2026-08-19T18:00:00Z"),
    ...overrides,
  };
}

export function discordSessionMessageRow(
  overrides: Partial<DiscordSessionMessageRow> = {}
): DiscordSessionMessageRow {
  return {
    session_uid: "1000000000000000001",
    channel_id: "channel-1",
    message_id: "message-1",
    finalized: false,
    created_at: new Date("2026-08-19T18:00:00Z"),
    ...overrides,
  };
}

export function userRow(overrides: Partial<UserRow> = {}): UserRow {
  return {
    id: 1,
    driver_name: "Driver One",
    nationality: "British",
    discord_id: null,
    discord_username: null,
    discord_nickname: null,
    discord_email: null,
    discord_avatar: null,
    created_at: new Date("2026-08-01T00:00:00Z"),
    updated_at: new Date("2026-08-01T00:00:00Z"),
    ...overrides,
  };
}
