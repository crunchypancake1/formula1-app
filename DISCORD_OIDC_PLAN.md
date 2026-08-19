# Discord OIDC wrapper — implementation plan

Implemented (`auth/`, see `DEPLOYMENT.md`'s "Discord OIDC wrapper" section
for the manual infra setup). This document is the plan it was built from,
kept for reference.

## Why a wrapper

Cloudflare Access's "Generic OIDC" IdP type expects a real OIDC provider
(discovery doc, `/authorize`, `/token`, JWKS, signed `id_token`). Discord's
OAuth2 isn't OIDC — no `id_token`. The wrapper Worker sits between Access and
Discord: runs the Discord OAuth dance, checks guild membership via the
existing bot token, then mints its own signed JWT that Access consumes.

Verified against current Cloudflare docs (not assumed):

- Access's Generic OIDC config needs Auth URL, Token URL, Certificate
  (JWKS) URL, Client ID/Secret, and supports RS256 signing. PKCE is
  optional.
- A path-scoped **Route** (`f1.crunchypancake.com/auth*`) coexists with
  `web`'s existing **Custom Domain** on the same hostname with no change to
  `web/wrangler.jsonc` — routes with path patterns take precedence over a
  Custom Domain on the same hostname.
- You already run this "same hostname, different Worker on a sub-path"
  pattern for `linkwarden` at `crunchypancake.com/mcp`, and confirmed
  scoping the Access Application to exclude the wrapper's route works the
  same way here.

## Decisions locked in from planning discussion

| Decision | Choice |
|---|---|
| Membership check | Bot-token lookup: `GET /guilds/{guild_id}/members/{user_id}` with the existing `DISCORD_BOT_TOKEN`. Discord OAuth scope is `identify` only for this purpose — no `guilds` scope, no extra consent line. |
| Authorization-code storage | Stateless signed JWTs end-to-end. No KV, no new infra. Both the Access⇄Discord "relay state" and the Discord⇄Access "authorization code" handoff are short-lived signed JWTs. |
| Worker routing | Path-scoped Route `f1.crunchypancake.com/auth*` on the `crunchypancake.com` zone — not a subdomain, not `custom_domain`. |
| ID token claims | Include `preferred_username` and `picture` from day one (free — already fetched during the membership check). |
| Discord OAuth scope | Defaulting to `identify email` (not just `identify`) so the `email` claim can be populated — Access's own docs use `email` as the claim it shows in its UI/audit log. **This is the one soft default, not an explicit sign-off — revisit before implementing if you'd rather skip the email scope and leave that claim unset.** The actual access gate stays purely "verified guild member," never email-based. |
| Signing key | Single RSA keypair (RS256) reused for the id_token *and* the two internal-only JWTs (relay-state, auth-code) — avoids provisioning/rotating a second secret for tokens that never leave this Worker's own request lifecycle. |

## New component: `auth/`

Sibling to `web/` and `bot/`, own npm workspace member, deployed as Worker
`formula1-auth`. No Hyperdrive/Postgres binding — this Worker never touches
the database.

```
auth/
  package.json
  wrangler.jsonc
  tsconfig.json
  vitest.config.ts
  src/
    env.ts
    discord.ts
    tokens.ts
    index.ts
  test/
    tokens.test.ts
    discord.test.ts
    index.test.ts
```

