# Workstream A — PostgreSQL Runtime Foundation

| Control | Value |
|---|---|
| Artifact ID | EV-WSA-001 |
| Version | 1.0 |
| Date | 2026-08-03 |
| Owner | Technical lead |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| **Decision** | **`WORKSTREAM_A_VERIFIED`** |

## 1. Driver version and Python-wheel compatibility

`psycopg[binary]==3.3.4`, pinned. Compatibility was **verified before pinning**, because a
missing wheel on any matrix version would fail `pip install` and take all 88 tests with it.

| Python | Core wheel | Binary wheel (manylinux, as CI runs) |
|---|---|---|
| 3.12 | `psycopg-3.3.4-py3-none-any.whl` | `psycopg_binary-3.3.4-cp312-…manylinux_2_17_x86_64.whl` |
| 3.13 | same | `…cp313-…manylinux_2_17_x86_64.whl` |
| 3.14 | same | `…cp314-…manylinux_2_17_x86_64.whl` |

All three present, so the driver goes in the main `requirements.txt` and the 3.12/3.13/3.14
matrix is preserved. Installed and imported locally: `psycopg 3.3.4`, `psycopg_binary` present.

No `IMPORT_TO_DISTRIBUTION` entry is needed — psycopg is never imported by name in `app/`;
SQLAlchemy loads it from the `postgresql+psycopg://` URL.

## 2. Files created and modified

**Created**
- `services/commerce-api/pytest.ini` — warnings promoted to errors
- `services/commerce-api/tests/test_datetime_contract.py` — 5 tests
- `evidence/workstream-a/WORKSTREAM_A_EVIDENCE.md`

**Modified**
- `services/commerce-api/requirements.txt` — driver pinned
- `services/commerce-api/app/commerce/db.py` — `pool_pre_ping`, `pool_recycle`, sized pool
- `services/commerce-api/app/commerce/models.py` — `as_utc()`
- `services/commerce-api/app/commerce/api.py` — `placed_at` normalised
- `services/commerce-api/app/commerce/services.py` — export timestamps normalised
- `services/commerce-api/tests/conftest.py` — explicit, safe test-database selection
- `services/commerce-api/tests/test_frontend_security.py` — robust repo-root discovery
- `services/commerce-api/docker-entrypoint.sh` — bounded readiness wait
- `docker-compose.yml` — `db` service, no published port, health-gated
- `.env.example` — database and pool configuration
- `.github/workflows/ci.yml` — `postgres` parity job

## 3. Migration commands and exact outputs

```text
$ docker compose exec api python -m alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 8d2d3d0f9b6f, initial commerce schema

$ ... downgrade base   -> Running downgrade 8d2d3d0f9b6f -> , initial commerce schema
  tables remaining: 1 (alembic_version only)

$ ... upgrade head     -> Running upgrade  -> 8d2d3d0f9b6f, initial commerce schema
  tables: 18
```

`Context impl PostgresqlImpl` and `transactional DDL` confirm this ran on PostgreSQL, not
SQLite. Up → down → up all succeeded.

## 4. PostgreSQL table inventory

18 tables (17 domain + `alembic_version`):

```text
addresses  alembic_version  analytics_events  audit_logs  cart_lines  carts
customers  inventory_items  notifications  order_lines  orders  payments
products  promotions  reservations  return_requests  shipments  variants
```

## 5. Clean-volume startup

`docker compose down -v` then `up --build`. Order observed: **db Healthy → api Starting →
api Healthy → storefront Started**. Entrypoint log:

