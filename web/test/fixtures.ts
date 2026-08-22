import type {
  CarDamageRow,
  PersonalFrameRow,
  RosterEntry,
  SessionRow,
  SessionTimelineRow,
  TyreSetRow,
} from "@f1/db";

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

export function personalFrameRow(overrides: Partial<PersonalFrameRow> = {}): PersonalFrameRow {
  return {
    user_id: 1,
    car_index: 0,
    driver_name: "Driver One",
    team_name: "MCLAREN_26",
    team_display_name: "McLaren '26",
    race_number: 4,
    position: 3,
    current_lap_num: 12,
    gap_to_car_ahead_ms: 850,
    gap_to_car_behind_ms: 1200,
    overtake_available: true,
    overtake_active: false,
    actual_tyre_compound: 20,
    visual_tyre_compound: 16,
    tyres_age_laps: 5,
    ahead_driver_name: "Driver Ahead",
    ahead_team_name: "FERRARI",
    ahead_visual_tyre_compound: 17,
    ahead_tyres_age_laps: 8,
    behind_driver_name: "Driver Behind",
    behind_team_name: "MERCEDES",
    behind_visual_tyre_compound: 18,
    behind_tyres_age_laps: 3,
    ...overrides,
  } as PersonalFrameRow;
}

export function carDamageRow(overrides: Partial<CarDamageRow> = {}): CarDamageRow {
  return {
    tyres_wear_rl: 12.5,
    tyres_wear_rr: 13.1,
    tyres_wear_fl: 10.2,
    tyres_wear_fr: 11.8,
    ...overrides,
  } as CarDamageRow;
}

export function tyreSetRow(overrides: Partial<TyreSetRow> = {}): TyreSetRow {
  return {
    lap_number: 12,
    set_index: 0,
    actual_compound: "C3",
    visual_compound: "MEDIUM",
    wear: 15,
    life_span: 100,
    usable_life: 80,
    lap_delta_time_ms: 0,
    fitted: true,
    ...overrides,
  } as TyreSetRow;
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
