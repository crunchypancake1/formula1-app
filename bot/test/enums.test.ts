import { describe, it, expect } from "vitest";
import { displayEnum, isKnownEnum, unknownEnumValue } from "../src/enums";

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
