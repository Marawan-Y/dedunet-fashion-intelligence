# DEDUNET — fashion commerce platform

A working, locally runnable commerce platform for **DEDUNET**, a fashion brand identity under
development, used to exercise and demonstrate the system.

> **Nothing here is a commercial offering.** No company, factory, supplier, product,
> certification or customer exists. Every product, material, origin, price, customer, order
> and support case is fabricated. Payments run against a sandbox adapter; no card is charged
> and nothing is fulfilled in the physical world. The brand is
> **`LEGAL_CLEARANCE_PENDING`**. This build is **not** approved for public deployment —
> see [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md).

> **Rewritten 2026-08-24 at `41cee4c`.** The previous README described a pre-workstream,
> MERET-era platform: it claimed 81 tests against an actual 415, omitted PostgreSQL, rate
> limiting, notification dispatch, staging, backup and commerce modes entirely, and three of
> its documentation links were dead. Recorded as **DISC-02** in the successor takeover
> report. Closes the README half of CONFLICT-009.

---

## Commerce modes — read this first

The deployment runs in one of two selectable modes, and **which one decides what the
software will let you do.**

| Mode | Catalogue | Purchase | Payment |
|---|---|---|---|
| `BRAND_PREVIEW_MODE` | visible | **refused** | none reachable |
| `COMMERCE_TEST_MODE` | visible | synthetic stock only | sandbox adapter |
| `PUBLIC_COMMERCE_MODE` | — | **refused by configuration** | — |

`PUBLIC_COMMERCE_MODE` cannot be enabled by setting an environment variable. It raises.
Reaching it requires a code change *and* the documented activation gate, because real money
for real customers must not be one variable away from a prototype whose brand is
`LEGAL_CLEARANCE_PENDING` and whose products carry `origin_claim_status = UNVERIFIED`.

Every customer-facing surface derives its disclosure from the mode via
`/api/v1/commerce/mode` rather than hard-coding a sentence. A banner that cannot tell which
mode it is in is how "no card is charged" ends up on a screen where one could be.

---

## What actually works

Verified by executed tests and by human acceptance where stated.

| Capability | State |
|---|---|
| Catalogue, variants, stock visibility, search, filter, sort | VERIFIED |
| Customer registration, login, RBAC, session tokens, expiry handling | VERIFIED |
| Cart, quote, VAT-inclusive pricing, promotions, shipping threshold | VERIFIED |
| Checkout with sandbox payment, idempotent replay | VERIFIED |
| Atomic stock reservation (no overselling under concurrency) | VERIFIED |
| Orders, admin fulfilment, shipment tracking, test-order provenance | VERIFIED |
| Cancellation, returns, refunds, restock | VERIFIED |
| Commerce modes and their disclosures | VERIFIED |
| **PostgreSQL 16 runtime** (Workstream A) | VERIFIED |
| **Notification outbox + dispatch worker, claim leases, fencing** (Workstream B) | VERIFIED |
| **Public request rate limiting** (Workstream C) | VERIFIED — process-local only |
| **PostgreSQL backup and isolated restore rehearsal** (Workstream D) | VERIFIED — local only |
| **Standalone local staging stack** (Workstream E) | VERIFIED |
| Customer data export and erasure | VERIFIED |
| Operations portal (orders, inventory, product creation) | VERIFIED |
| Browser clients rendered and asserted in jsdom | VERIFIED |
| AI stylist (deterministic, catalogue-grounded, **not** a language model) | VERIFIED |
| Structured logs, correlation IDs, health and readiness probes | VERIFIED |
| Migrations (apply and reverse) | VERIFIED |
| Docker Compose stacks (development and staging) | VERIFIED |
| Mobile app — Expo, 14 Jest suites, web export | VERIFIED |
| Mobile app — **Android native preview on emulator** | `NATIVE_ANDROID_PREVIEW_ACCEPTANCE_PASSED` |
| Mobile app — **iOS native** | **NOT TESTED** — Apple membership deferred, no budget |
| Mobile web on **physical iPhone Safari** | `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` — 25 gates, `BRAND_PREVIEW_MODE` |
| Local team acceptance, end to end, by a human | `LOCAL_TEAM_ACCEPTANCE_PASSED` |
| CI pipeline | **NOT EXECUTED** — no runner, and no Git remote to push to |
| Hosted staging, cloud, TLS, DNS | **NOT_STARTED** |
| Multi-replica deployment | **BLOCKED** — rate-limit buckets are process-local |