### `auth/wrangler.jsonc`

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "formula1-auth",
  "main": "./src/index.ts",
  "compatibility_date": "2026-08-08",
  // No nodejs_compat — jose and hono are edge-native, unlike bot/web's `postgres` dep.

  "workers_dev": false,
  "preview_urls": false,

  "vars": {
    "DISCORD_GUILD_ID": "",
    "DISCORD_OAUTH_CLIENT_ID": "",
    "ACCESS_CLIENT_ID": "",
    "ACCESS_TEAM_DOMAIN": "",
    "OIDC_ISSUER": "https://f1.crunchypancake.com/auth"
  },

  "secrets_store_secrets": [
    { "binding": "DISCORD_BOT_TOKEN", "store_id": "d947ac5bb8ef4800ac46fc59128a1a09", "secret_name": "discord-bot-token" },
    { "binding": "DISCORD_OAUTH_CLIENT_SECRET", "store_id": "d947ac5bb8ef4800ac46fc59128a1a09", "secret_name": "discord-oauth-client-secret" },
    { "binding": "ACCESS_CLIENT_SECRET", "store_id": "d947ac5bb8ef4800ac46fc59128a1a09", "secret_name": "access-client-secret" },
    { "binding": "OIDC_SIGNING_KEY", "store_id": "d947ac5bb8ef4800ac46fc59128a1a09", "secret_name": "oidc-signing-key" }
  ],

  "routes": [{ "pattern": "f1.crunchypancake.com/auth*", "zone_name": "crunchypancake.com" }],

  "observability": {
    "logs": { "enabled": true, "invocation_logs": true }
  }
}
```

`DISCORD_BOT_TOKEN` reuses the bot's existing secret (same store, read-only
here). The other three secrets are new.

### `auth/package.json`

Same shape as `bot/package.json` (scripts: `deploy`/`dev`/`test`/`typecheck`),
dependencies `hono` + `jose` (new — RS256 JWT sign/verify, JWKS export; no
Node-API dependency, runs natively on Workers), same devDependencies
(`@cloudflare/vitest-pool-workers`, `@cloudflare/workers-types`,
`typescript`, `vitest`, `wrangler`) at the versions already pinned in
`bot/package.json`.

## Request flow

1. Browser hits `f1.crunchypancake.com` → Access has no session → redirects
   to `/auth/authorize?client_id=...&redirect_uri=https://<team>.cloudflareaccess.com/cdn-cgi/access/callback&state=...`
2. Wrapper validates `client_id === ACCESS_CLIENT_ID` and that `redirect_uri`
   starts with `https://${ACCESS_TEAM_DOMAIN}/` (open-redirect guard), packs
   both into a signed relay-state JWT (aud `relay`, 10 min exp), redirects to
   Discord's `/oauth2/authorize` with `scope=identify email`, our own
   `redirect_uri=${OIDC_ISSUER}/callback`, `state=<relay-jwt>`
3. Discord redirects back to `/auth/callback?code&state` → wrapper verifies
   the relay-state JWT, exchanges the Discord code for an access token,
   fetches `/users/@me`, then calls `getGuildMember` with the bot token —
   a 404 renders a plain "not a member" 403 page and stops here; nothing
   ever reaches Access
4. On success, wrapper mints a signed auth-code JWT (aud `auth-code`, 60s
   exp) carrying `sub`, `preferred_username`, `picture`, `email`, redirects
   to `relay.redirectUri?code=<auth-code-jwt>&state=<relay.accessState>`
5. Access's backend calls `POST /auth/token` with client credentials (accept
   both HTTP Basic and POST-body `client_secret_post` — Cloudflare's docs
   don't pin down which one Access uses) → wrapper verifies the auth-code
   JWT, re-signs the same claims as an `id_token` (aud `ACCESS_CLIENT_ID`,
   5 min exp), returns `{ access_token, id_token, token_type, expires_in }`
   (access_token and id_token are the same JWT — no separate resource
   server exists here)
6. `/auth/userinfo` (optional per Access's docs, implemented anyway for
   spec completeness) and `/auth/jwks` round out the discovery contract

## File specs

### `auth/src/env.ts`

```ts
export interface SecretsStoreSecret {
  get(): Promise<string>;
}

export interface AuthEnv {
  DISCORD_GUILD_ID: string;
  DISCORD_OAUTH_CLIENT_ID: string;
  ACCESS_CLIENT_ID: string;
  ACCESS_TEAM_DOMAIN: string;
  OIDC_ISSUER: string;
  DISCORD_BOT_TOKEN: SecretsStoreSecret;
  DISCORD_OAUTH_CLIENT_SECRET: SecretsStoreSecret;
  ACCESS_CLIENT_SECRET: SecretsStoreSecret;
  OIDC_SIGNING_KEY: SecretsStoreSecret;
}
```

