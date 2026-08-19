import { describe, it, expect } from "vitest";
import { readRoster } from "../../worker/queries/entries";
import { rosterEntry } from "../fixtures";

describe("readRoster", () => {
  it("passes the joined rows through", async () => {
    const rows = [rosterEntry({ car_index: 0 }), rosterEntry({ car_index: 1, user_id: 2 })];

    expect(await readRoster(async () => rows)).toHaveLength(2);
  });

  it("is empty when the session has no entries yet", async () => {
    expect(await readRoster(async () => [])).toEqual([]);
  });
});
