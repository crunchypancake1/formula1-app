import { describe, it, expect } from "vitest";
import { formatLapTime, parseMs, parsePgArray, parsePgNumberArray } from "../src/schema";

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

describe("parsePgArray", () => {
  it("decodes the raw Postgres literal fetch_types:false leaves array columns as", () => {
    expect(parsePgArray("{YELLOW,GREEN}")).toEqual(["YELLOW", "GREEN"]);
  });

  it("decodes an empty array literal as an empty array, not null", () => {
    expect(parsePgArray("{}")).toEqual([]);
  });

  it("passes an already-parsed array through unchanged", () => {
    expect(parsePgArray(["YELLOW"])).toEqual(["YELLOW"]);
  });

  it("keeps null distinct from an empty array", () => {
    expect(parsePgArray(null)).toBeNull();
    expect(parsePgArray(undefined)).toBeNull();
  });

  it("unescapes a quoted element containing a comma", () => {
    expect(parsePgArray('{"a,b",c}')).toEqual(["a,b", "c"]);
  });

  it("unescapes a backslash-escaped quote inside a quoted element", () => {
    expect(parsePgArray('{"a\\"b"}')).toEqual(['a"b']);
  });
});

describe("parsePgNumberArray", () => {
  it("decodes a smallint array literal into numbers, not strings", () => {
    expect(parsePgNumberArray("{16,18}")).toEqual([16, 18]);
  });

  it("decodes an empty array literal as an empty array, not null", () => {
    expect(parsePgNumberArray("{}")).toEqual([]);
  });

  it("passes an already-parsed array through unchanged", () => {
    expect(parsePgNumberArray([16, 18])).toEqual([16, 18]);
  });

  it("keeps null distinct from an empty array", () => {
    expect(parsePgNumberArray(null)).toBeNull();
    expect(parsePgNumberArray(undefined)).toBeNull();
  });

  it("handles a negative element", () => {
    expect(parsePgNumberArray("{-1,0}")).toEqual([-1, 0]);
  });
});
