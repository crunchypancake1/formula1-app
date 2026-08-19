# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

F1 26 UDP telemetry capture, a live session dashboard, and a Discord bot.

| Component | Runs on | Path | Language |
|---|---|---|---|
| Listener | Local Docker | `listener/` | Python |
| Database schema | Local Docker (TimescaleDB / Postgres 16) | `schema/` | SQL |
| Live dashboard | Cloudflare Workers | `web/` | TypeScript (Hono) |
| Discord bot | Cloudflare Workers | `bot/` | TypeScript (Hono) |

The listener captures UDP telemetry from the game and writes it to a local
PostgreSQL/TimescaleDB instance. Both Workers read that same database through
Hyperdrive over a Cloudflare Tunnel (see `DEPLOYMENT.md` for the tunnel/VPC
service/TLS setup — that part is infrastructure, not app code, and rarely
needs touching).

**UDP format is 2026-only.** `packets/packet_header.py::validate_packet_header`
rejects anything where `packet_format != 2026` or `game_year != 26`. There is
no F1 25 back-compat and none is planned — don't add dual-format branching.

## Commands

### Listener (Python, `listener/`)

```bash
cd listener
source .venv/bin/activate        # venv already exists in the repo

pytest                           # full suite (~247 tests)
pytest tests/test_dispatcher.py  # single file
pytest tests/test_dispatcher.py::test_name  # single test
pytest -k car_frame              # by keyword

pyright                          # type check (pyrightconfig.json scopes to source dirs, excludes tests/)
```

**The suite needs a live Postgres.** `tests/conftest.py` connects to
`localhost:7005` (override with `POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB`)
and everything that touches the DB *skips* silently without one — a green run
with ~200 skips means the stack is down, not that the tests passed. Start it
with `docker compose up -d`. Pure parser and service tests use
`tests/mock_repo.py` and run either way.

`tests/scenario.py` and `tests/qualifying_scenario.py` build full binary packet
sequences via `tests/packet_builder/` and drive them through the real
dispatcher into the database. The race scenario deliberately includes drivers
with Your Telemetry set to Restricted (`scenario.RESTRICTED_CAR_INDICES`) so
the withheld-data paths are covered end to end. `tests/factories.py` builds the
real packet dataclasses for service tests — use it rather than hand-rolled
`SimpleNamespace` stand-ins, which silently drift from the parsers.

### Web dashboard / Discord bot (TypeScript, `web/` and `bot/`)

Same scripts in both:

```bash
npm run dev         # wrangler dev
npm test            # vitest run
npm run typecheck   # tsc --noEmit
npm run deploy      # wrangler deploy
```

Both use `@cloudflare/vitest-pool-workers`, so tests run inside the actual
Workers runtime, not Node.

### Local stack (Postgres + listener)

```bash
cp .env.example .env    # set POSTGRES_PASSWORD
docker compose up -d
```

`listener` container runs `schema/run_schema.py` (applies SQL in FK order)
then `main.py` on startup. Postgres is published on host port 7005, UDP
listener on 20777→9999.

## Architecture

### Listener packet flow

`server.py` (UDP socket) → `dispatcher.py` (`PacketDispatcher.handle_packet`)
→ per-packet-ID routing → `services/*.py` → `database/repositories/*.py` →
Postgres.

Key dispatcher behaviors, all in `dispatcher.py`:

- **Session gating**: packet ID 1 (Session) establishes a session as known;
  everything else (except Lobby Info, ID 9) is dropped until the session's
  Participants packet (ID 4) has built a `car_index → user_id` map.
  Session types `{0, 18}` (unknown, time trial) are excluded entirely.
- **Body-size validation**: `packet_header.EXPECTED_BODY_SIZE` gives exact
  sizes per packet ID; IDs 8/9/11 (`VARIABLE_LENGTH_PACKET_IDS`) are
  car/entry-count dependent and validated as upper bounds instead. Mismatches
  are dropped and logged once per `(session_uid, packet_id)`.
- **Frame buffering**: packets 0 (Motion), 2 (Lap Data), 6 (Telemetry), 7
  (Car Status), 10 (Car Damage), and 16 (Telemetry 2) all describe the same
  simulation tick and are combined into one `car_frame` row. `FrameBuffer`
  (`frame_buffer.py`) keys them by `(session_uid, overall_frame_identifier)`
  and flushes on the next frame's arrival, on session end (`SEND` event), or
  on a periodic stale-frame sweep. Packet 13 (Motion Ex) is player-only and
  writes immediately, unbuffered.