```text
[entrypoint] database reachable
[entrypoint] applying migrations
[entrypoint] seeding fictional MERET dataset (idempotent)
{"seeded": {"products": 5, "variants": 10, "promotions": 2, "customers": 2}}
[entrypoint] starting: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 6. Bootstrap idempotency

Re-seeding a **populated** database creates nothing:

```text
{"seeded": {"products": 0, "variants": 0, "promotions": 0, "customers": 0}}
row counts unchanged: products=5 variants=10 customers=2
```

## 7. `/ready`

```text
{"status":"ready","checks":{"database":"ok","catalog_fixture":"ok"}}
manage.py check -> {"database": "postgresql+psycopg", "status": "ok"}
```

The check reports the **scheme only** and never the URL, so no password can reach a log.

## 8-9. Test results — both engines

| Engine | Result |
|---|---|
| SQLite (in-memory, default) | **88 passed**, 0 warnings |
| PostgreSQL 16 (parity run) | **88 passed**, 0 warnings |

Identical counts. Warnings are errors, so "passed with warnings" cannot be reported as green.

## 10. Datetime-contract tests

5 tests, passing on both engines. Verified **load-bearing**: deleting `as_utc` from `api.py`
makes `test_placed_at_is_serialized_with_an_explicit_utc_offset` fail; restoring it passes.

## 11. Customer-erasure regression

`test_erasure_preserves_financial_records` passes on both engines. Asserts the order row, its
total and its lines survive; the customer row survives with `deleted_at` set, a pseudonymised
`@invalid.example` email, `full_name == "erased"` and no addresses; and the session is
immediately invalid (401).

## 12. Inventory concurrency on PostgreSQL

`test_concurrent_reservation_never_oversells` **PASSED** on PostgreSQL. 20 threads contend for
5 units; exactly 5 win. Pool raised to 10 + 20 overflow so all 20 threads genuinely contend at
the database rather than queueing on connection checkout, which would have made the test pass
for the wrong reason.

## 13. Warnings as errors

`pytest.ini` sets `filterwarnings = error`. Both runs report **0 warnings**. One ignore exists,
scoped to the exact Starlette `httpx` deprecation message and documented — a different
deprecation still fails.

## 14. Docker restart

`docker compose restart api` → healthy in 9s, `/ready` 200, `products=5` unchanged. Restart
neither duplicates data nor fails; the entrypoint's migrate and seed are both idempotent.

## 15. CI configuration

Status: **`CI_CONFIGURATION_VALIDATED_LOCALLY`** — *not* `CI_EXECUTED_ON_GITHUB`.

A `postgres` job was added with a health-gated `postgres:16-alpine` service, running migrations
up/down/up, a table-inventory assertion, bootstrap idempotency and the full suite. YAML parses
and all five job keys resolve. **No GitHub runner exists in this environment, so the pipeline
has never executed.** It must not be described as passing.

## 16. Known limitations

- **CI never executed.** See above.
- **SQLite remains the unit-test default.** Fast, and parity is proven by the PostgreSQL run.
  Only `COMMERCE_TEST_DATABASE_URL` can redirect it; an exported `DATABASE_URL` cannot.
- **`pool_pre_ping` has no automated test.** It only manifests against a dropped TCP
  connection and cannot be honestly unit-tested. Deliberately **not** given a mutation entry —
  a hand-waved guard would devalue the other 19.
- **PostgreSQL has no published host port**, by design. The parity suite runs inside the
  compose network.
- **Mobile, notifications, rate limiting, staging and DEDUNET integration are untouched**, per
  the Workstream A scope boundary.
- One empty untracked `platform/poc` directory persists behind a stale OS handle.

## 17. Rollback

```bash
git revert --no-edit <workstream-a-range>     # code
docker compose down -v                        # drops the pgdata volume
docker compose up --build                     # rebuild on the previous configuration
```

Reverting `docker-compose.yml` and `db.py` restores SQLite; `COMMERCE_DB_PATH` still defaults
correctly. No data migration occurred — the PostgreSQL volume was created empty and seeded, so
nothing is lost that the seed cannot recreate. The single Alembic revision applies to both
engines, so no migration rollback is required.

## 18. Commits

`f7af320` (R0) → this Workstream A commit. See the repository log for the exact hash.

## 19. Decision

**`WORKSTREAM_A_VERIFIED`** — all fourteen scope items implemented and evidenced, 88 tests
passing identically on both engines with zero warnings, migrations reversible on PostgreSQL,
and the one unverifiable item (CI execution) explicitly labelled rather than claimed.
