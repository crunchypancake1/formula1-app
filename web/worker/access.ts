import { createRemoteJWKSet, jwtVerify } from "jose";
import type { WebEnv } from "./env";

export interface Viewer {
  discordId: string;
  username: string;
}

/** Module-level so the JWKS is fetched once per isolate, not per request. */
let jwks: ReturnType<typeof createRemoteJWKSet> | null = null;

/**
 * Reads the signed-in viewer from Cloudflare Access's JWT assertion header.
 * Never throws — a viewer we cannot identify just gets the public dashboard.
 */
export async function readViewer(env: WebEnv, request: Request): Promise<Viewer | null> {
  const token = request.headers.get("cf-access-jwt-assertion");
  if (!token || !env.ACCESS_POLICY_AUD) return null;

  jwks ??= createRemoteJWKSet(new URL(`${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`));

  try {
    const { payload } = await jwtVerify(token, jwks, {
      issuer: env.ACCESS_TEAM_DOMAIN,
      audience: env.ACCESS_POLICY_AUD,
    });
    const custom = payload.custom as Record<string, unknown> | undefined;
    const discordId = typeof custom?.discord_id === "string" ? custom.discord_id : null;
    if (!discordId) return null;
    return {
      discordId,
      username: typeof custom?.preferred_username === "string" ? custom.preferred_username : "",
    };
  } catch {
    return null;
  }
}
