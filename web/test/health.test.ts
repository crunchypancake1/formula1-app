import { describe, it, expect } from "vitest";
import { checkHealth } from "../worker/health";

describe("checkHealth", () => {
  it("reports ok with the table count when the query succeeds", async () => {
    const result = await checkHealth(async () => 26);

    expect(result.ok).toBe(true);
    expect(result.telemetryTables).toBe(26);
    expect(result.latencyMs).toBeGreaterThanOrEqual(0);
  });

  it("reports not ok when the schema is incomplete", async () => {
    const result = await checkHealth(async () => 25);

    expect(result.ok).toBe(false);
    expect(result.telemetryTables).toBe(25);
  });

  it("reports not ok when the schema is missing tables", async () => {
    const result = await checkHealth(async () => 0);

    expect(result.ok).toBe(false);
    expect(result.telemetryTables).toBe(0);
  });

  it("propagates the error when the query throws", async () => {
    await expect(
      checkHealth(async () => {
        throw new Error("connection refused");
      })
    ).rejects.toThrow("connection refused");
  });
});
