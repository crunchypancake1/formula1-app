import { describe, it, expect } from "vitest";
import { byCarIndex, readRoster, restrictedDrivers } from "../../src/queries/entries";
import { MAX_CARS } from "../../src/schema";
import { rosterEntry } from "../fixtures";

describe("readRoster", () => {
  it("passes the joined rows through", async () => {
    const rows = [rosterEntry({ car_index: 0 }), rosterEntry({ car_index: 1, user_id: 2 })];

    expect(await readRoster(async () => rows)).toHaveLength(2);
  });
});

describe("restrictedDrivers", () => {
  it("selects the drivers whose telemetry is not public", () => {
    const roster = [
      rosterEntry({ user_id: 1, car_index: 0, telemetry_public: true }),
      rosterEntry({ user_id: 2, car_index: 1, telemetry_public: false }),
    ];

    expect(restrictedDrivers(roster).map((e) => e.user_id)).toEqual([2]);
  });

  it("is empty when every driver runs public telemetry", () => {
    expect(restrictedDrivers([rosterEntry({ telemetry_public: true })])).toEqual([]);
  });
});

describe("byCarIndex", () => {
  it("keys the roster by car_index across a full 24-car grid", () => {
    const roster = Array.from({ length: MAX_CARS }, (_, i) =>
      rosterEntry({ car_index: i, user_id: i + 1 })
    );

    const indexed = byCarIndex(roster);

    expect(indexed.size).toBe(MAX_CARS);
    expect(indexed.get(23)?.user_id).toBe(24);
  });
});
