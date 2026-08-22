# Plan — personal driver view (`/me`)

A signed-in user who is driving in the current live session gets a button to their own view:
who's ahead and behind and by how much, what tyre sets they have left and in what condition.

Scope is deliberately small. Everything under [Later](#later) is worth building and none of it
is needed for a first working page.

## Decisions

| Question | Decision |
|---|---|
| How `web` learns the signed-in identity | Custom OIDC claims (`discord_id`, `preferred_username`) passed through Access into the JWT's `custom` claim |
| Persisting the driver link | **Not persisted.** Every request re-runs the fuzzy match against the live roster; `identity.users` is never written from `web`. Simplest thing that works — a stored link is a later decision, made once it's clear what it needs to support |
| Low-confidence / ambiguous match | Best match or nothing — no button, no picker. ~50 guild members vs 22 seats means a picker would prompt ~30 spectators to claim a car |
| Page shape | New route `/me`, its own server-rendered shell polling `GET /api/me`, mirroring `dashboard.ts` |

---

## 1. Identity

### 1a. `auth/src/tokens.ts` — emit the Discord id under its own claim

`sub` is the Discord user id, but Access replaces `sub` with its own account-scoped id, so it does
not survive to the origin. Add a claim that does:

```ts
function claimsToPayload(claims: AuthClaims): Record<string, unknown> {
  return {
    sub: claims.sub,
    discord_id: claims.sub,          // Access overwrites `sub`; this is what reaches the origin
    preferred_username: claims.preferredUsername,
    picture: claims.picture,
    ...(claims.email !== undefined ? { email: claims.email } : {}),
  };
}
```

`payloadToClaims` needs no change — it already reconstructs from `sub`. Mirror both fields in the
`/auth/userinfo` response body (Access may read claims from either endpoint) and add them to
`claims_supported` in the discovery document.

### 1b. Cloudflare dashboard, one-time

Zero Trust → Settings → Authentication → the Discord OIDC provider → Optional configurations →
**OIDC Claims**: add `discord_id` and `preferred_username`.

They then arrive inside the Access application token's `custom` object.

Ship 1a and confirm the claim actually lands in `custom` before building against it — until this
edit is made, `readViewer` returns `null` for everyone and no button appears.

### 1c. `web/worker/access.ts` — verify the Access JWT

Add `jose` to `web/package.json` (already a dependency of `auth`).

```ts
import { createRemoteJWKSet, jwtVerify } from "jose";

export interface Viewer {
  discordId: string;
  username: string;
}

/** Module-level so the JWKS is fetched once per isolate, not per request. */
let jwks: ReturnType<typeof createRemoteJWKSet> | null = null;

export async function readViewer(env: Env, request: Request): Promise<Viewer | null> {
  const token = request.headers.get("cf-access-jwt-assertion");
  if (!token || !env.ACCESS_POLICY_AUD) return null;

  jwks ??= createRemoteJWKSet(new URL(`${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`));

  try {
    const { payload } = await jwtVerify(token, jwks, {
      issuer: env.ACCESS_TEAM_DOMAIN,
      audience: env.ACCESS_POLICY_AUD,
    });
    const custom = payload.custom as Record<string, unknown> | undefined;
    const discordId = typeof custom?.discord_id === "string" ? custom.discord_id : null;
    if (!discordId) return null;
    return {
      discordId,
      username: typeof custom?.preferred_username === "string" ? custom.preferred_username : "",
    };
  } catch {
    return null;
  }
}
```

Never throws. A viewer we cannot identify just gets the public dashboard.

New vars in `web/wrangler.jsonc`:

```jsonc
"vars": {
  "ACCESS_TEAM_DOMAIN": "https://<team-name>.cloudflareaccess.com",
  "ACCESS_POLICY_AUD": "<AUD tag from the Access application>"
}
```

`auth` stores `ACCESS_TEAM_DOMAIN` bare (`<team>.cloudflareaccess.com`) because it uses it as a
redirect-URI prefix; `jwtVerify`'s `issuer` needs the scheme. Store `web`'s with `https://` and
note the difference in `DEPLOYMENT.md`.

### 1d. `BOT_STATE` KV binding

Add the same read-only binding `auth` has (same namespace id, `bot`'s cron tick owns every write).
It gives the matcher the user's server nickname (`StoredMember.displayName` in `members:v1`), which
for a league is usually much closer to the in-game name than the Discord handle is.

---

## 2. Matching — `web/worker/matching.ts`

Pure, no I/O, fully unit-testable. Port of `f1-24-telemetry`'s
`code/api/app/utils/driver_matching.py`, with tier 2 moved out of `pg_trgm` and into the Worker —
the candidate set is only the drivers in the live session (≤22), so a trigram query buys nothing.

```ts
// Longest-first: the alternation is first-match-wins, so "reserve" must be tried
// before "res" or "namereserve" normalises to "nameerve".
const KNOWN_SUFFIXES = ["wildcard", "reserve", "res", "sub", "wc"];
const SUFFIX_RE = new RegExp(`[\\s_\\-]+(${KNOWN_SUFFIXES.join("|")})\\s*$`);

export function normalizeDriverName(name: string): string {
  const base = name.trim().toLowerCase().replace(SUFFIX_RE, "").replace(/[_\-\s]+/g, "");
  return base.replace(/\d+$/, "") || base;
}

export function similarity(a: string, b: string): number;  // bigram Dice coefficient, 0..1
```

Each driver is scored against **both** the Discord handle and the server nickname; the driver's
score is the better of the two. A normalized exact hit scores 1.0 and short-circuits.

A match is **confident** only when both hold:

- `score >= 0.6` — well above `pg_trgm`'s 0.3 default, too loose to auto-link an identity
- `bestScore - runnerUpScore >= 0.15` — stops two lookalike names (`rollie1881` /
  `rollie_a1181`) from producing a coin flip

Anything short of confident yields `null`: no button on the dashboard, and `/me` renders a
"we couldn't work out which car is yours" state.

**Resolution**, used by both `/api/live` and `/api/me`, is a single stateless step: score the
viewer against the live roster on every request (`web/worker/viewer.ts`'s `resolveViewerDriver`).
A confident hit returns `{ userId, driverName }`; nothing short of confident does. There is no
"linked account" tier — `identity.users.discord_id` is not read or written by `web` at all.

---

## 3. The page

| Route | Purpose |
|---|---|
| `GET /me` | `renderPersonalView()` — static shell, same pattern as `renderDashboard()` |
| `GET /api/me` | Polled payload: session + the viewer's matched driver + the panels below |

The dashboard gains one thing: when `/api/live` carries a `you` block, render a "Your race →"
button in the header. When it doesn't, the header is unchanged — the ~30 spectators see exactly
what they see today.

### Panels (v1)

1. **Identity strip** — `P{position} · {driver_name} #{race_number} · {team}`, lap X/Y, time
   remaining, back-link to the dashboard. Team colour via the existing `teamColor()` helper.
2. **Battle** — car ahead (name, team bar, gap, tyre + age), you, car behind (same). Highlight a
   gap under 1.0s; show DRS available and 2026 overtake boost available/active. Gaps come from
   `car_frame.gap_to_car_ahead_ms` / `gap_to_car_behind_ms` on your own row; the names from a join
   on the latest-frame CTE at `position = mine ± 1`.
3. **Available tyre sets** — newest `tyre_sets` snapshot for this user: compound, wear %,
   `usable_life - wear` remaining, `lap_delta_time_ms`, which set is `fitted`. It is a *per-lap*
   snapshot, so label it with the lap it came from.
4. **Tyres now** — current compound, age in laps, and per-corner wear from `car_frame_damage`.

### Rendering NULLs

Tyre sets and the whole `car_frame_damage` row are withheld by the game for a driver whose
*Your Telemetry* setting is Restricted. The schema stores NULL / no row rather than zeros on
purpose, so panels 3 and 4 must distinguish three states and never render a NULL as `0`:

- **value** — render it
- **not yet seen** — "waiting for data" (early in a session, before the first snapshot)
- **withheld** — "Your Telemetry is set to Restricted, so the game doesn't share tyre-set or
  wear data", with a hint that switching it to Public in the game's telemetry settings turns
  these panels on

`telemetry.entries.telemetry_public` says which of the last two applies, per driver. Use it
rather than guessing from the absence of rows.

---

## 4. Queries — `web/worker/queries/personal.ts`

Every query bounds `timestamp >= sessions.session_start_utc`. `car_frame`, `car_frame_damage` and
`session_timeline` are hypertables partitioned on `timestamp`; a query naming only `session_uid`
cannot exclude chunks and opens every one in the table.

- `personalFrame(sql, sessionUid, startUtc, userId)` — latest `car_frame` row for one driver, plus
  a `LATERAL` join naming the cars at `position ± 1`
- `availableTyreSets(sql, sessionUid, userId)` — newest `lap_number` snapshot. No hypertable; the
  `(session_uid, user_id, lap_number, set_index)` UNIQUE covers it
- `personalDamage(sql, sessionUid, startUtc, userId)` — latest `car_frame_damage` row, may be absent

---

## 5. Types and tests

`packages/db/src/schema.ts` gains `PersonalFrameRow` / `PersonalFrame`, `CarDamageRow`, `TyreSetRow`,
following the existing `LiveDriverRow` → `LiveDriver` raw-codes-in / resolved-names-out split.
`car_frame`'s enum columns resolve through `enumFromCode` exactly as `resolveLiveDriver` does.

Tests follow `web/test/queries/*.test.ts` — pure functions over builders, no database:

- `matching.test.ts` — port the Python docstring examples verbatim (`Crunchypancake1_RES` →
  `crunchypancake`, `Rollie_A1881` ≡ `Rollie A1881`, `rollie_a1181` ≢ `rollie1881`), plus the
  margin rule: two near-identical candidates must yield `null`, not a coin flip
- `access.test.ts` — no `custom`, bad audience, missing header all yield `null` rather than throwing
- `personal.test.ts` — resolver purity, and NULL wear surviving as `null` rather than `0`
- extend `web/test/fixtures.ts` with the new row builders

`wrangler.jsonc` supports an `access.dev` block for exercising the signed-in path under
`wrangler dev` without deploying.

---

## Build order

1. `matching.ts` + tests — pure, no dependencies, most likely to need tuning
2. `auth` claim change → deploy → confirm `custom.discord_id` arrives
3. `access.ts`, `web` vars, `BOT_STATE` binding
4. Query layer + `@f1/db` types
5. `GET /api/me` and the `you` block on `/api/live`
6. `renderPersonalView()` — panels 1–4
7. `DEPLOYMENT.md`: the OIDC-claims step and the two new vars. `CLAUDE.md`: `/me`

A stored link (`identity.users.discord_id`, a confirm affordance, a claim endpoint) is deliberately
not in this build — see the Decisions table. Add it later as its own pass if the runtime match
ever proves too slow or too fragile to run on every request.

---

## Later

- **Energy & fuel** — fuel in tank, `fuel_remaining_laps`, fuel mix; ERS store, deploy mode,
  deployed/harvested this lap (`car_frame`, restricted)
- **Damage & reliability** — wings, floor, diffuser, sidepod, gearbox, engine, per-component engine
  wear, `drs_fault` / `ers_fault` / `engine_blown` / `engine_seized` (`car_frame_damage`)
- **Strategy** — `session_timeline.pit_stop_window_ideal_lap` / `_latest_lap` / `_rejoin_position`,
  stops made, plus `weather_forecast` rain % ahead
- **Penalties** — `penalties_seconds`, warnings, corner-cutting, unserved DT/SG, lap-invalid
- **Your laps** — last N from `telemetry.laps` with sector splits and per-sector validity, personal
  best highlighted, delta to personal best and session best
- **Full tyre detail** — per-corner surface/inner temp, pressure, blisters, brake temp; stint number
- **Player-only telemetry** — `car_frame_motion_ex` (suspension, wheel slip, ride height). Only ever
  describes the capturing machine's player, so it lights up for one viewer at most
- **Fix `liveDrivers()`** in `web/worker/queries/live.ts` — it doesn't bound `timestamp`, so it opens
  every chunk on every 3s poll. `latestSession()` already returns `session_start_utc`; pass it through
