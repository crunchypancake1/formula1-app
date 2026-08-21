import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { env } from "cloudflare:test";
import { COMMANDS, ensureCommands } from "../../src/discord/commands";

const APP = "app-1";
const GUILD = "guild-1";
const SYNC_KEY = "commands:v1";

function stubDiscord() {
  const calls: Array<{ method: string; path: string; body: unknown }> = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit) => {
    const path = new URL(url).pathname.replace("/api/v10", "");
    calls.push({
      method: init.method ?? "GET",
      path,
      body: init.body ? JSON.parse(init.body as string) : null,
    });

    if (path === "/applications/@me") {
      return new Response(JSON.stringify({ id: APP }), { status: 200 });
    }
    return new Response("[]", { status: 200 });
  });
  return calls;
}

const kv = () => env.BOT_STATE;

beforeEach(async () => {
  await kv().delete(SYNC_KEY);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ensureCommands", () => {
  it("registers every command as a guild command on first run", async () => {
    const calls = stubDiscord();

    expect(await ensureCommands(kv(), "token", GUILD)).toBe(true);

    // The application id is looked up rather than configured, so a sync is two
    // calls: identify the app, then overwrite its guild command list.
    expect(calls.map((c) => c.path)).toEqual([
      "/applications/@me",
      `/applications/${APP}/guilds/${GUILD}/commands`,
    ]);
    expect(calls[1].method).toBe("PUT");
    expect(calls[1].body).toEqual(
      COMMANDS.map((c) => ({ name: c.name, description: c.description, options: [] }))
    );
  });

  it("skips the call entirely when the registered set is unchanged", async () => {
    stubDiscord();
    await ensureCommands(kv(), "token", GUILD);

    vi.unstubAllGlobals();
    const second = stubDiscord();

    // Not even the /applications/@me lookup — an unchanged set costs one KV
    // read and no Discord traffic.
    expect(await ensureCommands(kv(), "token", GUILD)).toBe(false);
    expect(second).toEqual([]);
  });

  it("re-registers once the stored fingerprint no longer matches", async () => {
    await kv().put(SYNC_KEY, "stale-from-an-older-deploy");
    const calls = stubDiscord();

    expect(await ensureCommands(kv(), "token", GUILD)).toBe(true);
    expect(calls.map((c) => c.method)).toEqual(["GET", "PUT"]);
  });

  it("refuses to call Discord with an empty guild id", async () => {
    const calls = stubDiscord();

    await expect(ensureCommands(kv(), "token", "")).rejects.toThrow("DISCORD_GUILD_ID");
    expect(calls).toEqual([]);
  });

  it("gives every command a name and description Discord will accept", () => {
    for (const command of COMMANDS) {
      expect(command.name).toMatch(/^[a-z][a-z0-9_-]{0,31}$/);
      expect(command.description.length).toBeGreaterThan(0);
      expect(command.description.length).toBeLessThanOrEqual(100);
      // Anything reading Postgres must defer — Hyperdrive plus the tunnel is
      // not reliably inside Discord's 3s initial-response budget.
      expect(command.deferred).toBe(true);
    }
  });
});
