import { exportPKCS8, generateKeyPair } from "jose";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import app from "../src/index";
import type { AuthEnv, SecretsStoreSecret } from "../src/env";
import { signAuthCode, signRelayState } from "../src/tokens";

function secret(value: string): SecretsStoreSecret {
  return { get: async () => value };
}

/** Stands in for the shared `BOT_STATE` KV namespace `bot`'s cron tick writes `members:v1` to. */
function membersKv(ids: string[]): KVNamespace {
  return { get: async () => ({ members: ids.map((id) => ({ id })) }) } as unknown as KVNamespace;
}

let env: AuthEnv;

beforeAll(async () => {
  const { privateKey } = await generateKeyPair("ES256", { extractable: true });
  const pem = await exportPKCS8(privateKey);

  env = {
    DISCORD_OAUTH_CLIENT_ID: "discord-client",
    ACCESS_CLIENT_ID: "access-client",
    ACCESS_TEAM_DOMAIN: "team.cloudflareaccess.com",
    OIDC_ISSUER: "https://f1.crunchypancake.com/auth",
    DISCORD_OAUTH_CLIENT_SECRET: secret("discord-secret"),
    ACCESS_CLIENT_SECRET: secret("access-secret"),
    OIDC_SIGNING_KEY: secret(pem),
    BOT_STATE: membersKv([]),
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("discovery document", () => {
  it("derives every endpoint from OIDC_ISSUER", async () => {
    const res = await app.request("/auth/.well-known/openid-configuration", {}, env);
    expect(res.status).toBe(200);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.issuer).toBe(env.OIDC_ISSUER);
    expect(body.authorization_endpoint).toBe(`${env.OIDC_ISSUER}/authorize`);
    expect(body.token_endpoint).toBe(`${env.OIDC_ISSUER}/token`);
    expect(body.jwks_uri).toBe(`${env.OIDC_ISSUER}/jwks`);
    expect(body.id_token_signing_alg_values_supported).toEqual(["ES256"]);
  });
});

describe("GET /auth/authorize", () => {
  const validRedirect = "https://team.cloudflareaccess.com/cdn-cgi/access/callback";

  it("redirects to Discord with a relay-state JWT", async () => {
    const res = await app.request(
      `/auth/authorize?client_id=access-client&redirect_uri=${encodeURIComponent(validRedirect)}&state=abc`,
      {},
      env
    );
    expect(res.status).toBe(302);
    const location = new URL(res.headers.get("location")!);
    expect(location.origin + location.pathname).toBe("https://discord.com/oauth2/authorize");
    expect(location.searchParams.get("client_id")).toBe("discord-client");
    expect(location.searchParams.get("redirect_uri")).toBe(`${env.OIDC_ISSUER}/callback`);
    expect(location.searchParams.get("scope")).toBe("identify email");
    expect(location.searchParams.get("state")).toBeTruthy();
  });

  it("rejects an unrecognized client_id", async () => {
    const res = await app.request(
      `/auth/authorize?client_id=wrong&redirect_uri=${encodeURIComponent(validRedirect)}&state=abc`,
      {},
      env
    );
    expect(res.status).toBe(400);
  });

  it("rejects a redirect_uri outside the Access team domain", async () => {
    const res = await app.request(
      `/auth/authorize?client_id=access-client&redirect_uri=${encodeURIComponent("https://evil.example.com/callback")}&state=abc`,
      {},
      env
    );
    expect(res.status).toBe(400);
  });
});

describe("GET /auth/callback", () => {
  const relayRedirect = "https://team.cloudflareaccess.com/cdn-cgi/access/callback";

  it("mints an auth-code and redirects back to Access on a verified member", async () => {
    const state = await signRelayState(env, { redirectUri: relayRedirect, accessState: "relay-state-xyz" });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/oauth2/token")) {
          return new Response(JSON.stringify({ access_token: "discord-at" }), { status: 200 });
        }
        if (url.includes("/users/@me")) {
          return new Response(
            JSON.stringify({ id: "42", username: "driver", avatar: null, email: "driver@example.com" }),
            { status: 200 }
          );
        }
        throw new Error(`unexpected fetch to ${url}`);
      })
    );

    const res = await app.request(
      `/auth/callback?code=discord-code&state=${state}`,
      {},
      { ...env, BOT_STATE: membersKv(["42"]) }
    );
    expect(res.status).toBe(302);
    const location = new URL(res.headers.get("location")!);
    expect(location.origin + location.pathname).toBe(relayRedirect);
    expect(location.searchParams.get("state")).toBe("relay-state-xyz");
    expect(location.searchParams.get("code")).toBeTruthy();
  });

  it("403s without reaching Access when the user isn't a guild member", async () => {
    const state = await signRelayState(env, { redirectUri: relayRedirect, accessState: "relay-state-xyz" });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/oauth2/token")) {
          return new Response(JSON.stringify({ access_token: "discord-at" }), { status: 200 });
        }
        if (url.includes("/users/@me")) {
          return new Response(JSON.stringify({ id: "42", username: "driver", avatar: null }), {
            status: 200,
          });
        }
        throw new Error(`unexpected fetch to ${url}`);
      })
    );

    const res = await app.request(
      `/auth/callback?code=discord-code&state=${state}`,
      {},
      { ...env, BOT_STATE: membersKv([]) }
    );
    expect(res.status).toBe(403);
  });
});

describe("POST /auth/token", () => {
  it("exchanges a valid auth-code for an id_token", async () => {
    const authCode = await signAuthCode(env, { sub: "42", preferredUsername: "driver", picture: null });

    const body = new URLSearchParams({
      grant_type: "authorization_code",
      code: authCode,
      client_id: "access-client",
      client_secret: "access-secret",
    });

    const res = await app.request(
      "/auth/token",
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      },
      env
    );
    expect(res.status).toBe(200);
    const json = (await res.json()) as Record<string, unknown>;
    expect(json.token_type).toBe("Bearer");
    expect(json.id_token).toBeTruthy();
    expect(json.access_token).toBe(json.id_token);
  });

  it("rejects a wrong client secret", async () => {
    const authCode = await signAuthCode(env, { sub: "42", preferredUsername: "driver", picture: null });

    const body = new URLSearchParams({
      grant_type: "authorization_code",
      code: authCode,
      client_id: "access-client",
      client_secret: "wrong-secret",
    });

    const res = await app.request(
      "/auth/token",
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      },
      env
    );
    expect(res.status).toBe(401);
  });
});

describe("GET /auth/jwks", () => {
  it("returns a single EC public key", async () => {
    const res = await app.request("/auth/jwks", {}, env);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { keys: Array<Record<string, unknown>> };
    expect(body.keys).toHaveLength(1);
    expect(body.keys[0].kty).toBe("EC");
  });
});
