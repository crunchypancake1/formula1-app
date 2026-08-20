import type { DiscordTeamRoleRow, Sql } from "@f1/db";

/** Pure over its query function so it can be tested without a database. */
export async function readTeamRoles(
  query: () => Promise<DiscordTeamRoleRow[]>
): Promise<DiscordTeamRoleRow[]> {
  return query();
}

export function teamRoles(sql: Sql) {
  return readTeamRoles(
    () => sql<DiscordTeamRoleRow[]>`
      SELECT *
        FROM bot.discord_team_roles
    `
  );
}

export function upsertTeamRole(
  sql: Sql,
  roleKey: string,
  roleId: string,
  roleName: string,
  color: number
) {
  return sql`
    INSERT INTO bot.discord_team_roles (role_key, role_id, role_name, color)
    VALUES (${roleKey}, ${roleId}, ${roleName}, ${color})
    ON CONFLICT (role_key) DO UPDATE SET
      role_id   = EXCLUDED.role_id,
      role_name = EXCLUDED.role_name,
      color     = EXCLUDED.color
  `;
}
