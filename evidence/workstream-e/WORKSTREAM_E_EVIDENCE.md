# Workstream E — Staging Configuration

| Control | Value |
|---|---|
| Artifact ID | EV-WSE-001 |
| Date | 2026-08-03 |
| Owner | Technical lead |
| **Status** | **`LOCAL_STAGING_CONFIGURATION_VERIFIED`** |
| Rate limiting | **`SINGLE_PROCESS_RATE_LIMITING_VERIFIED`** |
| Release constraint | **`MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING`** |
| **Decision** | **`WORKSTREAM_E_VERIFIED`** |

This is **not** `HOSTED_STAGING_VERIFIED`. A production-shaped Compose stack validated on a
developer machine is not a hosted environment, and nothing here should be described as one.

## 1. Architecture summary

A **standalone** `docker-compose.staging.yml` — not an override. An override silently
inherits the base entrypoint and environment, which is precisely how a staging stack ends
up shipping demo credentials. Three services: `db` (PostgreSQL 16, no published port),
`api` (one uvicorn process, read-only rootfs), `web` (nginx, read-only rootfs).

## 2. Files created and modified

**Created:** `docker-compose.staging.yml`, `.env.staging.example`,
`evidence/workstream-e/WORKSTREAM_E_EVIDENCE.md`

**Modified:** `services/commerce-api/docker-entrypoint.sh` (conditional seed + fail-fast
config gate), `services/commerce-api/manage.py` (`create-admin`, `check-config`, `os`
import), `services/commerce-api/app/commerce/security.py` (`assert_configured`)

## 3–4. Standalone Compose proof and effective JSON

`docker compose -f docker-compose.staging.yml --env-file .env.staging config --format json`
renders successfully. Effective values:

| Property | Value |
|---|---|
| project name | `dedunet-staging` (distinct from development) |
| **db published ports** | **NONE** |
| api command | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1` |
| api `read_only` | `True` |
| api `tmpfs` | `/tmp:size=64m,mode=1777` |
| api `security_opt` | `no-new-privileges:true` |
| api `restart` | `unless-stopped` |
| `SEED_DEMO_DATA` | `0` |
| `RATE_LIMIT_ENABLED` | `1` |
| `RATE_LIMIT_TRUSTED_PROXY_COUNT` | `0` |
| `deploy.replicas` | **absent** |
| api limits | 512 MiB, 1.0 CPU |
| db limits | 1 GiB, 1.0 CPU |
| web `read_only` | `True` |

## 5. Environment-variable reference

`.env.staging.example` contains **no usable secret**: `SESSION_SECRET`,
`POSTGRES_PASSWORD` and `ADMIN_BOOTSTRAP_PASSWORD` are all empty, and `ADMIN_API_TOKEN` is
the placeholder the fail-closed guard refuses in every environment. Staging ports (18080 /
13080) deliberately differ from development (18000 / 13000) so the two stacks cannot
silently answer for one another.

## 6. Seed-disabled evidence

```text
[entrypoint] SEED_DEMO_DATA=0 -> skipping demo seed; no demo customer, admin, product or order is created
```

## 7. Zero-data evidence

```text
customers=0  orders=0  carts=0  products=0  admins=0
GET /api/v1/catalog/products  ->  []
```

Known demo credentials rejected: `admin@meret.example` → **401**,
`customer@meret.example` → **401**.

## 8. Administrator bootstrap

```text
$ manage.py create-admin                       # no configuration
ERROR: ADMIN_BOOTSTRAP_EMAIL is not set

$ ADMIN_BOOTSTRAP_PASSWORD=short-11-ch ...     # 11 characters
ERROR: ADMIN_BOOTSTRAP_PASSWORD is 11 characters; at least 12 are required

$ ADMIN_BOOTSTRAP_PASSWORD=<redacted, 29 chars> ...
{"created": true, "email": "ops@dedunet.example", "role": "admin"}

$ (same command again)
{"created": false, "email": "ops@dedunet.example", "role": "admin",
 "detail": "account already exists; no change made"}

admin count: 1        login as the new admin: HTTP 200
```

The password is read from the environment (never an argument — arguments appear in shell
history and `ps`) and appears in **no** output. Only `created`, `email` and `role` are
printed. The command is manual; the entrypoint never runs it.

## 9. Session-secret failure and success

**A real defect was found and fixed here.** The first implementation put
`assert_configured()` only inside `manage.py check`, which the entrypoint calls in its
**database wait loop**. A blank secret therefore produced sixty seconds of
`[entrypoint] waiting for database (attempt N/30)` — a misleading diagnostic for a
permanent error that no amount of waiting can fix.

Fixed by adding `manage.py check-config`, which validates configuration only and touches
no database, and running it **before** the wait loop:

```text
{"configuration": "invalid", "error": "SESSION_SECRET is empty and APP_ENV='staging'.
 Sessions cannot be signed. Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""}
