import { Hono } from "hono";
import { checkSchema, connect, schemaMarkerColumns, type Env } from "@f1/db";
import { latestSession } from "./queries/sessions";

const app = new Hono<{ Bindings: Env }>();

app.get("/", (c) =>
  c.html(`<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>F1 Live Dashboard</title>
<style>
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; display: grid; place-items: center; min-height: 100vh; margin: 0; }
  main { text-align: center; }
  code { background: #222; padding: 0.15em 0.4em; border-radius: 4px; }
  a { color: #e10600; }
</style>
</head>
<body>
<main>
  <h1>F1 Live Dashboard</h1>
  <p id="status">Checking backend&hellip;</p>
  <p>The live session view is under construction. API health: <a href="/api/health"><code>/api/health</code></a></p>
</main>
<script>
  fetch("/api/health").then(r => r.json()).then(h => {
    document.getElementById("status").textContent = h.ok
      ? (h.latestSession ? "Backend online — latest session " + h.latestSession : "Backend online — no sessions recorded yet")
      : "Backend unavailable";
  }).catch(() => { document.getElementById("status").textContent = "Backend unavailable"; });
</script>
</body>
</html>`)
);

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

export default app satisfies ExportedHandler<Env>;
