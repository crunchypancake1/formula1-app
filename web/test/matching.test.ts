import { describe, it, expect } from "vitest";
import { matchDriver, normalizeDriverName, similarity } from "../worker/matching";

describe("normalizeDriverName", () => {
  it("strips known reserve/wildcard suffixes", () => {
    expect(normalizeDriverName("Crunchypancake1_RES")).toBe("crunchypancake");
  });

  it("treats separators as equivalent", () => {
    expect(normalizeDriverName("Rollie_A1881")).toBe(normalizeDriverName("Rollie A1881"));
  });

  it("does not collapse two genuinely different handles", () => {
    expect(normalizeDriverName("rollie_a1181")).not.toBe(normalizeDriverName("rollie1881"));
  });
});

describe("similarity", () => {
  it("scores identical strings as 1", () => {
    expect(similarity("rollie", "rollie")).toBe(1);
  });

  it("scores unrelated strings low", () => {
    expect(similarity("rollie", "zzzzzz")).toBeLessThan(0.2);
  });
});

describe("matchDriver", () => {
  it("matches a normalized exact hit", () => {
    const result = matchDriver("Crunchypancake1_RES", null, [
      { userId: 1, driverName: "Crunchypancake" },
      { userId: 2, driverName: "Someone Else" },
    ]);
    expect(result).toEqual({ userId: 1, driverName: "Crunchypancake" });
  });

  it("takes the better of username and nickname score", () => {
    const result = matchDriver("totally_unrelated_handle", "Rollie A1881", [
      { userId: 1, driverName: "Rollie_A1881" },
      { userId: 2, driverName: "Someone Else" },
    ]);
    expect(result?.userId).toBe(1);
  });

  it("returns null when two candidates tie (no confident margin)", () => {
    const result = matchDriver("rollo1881", null, [
      { userId: 1, driverName: "rollie1880" },
      { userId: 2, driverName: "rollie1882" },
    ]);
    expect(result).toBeNull();
  });

  it("returns null when nothing scores high enough", () => {
    const result = matchDriver("zzzzzzzz", null, [{ userId: 1, driverName: "Someone Else" }]);
    expect(result).toBeNull();
  });

  it("returns null for an empty candidate list", () => {
    expect(matchDriver("anyone", null, [])).toBeNull();
  });
});
