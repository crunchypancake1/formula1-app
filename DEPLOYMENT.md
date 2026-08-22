# Deployment

## Cloudflare resources

| Resource | Name | ID |
|---|---|---|
| Cloudflare Tunnel | `Home Network` | `9e35418e-b4db-4925-a652-3869c4f5c964` |
| Workers VPC service | `f1-postgres` | `019fed9e-c8cd-7672-bdbf-44b1cafbcddb` |
| Hyperdrive | `f1-db` | `ded8933c250e438cac3a2d76b2f97b5e` |
| Secrets Store | *(shared)* | `d947ac5bb8ef4800ac46fc59128a1a09` |
| KV namespace | `BOT_STATE` | `f95fefa1c9e245daaa8ed60a9230579b` |

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
| `formula1-bot` | `f1.crunchypancake.com/bot*` | `GET /bot/health` |
| `formula1-auth` | `f1.crunchypancake.com/auth*` | *(none — OIDC endpoints only, see below)* |

Both deploy from `master` via Workers Builds, one build connection each,
scoped by root directory — a push to `master` redeploys them. Manual deploys
work too: `npm run deploy` in `web/` or `bot/`.

The health endpoints verify connectivity end to end (Worker → Hyperdrive →
tunnel → Postgres) and probe for F1 26 marker columns
(`packages/db/src/health.ts`), so they return 503 with the missing markers
listed if the database schema is stale.

### Bot Discord session cards

`formula1-bot` runs two Cron Triggers (`bot/wrangler.jsonc`'s
`triggers.crons`): `* * * * *` posts and finalizes race-weekend session cards,
registers slash commands, and snapshots the guild roster to KV every minute;
`0 * * * *` reconciles team roles once an hour (`src/index.ts`'s `scheduled()`
branches on `event.cron` to tell them apart). It needs:

- `DISCORD_GUILD_ID` (`vars` in `bot/wrangler.jsonc`) — the target server's id.
- `DISCORD_CHANNEL_NAME` (`vars`, defaults to `active-session`) — the channel
  the bot creates/reuses for the current weekend.
- `DISCORD_ARCHIVE_CATEGORY_ID` (optional `vars`, unset by default) — a
  category to move a weekend's channel into once archived.
- `DISCORD_BOT_TOKEN` — the first binding against the shared Secrets Store
  (`d947ac5bb8ef4800ac46fc59128a1a09`, see the table above). Create it once
  with `npx wrangler secrets-store secret create <store-id> --name
  discord-bot-token --scopes workers`, then paste in a bot token from the
  Discord Developer Portal with `Manage Channels` + `Send Messages` +
  `Manage Messages` + `Manage Roles` permissions in that guild.
- `DISCORD_PUBLIC_KEY` (`vars`) — from the Developer Portal's **General
  Information** page. It only ever verifies inbound signatures, so it is not a
  secret and stays in `wrangler.jsonc` rather than the Secrets Store. The
  application id is deliberately *not* configured: the bot token already
  identifies the app, so `currentApplicationId` reads it from
  `GET /applications/@me` when a command sync actually happens, and inbound
  interactions carry it in their payload.
- `BOT_STATE` — the KV namespace above. Holds the fingerprint of the
  last-registered command set (`bot/src/discord/commands.ts`) and the guild
  roster snapshot (`bot/src/discord/memberStore.ts`, key `members:v1`) that
  `formula1-auth` also reads to check membership at login — see below. Team
  roles are **not** cached here: `bot/src/discord/roleStore.ts` re-lists the
  guild live on every hourly reconciliation, since `GET` on the role list is
  cheap and roles change only when someone edits the guild by hand. Deleting
  the namespace's contents just makes the next tick rebuild the command
  fingerprint and roster.

`Manage Roles` is what lets the bot create the per-team roles, and the bot's
own highest role has to sit **above** the roles it manages in the guild's role
list — Discord refuses `POST /guilds/{id}/roles` for a position at or above the
caller's own. If the role step logs a `403`, that ordering is why.

### Bot slash commands and webhook events

The cron tick is outbound-only, but slash commands are not: Discord POSTs
those *to* the Worker, so unlike the session cards they need a publicly
reachable URL. Two Developer Portal fields point at it, both on the
**General Information** page:

| Portal field | Value |
|---|---|
| Interactions Endpoint URL | `https://f1.crunchypancake.com/bot/interactions` |
| Event Webhooks URL (optional) | `https://f1.crunchypancake.com/bot/events` |

Saving either one makes Discord immediately probe it — a signed request that
must be answered correctly, then a corrupted one that must come back `401`.
`bot/src/discord/verify.ts` handles both; if the portal reports the endpoint
could not be verified, the cause is almost always one of the next two items
rather than the code.

Note that `DISCORD_PUBLIC_KEY` has to be set *before* saving the URL — with it
empty, `verifyDiscordRequest` rejects everything and the probe fails.

**Deploy before saving the URL.** The endpoint has to exist and be live at the
moment you press Save, so `git push` to `master` (or `npm run deploy` in
`bot/`) first.

**Access needs no change, because the Route itself is the exemption.** A
request matched by a path-scoped Workers Route on this hostname bypasses the
Access application; everything else on `f1.crunchypancake.com` gets the login
redirect. That is why `/auth/*` has never needed an exclusion rule, and why
widening the bot's pattern from `/bot` to `/bot*` is the whole fix — before it,
`/bot/interactions` didn't match the route, fell through to `web`, and answered
Discord with a 302 to the Access login page rather than a PONG.

