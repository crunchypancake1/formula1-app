import { Hono } from "hono";
import { checkSchema, connect, schemaMarkerColumns, type SessionRow, type Sql } from "@f1/db";
import { editChannel, createChannel, createRole, editMessage, listRoles, postMessage } from "./discord/client";
import { finalCardFor, placeholderCard } from "./discord/cards";
import { TEAM_ROLES } from "./discord/teamRoles";
import type { BotEnv } from "./env";
import {
  activeWeekend,
  archiveWeekend,
  finalizeSessionMessage,
  insertSessionMessage,
  insertWeekend,
  pendingSessionMessages,
  sessionMessage,
} from "./queries/discordState";
import { teamRoles, upsertTeamRole } from "./queries/discordRoles";
import { sessionBests } from "./queries/laps";
import { qualifyingClassification, raceClassification } from "./queries/results";
import { latestSession, latestSessionInWeekend, sessionByUid } from "./queries/sessions";
import { latestTimeline } from "./queries/timeline";
import { trackById } from "./queries/tracks";

const app = new Hono<{ Bindings: BotEnv }>();

app.get("/", (c) =>
  c.json({ service: "formula1-bot", status: "ok", health: "/health" })
);

app.get("/health", async (c) => {
  const sql = connect(c.env);
  try {
    const schema = await checkSchema(() => schemaMarkerColumns(sql));
    const session = schema.ok ? await latestSession(sql) : null;

    return c.json(
      {
        ok: schema.ok,
        missing: schema.missing,
        latencyMs: schema.latencyMs,
        latestSession: session?.session_uid ?? null,
      },
      schema.ok ? 200 : 503
    );
  } catch (e) {
    console.error(e);
    return c.json({ ok: false, error: e instanceof Error ? e.message : String(e) }, 503);
  } finally {
    c.executionCtx.waitUntil(sql.end());
  }
});

/**
 * A session's timeline going quiet this long means it has actually ended —
 * matches `web/worker/index.ts`'s LIVE_THRESHOLD_MS, which uses the same
 * "session_timeline is sampled at packet rate" assumption.
 */
const STALE_THRESHOLD_MS = 60_000;

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

/**
 * Renames the outgoing weekend's channel into an archive entry (optionally
 * moving it under an archive category) rather than deleting it — every
 * session card already posted there stays reachable.
 */
async function archivePreviousWeekend(
  sql: Sql,
  env: BotEnv,
  token: string,
  weekend: { weekend_link: string; channel_id: string }
): Promise<void> {
  const lastSession = await latestSessionInWeekend(sql, weekend.weekend_link);
  const track = lastSession ? await trackById(sql, lastSession.track_id) : null;
  const dateStr = lastSession
    ? lastSession.session_start_utc.toISOString().slice(0, 10)
    : "unknown";
  const name = `archive-${track ? slugify(track.name) : "weekend"}-${dateStr}`.slice(0, 100);

  await editChannel(token, weekend.channel_id, { name, parent_id: env.DISCORD_ARCHIVE_CATEGORY_ID });
  await archiveWeekend(sql, weekend.weekend_link);
}

/** Ensures the latest session's weekend has a live `active-session` channel, archiving the last one if it changed. */
async function ensureWeekendChannel(
  sql: Sql,
  env: BotEnv,
  token: string,
  session: SessionRow
): Promise<string> {
  const active = await activeWeekend(sql);
  if (active && active.weekend_link === session.weekend_link) {
    return active.channel_id;
  }

  if (active) {
    await archivePreviousWeekend(sql, env, token, active);
  }

  const channel = await createChannel(
    token,
    env.DISCORD_GUILD_ID,
    env.DISCORD_CHANNEL_NAME || "active-session"
  );
  await insertWeekend(sql, session.weekend_link, channel.id);
  return channel.id;
}

/**
 * Posts the session's placeholder card the first time it is seen. Non-race
 * sessions get a Discord-native countdown seeded from `session_time_left` at
 * post time; races never do, since they are not time-bounded the same way.
 */
