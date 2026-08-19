import type { SessionTimelineRow, Sql } from "@f1/db";

/** Pure over its query function so it can be tested without a database. */
export async function readLatestTimeline(
  query: () => Promise<SessionTimelineRow[]>
): Promise<SessionTimelineRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

/**
 * The most recent `telemetry.session_timeline` row for a session — weather,
 * safety car status, marshal-zone flags, and pit window. This is the live-state
 * half of a session that the dashboard needs and the bot's Discord commands
 * never touch.
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
