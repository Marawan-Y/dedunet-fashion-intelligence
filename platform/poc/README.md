# Fashion Commerce Platform — MERET

A working, locally runnable commerce platform for **MERET**, an entirely fictional premium
fashion brand used to exercise and demonstrate the system.

> **Nothing here is real.** MERET is not a company. Every product, material, origin, price,
> customer, order and support case is fabricated. Payments run against a sandbox adapter; no card
> is charged and nothing is fulfilled in the physical world. This build is **not** approved for
> public deployment — see `KNOWN_LIMITATIONS.md`.

---

## What actually works

Verified by executed tests and by driving both UIs in a browser:

| Capability | State |
|---|---|
| Catalogue, variants, stock visibility, search, filter, sort | VERIFIED |
| Customer registration, login, RBAC, session tokens | VERIFIED |
| Cart, quote, VAT-inclusive pricing, promotions, shipping threshold | VERIFIED |
| Checkout with sandbox payment, idempotent replay | VERIFIED |
| Atomic stock reservation (no overselling under concurrency) | VERIFIED |
| Orders, admin fulfilment, shipment tracking | VERIFIED |
| Cancellation, returns, refunds, restock | VERIFIED |
| Notifications (transactional outbox), analytics events, audit log | VERIFIED |
| Customer data export and erasure | VERIFIED |
| Operations portal (orders, inventory, product creation) | VERIFIED |
| AI stylist (deterministic, catalogue-grounded) | VERIFIED |
| Structured logs, correlation IDs, health and readiness probes | VERIFIED |
| Migrations (apply and reverse) | VERIFIED |
| Docker Compose stack (build, migrate, seed, serve, purchase) | VERIFIED |
| Mobile applications | **BLOCKED** — peer-dependency conflict, never built or run |
| CI pipeline | **NOT EXECUTED** — no runner available in this environment |

---

## Quick start

Requires Python 3.12+ (developed and tested on 3.14). No external services needed.

```bash
cd platform/poc/backend
python -m pip install -r requirements.txt

# Apply migrations and load the fictional MERET dataset. Safe to re-run.
python manage.py bootstrap

# Terminal 1 — API on :18000
APP_ENV=development \
CORS_ORIGINS="http://localhost:13000,http://127.0.0.1:13000" \
python -m uvicorn app.main:app --port 18000

# Terminal 2 — static clients on :13000, served from platform/poc
cd .. && python -m http.server 13000 --bind 127.0.0.1
```

| Surface | URL |
|---|---|
| Storefront | <http://127.0.0.1:13000/storefront/> |
| Operations portal | <http://127.0.0.1:13000/admin/> |
| API docs (Swagger) | <http://127.0.0.1:18000/docs> |
| Readiness probe | <http://127.0.0.1:18000/ready> |

**Demonstration accounts** (fictional, local database only):

| Role | Email | Password |
|---|---|---|
| Customer | `customer@meret.example` | `demo-password-123` |
| Administrator | `admin@meret.example` | `demo-password-123` |

Sandbox payment outcome is chosen at checkout: **succeeds**, **declined**, **provider error**.

> `CORS_ORIGINS` must list the exact origin you browse from. `localhost` and `127.0.0.1` are
> different origins to a browser, and the application does not auto-load `.env`.

### Docker alternative (verified)

```bash
cp .env.example .env
# Set a unique ADMIN_API_TOKEN. While the placeholder value is configured, the legacy
# admin API returns HTTP 503 in every environment.
docker compose up --build
```

The API container applies migrations and seeds the fictional dataset on start, so a plain
`up` yields a working store. Both steps are idempotent, so restarting neither fails nor
duplicates data. The database lives in the `commerce-db` volume, not in `backend/data`, so
it cannot touch the checksum-protected fixtures (which are mounted read-only).

| Surface | URL |
|---|---|
| Storefront | <http://localhost:13000/> (redirects to `/storefront/`) |
| Operations portal | <http://localhost:13000/admin/> |
| API | <http://localhost:18000/docs> |

The compose healthcheck probes `/ready`, not `/health`, so the storefront will not start
against an API whose database is unreachable.

If another checkout already holds those host ports, run an isolated instance rather than
stopping someone else's stack:

```bash
API_PORT=18100 STOREFRONT_PORT=13100 docker compose -p my-isolated-poc up --build --detach
docker compose -p my-isolated-poc down
```

---

## Repository map

