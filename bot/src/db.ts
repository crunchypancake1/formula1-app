import postgres from "postgres";
import type { Env } from "./types";

/**
 * Hyperdrive maintains the connection pool on Cloudflare's side, so creating a
 * client per request is cheap. `fetch_types: false` skips postgres.js's type
 * introspection round trip, which Hyperdrive cannot cache — the consequence is
 * that BIGINT columns arrive as strings (see `parseMs` in schema.ts).
 */
export function connect(env: Env) {
  return postgres(env.HYPERDRIVE.connectionString, {
    max: 5,
    fetch_types: false,
  });
}

export type Sql = ReturnType<typeof connect>;
