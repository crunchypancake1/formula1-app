import { describe, it, expect } from "vitest";
import { readTeamRoles } from "../../src/queries/discordRoles";
import { discordTeamRoleRow } from "../fixtures";

describe("readTeamRoles", () => {
  it("passes tracked role rows through", async () => {
    const rows = [
      discordTeamRoleRow({ role_key: "FERRARI" }),
      discordTeamRoleRow({ role_key: "MCLAREN" }),
    ];
    expect((await readTeamRoles(async () => rows)).map((r) => r.role_key)).toEqual([
      "FERRARI",
      "MCLAREN",
    ]);
  });

  it("returns an empty array when nothing is tracked yet", async () => {
    expect(await readTeamRoles(async () => [])).toEqual([]);
  });
});
