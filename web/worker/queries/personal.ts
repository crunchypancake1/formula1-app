import {
  ACTUAL_TYRE_COMPOUND_CODES,
  enumFromCode,
  VISUAL_TYRE_COMPOUND_CODES,
  type CarDamageRow,
  type PersonalFrame,
  type PersonalFrameRow,
  type Sql,
  type TyreSetRow,
} from "@f1/db";

/** Pure over its input so it can be tested without a database — mirrors `resolveLiveDriver`. */
export function resolvePersonalFrame(row: PersonalFrameRow): PersonalFrame {
  return {
    ...row,
    actual_tyre_compound: enumFromCode(ACTUAL_TYRE_COMPOUND_CODES, row.actual_tyre_compound),
    visual_tyre_compound: enumFromCode(VISUAL_TYRE_COMPOUND_CODES, row.visual_tyre_compound),
    ahead_visual_tyre_compound: enumFromCode(VISUAL_TYRE_COMPOUND_CODES, row.ahead_visual_tyre_compound),
    behind_visual_tyre_compound: enumFromCode(VISUAL_TYRE_COMPOUND_CODES, row.behind_visual_tyre_compound),
  };
}

/**
 * The viewer's latest telemetry.car_frame row for this session, joined to the
 * cars at position ± 1 for the battle panel.
 *
 * `board` is every driver's latest frame — the same DISTINCT ON pattern as
 * `queries/live.ts`'s `liveDrivers`, but bounded by `timestamp >= startUtc` so
 * the hypertable scan excludes every chunk before this session started rather
 * than opening the whole table.
 */
export async function personalFrame(
  sql: Sql,
  sessionUid: string,
  startUtc: Date,
  userId: number
): Promise<PersonalFrame | null> {
  const rows = await sql<PersonalFrameRow[]>`
    WITH board AS (
      SELECT DISTINCT ON (cf.user_id)
             cf.user_id,
             e.car_index,
             u.driver_name,
             t.name         AS team_name,
             t.display_name AS team_display_name,
             e.race_number,
             cf.position,
             cf.current_lap_num,
             cf.gap_to_car_ahead_ms,
             cf.gap_to_car_behind_ms,
             cf.overtake_available,
             cf.overtake_active,
             cf.actual_tyre_compound,
             cf.visual_tyre_compound,
             cf.tyres_age_laps
        FROM telemetry.car_frame cf
        JOIN telemetry.entries e ON e.session_uid = cf.session_uid AND e.user_id = cf.user_id
        JOIN identity.users u    ON u.id = cf.user_id
        JOIN telemetry.teams t   ON t.team_id = e.team_id
       WHERE cf.session_uid = ${sessionUid} AND cf.timestamp >= ${startUtc}
       ORDER BY cf.user_id, cf.overall_frame_identifier DESC
    )
    SELECT mine.*,
           ahead.driver_name           AS ahead_driver_name,
           ahead.team_name             AS ahead_team_name,
           ahead.visual_tyre_compound  AS ahead_visual_tyre_compound,
           ahead.tyres_age_laps        AS ahead_tyres_age_laps,
           behind.driver_name          AS behind_driver_name,
           behind.team_name            AS behind_team_name,
           behind.visual_tyre_compound AS behind_visual_tyre_compound,
           behind.tyres_age_laps       AS behind_tyres_age_laps
      FROM board mine
      LEFT JOIN board ahead  ON ahead.position = mine.position - 1
      LEFT JOIN board behind ON behind.position = mine.position + 1
     WHERE mine.user_id = ${userId}
  `;

  return rows.length > 0 ? resolvePersonalFrame(rows[0]) : null;
}

/**
 * The viewer's newest per-lap tyre-set snapshot. Empty when Your Telemetry is
 * Restricted or no snapshot has arrived yet — callers distinguish those with
 * `telemetry.entries.telemetry_public`, not by guessing from the empty array.
 */
export async function availableTyreSets(
  sql: Sql,
  sessionUid: string,
  userId: number
): Promise<TyreSetRow[]> {
  return sql<TyreSetRow[]>`
    WITH newest AS (
      SELECT MAX(lap_number) AS lap_number
        FROM telemetry.tyre_sets
       WHERE session_uid = ${sessionUid} AND user_id = ${userId}
    )
    SELECT ts.lap_number, ts.set_index, ts.actual_compound, ts.visual_compound,
           ts.wear, ts.life_span, ts.usable_life, ts.lap_delta_time_ms, ts.fitted
      FROM telemetry.tyre_sets ts, newest
     WHERE ts.session_uid = ${sessionUid}
       AND ts.user_id = ${userId}
       AND ts.lap_number = newest.lap_number
     ORDER BY ts.set_index
  `;
}

/** Pure over its query function so it can be tested without a database. */
export async function readPersonalDamage(
  query: () => Promise<CarDamageRow[]>
): Promise<CarDamageRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

/**
 * The viewer's latest telemetry.car_frame_damage row — absent entirely
 * (not a row of nulls) when Your Telemetry is Restricted.
 */
export function personalDamage(sql: Sql, sessionUid: string, startUtc: Date, userId: number) {
  return readPersonalDamage(
    () => sql<CarDamageRow[]>`
      SELECT tyres_wear_rl, tyres_wear_rr, tyres_wear_fl, tyres_wear_fr
        FROM telemetry.car_frame_damage
       WHERE session_uid = ${sessionUid} AND timestamp >= ${startUtc} AND user_id = ${userId}
       ORDER BY overall_frame_identifier DESC
       LIMIT 1
    `
  );
}

