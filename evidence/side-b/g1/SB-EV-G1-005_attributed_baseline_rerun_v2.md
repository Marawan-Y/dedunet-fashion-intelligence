# Attributed Baseline Re-run — v2.0.0 (supersedes SB-EV-BOOT-001..005)

- Artifact ID: SB-EV-G1-005
- Version: 2.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `platform/poc/**`; SB-EV-ATTR-001; controller M1 task A
- Acceptance criteria: every available build, test and validator is re-run in **this** checkout; exact commands, full outputs and exit codes are preserved; Docker runs in an isolated project on non-colliding ports with container labels proving attribution; teardown is clean; unavailable capabilities are marked BLOCKED, never inferred.
- Validation procedure/result: executed 2026-08-01 in `C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack`; results below.
- Evidence path: this file
- Readiness status: AUTOMATED-TESTED (backend, validators, Docker build/runtime) / BLOCKED (mobile)
- Downstream consumer: controller M1 review; SB-AR-B2-001; gate G1
- Remaining risks/next action: mobile remains BLOCKED and untested; local Python is 3.14 while the image is 3.12; there is still no isolated `.venv` or dependency lock.

## 0. Attribution and supersession

This artifact exists because SB-EV-BOOT-001..005 record a working directory of
`C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack`, not this tree.
The full finding, the byte-identical-copy proof and the stale-bytecode mechanism are in
`evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md`. Those files are preserved
unmodified. This artifact supersedes them for this working tree.

Every command below was run from this tree with `PYTHONDONTWRITEBYTECODE=1` after purging
all `__pycache__` and `.pytest_cache` directories.

## 1. Toolchain

```text
WORKING DIRECTORY: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc

COMMAND: python --version
Python 3.14.4
EXIT_CODE: 0

COMMAND: python -c "import sys;print(sys.executable);print(sys.version)"
C:\Python314\python.exe
3.14.4 (tags/v3.14.4:23116f9, Apr  7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)]
EXIT_CODE: 0

COMMAND: python -m pip --version
pip 26.0.1 from C:\Python314\Lib\site-packages\pip (python 3.14)
EXIT_CODE: 0

COMMAND: docker --version
Docker version 29.6.1, build 8900f1d
EXIT_CODE: 0

COMMAND: docker compose version
Docker Compose version v5.3.0
EXIT_CODE: 0

COMMAND: node --version
v24.15.0
EXIT_CODE: 0
```

**Divergence recorded:** `SIDE_B_G0_EXECPLAN.md` §9 targets an isolated **Python 3.12** environment; `backend/Dockerfile` uses `python:3.12-slim`. All local execution in this cycle used the user-site **Python 3.14.4** installation, not a `.venv`. CI now runs a 3.12/3.13/3.14 matrix. Risk SB-RISK-B2-001 remains open until a lockfile and isolated environment exist.

## 2. Backend suite

```text
WORKING DIRECTORY: ...\platform\poc\backend
COMMAND: python -m pytest -q -p no:cacheprovider

.....................................................                    [100%]
============================== warnings summary ===============================
..\..\..\..\..\..\AppData\Roaming\Python\Python314\site-packages\fastapi\testclient.py:1
  ...StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
53 passed, 1 warning in 2.21s
EXIT_CODE: 0
```

Controller baseline was `17 passed`. This cycle added 36 tests (money integrity, admin security, additional negative activation cases) and one `conftest.py` fixture-protection guard.

## 3. Validators

```text
WORKING DIRECTORY: ...\platform\poc

COMMAND: python scripts/validate_product_data.py
Validated 3 products and 9 unique SKUs
Authoritative prices (integer minor units): prod-nile-tee-001=5900 EUR, prod-desert-abaya-001=13900 EUR, prod-cairo-shirt-001=8900 EUR
EXIT_CODE: 0
```

```text
COMMAND: python scripts/validate_candidate_data.py
{
  "schema_version": "0.1.0",
  "candidate_count": 1,
  "synthetic_fixture_count": 1,
  "assessment": "current_state",
  "current_state_valid": true,
  "sellable_public_eligible": false,
  "errors": []
}
EXIT_CODE: 0
```

