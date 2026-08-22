/**
 * Reads a guild member's server nickname from `bot`'s KV roster snapshot
 * (`bot/src/discord/memberStore.ts`, key `members:v1`) — usually a much
 * closer match to an in-game driver name than the bare Discord handle.
 * Only as fresh as the last cron tick, up to ~1 minute.
 */

const MEMBERS_KEY = "members:v1";

interface StoredMembers {
  members: Array<{ id: string; displayName: string | null }>;
}

export async function memberNickname(kv: KVNamespace, discordId: string): Promise<string | null> {
  const stored = await kv.get<StoredMembers>(MEMBERS_KEY, "json");
  return stored?.members.find((member) => member.id === discordId)?.displayName ?? null;
}