Test baseline at `41cee4c`: **415 passed, 2 skipped** (SQLite path). The two skips are
PostgreSQL-only guarantees. **77 guard mutations** registered.

> **Mobile web is accepted; native iOS is not built.** These are separate facts and must not
> be merged. The storefront was exercised in Safari on a physical iPhone against local staging
> over the LAN, in `BRAND_PREVIEW_MODE`, across 25 gates
> ([`IPHONE_MOBILE_WEB_ACCEPTANCE.md`](evidence/team-acceptance/IPHONE_MOBILE_WEB_ACCEPTANCE.md)).
> **No iOS binary has ever been built** — no signing, no TestFlight, no App Store, and Apple
> Developer Program membership is `DEFERRED — FUNDING`. Mobile web and the native application
> share a commerce contract and nothing else. Neither may the Android and iPhone records be
> aggregated into "mobile is accepted": Android is an emulator preview, iPhone is mobile web,
> and native iOS is nothing at all.

---

## Quick start

Requires Python 3.12+ (developed and tested on 3.14). No external services needed.

```bash
cd services/commerce-api
python -m pip install -r requirements.txt
```

```bash
python manage.py bootstrap
```

`bootstrap` applies migrations and loads the fictional DEDUNET dataset. Safe to re-run.
Without `DATABASE_URL` set it uses SQLite, which is the local-development default;
every Compose stack runs PostgreSQL 16.

Terminal 1 — API on `:18000`:

```bash
APP_ENV=development CORS_ORIGINS="http://localhost:13000,http://127.0.0.1:13000" python -m app.server --port 18000
```

Terminal 2 — static clients on `:13000`, served from the repository root:

```bash
python -m http.server 13000 --bind 127.0.0.1
```

| Surface | URL |
|---|---|
| Storefront | <http://127.0.0.1:13000/apps/web/> |
| Operations portal | <http://127.0.0.1:13000/apps/admin/> |
| API docs (Swagger) | <http://127.0.0.1:18000/docs> |
| Readiness probe | <http://127.0.0.1:18000/ready> |

**Demonstration accounts** (fictional, local database only):

| Role | Email | Password |
|---|---|---|
| Customer | `customer@dedunet.example` | `demo-password-123` |
| Administrator | `admin@dedunet.example` | `demo-password-123` |

Sandbox payment outcome is chosen at checkout: **succeeds**, **declined**, **provider error**.

> **Local vs container paths differ.** Served from the repository root the clients are at
> `/apps/web/` and `/apps/admin/`. In Docker, nginx maps them to `/storefront/` and
> `/admin/`, which is why the Docker table below shows different URLs.
>
> `CORS_ORIGINS` must list the exact origin you browse from. `localhost` and `127.0.0.1` are
> different origins to a browser, and the application does not auto-load `.env`.

### Docker — development stack

```bash
cp .env.example .env
```

Set a unique `ADMIN_API_TOKEN` and a `POSTGRES_PASSWORD`. While the `change-me` placeholder
is configured, the legacy admin API returns HTTP 503 in every environment — by design.

```bash
docker compose up --build
```

Services: `db` (PostgreSQL 16), `api`, `storefront`. The API container applies migrations and
seeds on start; both steps are idempotent. The healthcheck probes `/ready`, not `/health`, so
the storefront will not start against an API whose database is unreachable.

| Surface | URL |
|---|---|
| Storefront | <http://localhost:13000/> (redirects to `/storefront/`) |
| Operations portal | <http://localhost:13000/admin/> |
| API | <http://localhost:18000/docs> |

If another checkout already holds those host ports, run an isolated instance rather than
stopping someone else's stack:

```bash
API_PORT=18100 STOREFRONT_PORT=13100 docker compose -p my-isolated-poc up --build --detach
```

### Docker — local staging stack

```bash
docker compose -f docker-compose.staging.yml up --build --detach
```

Services: `db`, `api`, `notification-worker`, `web`. API on `:18080`, web on `:13080`. The
database publishes **no host port** — that absence is the control, not an oversight.