```
platform/poc/
├── backend/
│   ├── app/
│   │   ├── commerce/          the commerce domain
│   │   │   ├── db.py          engine, session, declarative base
│   │   │   ├── models.py      ORM models; money is integer minor units
│   │   │   ├── security.py    PBKDF2 hashing + HMAC session tokens
│   │   │   ├── inventory.py   atomic reservation (anti-overselling)
│   │   │   ├── pricing.py     discounts, shipping, VAT extraction
│   │   │   ├── payments.py    gateway Protocol + sandbox adapter
│   │   │   ├── services.py    orchestration and transactions
│   │   │   ├── api.py         HTTP routes
│   │   │   └── seed.py        fictional MERET dataset
│   │   ├── main.py            app, middleware, health/ready, legacy PoC routes
│   │   ├── money.py           money primitives (binary floats rejected)
│   │   └── candidate_activation.py   evidence-gated product activation
│   ├── migrations/            Alembic
│   ├── tests/                 81 tests
│   └── manage.py              migrate / seed / bootstrap / export-openapi / check
├── storefront/                customer web client
├── admin/                     operations portal
├── docs/api/openapi.json      exported API contract
└── scripts/                   validators and the guard-mutation harness
```

Layering is one-directional: `api → services → {inventory, pricing, payments} → models → db`.
The rule modules never import `api` or `services`, so each is unit-testable without HTTP.

---

## Testing

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider   # 81 tests

cd ..
python scripts/validate_product_data.py                      # exits 0
python scripts/validate_candidate_data.py                    # exits 0
python scripts/validate_candidate_data.py --assess-sellable  # exits NON-ZERO by design
python scripts/mutation_guard_check.py                       # ~8 min
```

Those two pytest flags are not cosmetic. Bytecode caches copied between checkouts have
previously been executed in the wrong tree, because Python validates a `.pyc` against source
mtime and size — both preserved by a plain file copy. Never ship `__pycache__` or `.pytest_cache`.

`--assess-sellable` **must** exit non-zero: the synthetic candidate can never be eligible for
sellable/public activation. A zero exit there is a defect.

`mutation_guard_check.py` removes each safety guard one at a time and requires the suite to fail.
A guard whose removal nobody notices is not a guard.

### Preserved sample fixtures

`backend/tests/conftest.py` fails the run if any test changes these:

```text
sha256(products.json)           = 536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
sha256(candidate_products.json) = 7f052e4c8d75302695faa23b44efa7ed4e2f28ad64aaff9746d0109d8dab8323
```

---

## Design decisions worth knowing

**Money is integer minor units, everywhere.** €59.00 is `5900`. `price_eur` and `total_eur` do not
exist on the wire. Binary floats are rejected at every money boundary — never rounded or coerced —
and a test uses `0.70 × 3` to prove it. The browser clients format from integers by string
manipulation and never divide. Full rules: `docs/side-b/SIDE_B_MONEY_CONTRACT.md`.

**VAT is a component, not an addend.** Displayed prices are VAT-inclusive, as EU consumer retail
requires, so `tax = total − round(total ÷ (1 + rate))`. Adding VAT on top would change the price
the customer was shown. Rates are illustrative configuration and carry no tax advice.

**Stock reservation is one atomic SQL statement.** A `SELECT` followed by an `UPDATE` has a race
window between them, and that window is exactly where overselling happens. The check constraint
`reserved <= on_hand` is the backstop if the module is ever bypassed.

**Checkout reserves stock before authorizing payment.** Taking money for goods that are already
gone is worse than briefly holding stock for a payment that then declines.

**Orders copy their descriptive fields.** An order is a financial record; renaming a product must
never alter a past order.

**Erasure pseudonymizes; it does not delete orders.** Identifiers are removed and login disabled,
while the accounting history the business must be able to reconcile survives.

---

## Legacy proof-of-concept surface

The original fixture-backed endpoints (`/api/v1/products`, `/api/v1/candidate-products`,
`/api/v1/stylist/recommend`, `/api/v1/orders/quote`, `/api/v1/admin/products`) are preserved
unchanged, along with their evidence-gating behaviour and the `X-Admin-Token` control. The
commerce API is namespaced separately (`/api/v1/catalog`, `/cart`, `/checkout`, `/me`,
`/admin/catalog`, `/admin/orders`) because the two have different authentication models, and
sharing a path would let router registration order decide the effective guard.

Show a candidate that cannot be activated:
`GET /api/v1/candidate-products/VS-TEE-001/activation` returns `eligible: false` with 27 blocking
errors.

---

## Documentation

| Document | Contents |
|---|---|
| `../../docs/architecture/decisions/` | Architecture decision records |
| `docs/api/openapi.json` | Exported API contract |
| `docs/RUNBOOKS.md` | Operational runbooks |
| `docs/EXTERNAL_SERVICE_ACTIVATION.md` | Activating real providers |
| `KNOWN_LIMITATIONS.md` | What is deliberately not done, and why |
| `docs/side-b/SIDE_B_LAUNCH_BLOCKER_AUDIT.md` | Open launch blockers |
