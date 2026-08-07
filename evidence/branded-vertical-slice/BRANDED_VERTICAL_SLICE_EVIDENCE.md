# DEDUNET branded vertical slice — execution evidence

**Artifact ID:** EV-BVS-001 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED`
**Date:** 2026-08-07
**Result of this document:** `BRANDED_VERTICAL_SLICE_CONDITIONALLY_VERIFIED`

> **Superseded in part — this result is retained as the historical record.**
> This document's conditional result was accepted by the manager and is **not** rewritten.
> It was conditional on exactly three reproduced media defects, **L1, L2 and L3** (§6).
> Those three were closed by a subsequent focused milestone; see
> [`BRANDED_VERTICAL_SLICE_MEDIA_CLOSURE.md`](BRANDED_VERTICAL_SLICE_MEDIA_CLOSURE.md)
> (`EV-BVS-002`). Limitations **L4–L8** below remain open and were deliberately carried
> forward. Everything else recorded here was re-executed during that closure, not assumed.

Every number below was produced by executing a command in this repository. Nothing is
carried over from the continuation prompt or from an earlier evidence file without being
re-run. Where a claim could not be executed, it is named as a limitation rather than
softened.

---

## 1. Takeover

| Fact | Value |
|---|---|
| Git root | `C:/Users/User/Desktop/Claude/Fashion_Commerce_Codex_Multi_Agent_Pack` |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| Starting HEAD | `d6c6973` — *test: prepare DEDUNET branded vertical-slice fixtures* |
| Inherited verified integration commit | `66c3100` — present in history |
| Working tree at takeover | clean |
| Git remotes | none (CONFLICT-010, unchanged) |

The inherited partial commit `d6c6973` was preserved. Nothing was squashed, rewritten or
discarded, and no second repository was created.

### Inherited state, re-verified rather than assumed

| Claim | Method | Result |
|---|---|---|
| Side A package 54/54 checksums | `scripts/validation/verify_side_a_package.py` | 54/54 verified, 0 missing, 0 mismatched → `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| Normalized brand package no drift | `scripts/brand/build_brand_package.py --check` | `NORMALIZATION_VERIFIED` (nothing written) |
| 5 products / 62 variants / 62 SKUs / 18 media | brand check + import + database | 5 / 62 / 62 / 18 |
| Customer-facing legacy MERET/MERYT = 0 | word-boundary scan over all tracked text | **0** customer-facing |
| Public commerce blocked | `modes.current_mode()` refuses `PUBLIC_COMMERCE_MODE` | refused, executed |
| Phase A 13/13, Phase B 14/14 | re-run after the server change | 13/13 and 14/14 |

---

## 2. Proxy-header trust boundary

### 2.1 Reproduction — before any change

Executed against the documented development command,
`python -m uvicorn app.main:app --port 18300`, on the takeover commit:

```
control (no X-Forwarded-For)   401 x10 then 429 x6      limiter works
varied spoofed X-Forwarded-For 401 x16, never limited   limiter bypassed
malformed X-Forwarded-For      429, 401, 401, 429, 401
/ready after                   200
bypass_present                 true
```

The malformed row is itself diagnostic. `,,,` and `" , ,"` parse to nothing, so the real
loopback peer survives and is correctly limited (429). `not-an-ip`, `999.999.999.999` and
500 × `"a"` each became a *distinct client identity* and were not limited (401) — uvicorn
never checks that the value is an address.

### 2.2 Mechanism — read from the installed library, not inferred

uvicorn 0.35.0:

* `Config.__init__` defaults `proxy_headers=True`;
* `forwarded_allow_ips=None` resolves to `os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")`;
* `ProxyHeadersMiddleware.__call__` tests `client_host in self.trusted_hosts` and, for a
  trusted peer, sets `scope["client"] = (host, 0)` from the header.

That runs **before** any application code. `app/rate_limit.py` was never wrong — it reads
`request.client.host`, which the server had already replaced. The true peer is not
recoverable afterwards: the middleware overwrites it and the scope keeps no copy.

Why the existing suite could not have caught it: `fastapi.testclient.TestClient` builds
the ASGI scope itself and never installs that middleware. `tests/test_rate_limit.py`,
including `test_spoofed_forwarded_for_does_not_mint_a_fresh_bucket` and mutation `M22`,
was green throughout the period in which a real server was trivially bypassable.

