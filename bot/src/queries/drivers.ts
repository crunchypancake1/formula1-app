import type { Sql, UserRow } from "@f1/db";

/** Pure over its query function so it can be tested without a database. */
export async function readDriver(
  query: () => Promise<UserRow[]>
): Promise<UserRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

export async function readDrivers(
  query: () => Promise<UserRow[]>
): Promise<UserRow[]> {
  return query();
}

/** A row with no discord_id is a driver seen in telemetry but not linked to an account. */
export function isLinked(user: UserRow): boolean {
  return user.discord_id !== null;
}

export function driverByDiscordId(sql: Sql, discordId: string) {
  return readDriver(
    () => sql<UserRow[]>`
      SELECT *
        FROM identity.users
       WHERE discord_id = ${discordId}
    `
  );
}

/** Exact match, case-insensitive — mirrors the idx_users_driver_name_lower unique index. */
export function driverByName(sql: Sql, driverName: string) {
  return readDriver(
    () => sql<UserRow[]>`
      SELECT *
        FROM identity.users
       WHERE lower(driver_name) = lower(${driverName})
    `
  );
}

/** Fuzzy search over the gin_trgm_ops indexes on driver_name and discord_username. */
export function searchDrivers(sql: Sql, term: string, limit = 10) {
  return readDrivers(
    () => sql<UserRow[]>`
      SELECT *
        FROM identity.users
       WHERE driver_name % ${term}
          OR discord_username % ${term}
       ORDER BY similarity(driver_name, ${term}) DESC
       LIMIT ${limit}
    `
  );
}
