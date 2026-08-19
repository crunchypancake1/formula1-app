import type { Sql } from "../db";
import type { RosterEntry } from "../schema";

/** Pure over its query function so it can be tested without a database. */
export async function readRoster(
  query: () => Promise<RosterEntry[]>
): Promise<RosterEntry[]> {
  return query();
}

/**
 * Drivers whose telemetry is set to Restricted. The game zeroes their fuel, ERS
 * and damage in everyone else's stream, so the listener stores NULL for those
 * columns; callers need this set to distinguish "withheld" from a real value.
 */
export function restrictedDrivers(roster: RosterEntry[]): RosterEntry[] {
  return roster.filter((entry) => !entry.telemetry_public);
}

/** Roster indexed by car_index, which is what packet payloads are keyed on. */
export function byCarIndex(roster: RosterEntry[]): Map<number, RosterEntry> {
  return new Map(roster.map((entry) => [entry.car_index, entry]));
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
