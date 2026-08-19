import type { SessionBest, Sql, TyreStintRow } from "@f1/db";

export interface FastestLap {
  user_id: number;
  driver_name: string;
  lap_number: number;
  /** BIGINT — string. */
  lap_time_ms: string;
}

/** Pure over its query function so it can be tested without a database. */
export async function readFastestValidLap(
  query: () => Promise<FastestLap[]>
): Promise<FastestLap | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

export async function readSessionBests(
  query: () => Promise<SessionBest[]>
): Promise<SessionBest[]> {
  return query();
}

export async function readTyreStints(
  query: () => Promise<TyreStintRow[]>
): Promise<TyreStintRow[]> {
  return query();
}

/** Backed by idx_laps_fastest_valid (session_uid, lap_time_ms) WHERE is_valid. */
export function fastestValidLap(sql: Sql, sessionUid: string) {
  return readFastestValidLap(
    () => sql<FastestLap[]>`
      SELECT l.user_id, u.driver_name, l.lap_number, l.lap_time_ms
        FROM telemetry.laps l
        JOIN identity.users u ON u.id = l.user_id
       WHERE l.session_uid = ${sessionUid}
         AND l.is_valid = true
         AND l.lap_time_ms IS NOT NULL
       ORDER BY l.lap_time_ms
       LIMIT 1
    `
  );
}

/**
 * session_bests stores which lap each best was set on, not the time, so every
 * best needs its own join back to telemetry.laps. A null lap number means no
 * best has been set yet and stays null rather than becoming lap 0.
 */
export function sessionBests(sql: Sql, sessionUid: string) {
  return readSessionBests(
    () => sql<SessionBest[]>`
      SELECT sb.user_id,
             u.driver_name,
             sb.best_lap_num,
             bl.lap_time_ms      AS best_lap_time_ms,
             sb.best_sector1_lap_num,
             s1.sector1_time_ms  AS best_sector1_time_ms,
             sb.best_sector2_lap_num,
             s2.sector2_time_ms  AS best_sector2_time_ms,
             sb.best_sector3_lap_num,
             s3.sector3_time_ms  AS best_sector3_time_ms
        FROM telemetry.session_bests sb
        JOIN identity.users u ON u.id = sb.user_id
        LEFT JOIN telemetry.laps bl
               ON bl.session_uid = sb.session_uid
              AND bl.user_id = sb.user_id
              AND bl.lap_number = sb.best_lap_num
        LEFT JOIN telemetry.laps s1
               ON s1.session_uid = sb.session_uid
              AND s1.user_id = sb.user_id
              AND s1.lap_number = sb.best_sector1_lap_num
        LEFT JOIN telemetry.laps s2
               ON s2.session_uid = sb.session_uid
              AND s2.user_id = sb.user_id
              AND s2.lap_number = sb.best_sector2_lap_num
        LEFT JOIN telemetry.laps s3
               ON s3.session_uid = sb.session_uid
              AND s3.user_id = sb.user_id
              AND s3.lap_number = sb.best_sector3_lap_num
       WHERE sb.session_uid = ${sessionUid}
       ORDER BY bl.lap_time_ms NULLS LAST
    `
  );
}

export function tyreStints(sql: Sql, sessionUid: string, userId: number) {
  return readTyreStints(
    () => sql<TyreStintRow[]>`
      SELECT *
        FROM telemetry.tyre_stints
       WHERE session_uid = ${sessionUid}
         AND user_id = ${userId}
       ORDER BY stint_number
    `
  );
}