### 2.3 Correction

Two layers, because a fix that lives only on a command line can be bypassed by a command line.

**Layer 1 — `services/commerce-api/app/server.py`.** The supported entrypoint. Passes
`proxy_headers=False` **and** `forwarded_allow_ips=[]` explicitly, in both modes, so no
uvicorn default decides this on any path. `TRUSTED_PROXY_MODE` defaults to `none`;
`explicit` refuses to start unless `TRUSTED_PROXY_IPS` (wildcard rejected),
`RATE_LIMIT_TRUSTED_PROXY_COUNT >= 1` and `TRUSTED_PROXY_NETWORK_BOUNDARY` are all set.
The resolved boundary is logged once at startup as a structured line.

**Layer 2 — `rate_limit._peer_was_rewritten_upstream`.** Detection is exact, not
heuristic: `ProxyHeadersMiddleware` cannot recover the forwarded client's source port and
writes a literal `port 0`, which a real TCP peer never has. Such requests share one
quarantine bucket, so a forger gains nothing and cannot exhaust a genuine client's bucket.

Every committed launch path now uses `app.server`: `Dockerfile` CMD,
`docker-compose.staging.yml` command, `README.md`, `docs/operations/RUNBOOKS.md`,
`apps/mobile/README.md`. Documented in `RUNBOOKS.md` **R12**.

**The exact safe startup command:**

```bash
python -m app.server --host 127.0.0.1 --port 18000
```

### 2.4 After the correction — same script, same command

```
control (no X-Forwarded-For)   401 x10 then 429 x6
varied spoofed X-Forwarded-For 429 x16
malformed X-Forwarded-For      429, 429, 429, 429, 429
/ready after                   200
bypass_present                 false
```

Startup line observed on the running process:

```json
{"event": "asgi_proxy_trust_boundary", "mode": "none", "proxy_headers": false,
 "forwarded_allow_ips": [], "trusted_proxy_hops": 0}
```

### 2.5 Local staging, re-verified after rebuild

`docker-compose.staging.yml` was rebuilt and restarted so it runs the corrected entrypoint.

| Check | Result |
|---|---|
| container command | `["python","-m","app.server","--host","0.0.0.0","--port","8000","--workers","1"]` |
| boundary line | `mode=none, proxy_headers=false, forwarded_allow_ips=[]` |
| control burst | `429` × 6 |
| varied spoofed XFF | `429` × 16 |
| malformed XFF | `429` × 5 |
| `/ready`, `/health` | 200, 200 |
| `bypass_present` | false |

**Staging was never compromised, and this is stated as a measurement, not a reassurance.**
Its uvicorn binds `0.0.0.0` and requests arrive from the Docker bridge, which is not in
`forwarded_allow_ips`, so the original bypass did not reproduce there before the fix
either. No claim of prior compromise is made anywhere in this milestone.

### 2.6 Regression coverage

`services/commerce-api/tests/test_proxy_boundary.py` — **18 tests**, all launching real
server processes over real sockets, because the defect is unreachable in-process.

Layer 1 (`test_supported_server_*`): the logged boundary is explicit; a burst reaches the
threshold; varied spoofed XFF mints no fresh bucket; the direct peer stays the limiter
identity whether or not a header is present; malformed headers do not crash; the first 429
carries a readable `Retry-After` and a correlation ID and is exposed cross-origin;
`/ready` is never throttled; registration has its own bucket.

Layer 2 (`test_unsafe_server_*`): a server started **with** `--proxy-headers
--forwarded-allow-ips 127.0.0.1` — the exact mistake being defended against — still cannot
be bypassed, and a forger cannot exhaust a direct client's bucket.

Future-proxy contract: unconfigured fails closed; a fully specified proxy is accepted;
each missing element is refused; wildcard trust is refused; an unknown mode is refused
rather than silently treated as `none`; `build_config` passes both settings.

---

## 3. Phase results

All phases drive the real API over HTTP. Mode changes are **real process restarts**, not
variable changes.