```text
COMMAND: python scripts/validate_candidate_data.py --assess-sellable
{
  "schema_version": "0.1.0",
  "candidate_count": 1,
  "synthetic_fixture_count": 1,
  "assessment": "sellable_public",
  "current_state_valid": true,
  "sellable_public_eligible": false,
  "errors": [
    {"code": "SYNTHETIC_CANNOT_ACTIVATE", "field": "synthetic_fixture", "message": "synthetic fixtures cannot become sellable or public"},
    {"code": "MISSING_REQUIRED_FIELD", "field": "style_code", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "fibre_composition", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "country_of_origin", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "care_instructions", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "measurement_set_id", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "price", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "merchant_identity_id", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "importer_responsible_operator_id", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "withdrawal_return_policy_id", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "delivery_promise_id", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "batch", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "assets", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "warehouse_location_id", ...},
    {"code": "MISSING_REQUIRED_FIELD", "field": "approved_by", ...},
    {"code": "MISSING_OPERATOR", "field": "importer_responsible_operator_id", ...},
    {"code": "MISSING_EVIDENCE", "field": "fibre_composition", ...},
    {"code": "MISSING_EVIDENCE", "field": "country_of_origin", ...},
    {"code": "MISSING_EVIDENCE", "field": "care_instructions", ...},
    {"code": "MISSING_EVIDENCE", "field": "measurement_set_id", ...},
    {"code": "MISSING_EVIDENCE", "field": "importer_responsible_operator_id", ...},
    {"code": "MISSING_EVIDENCE", "field": "withdrawal_return_policy_id", ...},
    {"code": "MISSING_EVIDENCE", "field": "delivery_promise_id", ...},
    {"code": "MISSING_EVIDENCE", "field": "target_market_codes", ...},
    {"code": "BATCH_NOT_RELEASED", "field": "batch.qc_release_status", ...},
    {"code": "UNAPPROVED_PRICE", "field": "price", ...},
    {"code": "ACTIVATION_BLOCKED", "field": "lifecycle_status", "message": "sellable/public activation is blocked"}
  ]
}
EXIT_CODE: 1
```

Non-zero exit is the required fail-closed outcome. CI asserts it.

```text
COMMAND: python -m compileall -q backend scripts
EXIT_CODE: 0
```

(Run before the cache purge; it produced only this-tree bytecode. Caches were purged afterwards.)

```text
COMMAND: python scripts/mutation_guard_check.py
MUTATIONS RUN: 19
DETECTED:      19
SURVIVED:      0
EXIT_CODE: 0
```

Full detail in SB-EV-G1-003.

## 4. Docker — isolated project, non-colliding ports

The prior BLOCKED result (SB-EV-BOOT-004) was caused by another checkout holding host ports 8000/3000. This was resolved by isolation, not by stopping anyone else's containers.

### 4.1 Pre-existing foreign containers (untouched)

```text
COMMAND: docker ps --all --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
CONTAINER ID   NAMES                                        STATUS                       PORTS
f8951802a1ea   fashion-commerce-platform-poc-storefront-1   Up About an hour             0.0.0.0:3000->80/tcp
f01e841e47da   fashion-commerce-platform-poc-api-1          Up About an hour (healthy)   0.0.0.0:8000->8000/tcp
...
EXIT_CODE: 0
```

These belong to another checkout. They were never stopped, removed or modified.

### 4.2 Configuration render

```text
WORKING DIRECTORY: ...\platform\poc
COMMAND: docker compose config
name: fashion-commerce-codex-poc
services:
  api:
    build:
      context: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend
    ports:
      - {target: 8000, published: "18000"}
    volumes:
      - bind C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend\data -> /app/data
  storefront:
    build:
      context: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\storefront
    ports:
      - {target: 80, published: "13000"}
networks:
  default:
    name: fashion-commerce-codex-poc_default
EXIT_CODE: 0
```

All build contexts resolve inside **this** tree.

### 4.3 Build

