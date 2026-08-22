import { Hono } from "hono";
import { checkSchema, connect, schemaMarkerColumns } from "@f1/db";
import { readViewer } from "./access";
import { renderDashboard } from "./dashboard";
import type { WebEnv } from "./env";
import { renderPersonalView } from "./personalView";
import { buildFeed, fastestLapEvents, penaltyEvents, raceControlEvents, retirementEvents } from "./queries/feed";
import { roster } from "./queries/entries";
import { liveDrivers } from "./queries/live";
import { availableTyreSets, personalDamage, personalFrame } from "./queries/personal";
import { latestSession } from "./queries/sessions";
import { latestTimeline } from "./queries/timeline";
import { trackById } from "./queries/tracks";
import { resolveViewerDriver } from "./viewer";

const app = new Hono<{ Bindings: WebEnv }>();

/**
 * A session counts as "live" only while its timeline is still being written —
 * an old finished session must not linger on the dashboard looking active.
 * The listener samples session_timeline at packet rate (every frame), so a
 * gap this long only happens once the session has actually ended.
 */
const LIVE_THRESHOLD_MS = 60_000;

app.get("/", (c) => c.html(renderDashboard()));

app.get("/me", (c) => c.html(renderPersonalView()));

app.get("/api/live", async (c) => {
  const sql = connect(c.env);
  try {
    const session = await latestSession(sql);
    if (!session) return c.json({ live: false });

    const timeline = await latestTimeline(sql, session.session_uid);
    const live = timeline !== null && Date.now() - timeline.timestamp.getTime() <= LIVE_THRESHOLD_MS;
    if (!live) return c.json({ live: false });

    const viewer = await readViewer(c.env, c.req.raw);

    const [track, drivers, raceControl, penalties, retirements, fastestLaps, you] = await Promise.all([
      trackById(sql, session.track_id),
      liveDrivers(sql, session.session_uid),
      raceControlEvents(sql, session.session_uid),
      penaltyEvents(sql, session.session_uid),
      retirementEvents(sql, session.session_uid),
      fastestLapEvents(sql, session.session_uid),
      viewer ? resolveViewerDriver(sql, c.env.BOT_STATE, session.session_uid, viewer) : null,
    ]);

    const currentLap = drivers.reduce<number | null>((max, d) => {
      if (d.current_lap_num == null) return max;
      return max === null ? d.current_lap_num : Math.max(max, d.current_lap_num);
    }, null);

    return c.json({
      live: true,
      session,
      track,
      timeline,
      drivers,
      currentLap,
      feed: buildFeed(raceControl, penalties, retirements, fastestLaps),
      you,
    });
  } catch (e) {
    console.error(e);
    return c.json({ live: false, error: e instanceof Error ? e.message : String(e) }, 503);
  } finally {
    c.executionCtx.waitUntil(sql.end());
  }
});

app.get("/api/me", async (c) => {
  const viewer = await readViewer(c.env, c.req.raw);
  if (!viewer) return c.json({ live: false });

  const sql = connect(c.env);
  try {
    const session = await latestSession(sql);
    if (!session) return c.json({ live: false });

    const timeline = await latestTimeline(sql, session.session_uid);
    const live = timeline !== null && Date.now() - timeline.timestamp.getTime() <= LIVE_THRESHOLD_MS;
    if (!live) return c.json({ live: false });

    const resolved = await resolveViewerDriver(sql, c.env.BOT_STATE, session.session_uid, viewer);
    if (!resolved) return c.json({ live: true, frame: null });

    const [frame, sessionRoster] = await Promise.all([
      personalFrame(sql, session.session_uid, session.session_start_utc, resolved.userId),
      roster(sql, session.session_uid),
    ]);
    if (!frame) return c.json({ live: true, frame: null });

    const telemetryPublic = sessionRoster.find((r) => r.user_id === resolved.userId)?.telemetry_public ?? false;

    const [tyreSets, damage] = telemetryPublic
      ? await Promise.all([
          availableTyreSets(sql, session.session_uid, resolved.userId),
          personalDamage(sql, session.session_uid, session.session_start_utc, resolved.userId),
        ])
      : [[], null];

    return c.json({ live: true, session, timeline, frame, telemetryPublic, tyreSets, damage });
  } catch (e) {
    console.error(e);
    return c.json({ live: false, error: e instanceof Error ? e.message : String(e) }, 503);
  } finally {
    c.executionCtx.waitUntil(sql.end());
  }
});

app.get("/api/health", async (c) => {
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

export default app satisfies ExportedHandler<WebEnv>;
