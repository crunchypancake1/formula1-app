import type { RosterEntry, Sql } from "@f1/db";

/** Pure over its query function so it can be tested without a database. */
export async function readRoster(
  query: () => Promise<RosterEntry[]>
): Promise<RosterEntry[]> {
  return query();
}

export function roster(sql: Sql, sessionUid: string) {
  return readRoster(
    () => sql<RosterEntry[]>`
      SELECT e.*,
             u.driver_name,
             u.discord_id,
             t.name         AS team_name,
             t.display_name AS team_display_name
        FROM telemetry.entries e
        JOIN identity.users u  ON u.id = e.user_id
        JOIN telemetry.teams t ON t.team_id = e.team_id
       WHERE e.session_uid = ${sessionUid}
       ORDER BY e.car_index
    `
  );
}
