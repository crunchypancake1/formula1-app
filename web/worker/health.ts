export interface HealthResult {
  ok: boolean;
  telemetryTables: number;
  latencyMs: number;
}

/**
 * A healthy schema has all 26 telemetry base tables — 27 SQL files, of which
 * auto_link_trigger.sql creates a trigger rather than a table.
 */
const EXPECTED_TELEMETRY_TABLES = 26;

export async function checkHealth(
  countTelemetryTables: () => Promise<number>
): Promise<HealthResult> {
  const started = Date.now();
  const telemetryTables = await countTelemetryTables();

  return {
    ok: telemetryTables === EXPECTED_TELEMETRY_TABLES,
    telemetryTables,
    latencyMs: Date.now() - started,
  };
}
