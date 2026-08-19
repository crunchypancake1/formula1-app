import { describe, it, expect } from "vitest";
import {
  readLatestSession,
  readRecentSessions,
  readSessionByUid,
} from "../../src/queries/sessions";
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

describe("readSessionByUid", () => {
  it("returns the matching session", async () => {
    const session = await readSessionByUid(async () => [sessionRow({ session_uid: "abc" })]);
    expect(session?.session_uid).toBe("abc");
  });

  it("returns null when the uid is unknown", async () => {
    expect(await readSessionByUid(async () => [])).toBeNull();
  });
});

describe("readRecentSessions", () => {
  it("passes the rows through in query order", async () => {
    const rows = [sessionRow({ session_uid: "a" }), sessionRow({ session_uid: "b" })];

    expect((await readRecentSessions(async () => rows)).map((s) => s.session_uid)).toEqual([
      "a",
      "b",
    ]);
  });
});
