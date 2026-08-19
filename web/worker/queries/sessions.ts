import type { SessionRow, Sql } from "@f1/db";

/**
 * Ordering throughout is by `session_start_utc`, not `created_at`.
 *
 * `created_at` is row-insert time, so a session replayed or backfilled out of
 * order sorts wrongly. `session_start_utc` is the session's own anchor — written
 * once as NOW() - m_sessionTime and never moved — which is what "most recently
 * run" actually means.
 */

/** Pure over its query function so it can be tested without a database. */
export async function readLatestSession(
  query: () => Promise<SessionRow[]>
): Promise<SessionRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

export function latestSession(sql: Sql) {
  return readLatestSession(
    () => sql<SessionRow[]>`
      SELECT *
        FROM telemetry.sessions
       ORDER BY session_start_utc DESC
       LIMIT 1
    `
  );
}
