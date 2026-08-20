import { describe, it, expect } from "vitest";
import { TEAM_ROLES } from "../../src/discord/teamRoles";

describe("TEAM_ROLES", () => {
  it("covers all 11 F1 26 teams plus Reserve", () => {
    expect(TEAM_ROLES).toHaveLength(12);
  });

  it("has a unique key and name for every role", () => {
    expect(new Set(TEAM_ROLES.map((r) => r.key)).size).toBe(TEAM_ROLES.length);
    expect(new Set(TEAM_ROLES.map((r) => r.name)).size).toBe(TEAM_ROLES.length);
  });

  it("gives every role a valid RGB color", () => {
    for (const role of TEAM_ROLES) {
      expect(role.color).toBeGreaterThanOrEqual(0);
      expect(role.color).toBeLessThanOrEqual(0xffffff);
    }
  });

  it("includes a Reserve role", () => {
    expect(TEAM_ROLES.find((r) => r.key === "RESERVE")?.name).toBe("Reserve");
  });
});