```text
COMMAND: docker compose build
#7  [api internal] load metadata for docker.io/library/python:3.12-slim   DONE 2.7s
#4  [storefront internal] load metadata for docker.io/library/nginx:1.27-alpine  DONE 2.8s
#20 naming to docker.io/library/fashion-commerce-codex-poc-storefront:latest  DONE 1.1s
#21 naming to docker.io/library/fashion-commerce-codex-poc-api:latest         DONE 1.0s
 Image fashion-commerce-codex-poc-storefront Built
 Image fashion-commerce-codex-poc-api Built
EXIT_CODE: 0
```

### 4.4 Isolated runtime

```text
COMMAND: API_PORT=18100 STOREFRONT_PORT=13100 docker compose -p sb-g1-m1-final up --build --detach
 Image sb-g1-m1-final-api Built
 Image sb-g1-m1-final-storefront Built
 Network sb-g1-m1-final_default Created
 Container sb-g1-m1-final-api-1 Started
 Container sb-g1-m1-final-api-1 Healthy
 Container sb-g1-m1-final-storefront-1 Started
EXIT_CODE: 0

COMMAND: docker compose -p sb-g1-m1-final ps
NAME                          STATUS                    PORTS
sb-g1-m1-final-api-1          Up 11 seconds (healthy)   0.0.0.0:18100->8000/tcp
sb-g1-m1-final-storefront-1   Up                        0.0.0.0:13100->80/tcp
EXIT_CODE: 0
```

### 4.5 Container attribution (this is what makes the smoke checks admissible)

```text
COMMAND: docker inspect --format '{{.Name}} | project={{index .Config.Labels "com.docker.compose.project"}} | working_dir={{index .Config.Labels "com.docker.compose.project.working_dir"}} | config_files={{index .Config.Labels "com.docker.compose.project.config_files"}}' sb-g1-m1-isolated-api-1 sb-g1-m1-isolated-storefront-1

/sb-g1-m1-isolated-api-1 | project=sb-g1-m1-isolated | working_dir=C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc | config_files=C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\docker-compose.yml
/sb-g1-m1-isolated-storefront-1 | project=sb-g1-m1-isolated | working_dir=C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc | config_files=C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\docker-compose.yml
EXIT_CODE: 0
```

`working_dir` and `config_files` resolve to **this** checkout. The same labels apply to the `sb-g1-m1-final` project used for §4.6.

### 4.6 HTTP smoke checks against the attributed containers

```text
--- GET http://127.0.0.1:18100/health
HTTP_STATUS: 200
BODY: {"status":"ok","environment":"development"}

--- GET http://127.0.0.1:18100/api/v1/products
HTTP_STATUS: 200
BODY: 3 products; each carries "price_minor_units": 5900 / 13900 / 8900, "currency":"EUR"
      and a derived "price_display":"59.00" / "139.00" / "89.00". No `price_eur` field.

--- GET http://127.0.0.1:18100/api/v1/products/nile-calligraphy-oversized-tee
HTTP_STATUS: 200

--- GET http://127.0.0.1:18100/api/v1/candidate-products
HTTP_STATUS: 200
BODY: 1 candidate; synthetic_fixture=true, lifecycle_status="candidate",
      publication_status="preview", price=null, approved_claims=[], all opening_stock=0

--- GET http://127.0.0.1:18100/api/v1/candidate-products/VS-TEE-001/activation
HTTP_STATUS: 200
BODY: {"eligible": false, "errors": [27 activation errors]}   <- fails closed over HTTP

--- POST http://127.0.0.1:18100/api/v1/orders/quote  {"items":[{"sku":"ORG01-TEE-NILE-BLK-M","quantity":1}],"destination_country":"DE"}
HTTP_STATUS: 200
BODY: {"currency":"EUR","subtotal_minor_units":5900,"shipping_minor_units":890,
       "total_minor_units":6790, "subtotal_display":"59.00","shipping_display":"8.90","total_display":"67.90", ...}

--- POST http://127.0.0.1:18100/api/v1/stylist/recommend  {"budget_minor_units":16000,...}
HTTP_STATUS: 200
BODY: {"product_ids":["prod-nile-tee-001","prod-cairo-shirt-001"],"total_minor_units":14800,
       "currency":"EUR","total_display":"148.00"}

--- POST http://127.0.0.1:18100/api/v1/orders/quote  (float quantity injection: 1.5)
HTTP_STATUS: 422        <- strict integer contract rejects it

--- POST http://127.0.0.1:18100/api/v1/admin/products  X-Admin-Token: change-me
HTTP_STATUS: 401        <- container .env sets a non-placeholder token, so this is a mismatch

--- GET http://127.0.0.1:13100/  (storefront)
HTTP_STATUS: 200
BODY: <title>Synthetic Fashion Candidate PoC</title> ... "SYNTHETIC FIXTURES / NON-PUBLIC / LOCAL"
```

