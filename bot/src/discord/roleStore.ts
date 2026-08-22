import { createRole, listRoles } from "./client";
import { TEAM_ROLES } from "./teamRoles";

/** `role_key` (see `TEAM_ROLES`) → the guild role id backing it. */
export type TeamRoleMap = Record<string, string>;

/**
 * Creates the guild role for any F1 team (or Reserve) that doesn't have one,
 * returning the full `role_key → role_id` map so later features can assign
 * members by season lineup.
 *
 * No cache: roles change only when someone edits the guild by hand, and
 * `listRoles` is one cheap GET, so there's nothing worth persisting between
 * calls. The caller (the hourly cron branch in `index.ts`, not the per-minute
 * tick) is what keeps this off the hot path, not caching here.
 *
 * Discord is still the source of truth — this only adopts an existing role by
 * name (picking up one an owner created by hand instead of duplicating it)
 * before creating one.
 */
export async function ensureTeamRoles(token: string, guildId: string): Promise<TeamRoleMap> {
  if (!guildId) {
    throw new Error("DISCORD_GUILD_ID is unset — refusing to call Discord with an empty guild id");
  }

  const guildRoles = await listRoles(token, guildId);
  const byName = new Map(guildRoles.map((role) => [role.name, role]));

  const roles: TeamRoleMap = {};
  for (const role of TEAM_ROLES) {
    const guildRole = byName.get(role.name) ?? (await createRole(token, guildId, role.name, role.color));
    roles[role.key] = guildRole.id;
  }

  return roles;
}
