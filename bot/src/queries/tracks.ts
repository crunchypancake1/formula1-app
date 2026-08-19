import type { Sql, TrackRow } from "@f1/db";

/** Pure over its query function so it can be tested without a database. */
export async function readTrack(
  query: () => Promise<TrackRow[]>
): Promise<TrackRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

export function trackById(sql: Sql, trackId: number) {
  return readTrack(
    () => sql<TrackRow[]>`
      SELECT *
        FROM telemetry.tracks
       WHERE track_id = ${trackId}
       LIMIT 1
    `
  );
}
