import postgres from "postgres";
import type { Env } from "./types";

/**
 * Hyperdrive maintains the connection pool on Cloudflare's side, so creating a
 * client per request is cheap. `fetch_types: false` skips postgres.js's type
 * introspection round trip, which Hyperdrive cannot cache.
 */
export function connect(env: Env) {
  return postgres(env.HYPERDRIVE.connectionString, {
    max: 5,
    fetch_types: false,
  });
}

export interface SessionUidRow {
  session_uid: string;
}

/** Pure over its query function so it can be tested without a database. */
export async function readLatestSessionUid(
  query: () => Promise<SessionUidRow[]>
): Promise<string | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0].session_uid : null;
}

export function latestSessionUid(sql: ReturnType<typeof connect>) {
  return readLatestSessionUid(
    () => sql<SessionUidRow[]>`
      SELECT session_uid
        FROM telemetry.sessions
       ORDER BY created_at DESC
       LIMIT 1
    `
  );
}