| Phase | Subject | Result |
|---|---|---|
| A | default product truth | **13/13** |
| B | `BRAND_PREVIEW_MODE` | **14/14** |
| C | synthetic test inventory | **28/28** |
| C.10 | preview blocks despite stored synthetic stock | **5/5** |
| D | customer commerce-test journey | **38/38** |
| E | administration and notifications | **26/26** |
| F | rate limiting | **7/7** · session **6/6** |
| H | return to preview | **9/9** |
| G | restore value parity | **20/20** · functional **20/20** |
| | **Total executed checks** | **186** |

Combined A + B = **27/27**, matching the inherited claim after re-execution.

### 3.1 Phase C — synthetic inventory

Selected product **DDN-TS01**, selected SKU **DDN-SRC-CAR-XS**, still valid.

Verified before loading: `stock_quantity = 0`, `sellable = false`,
`inventory_status = prototype_unavailable`, `origin_claim_status = UNVERIFIED`,
`legal_brand_status = LEGAL_CLEARANCE_PENDING`.

| Quantity milestone | Value |
|---|---|
| starting | **0** |
| loaded | **25** |
| after a repeated load (idempotency) | **25** — set, not accumulated |
| after cleanup | **0** |
| after reload for the journey | 25 |
| after final Phase H cleanup | **0** |

Refusals, each checked to have written nothing: without `--confirm-test-only`; in
`BRAND_PREVIEW_MODE`; in `PUBLIC_COMMERCE_MODE`. Only the selected SKU received stock; the
other 61 variants and the other four products stayed at zero with `prototype_unavailable`.
Origin, material, legal, media and evidence states were hashed before and after and are
unchanged. Synthetic stock is **typed** (`synthetic_test_stock`), never inferred from a
quantity. Nothing loads synthetic inventory at startup.

### 3.2 Phase D — customer journey

Selected variant **DDN-SRC-CAR-XS** at **7200 EUR minor units**, quantity 2.

* Cart created, token persisted, variant added, quantity raised to 3 then lowered to 2.
* Server-priced totals: subtotal 14400. VAT is **inclusive**
  (`total = subtotal − discount + shipping`; tax 2299 is a *component*), which is
  `pricing.py`'s documented EU consumer-retail model.
* **Decline** (`pm_decline`): HTTP 402, correct reason, **no successful order created**,
  cart **not** consumed, reserved stock released back to 25. The attempt is retained as a
  `cancelled` order — the audit trail of a real attempt, not a hidden failure.
* **Success** (`pm_success`) under a **distinct idempotency intent**: HTTP 201,
  `replayed=false` — the success is not a replay of the decline. Replaying the *same* key
  returns the same order number rather than creating a second order.
* `commerce_mode_at_checkout = COMMERCE_TEST_MODE`, `is_test_order = true`.
* Inventory moved exactly **25 → 23**; an over-quantity add was refused 409; no overselling.
* The converted cart is marked `converted` and a **new** token is issued for the next
  purchase.
* Order history and order detail both show the truthful state and mode.

### 3.3 Phase E — administration and notifications

Administrator sees the order, labels it `COMMERCE_TEST_MODE` / `is_test_order`, sees the
synthetic inventory classification, performs the approved transition to `shipped` with a
tracking number; the customer then sees `shipped` with the mode still truthful. The
DEDUNET catalogue carries external identity throughout and no legacy item leaks into it.

Notification lifecycle, observed in the database because an outbox is deliberately not a
customer-facing resource:

| Property | Value |
|---|---|
| subject | `[TEST ORDER] DEDUNET — your order FC-037F5FAF is confirmed` |
| stable key | `order_confirmation` |
| queued → final | `queued` → `sent` |
| attempts | 1 |
| channel | console |
| claim metadata after | `claim_token=""`, `claimed_at=NULL`, `claim_expires_at=NULL` |
| rows deleted | none |

Stale-worker fencing, erased-customer suppression and maximum-attempt behaviour remain
covered by mutations M32–M41 and M28/M30, all detected in this run.

**No inbox delivery is claimed.** `EXTERNAL_SMTP_DELIVERY_PENDING` is unchanged.

### 3.4 Phase F — rate limiting and session

