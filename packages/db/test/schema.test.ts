import { describe, it, expect } from "vitest";
import { formatLapTime, parseMs } from "../src/schema";

describe("parseMs", () => {
  it("decodes the string postgres.js returns for BIGINT", () => {
    expect(parseMs("83456")).toBe(83456);
  });

  it("keeps a genuine zero distinct from a missing value", () => {
    expect(parseMs(0)).toBe(0);
    expect(parseMs(null)).toBeNull();
    expect(parseMs(undefined)).toBeNull();
  });

  it("returns null rather than NaN for junk", () => {
    expect(parseMs("not-a-number")).toBeNull();
  });
});

describe("formatLapTime", () => {
  it("formats milliseconds as m:ss.mmm", () => {
    expect(formatLapTime("83456")).toBe("1:23.456");
  });

  it("pads seconds and milliseconds", () => {
    expect(formatLapTime(61007)).toBe("1:01.007");
  });

  it("renders a withheld time as a dash, not 0:00.000", () => {
    expect(formatLapTime(null)).toBe("—");
  });
});
