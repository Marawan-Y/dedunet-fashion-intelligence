# Team-acceptance defect — admin API origin in staging

**Artifact ID:** EV-TA-001 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED` · **Date:** 2026-08-07
**Frozen baseline before acceptance:** `b7226cd`
**Reported by:** human acceptance testing, Test 3A
**Result:** `ACCEPTANCE_DEFECT_FIXED`

---

## 1. Human reproduction

The tester reported that <http://127.0.0.1:13080/admin/> loaded but showed **"Failed to
fetch"** and could not authenticate.

Reproduced before changing anything, on the frozen baseline:

| Probe | Result |
|---|---|
| `GET /admin/` | **200** — the page itself loads |
| `GET /admin/config.js` | **404** — no runtime configuration seam existed |
| scripts in the served markup | `brand.generated.js`, `admin.js` only |
| API base computed in the browser | **`http://127.0.0.1:18000`** |
| `GET :18000/ready` | **HTTP 000** — nothing is listening there |
| `GET :18080/ready` | **200** — the real staging API |
| login request from the page | **`FAILED: Failed to fetch`** |

The served `admin.js` line responsible:

```js
const API_BASE =
  window.FASHION_POC_API_BASE ?? `${window.location.protocol}//${window.location.hostname}:18000`;
```

So the portal asked a port nothing listens on, and the browser reported a transport
failure rather than an HTTP error — which is why the message was `Failed to fetch` and not
a status code.

## 2. Root cause

The storefront had already been given a runtime configuration seam
(`apps/web/config.js`, generated from the `API_BASE_URL` build argument, resolved by
`apps/web/media-url.js`). **The admin portal was never given one.** It resolved its API
inline, against a hard-coded development port, with no `config.js` in its markup and no
generation step in the image build.

Staging publishes the API on **18080** (`API_PORT` in `.env.staging`); the admin assumed
**18000**. Nothing reconciled the two.

This is the same class of defect as the two closed earlier in this programme: the
application code was correct in isolation and every in-process test passed, because a test
can set a variable freely and a deployed bundle cannot. The gap was in deployment
configuration, not in logic.

## 3. Correction

The narrowest architecture-consistent fix: give the admin the **same mechanism** the
storefront already proves, rather than invent a second one.

| File | Change |
|---|---|
| `apps/admin/api-config.js` | **new** — resolves the API origin, validates it, exposes `DEV_API_PORT`. UMD, so the rules are unit-testable off-browser. |
| `apps/admin/config.js` | **new** — committed copy configures nothing; replaced at build time. |
| `apps/admin/index.html` | loads `config.js` then `api-config.js` before `admin.js`. |
| `apps/admin/admin.js` | `const API_BASE = window.DedunetAdminConfig.apiBase();` — the inline port literal is gone. |
| `apps/web/Dockerfile` | the single `API_BASE_URL` argument now generates `config.js` for **both** surfaces. |
| `services/commerce-api/tests/test_admin_api_config.py` | **new** — 19 tests. |
| `scripts/validation/mutation_guard_check.py` | **new** mutation `M71`. |

Resolution precedence is deliberately **identical** to the storefront's:

1. `FASHION_POC_API_BASE` — the legacy manual override, still honoured
2. `DEDUNET_API_BASE` — what the generated `config.js` sets
3. this page's `protocol//hostname:18000` — the documented development default

A test asserts the two surfaces agree on both the precedence and the development port, so
they cannot drift into disagreeing about where the API lives.

Design notes worth stating:

* **`hostname`, not `host`** — the API is a different service on a different port; `host`
  would carry the storefront's port across. Reading it from the page preserves whichever of
  `localhost` / `127.0.0.1` the operator actually browsed with, which matters because they
  are distinct origins to CORS.
* **Malformed configuration is rejected, not ignored.** A configured value must be an
  absolute `http(s)` origin. Silently falling back after a typo is how a portal ends up
  pointing at the wrong host *while looking configured* — precisely this defect.
* **Build time, not run time.** The web container has a read-only root filesystem, so
  nothing may write into the served directory after start.
* **No deployment port in application logic.** `18080` appears nowhere in code; `18000`
  appears once, as the named `DEV_API_PORT` constant. A test enforces both.

Nothing else was touched: no storefront behaviour, no mobile behaviour, no authentication,
no administrator credentials, no commerce mode, no public-commerce activation.

## 4. Test evidence

`tests/test_admin_api_config.py` — **19 passed**. It runs the real module through Node,
because asserting on the *source text* of a URL builder proves nothing about the URLs it
builds, which is the entire shape of this defect.

| Required property | Test |
|---|---|
| runtime config overrides the fallback | `test_runtime_config_overrides_the_development_fallback` |
| staging resolves to the staging API origin | `test_staging_configuration_resolves_to_the_staging_api_origin` |
| split-origin admin/API works | `test_split_origin_admin_and_api` |
| missing config uses only the documented fallback | `test_missing_configuration_uses_only_the_documented_development_fallback` |
| malformed config fails clearly or is rejected | `test_malformed_configuration_is_rejected_clearly` (7 cases) |
| login request targets the configured base | `test_admin_login_request_targets_the_configured_api_base` |
| no staging port scattered through logic | `test_no_deployment_port_is_scattered_through_admin_logic` |

Plus: `localhost` and `127.0.0.1` each preserved with no https downgrade, trailing-slash
normalisation, script ordering, the committed config pinning nothing, cross-surface
precedence agreement, and the image build generating config for both surfaces.

### Mutation

