import {
  ACTUAL_TYRE_COMPOUND_CODES,
  DRIVER_STATUS_CODES,
  enumFromCode,
  PIT_STATUS_CODES,
  RESULT_STATUS_CODES,
  SECTOR_CODES,
  VISUAL_TYRE_COMPOUND_CODES,
  type LiveDriver,
  type LiveDriverRow,
  type Sql,
} from "@f1/db";

/**
 * Resolve one row's enum codes to member names.
 *
 * car_frame stores the game's raw integers (see packages/db/src/enums.ts), so
 * this is where they become the same `UNKNOWN_<n>`-capable strings every other
 * table returns — an unrecognised code degrades rather than throwing, which is
 * what lets a game patch add a tyre compound without breaking the dashboard.
 *
 * Pure over its input so it can be tested without a database.
 */
export function resolveLiveDriver(row: LiveDriverRow): LiveDriver {
  return {
    ...row,
    sector: enumFromCode(SECTOR_CODES, row.sector),
    pit_status: enumFromCode(PIT_STATUS_CODES, row.pit_status),
    driver_status: enumFromCode(DRIVER_STATUS_CODES, row.driver_status),
    result_status: enumFromCode(RESULT_STATUS_CODES, row.result_status),
    actual_tyre_compound: enumFromCode(
      ACTUAL_TYRE_COMPOUND_CODES,
      row.actual_tyre_compound
    ),
    visual_tyre_compound: enumFromCode(
      VISUAL_TYRE_COMPOUND_CODES,
      row.visual_tyre_compound
    ),
  };
}

/**
 * Every driver's latest telemetry.car_frame row for a session, joined to
 * roster/driver identity and each driver's personal-best lap.
 *
 * The `latest` CTE runs DISTINCT ON against the hypertable's
 * (session_uid, user_id, overall_frame_identifier DESC) index — a handful of
 * rows out — before any joins happen, so the joins never touch more than one
 * row per car regardless of how many frames the session has accumulated.
 */
export async function liveDrivers(
  sql: Sql,
  sessionUid: string
): Promise<LiveDriver[]> {
  const rows = await sql<LiveDriverRow[]>`
    WITH latest AS (
      SELECT DISTINCT ON (user_id) *
        FROM telemetry.car_frame
       WHERE session_uid = ${sessionUid}
       ORDER BY user_id, overall_frame_identifier DESC
    )
    SELECT latest.user_id,
           e.car_index,
           u.driver_name,
           t.name         AS team_name,
           t.display_name AS team_display_name,
           e.race_number,
           latest.position,
           latest.current_lap_num,
           latest.sector,
           latest.lap_distance,
           latest.total_distance,
           latest.last_lap_time_ms,
           latest.current_lap_time_ms,
           latest.sector1_time_ms,
           latest.sector2_time_ms,
           latest.gap_to_leader_ms,
           latest.gap_to_car_ahead_ms,
           latest.pit_status,
           latest.driver_status,
           latest.result_status,
           latest.current_lap_invalid,
           latest.actual_tyre_compound,
           latest.visual_tyre_compound,
           latest.tyres_age_laps,
           latest.num_pit_stops,
           latest.penalties_seconds,
           latest.total_warnings,
           latest.speed,
           latest.overtake_active,
           best.best_lap_time_ms
      FROM latest
      JOIN telemetry.entries e ON e.session_uid = ${sessionUid} AND e.user_id = latest.user_id
      JOIN identity.users u    ON u.id = latest.user_id
      JOIN telemetry.teams t   ON t.team_id = e.team_id
      LEFT JOIN LATERAL (
        SELECT l.lap_time_ms AS best_lap_time_ms
          FROM telemetry.session_bests sb
          JOIN telemetry.laps l
            ON l.session_uid = sb.session_uid
           AND l.user_id = sb.user_id
           AND l.lap_number = sb.best_lap_num
         WHERE sb.session_uid = ${sessionUid} AND sb.user_id = latest.user_id
      ) best ON true
     ORDER BY latest.position NULLS LAST, latest.user_id
  `;

  return rows.map(resolveLiveDriver);
}
