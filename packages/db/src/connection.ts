import postgres, { type PostgresType } from "postgres";
import { parsePgArray, parsePgNumberArray } from "./schema";
import type { Env } from "./types";

/**
 * Parsers for the array type oids this schema uses.
 *
 * postgres.js normally learns array oids from the database on connect, but
 * `fetch_types: false` (see `connect`) skips that round trip, and without it
 * every array column arrives as its raw Postgres literal (`{a,b,c}`) — which
 * would make `weekend_structure`, `marshal_zone_flags`, `livery_colors` and
 * `tyre_stints_*` lie about their types on every row model in `schema.ts`.
 * Registering the parsers by oid fixes it once, for every query, instead of
 * leaving each call site to remember.
 *
 * Parsers only, deliberately — no `serialize`. postgres.js registers a custom
 * type's serializer against the same oids, and it picks a serializer from the
 * inferred type of the bound *value*, so adding one here would change how a JS
 * array is sent as a parameter and break the hand-built array literals in
 * `health.ts`. Its own `typeHandlers` guards on `if (types[k].serialize)`, so
 * omitting it is supported at runtime even though the published type demands
 * it — hence the cast.
 */
const ARRAY_TYPES = {
  /** _text (1009), _varchar (1015): weekend_structure, marshal_zone_flags, buttons_pressed. */
  stringArray: { to: 1009, from: [1009, 1015], parse: parsePgArray },
  /** _int2 (1005), _int4 (1007): livery_colors, tyre_stints_*, lap_positions.positions. */
  numberArray: { to: 1007, from: [1005, 1007], parse: parsePgNumberArray },
} as unknown as Record<string, PostgresType>;

/**
 * Hyperdrive maintains the connection pool on Cloudflare's side, so creating a
 * client per request is cheap. `fetch_types: false` skips postgres.js's type
 * introspection round trip, which Hyperdrive cannot cache — the consequences are
 * that BIGINT columns arrive as strings (see `parseMs` in schema.ts) and that
 * array columns need the parsers registered above.
 */
export function connect(env: Env) {
  return postgres(env.HYPERDRIVE.connectionString, {
    max: 5,
    fetch_types: false,
    types: ARRAY_TYPES,
  });
}

export type Sql = ReturnType<typeof connect>;
