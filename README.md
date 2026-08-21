# formula1-app

Live telemetry pipeline for EA SPORTS F1 26: a Python listener captures the
game's UDP telemetry stream into TimescaleDB, and Cloudflare Workers serve a
live session dashboard and a Discord bot on top of that data, behind a
Discord-backed single sign-on.

```
F1 26 (UDP :20777)
      │
      ▼
┌─────────────┐     ┌──────────────────┐      Cloudflare Tunnel
│  listener/  │────▶│  TimescaleDB     │◀───────────┬───────────┐
│  (Python)   │     │  (Postgres 16)   │       Hyperdrive   Hyperdrive
└─────────────┘     └──────────────────┘            │           │
                                              ┌───────────┐ ┌──────────┐
                                              │   web/    │ │   bot/   │
                                              │ dashboard │ │ Discord  │
                                              └───────────┘ └──────────┘
                                                    ▲
                                     Cloudflare Access ─── auth/ (Discord OIDC)
```

| Component | Path | Stack | Runs on |
|---|---|---|---|
| UDP listener | `listener/` | Python 3.12, psycopg 3 | Local Docker |
| Database schema | `schema/` | SQL (TimescaleDB / Postgres 16) | Local Docker |
| Live dashboard | `web/` | TypeScript, Hono | Cloudflare Workers |
| Discord bot | `bot/` | TypeScript, Hono | Cloudflare Workers |
| Access OIDC wrapper | `auth/` | TypeScript, Hono, jose | Cloudflare Workers |
| Shared DB layer | `packages/db/` | TypeScript (`@f1/db`) | npm workspace |

## How it works

The game broadcasts its state as packed C structs over UDP — 17 packet types
covering motion, lap timing, car status, damage, events, and session state.
The listener parses these byte-exact (`listener/packets/`), applies business
rules (`listener/services/`), and writes to Postgres through per-table
repositories (`listener/database/repositories/`).

The parts that took actual thought:

- **Frame assembly** — six packet types describe the same simulation tick.
  A frame buffer keys them by `(session_uid, overall_frame_identifier)` and
  flushes each combined row when the next tick arrives, so one database row
  holds a car's complete state for that instant.
- **Derived timestamps** — row timestamps are computed from the session start
  plus in-game session time, not wall clock, which makes re-delivered packets
  genuinely idempotent under the primary key.
- **Flashback handling** — the in-game rewind feature rolls back session time
  but not frame counters; the listener detects it, deletes the undone frames,
  and records the event, so no phantom duplicate laps survive.
- **Telemetry privacy** — drivers can restrict their telemetry. Restricted or
  player-only fields are stored as `NULL` (or the row is omitted entirely),
  never as fake zeroes.
- **Forward-compatible enums** — unknown values from game patches degrade to
  `UNKNOWN_<value>` with a logged warning, and unseen team IDs are inserted
  on sight, so a game update never takes down collection mid-session.

`web` and `bot` reach the local database through a Cloudflare Tunnel + Workers
VPC service + Hyperdrive, sharing typed row models and queries from
`packages/db`. The dashboard renders a live leaderboard, track map, and
race-director feed off a polling endpoint; the bot posts and finalizes a card
per session into a per-weekend Discord channel on a one-minute cron, and serves
slash commands over signed interaction webhooks. `auth/` is a small OIDC
provider that lets Cloudflare Access authenticate visitors against Discord
guild membership — it touches no telemetry data.

## Running it

Requires Docker and an F1 26 install pointing its telemetry output at the
listener's host.

```bash
cp .env.example .env        # set POSTGRES_PASSWORD
docker compose up -d        # add --build to run local listener changes
```

This starts TimescaleDB (host port 7005) and the listener (UDP host port
9999), which applies the schema on startup. The listener image is published to
GHCR by CI, so a plain `up -d` pulls the last released build — pass `--build`
to run your working tree instead. Point the game's UDP telemetry at the host's
IP, port 9999, format **2026**.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Cloudflare side (tunnel, VPC
service, Hyperdrive, TLS).

## Testing

```bash
# Listener — ~250 tests, including full binary race/qualifying simulations
# that drive generated packet streams through the real dispatcher into Postgres
cd listener && source .venv/bin/activate
pytest
pyright

# Workers (vitest inside the Workers runtime) + the shared package
npm test --workspaces
npm run typecheck --workspaces
```

The listener suite needs the Docker Postgres up; database-backed tests skip
cleanly without it, pure parser/service tests run regardless.
