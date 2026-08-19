import type { SessionTimelineRow, Sql } from "@f1/db";

/** Pure over its query function so it can be tested without a database. */
export async function readLatestTimeline(
  query: () => Promise<SessionTimelineRow[]>
): Promise<SessionTimelineRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

/**
 * The most recent `telemetry.session_timeline` row for a session. The
 * scheduled handler uses its `timestamp` to detect a stalled session the same
 * way `web/worker/index.ts`'s LIVE_THRESHOLD_MS does, and `session_time_left`
 * to seed a non-race card's countdown.
 */
export function latestTimeline(sql: Sql, sessionUid: string) {
  return readLatestTimeline(
    () => sql<SessionTimelineRow[]>`
      SELECT *
        FROM telemetry.session_timeline
       WHERE session_uid = ${sessionUid}
       ORDER BY overall_frame_identifier DESC
       LIMIT 1
    `
  );
}
