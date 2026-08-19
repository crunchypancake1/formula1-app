import { SignJWT, jwtVerify, importPKCS8, exportJWK, importJWK, type JWK } from "jose";
import type { AuthEnv } from "./env";

const ALG = "RS256";
const KID = "1";

export interface AuthClaims {
  sub: string;
  preferredUsername: string;
  picture: string | null;
  email?: string;
}

interface RelayState {
  redirectUri: string;
  accessState: string;
}

interface Keys {
  privateKey: CryptoKey;
  publicJwk: JWK;
  verifyKey: CryptoKey;
}

/** Module-level memoized key derivation — one PKCS8 import + JWK export per isolate, not per request. */
let cachedKeys: Promise<Keys> | null = null;

async function getKeys(env: AuthEnv): Promise<Keys> {
  if (!cachedKeys) {
    cachedKeys = (async () => {
      const pem = await env.OIDC_SIGNING_KEY.get();
      // extractable: true — exportJWK() below needs to pull the public components back out.
      const privateKey = await importPKCS8(pem, ALG, { extractable: true });
      const fullJwk = await exportJWK(privateKey);
      // Explicit allowlist, not spread-and-delete: an RSA JWK exported from a private
      // CryptoKey carries d/p/q/dp/dq/qi, and those must never reach getJwks()'s output.
      const publicJwk: JWK = {
        kty: fullJwk.kty,
        n: fullJwk.n,
        e: fullJwk.e,
        alg: ALG,
        use: "sig",
        kid: KID,
      };
      const verifyKey = await importJWK(publicJwk, ALG);
      return { privateKey: privateKey as CryptoKey, publicJwk, verifyKey: verifyKey as CryptoKey };
    })();
  }
  return cachedKeys;
}

export async function getJwks(env: AuthEnv): Promise<{ keys: JWK[] }> {
  const { publicJwk } = await getKeys(env);
  return { keys: [publicJwk] };
}

export async function signRelayState(env: AuthEnv, relay: RelayState): Promise<string> {
  const { privateKey } = await getKeys(env);
  return new SignJWT({ ru: relay.redirectUri, rs: relay.accessState })
    .setProtectedHeader({ alg: ALG, kid: KID })
    .setIssuedAt()
    .setAudience("relay")
    .setExpirationTime("10m")
    .sign(privateKey);
}

export async function verifyRelayState(env: AuthEnv, token: string): Promise<RelayState> {
  const { verifyKey } = await getKeys(env);
  const { payload } = await jwtVerify(token, verifyKey, { audience: "relay" });
  return { redirectUri: payload.ru as string, accessState: payload.rs as string };
}

function claimsToPayload(claims: AuthClaims): Record<string, unknown> {
  return {
    sub: claims.sub,
    preferred_username: claims.preferredUsername,
    picture: claims.picture,
    ...(claims.email !== undefined ? { email: claims.email } : {}),
  };
}

function payloadToClaims(payload: Record<string, unknown>): AuthClaims {
  return {
    sub: payload.sub as string,
    preferredUsername: payload.preferred_username as string,
    picture: (payload.picture as string | null) ?? null,
    ...(payload.email !== undefined ? { email: payload.email as string } : {}),
  };
}

export async function signAuthCode(env: AuthEnv, claims: AuthClaims): Promise<string> {
  const { privateKey } = await getKeys(env);
  return new SignJWT(claimsToPayload(claims))
    .setProtectedHeader({ alg: ALG, kid: KID })
    .setIssuedAt()
    .setAudience("auth-code")
    .setExpirationTime("60s")
    .sign(privateKey);
}

export async function verifyAuthCode(env: AuthEnv, token: string): Promise<AuthClaims> {
  const { verifyKey } = await getKeys(env);
  const { payload } = await jwtVerify(token, verifyKey, { audience: "auth-code" });
  return payloadToClaims(payload);
}

export async function signIdToken(env: AuthEnv, claims: AuthClaims): Promise<string> {
  const { privateKey } = await getKeys(env);
  return new SignJWT(claimsToPayload(claims))
    .setProtectedHeader({ alg: ALG, kid: KID })
    .setIssuedAt()
    .setIssuer(env.OIDC_ISSUER)
    .setAudience(env.ACCESS_CLIENT_ID)
    .setExpirationTime("5m")
    .sign(privateKey);
}

export async function verifyIdToken(env: AuthEnv, token: string): Promise<AuthClaims> {
  const { verifyKey } = await getKeys(env);
  const { payload } = await jwtVerify(token, verifyKey, { audience: env.ACCESS_CLIENT_ID });
  return payloadToClaims(payload);
}