| Mutation | Attack | Guarding test | Outcome |
|---|---|---|---|
| `M71_admin_honours_runtime_api_configuration` | make `api-config.js` ignore the configured value | `test_staging_configuration_resolves_to_the_staging_api_origin` | **DETECTED**, exit 1 |

Failure reason — the mutation reproduces the original defect exactly:

```
assert 'http://127.0.0.1:18000' == 'http://127.0.0.1:18080'
```

Not an import error, not a syntax error, not an unrelated test.

Two false positives in my own test were found and fixed while writing it: naive comment
stripping flagged a prose mention of `:18000`, and the validator's error-message example
literally contained `18080`. The example now carries no port, and the test strips block
comments properly. Recorded because a test that passes for the wrong reason is worse than
no test.

## 5. Staging verification

Only the `web` image was rebuilt. The API image, database and worker were untouched.

Generated at build: `storefront API base: http://127.0.0.1:18080` and
`admin API base: http://127.0.0.1:18080`.

| # | Check | Result |
|---|---|---|
| 1 | `/admin/` loads | **200**, `readyState: complete` |
| 2 | no "Failed to fetch" before authentication | **none present** |
| 3 | login request reaches the API on 18080 | resolved base `http://127.0.0.1:18080`; endpoint returned a structured **401 `invalid credentials`** for deliberately wrong credentials — an HTTP response, not a transport failure |
| 4 | valid local admin login succeeds | **HTTP 200**, `role=admin`, token issued, `Access-Control-Allow-Origin: http://127.0.0.1:13080` |
| 5 | orders view loads | **HTTP 200** (0 orders in this staging database) |
| 6 | inventory / catalogue loads | **HTTP 200**, 6 products, 5 DEDUNET |
| 7 | DEDUNET products appear | `DDN-OS01, DDN-SC01, DDN-SH01, DDN-TR01, DDN-TS01` |
| 8 | DDN-TS01 appears | 18 variants, 4 media |
| 9 | prototype / evidence state truthful | `sellable=False`, stock `0`, `prototype_unavailable`, origin `UNVERIFIED`, legal `LEGAL_CLEARANCE_PENDING` |
| 10 | commerce mode | **`COMMERCE_TEST_MODE`** — see discrepancy below |
| 11 | storefront still blocks purchase | cart-add **409** *"The Source Tee is not available for purchase"* |
| 12 | `/ready` | **200** |

The served admin bundle now contains `config.js` and `api-config.js`, and the served
`admin.js` line reads `const API_BASE = window.DedunetAdminConfig.apiBase();`.

### ⚠️ Discrepancy on verification point 10

The brief expected *"Preview mode remains BRAND_PREVIEW_MODE"*. **Staging is not in preview
mode and was not before this fix.** `COMMERCE_MODE` is empty in `.env.staging`, so
`modes.DEFAULT_MODE` applies, which is `COMMERCE_TEST_MODE`.

This is reported rather than adjusted, because requirement 10 of the brief is *"Do not
change commerce mode."* The two instructions cannot both be satisfied, so the mode was left
exactly as found.

Purchase is nonetheless blocked in the current mode, by the product-state gate rather than
the mode gate: DDN-TS01 is `sellable=False` with zero stock, and cart-add returns 409.
Preview-mode blocking itself was verified separately and independently — Phase B **14/14**
against a `BRAND_PREVIEW_MODE` API, and default product truth **13/13**. This fix cannot
affect either: it changes only which origin the admin browser bundle calls.

### Administrator credentials

`.env.staging` ships `ADMIN_BOOTSTRAP_EMAIL` and `ADMIN_BOOTSTRAP_PASSWORD` **blank**, and
the pre-existing `ops@dedunet.example` administrator's password is not stored anywhere in
the repository. It was neither read, reset nor changed.

Point 4 was verified with a **separate, clearly-labelled local account**,
`admin.acceptance.local@dedunet.example`, created through the documented
`manage.py create-admin` flow with a generated password held only in a scratch file, never
printed and never committed. **The account was deleted after verification** so no extra
privileged account is left behind. No password appears in this document, in any commit, or
in any command argument.

## 6. Regression

| Check | Result |
|---|---|
| Targeted admin configuration tests | **19 passed** |
| Frontend security tests (web + admin) | **6 passed** |
| Web resolver + gallery (unchanged surfaces) | **23 passed** |
| Backend SQLite full suite | **326 passed, 2 skipped** |
| Backend PostgreSQL full suite | **328 passed** |
| Mutation harness | **69 run, 69 detected, 0 survived** (68 inherited + `M71`) |
| OpenAPI drift | **NO_DRIFT** |
| Staging readiness | `/ready` 200, `/health` 200, `/storefront/` 200, `/admin/` 200 |
| Storefront preview smoke | Phase B **14/14** |
| Default product truth | Phase A **13/13** |
| Git status | clean |

Suite deltas are the 19 new admin configuration tests: SQLite `307 → 326`,
PostgreSQL `309 → 328`. No test was weakened, skipped or relaxed; the two skips are the
same PostgreSQL-only pair as before.

## 7. Rollback

```bash
git revert <this commit>
docker compose -f docker-compose.staging.yml --env-file .env.staging build web
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d web
```

Reverting restores the defect — the admin portal will again resolve `:18000` and fail with
"Failed to fetch" in staging. Only the `web` image needs rebuilding; no API image,
database, schema or migration is involved, and no committed fixture changed.

## 8. Commit

`fix: configure admin API origin in staging` — hash recorded in the final response and in
the commit itself. One focused commit; verified milestone history was not rewritten.
