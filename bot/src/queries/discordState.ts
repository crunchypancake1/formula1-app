import type { DiscordSessionMessageRow, DiscordWeekendRow, Sql } from "@f1/db";

/** Pure over its query function so it can be tested without a database. */
export async function readActiveWeekend(
  query: () => Promise<DiscordWeekendRow[]>
): Promise<DiscordWeekendRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

export async function readSessionMessage(
  query: () => Promise<DiscordSessionMessageRow[]>
): Promise<DiscordSessionMessageRow | null> {
  const rows = await query();
  return rows.length > 0 ? rows[0] : null;
}

export async function readPendingSessionMessages(
  query: () => Promise<DiscordSessionMessageRow[]>
): Promise<DiscordSessionMessageRow[]> {
  return query();
}

/**
 * The current not-yet-archived weekend, if any. There is at most one — the
 * scheduled handler archives the previous row before inserting the next.
 */
export function activeWeekend(sql: Sql) {
  return readActiveWeekend(
    () => sql<DiscordWeekendRow[]>`
      SELECT *
        FROM bot.discord_weekends
       WHERE NOT archived
       LIMIT 1
    `
  );
}

export function insertWeekend(sql: Sql, weekendLink: string, channelId: string) {
  return sql`
    INSERT INTO bot.discord_weekends (weekend_link, channel_id)
    VALUES (${weekendLink}, ${channelId})
  `;
}

export function archiveWeekend(sql: Sql, weekendLink: string) {
  return sql`
    UPDATE bot.discord_weekends
       SET archived = TRUE
     WHERE weekend_link = ${weekendLink}
  `;
}

export function sessionMessage(sql: Sql, sessionUid: string) {
  return readSessionMessage(
    () => sql<DiscordSessionMessageRow[]>`
      SELECT *
        FROM bot.discord_session_messages
       WHERE session_uid = ${sessionUid}
    `
  );
}

/** Cards still eligible for a finalize check — every unfinalized message tracked so far. */
export function pendingSessionMessages(sql: Sql) {
  return readPendingSessionMessages(
    () => sql<DiscordSessionMessageRow[]>`
      SELECT *
        FROM bot.discord_session_messages
       WHERE NOT finalized
    `
  );
}

export function insertSessionMessage(
  sql: Sql,
  sessionUid: string,
  channelId: string,
  messageId: string
) {
  return sql`
    INSERT INTO bot.discord_session_messages (session_uid, channel_id, message_id)
    VALUES (${sessionUid}, ${channelId}, ${messageId})
  `;
}

export function finalizeSessionMessage(sql: Sql, sessionUid: string) {
  return sql`
    UPDATE bot.discord_session_messages
       SET finalized = TRUE
     WHERE session_uid = ${sessionUid}
  `;
}
