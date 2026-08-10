import { Hono } from "hono";
import { connect, countTelemetryTables } from "./db";
import { checkHealth } from "./health";
import type { Env } from "./types";

const app = new Hono<{ Bindings: Env }>();

app.get("/api/health", async (c) => {
  const sql = connect(c.env);
  try {
    const result = await checkHealth(() => countTelemetryTables(sql));
    return c.json(result, result.ok ? 200 : 503);
  } catch (e) {
    console.error(e);
    return c.json({ ok: false, error: e instanceof Error ? e.message : String(e) }, 503);
  } finally {
    c.executionCtx.waitUntil(sql.end());
  }
});

export default app satisfies ExportedHandler<Env>;
