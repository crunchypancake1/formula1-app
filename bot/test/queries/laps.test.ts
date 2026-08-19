import { describe, it, expect } from "vitest";
import { readFastestValidLap, readSessionBests, readTyreStints } from "../../src/queries/laps";
import { formatLapTime } from "@f1/db";
import { fastestLap, sessionBest, tyreStint } from "../fixtures";

describe("readFastestValidLap", () => {
  it("returns the first row — the query orders by lap_time_ms", async () => {
    const lap = await readFastestValidLap(async () => [
      fastestLap({ driver_name: "Driver One", lap_time_ms: 83456 }),
    ]);

    expect(lap?.driver_name).toBe("Driver One");
    expect(formatLapTime(lap?.lap_time_ms)).toBe("1:23.456");
  });

  it("returns null when nobody has set a valid lap", async () => {
    expect(await readFastestValidLap(async () => [])).toBeNull();
  });
});

describe("readSessionBests", () => {
  it("carries the joined lap times", async () => {
    const [best] = await readSessionBests(async () => [sessionBest()]);

    expect(best.best_lap_num).toBe(12);
    expect(formatLapTime(best.best_lap_time_ms)).toBe("1:23.456");
  });

  it("keeps an unset best null rather than reporting lap 0", async () => {
    const [best] = await readSessionBests(async () => [
      sessionBest({ best_lap_num: null, best_lap_time_ms: null }),
    ]);

    expect(best.best_lap_num).toBeNull();
    expect(best.best_lap_num).not.toBe(0);
    expect(formatLapTime(best.best_lap_time_ms)).toBe("—");
  });

  it("allows a sector best from a different lap than the best lap", async () => {
    const [best] = await readSessionBests(async () => [sessionBest()]);

    expect(best.best_sector2_lap_num).toBe(9);
    expect(best.best_lap_num).toBe(12);
  });
});

describe("readTyreStints", () => {
  it("passes stints through in order", async () => {
    const rows = [
      tyreStint({ stint_number: 1, actual_compound: "C3", visual_compound: "MEDIUM" }),
      tyreStint({ stint_number: 2, actual_compound: "C4", visual_compound: "SOFT" }),
    ];

    expect((await readTyreStints(async () => rows)).map((s) => s.visual_compound)).toEqual([
      "MEDIUM",
      "SOFT",
    ]);
  });

  it("accepts a compound this build does not know about", async () => {
    // safe_enum_name degrades an unrecognised compound rather than dropping the
    // stint, so the row type has to admit it too.
    const rows = [tyreStint({ actual_compound: "UNKNOWN_99", visual_compound: "UNKNOWN_99" })];

    const [stint] = await readTyreStints(async () => rows);

    expect(stint.actual_compound).toBe("UNKNOWN_99");
  });
});
