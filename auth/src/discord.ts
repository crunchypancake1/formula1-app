/**
 * Plain `fetch` wrapper over the Discord REST/OAuth2 API, styled after
 * `bot/src/discord/client.ts`. No gateway connection.
 */

const API_BASE = "https://discord.com/api/v10";

export interface DiscordUser {
  id: string;
  username: string;
  avatar: string | null;
  email?: string;
  verified?: boolean;
}

interface DiscordTokenResponse {
  access_token: string;
}

interface DiscordGuildMember {
  user: { id: string };
}

class DiscordApiError extends Error {
  constructor(method: string, path: string, status: number, body: string) {
    super(`Discord API ${method} ${path} -> ${status}: ${body}`);
  }
}

export async function exchangeDiscordCode(
  clientId: string,
  clientSecret: string,
  code: string,
  redirectUri: string
): Promise<{ access_token: string }> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri,
    client_id: clientId,
    client_secret: clientSecret,
  });

  const res = await fetch(`${API_BASE}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!res.ok) {
    throw new DiscordApiError("POST", "/oauth2/token", res.status, await res.text());
  }

  return (await res.json()) as DiscordTokenResponse;
}

export async function getDiscordUser(accessToken: string): Promise<DiscordUser> {
  const res = await fetch(`${API_BASE}/users/@me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    throw new DiscordApiError("GET", "/users/@me", res.status, await res.text());
  }

  return (await res.json()) as DiscordUser;
}

/** 404 (not a member) is the only branch the callback route needs — returns `null`, not a thrown error. */
export async function getGuildMember(
  botToken: string,
  guildId: string,
  userId: string
): Promise<DiscordGuildMember | null> {
  const res = await fetch(`${API_BASE}/guilds/${guildId}/members/${userId}`, {
    headers: { Authorization: `Bot ${botToken}` },
  });

  if (res.status === 404) return null;

  if (!res.ok) {
    throw new DiscordApiError(
      "GET",
      `/guilds/${guildId}/members/${userId}`,
      res.status,
      await res.text()
    );
  }

  return (await res.json()) as DiscordGuildMember;
}

export function discordAvatarUrl(user: DiscordUser): string | null {
  if (!user.avatar) return null;
  const ext = user.avatar.startsWith("a_") ? "gif" : "png";
  return `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.${ext}`;
}
