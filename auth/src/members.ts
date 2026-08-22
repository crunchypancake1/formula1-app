/**
 * Reads guild membership from the KV snapshot `bot`'s cron tick already
 * maintains (`bot/src/discord/memberStore.ts`) instead of calling Discord
 * with a bot token here too — one fewer privileged credential for a
 * public-facing gate to hold. The tradeoff is freshness: this is only as
 * current as the last cron tick (up to ~1 minute), not live.
 */

const MEMBERS_KEY = "members:v1";

interface StoredMembers {
  members: Array<{ id: string }>;
}

/** Missing/unreadable KV data fails closed — an access gate defaults to "not a member". */
export async function isGuildMember(kv: KVNamespace, userId: string): Promise<boolean> {
  const stored = await kv.get<StoredMembers>(MEMBERS_KEY, "json");
  return stored?.members.some((member) => member.id === userId) ?? false;
}
