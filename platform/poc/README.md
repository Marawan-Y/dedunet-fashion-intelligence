# Fashion Commerce Platform — Proof of Concept

This repository is a vertical slice for a premium Egyptian-cotton fashion brand selling to Europe. It proves that one product master can serve a web storefront, a mobile application, inventory visibility, order quoting and an AI-style recommendation flow.

## What is included

- FastAPI catalog API with validated product/variant schemas
- Static storefront connected to the API
- Expo mobile source connected to the same API
- Rule-based stylist that can later be replaced with evaluated AI ranking
- Product data validation and sample master-data templates
- Docker Compose for the web PoC
- Backend tests and GitHub Actions CI

## What is deliberately not production-ready

Payments, VAT, customs, identity, database transactions, warehouse reservations, carrier labels, refunds, legal pages, image hosting and generative AI are not implemented. These depend on the final merchant/importer model and business policies. Do not expose the PoC publicly as a real shop.

Known open launch blockers, with exact locations and remediation, are in
`docs/side-b/SIDE_B_LAUNCH_BLOCKER_AUDIT.md`: stored XSS in the storefront,
non-transactional inventory/catalog persistence, and secrets handling. The admin gate is a
fail-closed PoC control, **not** an authentication system.

## Money contract (breaking change)

Authoritative monetary values are **integer minor units**. EUR 59.00 is `5900`.

- The API emits `price_minor_units` + `currency` (authoritative) and
  `price_display` / `subtotal_display` / `total_display` (derived, presentation only).
- `price_eur` and `total_eur` no longer exist on the wire.
- A binary `float` is rejected at every money boundary; it is never rounded or coerced.
- Full rules: `docs/side-b/SIDE_B_MONEY_CONTRACT.md` (SB-AR-B3-003 v2.0.0).

## Run the web PoC

Prerequisites: Docker Desktop or Docker Engine with Compose.

```bash
cp .env.example .env
# Set a unique ADMIN_API_TOKEN. While the placeholder value is configured, the admin
# API returns HTTP 503 in every environment.
docker compose up --build
```

Open (default host ports 18000/13000, overridable via `API_PORT` / `STOREFRONT_PORT`):
- Storefront: http://localhost:13000
- API docs: http://localhost:18000/docs
- Health: http://localhost:18000/health

If another checkout already holds those host ports, run an isolated instance rather than
stopping someone else's stack:

```bash
API_PORT=18100 STOREFRONT_PORT=13100 docker compose -p my-isolated-poc up --build --detach
docker compose -p my-isolated-poc down
```

## Run backend tests locally

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
```

Those two flags are not cosmetic. Bytecode caches copied between checkouts have previously
been executed in the wrong tree, because Python validates a `.pyc` against source mtime and
size — both preserved by a plain file copy. Never ship `__pycache__` or `.pytest_cache`.

## Validate data

```bash
python scripts/validate_product_data.py                      # exits 0
python scripts/validate_candidate_data.py                    # exits 0 (current state valid)
python scripts/validate_candidate_data.py --assess-sellable  # exits NON-ZERO by design
```

The last command **must** exit non-zero: the synthetic candidate can never be eligible for
sellable/public activation. A zero exit there is a defect.

## Verify that the negative tests actually guard

```bash
python scripts/mutation_guard_check.py
```

This removes one guard at a time from the source, asserts that the test claiming to guard
it FAILS, and restores the file. Exit 0 means every guard removal was detected; exit 1
means some test does not actually guard its rule.

## Preserved sample fixtures

`backend/data/products.json` and `backend/data/candidate_products.json` are preserved
sample fixtures. `backend/tests/conftest.py` fails the test run if any test changes them.

```text
sha256(products.json)           = 536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
sha256(candidate_products.json) = 7f052e4c8d75302695faa23b44efa7ed4e2f28ad64aaff9746d0109d8dab8323
```

## Demo script

1. Show the three catalog products on the storefront.
2. Explain that every size/color variant has a unique SKU and stock value.
3. Submit the AI Stylist form with a budget and preferences.
4. Open `/docs` and call the quote endpoint using a real SKU.
5. Change a product in `backend/data/products.json`, validate it, and restart the API.
   Restore the file afterwards — the checksums above are asserted by CI.
6. Show the Expo app source consuming the same API. Note: the mobile package is
   **BLOCKED** (peer-dependency conflict) and has never been built or run.
7. Show a candidate that cannot be activated:
   `GET /api/v1/candidate-products/VS-TEE-001/activation` returns `eligible: false` with
   27 blocking errors.

## Production migration

1. Replace JSON persistence with PostgreSQL and migrations.
2. Introduce an event-driven order/inventory model with idempotent payment and carrier webhooks.
3. Use hosted payment UI so raw card data never reaches the platform.
4. Add EU tax, invoice, customs and return rules based on the chosen merchant/importer structure.
5. Add object storage/CDN, authentication, role-based access, secrets management and audit logging.
6. Replace the deterministic recommender only after event tracking, consent, evaluation data and safety/privacy controls exist.
7. Build a Next.js storefront and production Expo application against versioned API contracts.

The detailed governance, dependencies, roadmaps, checklists and compliance baseline are in the accompanying Project Setup Book.
