import { Hono } from "hono";
import { checkSchema, connect, schemaMarkerColumns, type SessionRow, type Sql } from "@f1/db";
import { editChannel, createChannel, editMessage, postMessage } from "./discord/client";
import { finalCardFor, placeholderCard } from "./discord/cards";
import { COMMANDS, COMPONENTS, ensureCommands } from "./discord/commands";
import { dispatchEvent, type WebhookEvent } from "./discord/events";
import { dispatchInteraction, type Interaction } from "./discord/interactions";
import { ensureTeamRoles } from "./discord/roleStore";
import { verifyRequestHeaders } from "./discord/verify";
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
import { sessionBests } from "./queries/laps";
import { qualifyingClassification, raceClassification } from "./queries/results";
import { latestSession, latestSessionInWeekend, sessionByUid } from "./queries/sessions";
import { latestTimeline } from "./queries/timeline";
import { trackById } from "./queries/tracks";

const app = new Hono<{ Bindings: BotEnv }>();

/** Path-scoped Workers Routes don't strip the prefix, so every path starts with `/bot`. */
app.get("/bot", (c) =>
  c.json({ service: "formula1-bot", status: "ok", health: "/bot/health" })
);

/** Both must 401 an unsigned request — the portal probes that before saving the URL. */
app.post("/bot/interactions", async (c) => {
  const raw = await c.req.text();
  if (!(await verifyRequestHeaders(c.env.DISCORD_PUBLIC_KEY, c.req.raw.headers, raw))) {
    return c.text("invalid request signature", 401);
  }

  const interaction = JSON.parse(raw) as Interaction;
  const response = await dispatchInteraction(
    interaction,
    c.env,
    (promise) => c.executionCtx.waitUntil(promise),
    { commands: COMMANDS, components: COMPONENTS }
  );
  return c.json(response);
});

app.post("/bot/events", async (c) => {
  const raw = await c.req.text();
  if (!(await verifyRequestHeaders(c.env.DISCORD_PUBLIC_KEY, c.req.raw.headers, raw))) {
    return c.text("invalid request signature", 401);
  }

  // 204 for the PING and every real event alike; a JSON body makes Discord retry.
  c.executionCtx.waitUntil(dispatchEvent(JSON.parse(raw) as WebhookEvent, c.env));
  return c.body(null, 204);
});

app.get("/bot/health", async (c) => {
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
 * Runs one independent piece of a tick, logging its failure instead of
 * propagating. The pieces don't depend on each other, and a single try/catch
 * around the whole tick meant the first one to throw silently cancelled the
 * rest — a missing table in the role step took session cards down with it.
 */
async function step(name: string, run: () => Promise<void>): Promise<void> {
  try {
    await run();
  } catch (e) {
    console.error(`tick step "${name}" failed:`, e);
  }
}

async function tick(env: BotEnv): Promise<void> {
  let token: string;
  try {
    token = await env.DISCORD_BOT_TOKEN.get();
  } catch (e) {
    // Without a token every step below is a guaranteed 401, so this one
    // failure really does end the tick.
    console.error("tick could not read DISCORD_BOT_TOKEN:", e);
    return;
  }

  await step("teamRoles", async () => {
    await ensureTeamRoles(env.BOT_STATE, token, env.DISCORD_GUILD_ID);
  });

  await step("commands", async () => {
    await ensureCommands(env.BOT_STATE, token, env.DISCORD_GUILD_ID);
  });

  const sql = connect(env);
  try {
    await step("sessionCard", async () => {
      const session = await latestSession(sql);
      if (!session) return;

      const channelId = await ensureWeekendChannel(sql, env, token, session);
      await ensurePlaceholderCard(sql, token, session, channelId);
    });

    await step("finalizeCards", () => finalizePendingCards(sql, token));
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