Normal requests pass; a burst yields `401` ×10 then `429`; `Retry-After: 6` present and
listed in `Access-Control-Expose-Headers` alongside `X-Correlation-ID` and the
`X-RateLimit-*` headers, so a browser can honour it; varied spoofed `X-Forwarded-For`
produced **16/16 429** — no fresh buckets; `/ready` stayed 200 through the burst;
`/health` available; the notification worker was stopped and restarted and `/ready`
remained 200 throughout, confirming worker state does not affect API readiness.

Session: a forged token, an empty bearer, a forged signature with a valid shape, and a
missing session all return 401. Correlation IDs are present on unauthenticated calls.
The limiter was not weakened and no limit was raised.

### 3.5 Phase G — backup and isolated restore

| Step | Result |
|---|---|
| backup | `dedunet_slice-20260807T004046Z`, 61218 bytes, PostgreSQL custom format |
| SHA-256 | `bf60c0495fa14109be69e8dc547ae557bd42083d8197425ddede9a5fd7017491` |
| verified **before** restore | yes |
| restored into | `dedunet_slice_rehearsal` — a **new** database |
| migrations before parity | **none run**, so parity measures the dump |
| schema parity | `PASS` |
| value parity | 20/20 |
| restored functional | 20/20 |
| cleanup | rehearsal dropped; source `dedunet_slice` intact |

Preserved and compared **by value**, not by row count: 5 products, 62 variants, 62 unique
SKUs, 18 product-media rows, hashed origin/material/legal/media/evidence states,
`DDN-SRC-CAR-XS=synthetic_test_stock:23/0`, both customers, converted and open carts, both
orders with `COMMERCE_TEST_MODE`, order lines, reservations `RELEASED` and `COMMITTED`,
sandbox payments `DECLINED` and `AUTHORIZED`, both notifications `sent` with `attempts=1`
and no residual claim, migration revision `a7c31f9be402`, and identical indexes, foreign
keys, check constraints, unique constraints and primary keys.

Functional checks ran against an API served **from the restored database**: readiness,
catalogue, product media fetchable (200 × 4), customer and administrator authentication,
order read, test-order mode, notification read, an invalid state transition refused 409,
a write that commits and rolls back cleanly, and foreign-key and inventory constraint
enforcement.

`LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED`. This is a local rehearsal on a developer
machine. **No production disaster-recovery capability is claimed.**

### 3.6 Phase H — cleanup

Synthetic inventory removed through the approved command; selected SKU back to **0** and
`prototype_unavailable`; no DEDUNET variant carries synthetic stock; mode returned to
`BRAND_PREVIEW_MODE`; cart-add refused 409 naming brand preview; checkout blocked;
catalogue still lists 5 DEDUNET products; `/ready` and `/health` 200. Truthful test-order
evidence was retained deliberately — the order and its notification are the record of what
was verified. The rehearsal database was dropped; the temporary slice database and
container are development scaffolding outside the repository.

---

## 4. Regression suite

| Check | Result |
|---|---|
| Side A checksum verification | **54/54**, 0 missing, 0 mismatched |
| Normalized-brand drift | `NORMALIZATION_VERIFIED` (no drift) |
| SQLite full suite | **267 passed, 2 skipped** |
| PostgreSQL full suite | **269 passed** (the 2 SQLite skips are PostgreSQL-only) |
| SQLite + PostgreSQL concurrency | included in both suites above; pytest promotes warnings to errors, so an unhandled thread exception fails the run |
| Backend mutation harness | **61 run, 61 detected, 0 survived** (59 inherited + 2 added) |
| Mobile clean typecheck | `tsc --noEmit` clean |
| Mobile test suite | **117 passed**, 9 suites |
| Mobile mutation harness | **18/18 detected, 0 survived** |
| Mobile dependency matrix | `expo install --check` → up to date |
| Expo web export | succeeded, 230 modules |
| Web / admin client tests | covered by `tests/test_frontend_security.py` in the backend suite |
| OpenAPI export and drift | exported 30 paths; `git diff --exit-code` clean → **no drift** |
| Staging readiness | rebuilt, healthy, `/ready` and `/health` 200 |
| Rate-limit smoke | control 429×6 |
| Proxy-header spoofing test | spoofed 429×16, `bypass_present=false` |
| Notification-worker smoke | worker starts, console sender, API readiness unaffected by stop/start |
| Asset-serving smoke | **see limitation L1** |
| Preview-mode / commerce-test / order-provenance tests | in the backend suite; also executed live as Phases B, C, D |
| Secret scan | no `.env` in history; no `.env`/`.env.staging` tracked |
| Personal-data scan | no real emails, phone numbers or IBANs in tracked text (all matches are `.example` domains or npm `sha512` integrity hashes) |
| Active MERET/MERYT scan | **0 customer-facing**; 62 tracked-text hits, all documentation/evidence, the separately-classified legacy seed fixture, or tests that must name the strings they forbid |
| Preserved fixture checksums | both match the values CI asserts |
| Git cleanliness | clean at the final commit |

