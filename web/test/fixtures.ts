import type { RosterEntry, SessionRow, SessionTimelineRow } from "@f1/db";

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