async function ensurePlaceholderCard(
  sql: Sql,
  token: string,
  session: SessionRow,
  channelId: string
): Promise<void> {
  const existing = await sessionMessage(sql, session.session_uid);
  if (existing) return;

  const track = await trackById(sql, session.track_id);
  const isRace = session.session_type.includes("RACE");
  const timeline = isRace ? null : await latestTimeline(sql, session.session_uid);
  const countdownUnix = timeline
    ? Math.round(Date.now() / 1000 + timeline.session_time_left)
    : null;

  const content = placeholderCard(session, track, countdownUnix);
  const message = await postMessage(token, channelId, content);
  await insertSessionMessage(sql, session.session_uid, channelId, message.id);
}

/** A tracked session is done once a newer one in the same weekend exists, or its timeline stalls. */
async function isSessionDone(sql: Sql, session: SessionRow): Promise<boolean> {
  const latest = await latestSession(sql);
  if (
    latest &&
    latest.session_uid !== session.session_uid &&
    latest.weekend_link === session.weekend_link
  ) {
    return true;
  }

  const timeline = await latestTimeline(sql, session.session_uid);
  if (!timeline) return false;
  return Date.now() - timeline.timestamp.getTime() > STALE_THRESHOLD_MS;
}

async function finalResultData(sql: Sql, session: SessionRow) {
  if (session.session_type.includes("RACE")) {
    return { race: await raceClassification(sql, session.session_uid) };
  }
  if (session.session_type.includes("QUALIFYING") || session.session_type.includes("SHOOTOUT")) {
    return { qualifying: await qualifyingClassification(sql, session.session_uid) };
  }
  return { bests: await sessionBests(sql, session.session_uid) };
}

/** Finalizes every tracked-but-unfinalized card whose session has actually ended. */
async function finalizePendingCards(sql: Sql, token: string): Promise<void> {
  const pending = await pendingSessionMessages(sql);
  for (const row of pending) {
    const session = await sessionByUid(sql, row.session_uid);
    if (!session || !(await isSessionDone(sql, session))) continue;

    const track = await trackById(sql, session.track_id);
    const data = await finalResultData(sql, session);
    const content = finalCardFor(session, track, data);
    await editMessage(token, row.channel_id, row.message_id, content);
    await finalizeSessionMessage(sql, session.session_uid);
  }
}

/**
 * Creates the guild role for any F1 team (or Reserve) that doesn't have one
 * yet, recording each in `bot.discord_team_roles` so future features can look
 * up a team's role_id without another Discord API call. Skips the guild-roles
 * fetch entirely once every role is already tracked — this runs on every tick
 * but the roles almost never change after initial setup.
 */
async function ensureTeamRoles(sql: Sql, env: BotEnv, token: string): Promise<void> {
  const tracked = new Set((await teamRoles(sql)).map((row) => row.role_key));
  const missing = TEAM_ROLES.filter((role) => !tracked.has(role.key));
  if (missing.length === 0) return;

  const guildRoles = await listRoles(token, env.DISCORD_GUILD_ID);
  const byName = new Map(guildRoles.map((role) => [role.name, role]));

  for (const role of missing) {
    const existing = byName.get(role.name);
    const guildRole = existing ?? (await createRole(token, env.DISCORD_GUILD_ID, role.name, role.color));
    await upsertTeamRole(sql, role.key, guildRole.id, role.name, role.color);
  }
}

async function tick(env: BotEnv): Promise<void> {
  const sql = connect(env);
  try {
    const token = await env.DISCORD_BOT_TOKEN.get();
    await ensureTeamRoles(sql, env, token);

    const session = await latestSession(sql);

    if (session) {
      const channelId = await ensureWeekendChannel(sql, env, token, session);
      await ensurePlaceholderCard(sql, token, session, channelId);
    }

    await finalizePendingCards(sql, token);
  } catch (e) {
    console.error(e);
  } finally {
    await sql.end();
  }
}

export default {
  fetch: app.fetch,
  scheduled(_event, env, ctx) {
    ctx.waitUntil(tick(env));
  },
} satisfies ExportedHandler<BotEnv>;
