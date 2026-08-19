import type { Sql } from "./connection";

/**
 * Columns that exist only in the F1 26 schema. Probing for these rather than
 * counting tables is deliberate: a table count has to be bumped every time the
 * schema grows a file, and goes stale silently when nobody remembers to.
 *
 * `entries.telemetry_public` was `telemetry_setting` before the upgrade, and
 * `session_bests` did not exist at all, so a pre-2026 database fails on both.
 */
export const SCHEMA_MARKERS: ReadonlyArray<[table: string, column: string]> = [
  ["sessions", "session_start_utc"],
  ["entries", "telemetry_public"],
  ["race_classification", "game_points"],
  ["qualifying_classification", "result_reason"],
  ["session_bests", "best_lap_num"],
];

export interface HealthResult {
  ok: boolean;
  /** Markers from SCHEMA_MARKERS that the database does not have. */
  missing: string[];
  latencyMs: number;
}

export interface SchemaColumnRow {
  table_name: string;
  column_name: string;
}

/** Pure over its query function so it can be tested without a database. */
export async function checkSchema(
  query: () => Promise<SchemaColumnRow[]>
): Promise<HealthResult> {
  const started = Date.now();
  const rows = await query();
  const present = new Set(rows.map((r) => `${r.table_name}.${r.column_name}`));

  const missing = SCHEMA_MARKERS.map(([table, column]) => `${table}.${column}`).filter(
    (marker) => !present.has(marker)
  );

  return { ok: missing.length === 0, missing, latencyMs: Date.now() - started };
}

/**
 * Postgres array literal syntax (`{a,b,c}`), built by hand rather than passed
 * as a JS array. `fetch_types: false` (see `connection.ts`) means postgres.js
 * never learns array type oids from the database, so a bound JS array
 * serializes as a bare comma-joined string (`a,b,c`) instead of `{a,b,c}` —
 * `ANY($1::text[])` then fails with "malformed array literal". Casting the
 * SQL text alone doesn't fix it; the value itself has to already be in
 * literal form when it reaches Postgres.
 */
function pgTextArray(values: readonly string[]): string {
  const escaped = values.map((v) => `"${v.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`);
  return `{${escaped.join(",")}}`;
}

export function schemaMarkerColumns(sql: Sql) {
  const tables = pgTextArray(SCHEMA_MARKERS.map(([table]) => table));
  const columns = pgTextArray(SCHEMA_MARKERS.map(([, column]) => column));

  return sql<SchemaColumnRow[]>`
    SELECT table_name, column_name
      FROM information_schema.columns
     WHERE table_schema = 'telemetry'
       AND table_name = ANY(${tables}::text[])
       AND column_name = ANY(${columns}::text[])
  `;
}