Mirrors `bot/src/env.ts`'s pattern (own local `SecretsStoreSecret`
interface rather than a shared package — this Worker doesn't use `@f1/db`
at all).

### `auth/src/discord.ts`

Plain `fetch` wrapper, styled after `bot/src/discord/client.ts`:

- `exchangeDiscordCode(clientId, clientSecret, code, redirectUri): Promise<{access_token: string}>` — `POST https://discord.com/api/v10/oauth2/token`, form-urlencoded, `grant_type=authorization_code`
- `getDiscordUser(accessToken): Promise<DiscordUser>` — `GET /users/@me` with `Authorization: Bearer`. `DiscordUser = { id, username, avatar: string|null, email?, verified? }`
- `getGuildMember(botToken, guildId, userId): Promise<{user:{id:string}}|null>` — `GET /guilds/{guild}/members/{user}` with `Authorization: Bot`; **404 → return `null`** (the only branch the callback route needs), other non-2xx → throw
- `discordAvatarUrl(user): string|null` — `null` if no avatar hash, else `https://cdn.discordapp.com/avatars/{id}/{hash}.{gif|png}` (`.gif` when the hash starts with `a_`, i.e. animated)

### `auth/src/tokens.ts`

Built on `jose`. One module-level memoized key derivation
(`let cachedKeys: Promise<Keys> | null`) that imports the PKCS8 private key
from `OIDC_SIGNING_KEY`, derives the public JWK from it, and imports a
separate verify-only `CryptoKey` from that public JWK (an RSA sign-only
`CryptoKey` can't itself verify in WebCrypto).

- `getJwks(env): Promise<{keys: JWK[]}>` — public JWK only: `{kty, n, e, alg: "RS256", use: "sig", kid: "1"}`. **Must never include the private components (`d`, `p`, `q`, `dp`, `dq`, `qi`) that `exportJWK` would include if given the private key directly** — strip to an explicit allowlist of fields, don't spread-and-delete.
- `signRelayState(env, {redirectUri, accessState}): Promise<string>` / `verifyRelayState(env, token): Promise<{redirectUri, accessState}>` — claims `ru`/`rs`, `aud: "relay"`, 10m exp
- `signAuthCode(env, claims: AuthClaims): Promise<string>` / `verifyAuthCode(env, token): Promise<AuthClaims>` — `aud: "auth-code"`, 60s exp. `AuthClaims = { sub, preferredUsername, picture: string|null, email?: string }`
- `signIdToken(env, claims): Promise<string>` / `verifyIdToken(env, token): Promise<AuthClaims>` — `aud: env.ACCESS_CLIENT_ID`, 5m exp

### `auth/src/index.ts`

Hono app, `Bindings: AuthEnv`, routes (all under `/auth/*` — Workers Routes
don't strip the path prefix, so every handler path must include it):

- `GET /auth/.well-known/openid-configuration` — discovery doc, all URLs derived from `OIDC_ISSUER`; `id_token_signing_alg_values_supported: ["RS256"]`, `token_endpoint_auth_methods_supported: ["client_secret_basic", "client_secret_post"]`
- `GET /auth/authorize` — validates `client_id`/`redirect_uri` as above, redirects to Discord
- `GET /auth/callback` — verifies relay state, does the Discord token+user+membership calls, redirects to Access with the minted auth-code, or 403s with a plain-text "not a member" page
- `POST /auth/token` — parse body once (`c.req.parseBody()`), pull client credentials from `Authorization: Basic` header if present else from the parsed body's `client_id`/`client_secret`, constant-comparison-free equality against `ACCESS_CLIENT_ID`/`ACCESS_CLIENT_SECRET` is fine here (not a high-value timing target), verify the `code` field as an auth-code JWT, sign and return the id_token
- `GET /auth/userinfo` — Bearer-token variant of `verifyIdToken`, returns the same claims as JSON
- `GET /auth/jwks` — `getJwks(c.env)`

## Tests to write

- `tokens.test.ts` — pure, no I/O: generate an ephemeral RSA keypair per test run (`jose.generateKeyPair`) exported as PKCS8, fed through a fake `AuthEnv`. Round-trip each sign/verify pair; assert audience mismatches and expired tokens are rejected; assert `getJwks()` output has no private key fields.
- `discord.test.ts` — `vi.stubGlobal("fetch", ...)` (works under `@cloudflare/vitest-pool-workers` since tests execute inside the same workerd realm as the source, and the source calls bare `fetch(...)` rather than an imported binding, same as `bot/src/discord/client.ts`). Cover the token exchange, user fetch, guild-member 200/404, and `discordAvatarUrl`'s static/animated/null cases.
- `index.test.ts` — drive the Hono app via `app.request(path, init, fakeEnv)` (bypasses real Wrangler bindings, matching how Hono apps are typically unit-tested under vitest-pool-workers) with `fetch` mocked for the Discord calls. Cover: discovery doc shape; `/authorize` happy path and bad-`client_id`/bad-`redirect_uri` rejections; `/callback` happy path and the not-a-member 403; `/token` happy path plus wrong-client-secret 401; `/jwks` shape.

## Repo-wide changes

- Root `package.json`: add `"auth"` to `workspaces`.
- `DEPLOYMENT.md`: new section alongside the existing bot-setup writeup —
  Workers table gets a `formula1-auth` row (no public health check route,
  since this Worker only ever serves the OIDC endpoints), Secrets Store
  table gets the three new secrets with their `wrangler secrets-store
  secret create` commands, plus the manual external-setup steps below.

## Manual setup (infra, not app code — same treatment as the Tunnel)

Sequenced, since later steps need values generated in earlier ones:

1. Generate the RSA keypair once (e.g. via a throwaway `node -e` script
   using `jose.generateKeyPair("RS256")`, or `openssl genrsa` +
   `openssl pkcs8`), store the PKCS8 private key PEM as the
   `oidc-signing-key` Secrets Store secret.
2. Mint two arbitrary strings for `ACCESS_CLIENT_ID` / `access-client-secret`
   (these are values *we* invent — Access will be configured with them, and
   our `/token` handler checks incoming requests against them). Put the
   client ID in `auth/wrangler.jsonc`'s `vars.ACCESS_CLIENT_ID`, the secret
   in the Secrets Store.
3. Discord Developer Portal → the bot's existing application (or a new one)
   → OAuth2 tab → add redirect URI `https://f1.crunchypancake.com/auth/callback`
   → copy the OAuth2 Client ID into `vars.DISCORD_OAUTH_CLIENT_ID`, the
   Client Secret into the `discord-oauth-client-secret` Secrets Store entry.
4. Deploy `auth/` (`npm run deploy` from `auth/`) so the endpoints exist.
5. Cloudflare Zero Trust → Settings → Authentication → Add identity provider
   → OpenID Connect: Auth URL `https://f1.crunchypancake.com/auth/authorize`,
   Token URL `.../auth/token`, Certificate URL `.../auth/jwks`, Client
   ID/Secret = the values from step 2.
6. Zero Trust → Access → Applications: protect `f1.crunchypancake.com`,
   **scoping the Application's path to exclude `/auth/*`** — same pattern
   already used for `crunchypancake.com/mcp` with linkwarden. Getting this
   wrong causes a login loop: Access would intercept its own IdP-callback
   traffic before it reaches the wrapper.
7. Access Policy: "Login Method is Discord" — no email allowlist needed,
   since guild membership is already the sole gate, enforced inside the
   wrapper before any code is ever minted.
8. Set `vars.ACCESS_TEAM_DOMAIN` to the `<team-name>.cloudflareaccess.com`
   value and redeploy `auth/` — this is what `/authorize` validates
   incoming `redirect_uri`s against.

## Verification pass (once implemented)

Single pass at the end, not per-file: `npm run typecheck` and `npm test` in
`auth/`, then a real browser walkthrough of the full login loop against the
deployed Worker and a live Access Application — the JWT plumbing is exactly
the kind of thing that type-checks and unit-tests clean while still being
wrong end-to-end (wrong claim name, wrong audience, Access's actual
Basic-vs-body auth-method choice), so the manual walkthrough isn't optional.
