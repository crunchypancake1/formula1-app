import { createRole, listRoles } from "./client";
import { TEAM_ROLES } from "./teamRoles";

/** `role_key` (see `TEAM_ROLES`) → the guild role id backing it. */
export type TeamRoleMap = Record<string, string>;

interface CachedRoles {
  roles: TeamRoleMap;
  /** Epoch ms of the last reconciliation against the live guild role list. */
  verifiedAt: number;
}

/**
 * One KV key for the whole map rather than a key per role: twelve role ids are
 * a few hundred bytes, and a single key means one read per cold isolate
 * instead of twelve. The `:v1` suffix makes a future shape change a new key
 * rather than a parse guard against whatever the old one held.
 */
const CACHE_KEY = "team-roles:v1";

/**
 * How long a complete map is trusted before it is reconciled against Discord
 * again. Roles only change when somebody edits the guild by hand, so an hourly
 * check heals a deleted role while leaving 59 of every 60 cron ticks with no
 * Discord API call at all.
 */
const REVALIDATE_MS = 60 * 60 * 1000;

/**
 * Per-isolate front cache for the KV value. A Worker isolate serves many cron
 * ticks, so this absorbs most of the KV reads; it is only ever a copy of what
 * KV holds, so losing it on isolate recycle costs one read, never a Discord
 * round trip.
 */
let memo: CachedRoles | null = null;

/** Test seam — vitest reuses a single isolate across cases. */
export function resetTeamRoleCache(): void {
  memo = null;
}

function isComplete(roles: TeamRoleMap): boolean {
  return TEAM_ROLES.every((role) => typeof roles[role.key] === "string");
}

/**
 * Anything written by an older version of this Worker, or edited by hand in
 * the dashboard, has to be treated as untrusted input — a bad value degrades
 * to "nothing cached" and the next tick rebuilds it from the guild.
 */
async function readCache(kv: KVNamespace): Promise<CachedRoles | null> {
  const cached = await kv.get<Partial<CachedRoles>>(CACHE_KEY, "json");
  if (!cached || typeof cached.verifiedAt !== "number" || typeof cached.roles !== "object") {
    return null;
  }
  return { roles: cached.roles as TeamRoleMap, verifiedAt: cached.verifiedAt };
}

/**
 * Creates the guild role for any F1 team (or Reserve) that doesn't have one,
 * returning the full `role_key → role_id` map so later features can assign
 * members by season lineup without another Discord API call.
 *
 * The map lives in KV, not Postgres: it is twelve ids that change roughly
 * never, no query joins against it, and the database is behind Hyperdrive and
 * a tunnel — a KV read is both cheaper and one less thing that can take the
 * whole tick down.
 *
 * Discord is still the source of truth. The cache is only ever an index into
 * it, and reconciliation prefers the cached id, falls back to matching a role
 * by name (adopting one an owner created by hand instead of duplicating it),
 * and only then creates.
 */
export async function ensureTeamRoles(
  kv: KVNamespace,
  token: string,
  guildId: string,
  now: number = Date.now()
): Promise<TeamRoleMap> {
  if (!guildId) {
    throw new Error("DISCORD_GUILD_ID is unset — refusing to call Discord with an empty guild id");
  }

  const cached = memo ?? (await readCache(kv));
  if (cached && isComplete(cached.roles) && now - cached.verifiedAt < REVALIDATE_MS) {
    memo = cached;
    return cached.roles;
  }

  const guildRoles = await listRoles(token, guildId);
  const byId = new Map(guildRoles.map((role) => [role.id, role]));
  const byName = new Map(guildRoles.map((role) => [role.name, role]));

  const roles: TeamRoleMap = {};
  for (const role of TEAM_ROLES) {
    const cachedId = cached?.roles[role.key];
    const guildRole =
      (cachedId === undefined ? undefined : byId.get(cachedId)) ??
      byName.get(role.name) ??
      (await createRole(token, guildId, role.name, role.color));
    roles[role.key] = guildRole.id;
  }

  const fresh: CachedRoles = { roles, verifiedAt: now };
  await kv.put(CACHE_KEY, JSON.stringify(fresh));
  memo = fresh;
  return roles;
}
