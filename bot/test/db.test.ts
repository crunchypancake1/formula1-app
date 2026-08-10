import { describe, it, expect } from "vitest";
import { readLatestSessionUid } from "../src/db";

describe("readLatestSessionUid", () => {
  it("returns the uid when a session exists", async () => {
    const rows = [{ session_uid: "1234567890" }];
    expect(await readLatestSessionUid(async () => rows)).toBe("1234567890");
  });

  it("returns null on an empty database", async () => {
    expect(await readLatestSessionUid(async () => [])).toBeNull();
  });
});