### Required visible counts

| Count | Required | Observed |
|---|---|---|
| DEDUNET products | 5 | **5** |
| DEDUNET variants | 62 | **62** |
| Unique DEDUNET SKUs | 62 | **62** |
| Product-media records | 18 | **18** |
| Active customer-facing MERET/MERYT | 0 | **0** |

---

## 5. Mutations

**61 mutations run, 61 detected, 0 survived.** All 59 inherited guards preserved and
re-verified; two added for the ASGI boundary, mutated **separately** so neither layer can
hide behind the other.

| Mutation | Guard | Expected failing test | Actual | Intended reason | Restored |
|---|---|---|---|---|---|
| `M62_asgi_proxy_headers_disabled_explicitly` | `app/server.py` states `proxy_headers=False` and an empty allowlist | `test_proxy_boundary.py::test_supported_server_states_its_proxy_boundary_explicitly` | **DETECTED**, exit 1 | `AssertionError: the ASGI server would interpret forwarded headers` / `assert True is False` | yes |
| `M63_rewritten_peer_is_not_trusted` | a header-asserted peer is quarantined | `test_proxy_boundary.py::test_unsafe_server_still_cannot_be_bypassed` | **DETECTED**, exit 1 | `varied X-Forwarded-For minted a fresh bucket per request: [401 × 16]` — the original bypass signature | yes |

Neither failed by import error, startup error, syntax error or an unrelated test. The full
suite was green before and after each (`267 passed, 2 skipped`).

M62 is detected by the boundary-line test and **not** by the end-to-end spoofing tests,
which correctly keep passing because layer 2 still holds. That is the intended behaviour
of defence in depth and is why M63 exists to prove layer 2 independently.

### Anchor repair

Adding the layer-2 quarantine changed the text `M22_xff_not_trusted_by_default` anchored
on, and the harness **refused to run** (`anchor matched 0 times`) rather than silently
skipping the mutation. The anchor was updated to the new four-line form and M22 re-verified
as **DETECTED**. This is the harness behaving exactly as required: it fails on missing
anchors.

---

## 6. Remaining limitations

**L1 — Brand and product media do not serve in any Docker deployment.** *Reproduced, not
fixed.* `_MEDIA_ROOT` resolves to `<repo>/packages/brand/assets`, but the API image build
context is `./services/commerce-api`, so `packages/` is not and cannot be in the image.
`docker exec … ls /app/packages` → *No such file or directory*; all five sampled brand and
product assets return `{"detail":"asset not found"}` on local staging. Media serves
correctly only from a full checkout on disk, which is where the original
"18/18 product media and 31/31 brand assets return 200" verification in `f17dad3` was
performed. **Pre-existing and unrelated to this milestone's correction** — the pre-change
poc image (built 2026-08-04) equally has no `/app/packages`. Fixing it means changing the
build context and the asset-root resolution together, which is a deployment change, not a
narrow correction. Unsafe-path refusals still behave correctly (traversal, directories,
dotfiles and missing files all 404).

**L2 — The web client does not render product media.** `apps/web/app.js` renders a
`card__media` / `pdp__media` div containing the first letter of the product name. This was
an explicit scope boundary of `f17dad3` ("Mobile gains the gallery"); the web gallery was
never built. Mobile renders all four images correctly, so **web and mobile do not agree on
media**, which is the one Phase D acceptance criterion not met.

**L3 — The web client's brand mark and favicon 404 in every split-origin topology.**
`apps/web/index.html` uses root-relative `/api/v1/media/assets/.../logo-primary.svg`, which
resolves against the *web* origin while the API is a different origin, and `nginx.conf` has
no proxy for `/api`. Measured 404 on both the local static origin and the shipped nginx
storefront (`:13080`). Mobile resolves the same assets against `API_BASE` and they load at
1200×1500. Narrow to fix, but left unfixed because L2 would leave web and mobile still
disagreeing, and a partial fix would change the appearance of the gap without closing it.

