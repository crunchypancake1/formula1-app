import { describe, it, expect } from "vitest";
import { readLatestSession } from "../../worker/queries/sessions";
import { sessionRow } from "../fixtures";

describe("readLatestSession", () => {
  it("returns the first row — the query orders by session_start_utc DESC", async () => {
    const rows = [
      sessionRow({ session_uid: "newest", session_start_utc: new Date("2026-08-19T18:00:00Z") }),
    ];

    const session = await readLatestSession(async () => rows);

    expect(session?.session_uid).toBe("newest");
  });

  it("returns null on an empty database", async () => {
    expect(await readLatestSession(async () => [])).toBeNull();
  });
});