Verify with curl after deploying; an Access redirect here means the route
pattern is wrong, not the Access policy:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://f1.crunchypancake.com/bot
# 200, not 302
```

Commands themselves register from the cron tick, not by hand: `ensureCommands`
hashes the schemas in `bot/src/discord/commands.ts` against a KV key and calls
`PUT /applications/{id}/guilds/{guild}/commands` whenever they differ. They are
guild-scoped, so a change appears in Discord within a minute of the deploy
instead of the up-to-an-hour propagation global commands get.

The bot holds no gateway connection either way — no `GatewayIntents`, nothing
persistent to manage. Interactions arrive as ordinary HTTP requests.

### Discord OIDC wrapper (`formula1-auth`)

`formula1-auth` lets Cloudflare Access use Discord server membership as an
identity provider for `f1.crunchypancake.com`. It runs the Discord OAuth
dance, checks guild membership against the roster `formula1-bot`'s cron tick
snapshots into the shared `BOT_STATE` KV namespace (`src/members.ts`, key
`members:v1` — no bot token or Discord API call needed here, but membership
checks are only as fresh as the last cron tick, up to ~1 minute), then
mints its own signed JWT (`ES256`) that Access consumes as an OIDC
`id_token`. It never touches the database — no Hyperdrive binding.

It's deployed via a path-scoped **Route**
(`f1.crunchypancake.com/auth*`, `auth/wrangler.jsonc`), not a Custom Domain
— routes with path patterns take precedence over `web`'s Custom Domain on
the same hostname, the same "same hostname, different Worker on a sub-path"
pattern already used for `crunchypancake.com/mcp` (linkwarden).

It also needs a `BOT_STATE` binding — the same KV namespace id as `formula1-bot`'s
(`kv_namespaces` in `auth/wrangler.jsonc`), read-only from this Worker's side;
`formula1-bot`'s cron tick owns the writes.

Secrets (Secrets Store, same store as the table above):

| Secret name | Purpose | Create with |
|---|---|---|
| `discord-oauth-client-secret` | Discord OAuth2 code exchange | `npx wrangler secrets-store secret create d947ac5bb8ef4800ac46fc59128a1a09 --name discord-oauth-client-secret --scopes workers` |
| `access-client-secret` | Value Access is configured with; `/auth/token` checks incoming requests against it (we invent this string, Access doesn't issue it) | same command, `--name access-client-secret` |
| `oidc-signing-key` | EC (ES256, P-256) PKCS8 private key PEM, signs the id_token plus the two internal-only relay-state/auth-code JWTs | same command, `--name oidc-signing-key` |

Manual setup, in order (later steps need values from earlier ones):

1. Generate an EC (P-256) keypair (e.g. `jose.generateKeyPair("ES256")` in a
   throwaway script, or `openssl ecparam -name prime256v1 -genkey` +
   `openssl pkcs8`); store the PKCS8 private key PEM as `oidc-signing-key`.
   An RSA key will fail to import — `tokens.ts` hardcodes `ES256`.
2. Invent two arbitrary strings for `ACCESS_CLIENT_ID` /
   `access-client-secret`. Put the client ID in `auth/wrangler.jsonc`'s
   `vars.ACCESS_CLIENT_ID`, the secret in the Secrets Store.
3. Discord Developer Portal → the bot's application → OAuth2 tab → add
   redirect URI `https://f1.crunchypancake.com/auth/callback` → copy the
   OAuth2 Client ID into `vars.DISCORD_OAUTH_CLIENT_ID`, the Client Secret
   into `discord-oauth-client-secret`.
4. Deploy `auth/` (`npm run deploy` from `auth/`) so the endpoints exist.
5. Cloudflare Zero Trust → Settings → Authentication → Add identity
   provider → OpenID Connect: Auth URL
   `https://f1.crunchypancake.com/auth/authorize`, Token URL `.../auth/token`,
   Certificate URL `.../auth/jwks`, Client ID/Secret = the values from step 2.
6. Zero Trust → Access → Applications: protect `f1.crunchypancake.com`. No
   path exclusion is needed — a request matched by a path-scoped Workers Route
   bypasses the Access application, so `/auth/*` is exempt by virtue of the
   Route existing, the same "same hostname, different Worker on a sub-path"
   arrangement as `crunchypancake.com/mcp`. (Earlier revisions of this document
   called for an explicit exclusion rule here. It was never necessary, and none
   was ever created.) Confirm rather than assume — if this is wrong the symptom
   is a login loop, Access intercepting its own IdP callback before it reaches
   the wrapper:

   ```sh
   curl -sS -o /dev/null -w '%{http_code}\n' https://f1.crunchypancake.com/auth/jwks
   # 200 = the Route takes precedence. 302 = it does not, and Access needs scoping.
   ```
7. Access Policy: "Login Method is Discord" — no email allowlist needed,
   guild membership is already the sole gate, enforced inside the wrapper
   before any code is ever minted.
8. Set `vars.ACCESS_TEAM_DOMAIN` to the `<team-name>.cloudflareaccess.com`
   value and redeploy `auth/` — `/authorize` validates incoming
   `redirect_uri`s against it (open-redirect guard).
