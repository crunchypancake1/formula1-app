import { Hono } from "hono";
import { connect, latestSessionUid } from "./db";
import type { Env } from "./types";

const app = new Hono<{ Bindings: Env }>();

app.get("/health", async (c) => {
  const sql = connect(c.env);
  try {
    const latestSession = await latestSessionUid(sql);
    return c.json({ ok: true, latestSession });
  } catch (e) {
    console.error(e);
    return c.json({ ok: false, error: e instanceof Error ? e.message : String(e) }, 503);
  } finally {
    c.executionCtx.waitUntil(sql.end());
  }
});

export default app satisfies ExportedHandler<Env>;
