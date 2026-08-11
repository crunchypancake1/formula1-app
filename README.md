# formula1-app

F1 25 UDP telemetry capture, a live session dashboard, and a Discord bot.

| Component | Runs on | Path |
|---|---|---|
| Listener | Local Docker | `listener/` |
| Database | Local Docker (TimescaleDB) | `schema/` |
| Live dashboard | Cloudflare Workers | `web/` |
| Discord bot | Cloudflare Workers | `bot/` |

The listener captures UDP telemetry to a local PostgreSQL/TimescaleDB
instance. Both Workers read that database through Hyperdrive over a
Cloudflare Tunnel. Setup instructions follow once the Workers exist.

Edit for testing
