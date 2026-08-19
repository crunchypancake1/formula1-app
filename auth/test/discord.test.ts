import { afterEach, describe, expect, it, vi } from "vitest";
import {
  discordAvatarUrl,
  exchangeDiscordCode,
  getDiscordUser,
  getGuildMember,
} from "../src/discord";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("exchangeDiscordCode", () => {
  it("posts a form-urlencoded token exchange and returns the access token", async () => {
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      expect(url).toBe("https://discord.com/api/v10/oauth2/token");
      expect(init.method).toBe("POST");
      expect(init.headers).toMatchObject({ "Content-Type": "application/x-www-form-urlencoded" });
      const body = new URLSearchParams(init.body as string);
      expect(body.get("grant_type")).toBe("authorization_code");
      expect(body.get("code")).toBe("the-code");
      return new Response(JSON.stringify({ access_token: "at-123" }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await exchangeDiscordCode(
      "client-id",
      "client-secret",
      "the-code",
      "https://f1.crunchypancake.com/auth/callback"
    );
    expect(result.access_token).toBe("at-123");
  });

  it("throws on a non-2xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("bad code", { status: 400 }))
    );
    await expect(
      exchangeDiscordCode("client-id", "client-secret", "bad-code", "https://example.com/callback")
    ).rejects.toThrow();
  });
});

describe("getDiscordUser", () => {
  it("fetches the current user with a bearer token", async () => {
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      expect(url).toBe("https://discord.com/api/v10/users/@me");
      expect((init.headers as Record<string, string>).Authorization).toBe("Bearer at-123");
      return new Response(JSON.stringify({ id: "1", username: "driver", avatar: null }), {
        status: 200,
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = await getDiscordUser("at-123");
    expect(user.username).toBe("driver");
  });
});

describe("getGuildMember", () => {
  it("returns the member on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ user: { id: "1" } }), { status: 200 }))
    );
    const member = await getGuildMember("bot-token", "guild-1", "1");
    expect(member?.user.id).toBe("1");
  });

  it("returns null on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("not found", { status: 404 }))
    );
    const member = await getGuildMember("bot-token", "guild-1", "1");
    expect(member).toBeNull();
  });

  it("throws on other non-2xx statuses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("server error", { status: 500 }))
    );
    await expect(getGuildMember("bot-token", "guild-1", "1")).rejects.toThrow();
  });
});

describe("discordAvatarUrl", () => {
  it("returns null when the user has no avatar", () => {
    expect(discordAvatarUrl({ id: "1", username: "driver", avatar: null })).toBeNull();
  });

  it("returns a static png URL for a non-animated avatar", () => {
    expect(discordAvatarUrl({ id: "1", username: "driver", avatar: "abc123" })).toBe(
      "https://cdn.discordapp.com/avatars/1/abc123.png"
    );
  });

  it("returns an animated gif URL for an animated avatar hash", () => {
    expect(discordAvatarUrl({ id: "1", username: "driver", avatar: "a_abc123" })).toBe(
      "https://cdn.discordapp.com/avatars/1/a_abc123.gif"
    );
  });
});