[entrypoint] configuration is invalid; refusing to start
```

Immediate, names the setting, states the consequence, gives the fix. The secret value and
the connection string are never printed. `/ready` returned **000** — the API never served
a single request. With a valid secret: `{"configuration": "valid"}`, container healthy,
`/ready` 200.

`assert_configured()` also rejects the known development secret and any secret under 32
characters, reporting only the length.

## 10. One-process / one-worker proof

`ps` is absent from the slim image, so counted via `/proc`, excluding the probe's own PID:

```text
processes excluding this probe: 1
  pid 1: /usr/local/bin/python3.12 /usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
uvicorn server processes: 1
RESULT: PASS - exactly one process, one worker
```

An earlier count reported 2 — a false positive, because the probe script's own source text
contained the word `uvicorn`.

Rate limiting confirmed live on the staging port: `401 ×10` then `429 ×3`.

## 11. No database port

```text
api -> 0.0.0.0:18080->8000/tcp
db  -> 5432/tcp            (container-internal only; no host mapping)
web -> 0.0.0.0:13080->80/tcp
host 127.0.0.1:5432 -> no listener
```

## 12. Read-only filesystem proof

Verified by attempting writes, not assumed:

| Path | Result |
|---|---|
| `/app` | read-only (correct) |
| `/usr` | read-only (correct) |
| `/tmp` | writable (required, tmpfs) |
| `.pyc` files under `/app` | **0** |

Read-only is viable because every write path was identified first: logs go to
stdout/stderr, `PYTHONDONTWRITEBYTECODE=1` stops bytecode writes, migrations write only to
the database, `data/` is mounted read-only, and the API produces no uploads or backups.
`docker inspect` confirms `ReadonlyRootfs=true`.

nginx needs `/var/cache/nginx`, `/var/run` and `/tmp` writable even for purely static
content, so `web` gets three small tmpfs mounts.

## 13. Resource constraints — and what the runtime actually enforces

| Service | Memory | CPU | Rationale |
|---|---|---|---|
| api | 512 MiB | 1.0 | One uvicorn process; room for SQLAlchemy pools and PBKDF2 without hiding a leak |
| db | 1 GiB | 1.0 | `shared_buffers`, `work_mem`, connections |
| web | 128 MiB | 0.5 | Static file serving |

**Enforcement verified, not assumed.** `deploy.resources.limits` is often described as
Swarm-only and ignored by plain Compose. On this runtime (Compose v5.3.0) `docker inspect`
shows the limits genuinely applied:

```text
Memory: 536870912      (512 MiB)
NanoCpus: 1000000000   (1.0 CPU)
```

These are Docker cgroup limits, **not** Kubernetes-style requests/guarantees. There is no
scheduler reserving capacity — only a ceiling.

## 14. Health and readiness

`/ready` → 200 `{"status":"ready","checks":{"database":"ok","catalog_fixture":"ok"}}`,
`/health` → 200, storefront → 200. All three services healthy; the healthcheck probes
`/ready`, so the API is not declared healthy until the database is genuinely reachable.

## 15–17. Suites and mutations

| Check | Result |
|---|---|
| SQLite full suite | **112 passed, 0 warnings** |
| PostgreSQL full suite | **112 passed, 0 warnings** |
| Mutation guards | **23/23 detected, 0 survived** |

## 18. Restart and reset

`docker compose restart api` → healthy in ~10s, `/ready` 200, the manually created
administrator persisted (1 admin). `down -v` removed the network and the
`staging-pgdata` volume; **0** staging volumes remained.

## 19. Secret and runtime-artifact scan

| File | Tracked | Ignored |
|---|---|---|
| `.env` | no | yes |
| `.env.staging` | no | yes |
| `.env.example` | yes (template) | — |
| `.env.staging.example` | yes (template, empty secrets) | — |

`.env*` occurrences in git history: **0**.

## 20. Known limitations

- **`LOCAL_STAGING_CONFIGURATION_VERIFIED`, not hosted staging.** No cloud, DNS, TLS or
  external proxy exists. This is a production-shaped Compose stack on a developer machine.
- **`SINGLE_PROCESS_RATE_LIMITING_VERIFIED`.** One process, one worker, no `replicas` key.
  **`MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING`.**
- `RATE_LIMIT_TRUSTED_PROXY_COUNT=0` because local staging has no proxy chain. A hosted
  environment must determine and test its real chain before raising this; setting it in
  anticipation would let any client spoof its bucket key.
- Resource limits are cgroup ceilings, not scheduler guarantees.
- `restart: unless-stopped` means a misconfigured container restart-loops rather than
  stopping. It fails loudly and never serves, which is the intended trade-off, but the
  loop is visible in `docker ps`.
- No SMTP, backups, DEDUNET data, mobile or cloud deployment — all out of scope here.
- TLS terminates nowhere; staging is plain HTTP on localhost.

## 21. Rollback

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging down -v
git revert --no-edit <workstream-e-commit>
```

Development compose is untouched and still starts. `SEED_DEMO_DATA` defaults to `1`, so
reverting restores the previous development behaviour byte-for-byte. No schema change and
no migration — the staging volume is created empty and discarded on `down -v`.

## 22. Commit

One commit on `dedunet/repository-restructure-and-workstreams-a-f`.

## 23. Decision

**`WORKSTREAM_E_VERIFIED`**
