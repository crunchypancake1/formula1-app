import { describe, it, expect } from "vitest";
import {
  nonFinishers,
  readQualifyingClassification,
  readRaceClassification,
} from "../../src/queries/results";
import { formatLapTime, parseMs } from "@f1/db";
import { qualifyingResult, raceResult } from "../fixtures";

describe("readRaceClassification", () => {
  it("passes the rows through in position order", async () => {
    const rows = [
      raceResult({ position: 1, user_id: 1 }),
      raceResult({ position: 2, user_id: 2 }),
    ];

    expect((await readRaceClassification(async () => rows)).map((r) => r.position)).toEqual([1, 2]);
  });

  it("keeps a null game_points null — the game awarded none, it did not award zero", async () => {
    const [row] = await readRaceClassification(async () => [raceResult({ game_points: null })]);

    expect(row.game_points).toBeNull();
    expect(row.game_points).not.toBe(0);
  });

  it("decodes best_lap_time_ms, which arrives as a BIGINT string", async () => {
    const [row] = await readRaceClassification(async () => [
      raceResult({ best_lap_time_ms: "83456" }),
    ]);

    expect(parseMs(row.best_lap_time_ms)).toBe(83456);
    expect(formatLapTime(row.best_lap_time_ms)).toBe("1:23.456");
  });
});

describe("readQualifyingClassification", () => {
  it("carries the F1 26 result_reason column", async () => {
    const [row] = await readQualifyingClassification(async () => [
      qualifyingResult({ result_status: "DID_NOT_FINISH", result_reason: "TERMINAL_DAMAGE" }),
    ]);

    expect(row.result_reason).toBe("TERMINAL_DAMAGE");
  });

  it("renders a driver with no valid lap as a dash", async () => {
    const [row] = await readQualifyingClassification(async () => [
      qualifyingResult({ best_lap_time_ms: null }),
    ]);

    expect(formatLapTime(row.best_lap_time_ms)).toBe("—");
  });
});

describe("nonFinishers", () => {
  it("selects on result_status, which is populated even when result_reason is null", () => {
    const results = [
      raceResult({ user_id: 1, result_status: "FINISHED" }),
      raceResult({ user_id: 2, result_status: "RETIRED", result_reason: null }),
      raceResult({ user_id: 3, result_status: "DISQUALIFIED", result_reason: "BLACK_FLAGGED" }),
    ];

    expect(nonFinishers(results).map((r) => r.user_id)).toEqual([2, 3]);
  });
});
