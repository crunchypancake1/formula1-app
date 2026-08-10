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

export async function countTelemetryTables(
  sql: ReturnType<typeof connect>
): Promise<number> {
  const rows = await sql<{ count: string }[]>`
    SELECT count(*)::text AS count
      FROM information_schema.tables
     WHERE table_schema = 'telemetry'
       AND table_type = 'BASE TABLE'
  `;
  return Number(rows[0].count);
}
