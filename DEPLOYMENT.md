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

## Workers

Both Workers deploy from `master` via Workers Builds, one build connection
each, scoped by root directory. See the per-Worker sections below once they
exist.