- **Frame timestamps are derived, not wall-clock.** `sessions.session_start_utc`
  is written once (as `NOW() - m_sessionTime`) and never moved; every frame row's
  `timestamp` is `session_start_utc + session_time`. That is what makes the
  `(timestamp, session_uid, user_id, overall_frame_identifier)` primary keys
  actually de-duplicate a frame that arrives twice. Don't reach for
  `clock_timestamp()` in these tables — it silently defeats the key.
- **Race gating**: a race records no `car_frame` rows until the dispatcher sees
  the race start — `LGOT` (lights out), the formation-lap `SCAR(3, 3)`, or the
  backstop of any car reaching lap 2. All three matter: relying on `SCAR` alone
  discards an entire race whenever formation laps are off.
- **Flashbacks**: `FLBK` rewinds `m_sessionTime` but not
  `m_overallFrameIdentifier`, so the dispatcher deletes frame rows above the
  rewind point and records the event in `telemetry.events_flashbacks`. Without
  that, the undone run stays in the database as a duplicate lap.
- **Row shape is defined once.** `database/repositories/car_frame.py` owns
  `CAR_FRAME_COLUMNS`; the INSERT and the service's field lookups are both
  derived from it (`COLUMN_INDEX`). Add a column there, not by counting
  placeholders.
- **Lap completion detection**: `_check_lap_completions` diffs
  `current_lap_num` per car frame to trigger car-setup and tyre-set snapshot
  writes at the moment a lap ends.
- **Restricted telemetry**: some fields are only visible for the player's own
  car, or hidden entirely depending on a driver's telemetry privacy setting
  (see the `f1-udp-telemetry` skill for exact per-field rules). Restricted
  car indices come from `ParticipantsService.get_restricted_indices`.
  **Never store zero-filled rows for player-only or restricted data** — if a
  field isn't available for a car, its row should be omitted or the column
  left `NULL`, not written as `0`. In practice: Car Status fuel/ERS/brake-bias
  are NULLed per car, the whole `car_frame_damage` row is skipped, Tyre Sets
  are skipped, and an all-zero Car Setup is never persisted.

Each `packets/*.py` module owns `struct.unpack` binary layouts for one packet
type; each `services/*.py` module owns the business logic (validation,
enum resolution, restricted-field handling) for turning an unpacked packet
into repository calls; each `database/repositories/*.py` owns the SQL for one
table. `enums/` mirrors the game's integer enum tables (teams, tracks,
tyre compounds, etc.) via `safe_enum_name` (`database/repositories/base.py`)
so unrecognized values degrade to a logged warning instead of a crash.

### Schema (`schema/`)

`schema/run_schema.py` applies `.sql` files in explicit FK-dependency order
(`SCHEMA_EXECUTION_ORDER`) — `identity.users` first, then `telemetry.*`
tables. When adding a table with a new FK dependency, add it to that list in
dependency order, don't rely on filename sorting.

No database has been deployed yet, so **there is no migration path and none is
wanted**: each `.sql` file is the whole current definition of its table. Change
the `CREATE TABLE` in place rather than appending `ALTER TABLE`, and recreate
the database.

`telemetry.sessions` holds the session's static configuration;
`telemetry.session_timeline` holds everything that changes while it runs
(weather, safety car, period counters, marshal-zone flags, pit window).
`telemetry.tracks` is track-static only — marshal zone *positions* live there,
their *flags* do not.

Unknown enum values must never block collection. `safe_enum_name` degrades to
`UNKNOWN_<value>`, and `EntriesRepository.ensure_teams` inserts any unseen
`team_id` before the roster references it — a team added by a game patch would
otherwise fail the FK and take the whole session's roster with it.

### Web / bot Workers

Both are thin Hono apps. `db.ts` in each connects via the `HYPERDRIVE`
binding (`postgres` npm package, `fetch_types: false` since Hyperdrive can't
cache the type-introspection query). Hyperdrive caching itself is disabled
project-wide (see `DEPLOYMENT.md`) because the live view needs fresh car
positions on every poll, not cached rows. Both currently only expose a
`/health`-style endpoint — the actual dashboard/bot functionality has not
been built yet.