`COMMERCE_MODE` is declared in both compose files. It has to be: Compose forwards no
arbitrary shell variable, so before that was fixed (`1e657bf`) the mode could not be switched
in any deployed stack, silently.

> **`docker compose down` stops the stack. `docker compose down -v` destroys its data.**
> The staging volume holds the backup-rehearsal fixtures and the retained acceptance orders.

---

## Repository map

```
services/commerce-api/
  app/
    commerce/          the commerce domain
      db.py            engine, session, declarative base
      models.py        18 tables + 5 status enums; money is integer minor units
      modes.py         BRAND_PREVIEW / COMMERCE_TEST / PUBLIC_COMMERCE (refused)
      security.py      PBKDF2 hashing + HMAC session tokens
      inventory.py     atomic reservation (anti-overselling)
      pricing.py       discounts, shipping, VAT extraction
      payments.py      gateway Protocol + sandbox adapter
      notifications.py transactional outbox
      services.py      orchestration and transactions
      api.py           HTTP routes
      seed.py          fictional DEDUNET dataset
      synthetic_inventory.py   explicit, mode-gated test stock
    rate_limit.py      token bucket, stdlib only, PROCESS-LOCAL
    server.py          explicit ASGI proxy boundary
    main.py            app, middleware, health/ready, legacy PoC routes
    money.py           money primitives (binary floats rejected)
    ai_stylist.py      68-line deterministic scorer — NOT a language model
  migrations/          Alembic — 5 revisions, head a7c31f9be402
  tests/               24 modules — 415 passed, 2 skipped
  notification_worker.py   separate dispatch process
  manage.py            migrate / seed / bootstrap / export-openapi / check /
                       check-config / create-admin / load-test-inventory /
                       clear-test-inventory
apps/web/              customer storefront (static, no build step)
apps/admin/            operations portal (static, no build step)
apps/mobile/           Expo / React Native — 14 Jest suites, own mutation harness
packages/contracts/openapi/openapi.json    authoritative API contract, 31 paths
infrastructure/backup/ backup_manager.py + failure-mode tests
scripts/validation/    data validators + the 79-entry mutation harness
docs/ evidence/ handoffs/    system of record
```

Layering is one-directional: `api → services → {inventory, pricing, payments} → models → db`.
The rule modules never import `api` or `services`, so each is unit-testable without HTTP.

Middleware order: **correlation → CORS → rate limiter → routes**, so a 429 stays readable by
a browser and carries a correlation ID.

---

## Testing

```bash
cd services/commerce-api && PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
```

```bash
python scripts/validation/validate_product_data.py
```

```bash
python scripts/validation/validate_candidate_data.py --assess-sellable
```

```bash
python scripts/validation/mutation_guard_check.py
```

Those two pytest flags are not cosmetic. Bytecode caches copied between checkouts have
previously been executed in the wrong tree, because Python validates a `.pyc` against source
mtime and size — both preserved by a plain file copy. Never ship `__pycache__` or
`.pytest_cache`.

`--assess-sellable` **must** exit non-zero: the synthetic candidate can never be eligible for
sellable/public activation. A zero exit there is a defect.

`mutation_guard_check.py` removes each safety guard one at a time and requires the suite to
fail. A guard whose removal nobody notices is not a guard. It takes roughly 3 minutes per
mutation because each run also re-verifies that the restored source is green.

### Preserved sample fixtures

`services/commerce-api/tests/conftest.py` fails the run if any test changes these:

```text
sha256(products.json)           = 536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
sha256(candidate_products.json) = 7f052e4c8d75302695faa23b44efa7ed4e2f28ad64aaff9746d0109d8dab8323
```

---

## Design decisions worth knowing

**Money is integer minor units, everywhere.** €59.00 is `5900`. `price_eur` and `total_eur`
do not exist on the wire. Binary floats are rejected at every money boundary — never rounded
or coerced — and a test uses `0.70 × 3` to prove it. The browser clients format from integers
by string manipulation and never divide. Full rules:
[`docs/side-b/SIDE_B_MONEY_CONTRACT.md`](docs/side-b/SIDE_B_MONEY_CONTRACT.md).

**VAT is a component, not an addend.** Displayed prices are VAT-inclusive, as EU consumer
retail requires, so `tax = total − round(total ÷ (1 + rate))`. Adding VAT on top would change
the price the customer was shown. Rates are illustrative configuration and carry no tax
advice.

