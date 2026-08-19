/**
 * Plain `fetch` wrapper over the Discord REST API — no gateway connection.
 * The scheduled handler only ever creates channels, posts messages, edits
 * messages, and renames/moves channels for archiving, all of which are
 * outbound REST calls (confirmed against `/discord/discord-api-docs`).
 */

const API_BASE = "https://discord.com/api/v10";

const GUILD_TEXT_CHANNEL_TYPE = 0;

export interface DiscordChannel {
  id: string;
  name: string;
}

export interface DiscordMessage {
  id: string;
  channel_id: string;
}

class DiscordApiError extends Error {
  constructor(method: string, path: string, status: number, body: string) {
    super(`Discord API ${method} ${path} -> ${status}: ${body}`);
  }
}

async function discordFetch<T>(
  token: string,
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      Authorization: `Bot ${token}`,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!res.ok) {
    throw new DiscordApiError(method, path, res.status, await res.text());
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export function createChannel(
  token: string,
  guildId: string,
  name: string,
  parentId?: string
): Promise<DiscordChannel> {
  return discordFetch<DiscordChannel>(token, "POST", `/guilds/${guildId}/channels`, {
    name,
    type: GUILD_TEXT_CHANNEL_TYPE,
    parent_id: parentId ?? null,
  });
}

/** Rename and/or move a channel — used to turn `active-session` into an archive entry. */
export function editChannel(
  token: string,
  channelId: string,
  changes: { name?: string; parent_id?: string }
): Promise<DiscordChannel> {
  return discordFetch<DiscordChannel>(token, "PATCH", `/channels/${channelId}`, changes);
}

export function postMessage(
  token: string,
  channelId: string,
  content: string
): Promise<DiscordMessage> {
  return discordFetch<DiscordMessage>(token, "POST", `/channels/${channelId}/messages`, {
    content,
  });
}

export function editMessage(
  token: string,
  channelId: string,
  messageId: string,
  content: string
): Promise<DiscordMessage> {
  return discordFetch<DiscordMessage>(
    token,
    "PATCH",
    `/channels/${channelId}/messages/${messageId}`,
    { content }
  );
}
