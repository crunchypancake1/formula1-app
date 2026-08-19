import { describe, it, expect } from "vitest";
import { isLinked, readDriver, readDrivers } from "../../src/queries/drivers";
import { userRow } from "../fixtures";

describe("readDriver", () => {
  it("returns the matching user", async () => {
    const user = await readDriver(async () => [userRow({ driver_name: "Driver One" })]);
    expect(user?.driver_name).toBe("Driver One");
  });

  it("returns null when nothing matches", async () => {
    expect(await readDriver(async () => [])).toBeNull();
  });
});

describe("readDrivers", () => {
  it("passes fuzzy search results through in rank order", async () => {
    const rows = [userRow({ id: 1, driver_name: "Driver One" }), userRow({ id: 2, driver_name: "Driver Two" })];

    expect((await readDrivers(async () => rows)).map((u) => u.id)).toEqual([1, 2]);
  });
});

describe("isLinked", () => {
  it("is false for a driver seen in telemetry but not linked to Discord", () => {
    expect(isLinked(userRow({ discord_id: null }))).toBe(false);
  });

  it("is true once a Discord account is attached", () => {
    expect(isLinked(userRow({ discord_id: "123456789" }))).toBe(true);
  });
});
