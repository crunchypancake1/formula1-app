import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { env } from "cloudflare:test";
import { ensureTeamRoles, resetTeamRoleCache } from "../../src/discord/roleStore";
import { TEAM_ROLES } from "../../src/discord/teamRoles";

const GUILD = "guild-1";
const CACHE_KEY = "team-roles:v1";

interface FetchCall {
  method: string;
  path: string;
  body: Record<string, unknown> | null;
}

/**
 * Stands in for the guild's role list. `client.ts` talks to Discord over bare
 * `fetch`, so stubbing that is the seam — it keeps the request shape
 * (`POST /guilds/{id}/roles`) under test rather than mocking it away.
 */
function stubDiscord(initial: Array<{ id: string; name: string; color: number }> = []) {
  const roles = [...initial];
  const calls: FetchCall[] = [];
  let created = 0;

  vi.stubGlobal("fetch", async (url: string, init: RequestInit) => {
    const path = new URL(url).pathname.replace("/api/v10", "");
    const body = init.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : null;
    calls.push({ method: init.method ?? "GET", path, body });

    if (init.method === "POST" && path === `/guilds/${GUILD}/roles`) {
      const role = { id: `created-${++created}`, name: body!.name as string, color: body!.color as number };
      roles.push(role);
      return new Response(JSON.stringify(role), { status: 200 });
    }
    if (path === `/guilds/${GUILD}/roles`) {
      return new Response(JSON.stringify(roles), { status: 200 });
    }
    return new Response("unexpected", { status: 500 });
  });

  return { calls, roles };
}

const kv = () => env.BOT_STATE;

beforeEach(async () => {
  resetTeamRoleCache();
  await kv().delete(CACHE_KEY);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ensureTeamRoles", () => {
  it("creates every missing role and caches the map in KV", async () => {
    const { calls } = stubDiscord();

    const map = await ensureTeamRoles(kv(), "token", GUILD);

    expect(Object.keys(map)).toHaveLength(TEAM_ROLES.length);
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(TEAM_ROLES.length);
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      name: "Mercedes",
      color: 0x00d2be,
    });

    const cached = await kv().get<{ roles: Record<string, string> }>(CACHE_KEY, "json");
    expect(cached?.roles).toEqual(map);
  });

  it("adopts a role that already exists in the guild instead of duplicating it", async () => {
    const { calls } = stubDiscord([{ id: "existing-ferrari", name: "Ferrari", color: 0x111111 }]);

    const map = await ensureTeamRoles(kv(), "token", GUILD);

    expect(map.FERRARI).toBe("existing-ferrari");
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(TEAM_ROLES.length - 1);
  });

  it("serves a fresh cache without calling Discord at all", async () => {
    const first = stubDiscord();
    const map = await ensureTeamRoles(kv(), "token", GUILD, 1_000);
    expect(first.calls.length).toBeGreaterThan(0);

    vi.unstubAllGlobals();
    resetTeamRoleCache(); // force the KV read rather than the in-isolate memo
    const second = stubDiscord();

    expect(await ensureTeamRoles(kv(), "token", GUILD, 1_000 + 60_000)).toEqual(map);
    expect(second.calls).toEqual([]);
  });

  it("re-lists the guild once the cache goes stale, keeping the ids it still finds", async () => {
    const first = stubDiscord();
    const map = await ensureTeamRoles(kv(), "token", GUILD, 1_000);

    vi.unstubAllGlobals();
    resetTeamRoleCache();
    const second = stubDiscord(first.roles);

    const later = await ensureTeamRoles(kv(), "token", GUILD, 1_000 + 2 * 60 * 60 * 1000);

    expect(later).toEqual(map);
    expect(second.calls.filter((c) => c.method === "GET")).toHaveLength(1);
    expect(second.calls.filter((c) => c.method === "POST")).toEqual([]);
  });

  it("recreates a role deleted from the guild on the next revalidation", async () => {
    const first = stubDiscord();
    const map = await ensureTeamRoles(kv(), "token", GUILD, 1_000);

    vi.unstubAllGlobals();
    resetTeamRoleCache();
    const survivors = first.roles.filter((r) => r.name !== "Haas");
    const second = stubDiscord(survivors);

    const later = await ensureTeamRoles(kv(), "token", GUILD, 1_000 + 2 * 60 * 60 * 1000);

    expect(second.calls.filter((c) => c.method === "POST").map((c) => c.body?.name)).toEqual([
      "Haas",
    ]);
    expect(later.HAAS).not.toBe(map.HAAS);
    expect(later.MERCEDES).toBe(map.MERCEDES);
  });

  it("rebuilds from the guild when the cached value is malformed", async () => {
    await kv().put(CACHE_KEY, JSON.stringify({ nonsense: true }));
    const { calls } = stubDiscord();

    const map = await ensureTeamRoles(kv(), "token", GUILD);

    expect(Object.keys(map)).toHaveLength(TEAM_ROLES.length);
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(TEAM_ROLES.length);
  });

  it("refuses to call Discord with an empty guild id", async () => {
    const { calls } = stubDiscord();
    await expect(ensureTeamRoles(kv(), "token", "")).rejects.toThrow("DISCORD_GUILD_ID");
    expect(calls).toEqual([]);
  });
});
