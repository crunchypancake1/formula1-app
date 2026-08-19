import { describe, it, expect } from "vitest";
import {
  ACTUAL_TYRE_COMPOUND_CODES,
  displayEnum,
  DRIVER_STATUS_CODES,
  enumFromCode,
  FLAG_STATUS_CODES,
  isKnownEnum,
  PIT_STATUS_CODES,
  SURFACE_TYPE_CODES,
  unknownEnumValue,
  VISUAL_TYRE_COMPOUND_CODES,
} from "../src/enums";

describe("isKnownEnum", () => {
  it("accepts a member name the listener resolved", () => {
    expect(isKnownEnum("DID_NOT_FINISH")).toBe(true);
  });

  it("rejects the UNKNOWN_<n> fallback", () => {
    expect(isKnownEnum("UNKNOWN_37")).toBe(false);
  });

  it("treats a bare UNKNOWN as known — several enums define it as a real member", () => {
    expect(isKnownEnum("UNKNOWN")).toBe(true);
  });
});

describe("unknownEnumValue", () => {
  it("recovers the raw integer the game sent", () => {
    expect(unknownEnumValue("UNKNOWN_37")).toBe(37);
  });

  it("returns null for a resolved member", () => {
    expect(unknownEnumValue("FINISHED")).toBeNull();
  });
});

describe("displayEnum", () => {
  it("title-cases a member name", () => {
    expect(displayEnum("DID_NOT_FINISH")).toBe("Did Not Finish");
  });

  it("keeps compound identifiers intact", () => {
    expect(displayEnum("C5")).toBe("C5");
    expect(displayEnum("F1_26")).toBe("F1 26");
  });

  it("renders an unrecognised value instead of leaking the sentinel", () => {
    expect(displayEnum("UNKNOWN_37")).toBe("Unknown (37)");
  });
});

describe("enumFromCode", () => {
  it("resolves a car_frame code to its member name", () => {
    expect(enumFromCode(VISUAL_TYRE_COMPOUND_CODES, 16)).toBe("SOFT");
    expect(enumFromCode(DRIVER_STATUS_CODES, 4)).toBe("ON_TRACK");
    expect(enumFromCode(SURFACE_TYPE_CODES, 0)).toBe("TARMAC");
  });

  it("degrades an unrecognised code instead of throwing — a game patch must not break the read", () => {
    const resolved = enumFromCode(ACTUAL_TYRE_COMPOUND_CODES, 99);

    expect(resolved).toBe("UNKNOWN_99");
    expect(isKnownEnum(resolved!)).toBe(false);
    expect(unknownEnumValue(resolved!)).toBe(99);
    expect(displayEnum(resolved!)).toBe("Unknown (99)");
  });

  it("keeps NULL distinct from a zero code — 0 is a real member of several of these", () => {
    expect(enumFromCode(PIT_STATUS_CODES, null)).toBeNull();
    expect(enumFromCode(PIT_STATUS_CODES, 0)).toBe("NONE");
  });

  it("resolves FlagStatus -1, which is a named member rather than the fallback", () => {
    const resolved = enumFromCode(FLAG_STATUS_CODES, -1);

    expect(resolved).toBe("UNKNOWN");
    expect(isKnownEnum(resolved!)).toBe(true);
  });

  it("degrades an unrecognised negative code round-trippably", () => {
    expect(unknownEnumValue(enumFromCode(FLAG_STATUS_CODES, -7)!)).toBe(-7);
  });

  it("maps the compound tables over the gaps the game leaves in its ids", () => {
    // Actual compound ids jump 0 -> 7; 1..6 are genuinely unassigned.
    expect(enumFromCode(ACTUAL_TYRE_COMPOUND_CODES, 0)).toBe("NONE");
    expect(enumFromCode(ACTUAL_TYRE_COMPOUND_CODES, 7)).toBe("INTER");
    expect(enumFromCode(ACTUAL_TYRE_COMPOUND_CODES, 3)).toBe("UNKNOWN_3");
  });
});