Unsafe-default guard proven at runtime with a one-off container configured with the placeholder token:

```text
COMMAND: docker run --rm -e APP_ENV=production -e ADMIN_API_TOKEN=change-me -p 18200:8000 -d --name sb-g1-m1-unsafe-probe sb-g1-m1-final-api
EXIT_CODE: 0
--- POST http://127.0.0.1:18200/api/v1/admin/products  X-Admin-Token: change-me
HTTP_STATUS: 503        <- admin API disabled while a placeholder credential is configured
COMMAND: docker stop sb-g1-m1-unsafe-probe
EXIT_CODE: 0
```

### 4.7 Container logs

```text
COMMAND: docker compose -p sb-g1-m1-final logs --no-color api --tail 25
api-1  | INFO:     Started server process [1]
api-1  | INFO:     Application startup complete.
api-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
api-1  | INFO:     172.21.0.1:52784 - "GET /health HTTP/1.1" 200 OK
api-1  | INFO:     172.21.0.1:52784 - "GET /api/v1/products HTTP/1.1" 200 OK
api-1  | INFO:     172.21.0.1:52784 - "POST /api/v1/orders/quote HTTP/1.1" 200 OK
api-1  | INFO:     172.21.0.1:52784 - "POST /api/v1/stylist/recommend HTTP/1.1" 200 OK
api-1  | INFO:     172.21.0.1:52784 - "POST /api/v1/orders/quote HTTP/1.1" 422 Unprocessable Entity
api-1  | INFO:     172.21.0.1:52784 - "POST /api/v1/admin/products HTTP/1.1" 401 Unauthorized
api-1  | INFO:     127.0.0.1:... - "GET /health HTTP/1.1" 200 OK      (healthcheck probes)
EXIT_CODE: 0
```

Storefront (nginx 1.27.5) served `GET / HTTP/1.1 200 2280` and started 8 workers without error.

### 4.8 Teardown

```text
COMMAND: docker compose -p sb-g1-m1-final down
 Container sb-g1-m1-final-storefront-1 Removed
 Container sb-g1-m1-final-api-1 Removed
 Network sb-g1-m1-final_default Removed
EXIT_CODE: 0
```

The earlier `sb-g1-m1-isolated` project was torn down identically. Foreign containers on 8000/3000 were verified still running and untouched afterwards.

### 4.9 Fixture integrity after Docker runtime (bind mount is read-write)

```text
COMMAND: sha256sum backend/data/products.json
536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
EXIT_CODE: 0
```

Unchanged.

## 5. Docker availability

Docker **is** available in this environment. No part of task A is BLOCKED on Docker.

## 6. Mobile — BLOCKED (not re-run)

`SB-EV-BOOT-003` recorded a peer-dependency conflict in `platform/poc/mobile`. That was **not** retested this cycle: resolving it requires an approved dependency change, and no Expo build, emulator or device result exists.

- Status: **BLOCKED**
- Evidence required: successful `npm install`, `npx tsc --noEmit`, and an Expo export/build on a pinned SDK.
- What was done: `mobile/App.tsx` was updated for the money contract (integer minor units) and its default API base corrected from `:8000` to `:18000`. This is a **source change only**. It has not been compiled, type-checked or run. No mobile claim is made.

## 7. What this evidence does not prove

Local Docker Compose on synthetic fixtures is not a deployment. Nothing here demonstrates production infrastructure, TLS, secrets management, persistence, backups, monitoring, payment, tax, customs, carrier, identity or app-store status. The PoC must not be exposed publicly.
