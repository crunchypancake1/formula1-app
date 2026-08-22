import { listMembers, type DiscordMember } from "./client";

export interface StoredMember {
  id: string;
  username: string;
  displayName: string | null;
  avatar: string | null;
  roles: string[];
  joinedAt: string;
}

const MEMBERS_KEY = "members:v1";

function toStored(member: DiscordMember): StoredMember {
  return {
    id: member.user.id,
    username: member.user.username,
    displayName: member.nick ?? member.user.global_name,
    avatar: member.user.avatar,
    roles: member.roles,
    joinedAt: member.joined_at,
  };
}

async function fingerprint(members: StoredMember[]): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(members)));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Snapshots the full guild roster into KV, skipping the write when nothing
 * changed since the last tick — same fingerprint-diff shape as
 * `commands.ts`'s `ensureCommands`, so a quiet server costs one Discord GET
 * and no KV write.
 */
export async function syncMembers(
  kv: KVNamespace,
  token: string,
  guildId: string
): Promise<StoredMember[]> {
  if (!guildId) {
    throw new Error("DISCORD_GUILD_ID is unset — refusing to call Discord with an empty guild id");
  }

  const members = (await listMembers(token, guildId)).map(toStored);
  const current = await fingerprint(members);
  const stored = await kv.get<{ fingerprint: string }>(MEMBERS_KEY, "json");

  if (stored?.fingerprint !== current) {
    await kv.put(MEMBERS_KEY, JSON.stringify({ fingerprint: current, members }));
  }

  return members;
}
