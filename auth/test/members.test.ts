import { describe, it, expect } from "vitest";
import { isGuildMember } from "../src/members";

function membersKv(stored: unknown): KVNamespace {
  return { get: async () => stored } as unknown as KVNamespace;
}

describe("isGuildMember", () => {
  it("returns true when the id is in the stored roster", async () => {
    const kv = membersKv({ members: [{ id: "1" }, { id: "42" }] });
    expect(await isGuildMember(kv, "42")).toBe(true);
  });

  it("returns false when the id isn't in the stored roster", async () => {
    const kv = membersKv({ members: [{ id: "1" }] });
    expect(await isGuildMember(kv, "42")).toBe(false);
  });

  it("fails closed when nothing has been synced yet", async () => {
    const kv = membersKv(null);
    expect(await isGuildMember(kv, "42")).toBe(false);
  });
});
