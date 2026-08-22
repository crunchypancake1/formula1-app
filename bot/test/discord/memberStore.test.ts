import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { env } from "cloudflare:test";
import { syncMembers } from "../../src/discord/memberStore";

const GUILD = "guild-1";
const MEMBERS_KEY = "members:v1";

function member(id: string, overrides: Partial<{ nick: string | null; roles: string[] }> = {}) {
  return {
    user: { id, username: `user-${id}`, global_name: `Global ${id}`, avatar: null },
    nick: overrides.nick ?? null,
    roles: overrides.roles ?? [],
    joined_at: "2026-01-01T00:00:00Z",
  };
}

/**
 * Stands in for `GET /guilds/{id}/members`. `client.ts` talks to Discord over
 * bare `fetch`, so stubbing that is the seam — it keeps pagination (the
 * `after` cursor) under test rather than mocking it away.
 */
function stubDiscord(pages: ReturnType<typeof member>[][]) {
  const calls: Array<{ path: string }> = [];
  let call = 0;

  vi.stubGlobal("fetch", async (url: string) => {
    const path = new URL(url).pathname.replace("/api/v10", "") + new URL(url).search;
    calls.push({ path });
    const page = pages[call] ?? [];
    call++;
    return new Response(JSON.stringify(page), { status: 200 });
  });

  return calls;
}

const kv = () => env.BOT_STATE;

beforeEach(async () => {
  await kv().delete(MEMBERS_KEY);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("syncMembers", () => {
  it("fetches the roster and stores it in KV", async () => {
    stubDiscord([[member("1"), member("2", { nick: "Nicky", roles: ["role-a"] })]]);

    const members = await syncMembers(kv(), "token", GUILD);

    expect(members).toEqual([
      { id: "1", username: "user-1", displayName: "Global 1", avatar: null, roles: [], joinedAt: "2026-01-01T00:00:00Z" },
      { id: "2", username: "user-2", displayName: "Nicky", avatar: null, roles: ["role-a"], joinedAt: "2026-01-01T00:00:00Z" },
    ]);

    const stored = await kv().get<{ members: unknown[] }>(MEMBERS_KEY, "json");
    expect(stored?.members).toEqual(members);
  });

  it("pages through the roster with the after-cursor until a short page ends it", async () => {
    const page1 = Array.from({ length: 1000 }, (_, i) => member(String(i + 1)));
    const page2 = [member("1001")];
    const calls = stubDiscord([page1, page2]);

    const members = await syncMembers(kv(), "token", GUILD);

    expect(members).toHaveLength(1001);
    expect(calls).toEqual([
      { path: `/guilds/${GUILD}/members?limit=1000&after=0` },
      { path: `/guilds/${GUILD}/members?limit=1000&after=1000` },
    ]);
  });

  it("skips the KV write when the roster hasn't changed", async () => {
    stubDiscord([[member("1")]]);
    await syncMembers(kv(), "token", GUILD);
    const firstWrite = await kv().get(MEMBERS_KEY);

    vi.unstubAllGlobals();
    stubDiscord([[member("1")]]);
    await syncMembers(kv(), "token", GUILD);

    expect(await kv().get(MEMBERS_KEY)).toBe(firstWrite);
  });

  it("overwrites KV once the roster changes", async () => {
    stubDiscord([[member("1")]]);
    await syncMembers(kv(), "token", GUILD);

    vi.unstubAllGlobals();
    stubDiscord([[member("1"), member("2")]]);
    const members = await syncMembers(kv(), "token", GUILD);

    const stored = await kv().get<{ members: unknown[] }>(MEMBERS_KEY, "json");
    expect(stored?.members).toEqual(members);
    expect(stored?.members).toHaveLength(2);
  });

  it("refuses to call Discord with an empty guild id", async () => {
    const calls = stubDiscord([[]]);
    await expect(syncMembers(kv(), "token", "")).rejects.toThrow("DISCORD_GUILD_ID");
    expect(calls).toEqual([]);
  });
});