**Stock reservation is one atomic SQL statement.** A `SELECT` followed by an `UPDATE` has a
race window between them, and that window is exactly where overselling happens. The check
constraint `reserved <= on_hand` is the backstop if the module is ever bypassed.

**Checkout reserves stock before authorizing payment.** Taking money for goods that are
already gone is worse than briefly holding stock for a payment that then declines.

**Purchasability has two independent gates.** `modes.assert_purchasable` refuses on the mode
*and* on the product, and neither is inferred from the other. A prototype does not become
purchasable merely because it has a price, and the storefront mirrors both gates so it never
offers a control whose only outcome is a rejection.

**Orders copy their descriptive fields.** An order is a financial record; renaming a product
must never alter a past order.

**Erasure pseudonymizes; it does not delete orders.** Identifiers are removed and login
disabled, while the accounting history the business must be able to reconcile survives.

**No `innerHTML` anywhere in the browser clients.** Every node is built with
`document.createElement` and every string inserted as `textContent`. A test asserts it. This
closed SB-RISK-003 (stored XSS) and the discipline is file-wide, not per-field.

---

## Where this is going

`ADR-0002` proposes repositioning DEDUNET from a single-brand commerce platform into a
fashion intelligence platform: AI stylist, multi-brand marketplace and merchant SaaS.

**None of that exists yet.** No style profile, no outfit engine, no brand entity, no tenant
column, no LLM. See
[`docs/architecture/DEDUNET_V1_TARGET_DOMAIN_ARCHITECTURE.md`](docs/architecture/DEDUNET_V1_TARGET_DOMAIN_ARCHITECTURE.md)
for the target and
[`DEDUNET_V1_EXECUTION_PLAN.md`](docs/architecture/DEDUNET_V1_EXECUTION_PLAN.md) for the
phases. Read them as a target, not an inventory.

---

## Legacy proof-of-concept surface

The original fixture-backed endpoints (`/api/v1/products`, `/api/v1/candidate-products`,
`/api/v1/stylist/recommend`, `/api/v1/orders/quote`, `/api/v1/admin/products`) are preserved
unchanged, along with their evidence-gating behaviour and the `X-Admin-Token` control. The
commerce API is namespaced separately (`/api/v1/catalog`, `/cart`, `/checkout`, `/me`,
`/admin/catalog`, `/admin/orders`) because the two have different authentication models, and
sharing a path would let router registration order decide the effective guard.

Show a candidate that cannot be activated:
`GET /api/v1/candidate-products/VS-TEE-001/activation` returns `eligible: false` with 27
blocking errors.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) | What is deliberately not done, and why |
| [`docs/architecture/decisions/`](docs/architecture/decisions/) | Architecture decision records |
| [`packages/contracts/openapi/openapi.json`](packages/contracts/openapi/openapi.json) | Authoritative API contract |
| [`docs/operations/RUNBOOKS.md`](docs/operations/RUNBOOKS.md) | Operational runbooks |
| [`docs/operations/TEAM_ACCEPTANCE_TEST_SCRIPT.md`](docs/operations/TEAM_ACCEPTANCE_TEST_SCRIPT.md) | The 19-step human acceptance script |
| [`docs/operations/BACKUP_AND_RESTORE_RUNBOOK.md`](docs/operations/BACKUP_AND_RESTORE_RUNBOOK.md) | Backup and restore |
| [`docs/operations/EXTERNAL_SERVICE_ACTIVATION.md`](docs/operations/EXTERNAL_SERVICE_ACTIVATION.md) | Activating real providers |
| [`docs/system-of-record/`](docs/system-of-record/) | Gates, decisions, risks, conflicts |
| [`docs/system-of-record/SUCCESSOR_AGENT_TAKEOVER_REPORT.md`](docs/system-of-record/SUCCESSOR_AGENT_TAKEOVER_REPORT.md) | Verified baseline for a new agent |
| [`docs/side-b/SIDE_B_LAUNCH_BLOCKER_AUDIT.md`](docs/side-b/SIDE_B_LAUNCH_BLOCKER_AUDIT.md) | Open launch blockers |

**`PUBLIC_COMMERCIAL_LAUNCH` is `BLOCKED`.** Production-grade code and public commercial
launch are two separate decisions, and only the first is an engineering matter.
