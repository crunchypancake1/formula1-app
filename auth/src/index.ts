import { Hono } from "hono";
import {
  discordAvatarUrl,
  exchangeDiscordCode,
  getDiscordUser,
  getGuildMember,
} from "./discord";
import type { AuthEnv } from "./env";
import {
  getJwks,
  signAuthCode,
  signIdToken,
  signRelayState,
  verifyAuthCode,
  verifyIdToken,
  verifyRelayState,
  type AuthClaims,
} from "./tokens";

const app = new Hono<{ Bindings: AuthEnv }>();

app.get("/auth/.well-known/openid-configuration", (c) => {
  const issuer = c.env.OIDC_ISSUER;
  return c.json({
    issuer,
    authorization_endpoint: `${issuer}/authorize`,
    token_endpoint: `${issuer}/token`,
    userinfo_endpoint: `${issuer}/userinfo`,
    jwks_uri: `${issuer}/jwks`,
    response_types_supported: ["code"],
    subject_types_supported: ["public"],
    id_token_signing_alg_values_supported: ["RS256"],
    scopes_supported: ["openid", "profile", "email"],
    token_endpoint_auth_methods_supported: ["client_secret_basic", "client_secret_post"],
    claims_supported: ["sub", "preferred_username", "picture", "email"],
  });
});

app.get("/auth/authorize", async (c) => {
  const clientId = c.req.query("client_id");
  const redirectUri = c.req.query("redirect_uri");
  const state = c.req.query("state") ?? "";

  if (clientId !== c.env.ACCESS_CLIENT_ID) {
    return c.text("invalid client_id", 400);
  }
  if (!redirectUri || !redirectUri.startsWith(`https://${c.env.ACCESS_TEAM_DOMAIN}/`)) {
    return c.text("invalid redirect_uri", 400);
  }

  const relayState = await signRelayState(c.env, { redirectUri, accessState: state });

  const discordUrl = new URL("https://discord.com/oauth2/authorize");
  discordUrl.searchParams.set("client_id", c.env.DISCORD_OAUTH_CLIENT_ID);
  discordUrl.searchParams.set("redirect_uri", `${c.env.OIDC_ISSUER}/callback`);
  discordUrl.searchParams.set("response_type", "code");
  discordUrl.searchParams.set("scope", "identify email");
  discordUrl.searchParams.set("state", relayState);

  return c.redirect(discordUrl.toString());
});

app.get("/auth/callback", async (c) => {
  const code = c.req.query("code");
  const state = c.req.query("state");
  if (!code || !state) return c.text("missing code or state", 400);

  let relay: Awaited<ReturnType<typeof verifyRelayState>>;
  try {
    relay = await verifyRelayState(c.env, state);
  } catch {
    return c.text("invalid or expired state", 400);
  }

  const clientSecret = await c.env.DISCORD_OAUTH_CLIENT_SECRET.get();
  const { access_token } = await exchangeDiscordCode(
    c.env.DISCORD_OAUTH_CLIENT_ID,
    clientSecret,
    code,
    `${c.env.OIDC_ISSUER}/callback`
  );

  const discordUser = await getDiscordUser(access_token);

  const botToken = await c.env.DISCORD_BOT_TOKEN.get();
  const member = await getGuildMember(botToken, c.env.DISCORD_GUILD_ID, discordUser.id);
  if (!member) {
    return c.text("You are not a member of the required Discord server.", 403);
  }

  const claims: AuthClaims = {
    sub: discordUser.id,
    preferredUsername: discordUser.username,
    picture: discordAvatarUrl(discordUser),
    ...(discordUser.email ? { email: discordUser.email } : {}),
  };
  const authCode = await signAuthCode(c.env, claims);

  const redirect = new URL(relay.redirectUri);
  redirect.searchParams.set("code", authCode);
  redirect.searchParams.set("state", relay.accessState);

  return c.redirect(redirect.toString());
});

function parseClientCredentials(
  authHeader: string | undefined,
  body: Record<string, unknown>
): { clientId?: string; clientSecret?: string } {
  if (authHeader?.startsWith("Basic ")) {
    const decoded = atob(authHeader.slice("Basic ".length));
    const sep = decoded.indexOf(":");
    if (sep === -1) return {};
    return { clientId: decoded.slice(0, sep), clientSecret: decoded.slice(sep + 1) };
  }
  return {
    clientId: typeof body.client_id === "string" ? body.client_id : undefined,
    clientSecret: typeof body.client_secret === "string" ? body.client_secret : undefined,
  };
}

app.post("/auth/token", async (c) => {
  const body = await c.req.parseBody();
  const { clientId, clientSecret } = parseClientCredentials(
    c.req.header("Authorization"),
    body as Record<string, unknown>
  );

  const expectedSecret = await c.env.ACCESS_CLIENT_SECRET.get();
  if (clientId !== c.env.ACCESS_CLIENT_ID || clientSecret !== expectedSecret) {
    return c.text("invalid client credentials", 401);
  }

  const code = body.code;
  if (typeof code !== "string") return c.text("missing code", 400);

  let claims: AuthClaims;
  try {
    claims = await verifyAuthCode(c.env, code);
  } catch {
    return c.text("invalid or expired code", 400);
  }

  const idToken = await signIdToken(c.env, claims);

  return c.json({
    access_token: idToken,
    id_token: idToken,
    token_type: "Bearer",
    expires_in: 300,
  });
});

app.get("/auth/userinfo", async (c) => {
  const authHeader = c.req.header("Authorization");
  if (!authHeader?.startsWith("Bearer ")) return c.text("missing bearer token", 401);
  const token = authHeader.slice("Bearer ".length);

  try {
    const claims = await verifyIdToken(c.env, token);
    return c.json({
      sub: claims.sub,
      preferred_username: claims.preferredUsername,
      picture: claims.picture,
      ...(claims.email !== undefined ? { email: claims.email } : {}),
    });
  } catch {
    return c.text("invalid or expired token", 401);
  }
});

app.get("/auth/jwks", async (c) => c.json(await getJwks(c.env)));

export default app;
