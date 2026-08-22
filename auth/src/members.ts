/**
 * Reads guild membership from `bot`'s KV roster snapshot
 * (`bot/src/discord/memberStore.ts`, key `members:v1`). Only as fresh as
 * the last cron tick — up to ~1 minute.
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