**L4 — `load-test-inventory` in `PUBLIC_COMMERCE_MODE` surfaces an uncaught traceback.**
`manage.py` catches `TestInventoryRefused` but not `CommerceModeError`, so this refusal
prints a stack trace where the other two print `{"result": "refused", …}`. It **fails
closed** — non-zero exit, nothing written, both asserted. Cosmetic.

**L5 — `orders.status` has no database-level validity constraint.** It is `varchar(15)`
with no enum type and no `CHECK`. `'not_a_real_status'` is rejected only for exceeding 15
characters; `'xx'` is **accepted** by the database. Validity is enforced by the Python enum
and the transition guards in `services.py`, which were verified to survive the restore
(invalid transition refused 409). Identical in source and restored, so this is a schema
characteristic, not restore infidelity.

**L6 — Runbook R11 still states no notification dispatcher exists.** Recorded as
CONFLICT-012; Workstream B delivered one. Not corrected here: it belongs with CONFLICT-009,
the same class of documentation lag, in one documentation commit.

**L7 — Single-process rate limiting.** Buckets are process-local.
`MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING` is unchanged.

**L8 — No Git remote.** CONFLICT-010 remains open and is an owner decision.

### Preserved external blockers

`EAS_PROJECT_CONFIGURATION_VERIFIED` · `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` ·
`EXTERNAL_SMTP_DELIVERY_PENDING` · `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED`

Nothing in this milestone implemented real SMTP, hosted deployment, Cloudflare, store
enrolment, EAS authentication, native submission, live payments, real inventory, real
fulfilment, public commerce, trademark clearance or manufacturing claims.

---

## 7. Rollback

Each continuation commit is independently revertible and none rewrites inherited history.

| To undo | Command |
|---|---|
| the whole milestone, back to the inherited state | `git revert --no-commit 3835aa0..HEAD && git commit` |
| only the proxy-header correction | `git revert 3835aa0` |
| return to the takeover commit without rewriting | `git checkout d6c6973` |

Reverting `3835aa0` restores the bypassable configuration and is not recommended. After
any revert, rebuild the staging image — the running container carries the corrected
entrypoint.

The database changes are confined to a disposable slice database created for this
milestone. No committed fixture was modified: both preserved fixtures still hash to the
values CI asserts.

---

## 8. Commit range

| Commit | Subject |
|---|---|
| `d6c6973` | *(inherited, preserved)* test: prepare DEDUNET branded vertical-slice fixtures |
| `3835aa0` | fix: make ASGI proxy-header trust explicit and fail closed |
| `c1cb745` | test: complete DEDUNET commerce-test customer, admin and notification journey |
| `0809955` | test: verify branded backup and isolated restore |
| `ee4b5d3` | fix: repair the M22 mutation anchor after the proxy-header quarantine |
| *(this file)* | docs: complete branded vertical-slice evidence |

The prompt's suggested split named separate customer-journey and admin/notification
commits. Both live in one file (`scripts/validation/branded_slice_journey.py`) whose
phases share a dispatch table, so splitting them would have meant committing a
deliberately broken intermediate state. They are one commit, and the message states both.

---

## 9. Final status

`BRANDED_VERTICAL_SLICE_CONDITIONALLY_VERIFIED`

**Verified:** the proxy-header trust boundary is reproduced, corrected, regression-tested
at the real server boundary and protected by two independent mutations; all 186 executed
phase checks pass; the required visible counts hold; the full backend, PostgreSQL and
mobile suites and both mutation harnesses are green; backup and isolated restore are
rehearsed with value-level parity and functional checks against the restored database.

**Conditional on:** L1, L2 and L3 — brand and product media do not serve in any container
deployment, the web client renders no product media, and its brand mark 404s in every
split-origin topology. Phase D required web and mobile to agree on media, and they do not.
The condition is a media-delivery gap in the web and container surfaces, not a failure of
the commerce, provenance, notification, rate-limiting or restore behaviour, each of which
was executed and passed.

The final team-readiness review has **not** been started.
