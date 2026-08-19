import { describe, it, expect } from "vitest";
import { checkSchema, SCHEMA_MARKERS, type SchemaColumnRow } from "../src/health";

const allMarkers = (): SchemaColumnRow[] =>
  SCHEMA_MARKERS.map(([table_name, column_name]) => ({ table_name, column_name }));

describe("checkSchema", () => {
  it("passes when every 2026 marker column is present", async () => {
    const result = await checkSchema(async () => allMarkers());

    expect(result.ok).toBe(true);
    expect(result.missing).toEqual([]);
    expect(result.latencyMs).toBeGreaterThanOrEqual(0);
  });

  it("names the markers a pre-2026 database is missing", async () => {
    // The pre-upgrade schema called it entries.telemetry_setting and had no
    // session_bests table at all.
    const stale = allMarkers().filter(
      (row) =>
        !(row.table_name === "entries" && row.column_name === "telemetry_public") &&
        row.table_name !== "session_bests"
    );

    const result = await checkSchema(async () => stale);

    expect(result.ok).toBe(false);
    expect(result.missing).toContain("entries.telemetry_public");
    expect(result.missing).toContain("session_bests.best_lap_num");
  });

  it("fails against an empty database", async () => {
    const result = await checkSchema(async () => []);

    expect(result.ok).toBe(false);
    expect(result.missing).toHaveLength(SCHEMA_MARKERS.length);
  });

  it("does not credit a marker to the wrong table", async () => {
    const crossed = allMarkers().map((row) =>
      row.column_name === "game_points" ? { ...row, table_name: "sessions" } : row
    );

    const result = await checkSchema(async () => crossed);

    expect(result.ok).toBe(false);
    expect(result.missing).toEqual(["race_classification.game_points"]);
  });

  it("propagates the error when the query throws", async () => {
    await expect(
      checkSchema(async () => {
        throw new Error("connection refused");
      })
    ).rejects.toThrow("connection refused");
  });
});
