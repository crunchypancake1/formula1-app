import { generateKeyPair, exportPKCS8 } from "jose";
import { describe, it, expect, beforeAll } from "vitest";
import type { AuthEnv, SecretsStoreSecret } from "../src/env";
import {
  getJwks,
  signAuthCode,
  signIdToken,
  signRelayState,
  verifyAuthCode,
  verifyIdToken,
  verifyRelayState,
} from "../src/tokens";

function secret(value: string): SecretsStoreSecret {
  return { get: async () => value };
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
    // Unused by tokens.ts — AuthEnv just requires the field.
    BOT_STATE: {} as KVNamespace,
  };
});

describe("relay state", () => {
  it("round-trips redirectUri and accessState", async () => {
    const token = await signRelayState(env, {
      redirectUri: "https://team.cloudflareaccess.com/cdn-cgi/access/callback",
      accessState: "xyz",
    });
    const relay = await verifyRelayState(env, token);
    expect(relay.redirectUri).toBe("https://team.cloudflareaccess.com/cdn-cgi/access/callback");
    expect(relay.accessState).toBe("xyz");
  });
});

describe("auth code", () => {
  it("round-trips claims", async () => {
    const token = await signAuthCode(env, {
      sub: "123",
      preferredUsername: "driver",
      picture: "https://cdn.discordapp.com/avatars/123/abc.png",
      email: "driver@example.com",
    });
    const claims = await verifyAuthCode(env, token);
    expect(claims).toEqual({
      sub: "123",
      preferredUsername: "driver",
      picture: "https://cdn.discordapp.com/avatars/123/abc.png",
      email: "driver@example.com",
    });
  });

  it("omits email when not present", async () => {
    const token = await signAuthCode(env, { sub: "123", preferredUsername: "driver", picture: null });
    const claims = await verifyAuthCode(env, token);
    expect(claims.email).toBeUndefined();
  });

  it("rejects a token signed for a different audience", async () => {
    const idToken = await signIdToken(env, { sub: "123", preferredUsername: "driver", picture: null });
    await expect(verifyAuthCode(env, idToken)).rejects.toThrow();
  });
});

describe("id token", () => {
  it("round-trips claims and is scoped to ACCESS_CLIENT_ID", async () => {
    const token = await signIdToken(env, {
      sub: "123",
      preferredUsername: "driver",
      picture: null,
    });
    const claims = await verifyIdToken(env, token);
    expect(claims.sub).toBe("123");
    expect(claims.preferredUsername).toBe("driver");
  });

  it("rejects an auth-code token", async () => {
    const authCode = await signAuthCode(env, { sub: "123", preferredUsername: "driver", picture: null });
    await expect(verifyIdToken(env, authCode)).rejects.toThrow();
  });
});

describe("getJwks", () => {
  it("exposes only public key fields", async () => {
    const jwks = await getJwks(env);
    expect(jwks.keys).toHaveLength(1);
    const key = jwks.keys[0];
    expect(key.kty).toBe("EC");
    expect(key.crv).toBe("P-256");
    expect(key.x).toBeTruthy();
    expect(key.y).toBeTruthy();
    expect(key.alg).toBe("ES256");
    expect(key.use).toBe("sig");
    expect(key).not.toHaveProperty("d");
  });
});
