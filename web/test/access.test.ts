import { exportJWK, generateKeyPair, SignJWT } from "jose";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { readViewer } from "../worker/access";
import type { WebEnv } from "../worker/env";

const TEAM_DOMAIN = "https://team.cloudflareaccess.com";
const AUD = "test-aud";

let privateKey: CryptoKey;
let publicJwk: Record<string, unknown>;

beforeAll(async () => {
  const { privateKey: priv, publicKey } = await generateKeyPair("ES256", { extractable: true });
  privateKey = priv;
  publicJwk = { ...(await exportJWK(publicKey)), alg: "ES256", use: "sig", kid: "1" };
});

function env(): WebEnv {
  return {
    HYPERDRIVE: {} as Hyperdrive,
    ACCESS_TEAM_DOMAIN: TEAM_DOMAIN,
    ACCESS_POLICY_AUD: AUD,
    BOT_STATE: {} as KVNamespace,
  };
}

function request(token?: string): Request {
  return new Request("https://f1.example.com/me", {
    headers: token ? { "cf-access-jwt-assertion": token } : {},
  });
}

function sign(payload: Record<string, unknown>, audience = AUD): Promise<string> {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: "ES256", kid: "1" })
    .setIssuedAt()
    .setIssuer(TEAM_DOMAIN)
    .setAudience(audience)
    .setExpirationTime("5m")
    .sign(privateKey);
}

describe("readViewer", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns null with no cf-access-jwt-assertion header", async () => {
    expect(await readViewer(env(), request())).toBeNull();
  });

  it("returns null when the token audience does not match", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ keys: [publicJwk] }))));
    const token = await sign({ custom: { discord_id: "42" } }, "someone-else");
    expect(await readViewer(env(), request(token))).toBeNull();
  });

  it("returns null when the token has no custom.discord_id claim", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ keys: [publicJwk] }))));
    const token = await sign({});
    expect(await readViewer(env(), request(token))).toBeNull();
  });

  it("returns the viewer for a valid token", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ keys: [publicJwk] }))));
    const token = await sign({ custom: { discord_id: "42", preferred_username: "driver" } });
    expect(await readViewer(env(), request(token))).toEqual({ discordId: "42", username: "driver" });
  });
});
