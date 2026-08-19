# Deployment

## Cloudflare resources

| Resource | Name | ID |
|---|---|---|
| Cloudflare Tunnel | `Home Network` | `9e35418e-b4db-4925-a652-3869c4f5c964` |
| Workers VPC service | `f1-postgres` | `019fed9e-c8cd-7672-bdbf-44b1cafbcddb` |
| Hyperdrive | `f1-db` | `ded8933c250e438cac3a2d76b2f97b5e` |
| Secrets Store | *(shared)* | `d947ac5bb8ef4800ac46fc59128a1a09` |

The tunnel predates this project and already has private network access to the
database host. Nothing about it is managed here.

Hyperdrive query caching is **disabled** — the live view polls for fresh
telemetry frames and a cache would serve stale car positions.

### TLS

Hyperdrive requires TLS on the origin database. The local Postgres container
uses a self-signed certificate (`certs/server.crt` / `certs/server.key`, not
committed — see `docker-compose.yaml` for how it's mounted and enabled). The
`f1-postgres` VPC service has `--cert-verification-mode disabled`: Hyperdrive
configs backed by a Workers VPC service cannot be paired with a custom CA
certificate (`mtls cannot be used with service_id`), so certificate
verification is turned off at the VPC service layer instead. The connection
between Hyperdrive and the origin is still encrypted; only certificate
identity verification is skipped, which is acceptable here because the path
runs entirely over the private Cloudflare Tunnel, not the public internet.

To regenerate the cert locally:

```bash
mkdir -p certs
openssl req -new -x509 -days 3650 -nodes -text \
  -out certs/server.crt -keyout certs/server.key \
  -subj "/CN=f1-postgres"
chmod 600 certs/server.key
docker compose up -d postgres
```

## Local stack

```bash
cp .env.example .env    # set POSTGRES_PASSWORD
docker compose up -d
```

Two services: `postgres` (TimescaleDB, published on host port 7005) and
`listener` (applies `schema/run_schema.py` on startup, then captures UDP on
port 9999).

### Resetting the database

There is no migration path (pre-1.0 schema churn is handled by recreation,
not `ALTER TABLE`). To wipe and rebuild with the current schema:

```bash
docker compose down -v      # drops the postgres_data volume
docker compose up -d --build
```

The init script recreates `f1_app` with the TimescaleDB extension and the
`identity`/`telemetry` schemas; the listener applies `schema/*.sql` on
startup. Hyperdrive holds no schema state (query caching is disabled and
`fetch_types` is off), so nothing on the Cloudflare side needs recreating.

## Workers

| Worker | Route | Health check |
|---|---|---|
| `formula1-web` | `f1.crunchypancake.com` | `GET /api/health` |
| `formula1-bot` | `f1-bot.crunchypancake.com` | `GET /health` |

Both deploy from `master` via Workers Builds, one build connection each,
scoped by root directory — a push to `master` redeploys them. Manual deploys
work too: `npm run deploy` in `web/` or `bot/`.

The health endpoints verify connectivity end to end (Worker → Hyperdrive →
tunnel → Postgres) and probe for F1 26 marker columns
(`packages/db/src/health.ts`), so they return 503 with the missing markers
listed if the database schema is stale.

### Bot Discord session cards

`formula1-bot` runs a 1-minute Cron Trigger (`bot/wrangler.jsonc`'s
`triggers.crons`) that posts and finalizes race-weekend session cards into a
Discord channel. It needs:

- `DISCORD_GUILD_ID` (`vars` in `bot/wrangler.jsonc`) — the target server's id.
  Currently blank; set it before deploying.
- `DISCORD_CHANNEL_NAME` (`vars`, defaults to `active-session`) — the channel
  the bot creates/reuses for the current weekend.
- `DISCORD_ARCHIVE_CATEGORY_ID` (optional `vars`, unset by default) — a
  category to move a weekend's channel into once archived.
- `DISCORD_BOT_TOKEN` — the first binding against the shared Secrets Store
  (`d947ac5bb8ef4800ac46fc59128a1a09`, see the table above). Create it once
  with `npx wrangler secrets-store secret create <store-id> --name
  discord-bot-token --scopes workers`, then paste in a bot token from the
  Discord Developer Portal with `Manage Channels` + `Send Messages` +
  `Manage Messages` permissions in that guild.

The bot's Discord REST calls are outbound-only (`bot/src/discord/client.ts`)
— no gateway connection, so no `GatewayIntents` or persistent connection to
manage.
