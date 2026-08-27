# Staging cutover — execution record

| Field | Value |
|---|---|
| Artifact ID | EV-CUT-001 · **Version** 1.0 |
| Status | **`AUTOMATED-TESTED`** — awaiting the human iPhone smoke |
| Plan | `docs/operations/STAGING_CUTOVER_PLAN.md` (OPS-CUT-001), option **A**, same-origin proxy |
| Authorization | Explicit owner instruction, in session, 2026-08-27 |
| Date | 2026-08-27 |
| Owner | Side B / platform |

> **What this is.** The `web` service on normal staging now serves the enterprise consumer
> application instead of the classic client. Nothing else changed. `PUBLIC_COMMERCIAL_LAUNCH`
> remains **BLOCKED**, the commerce mode is untouched, and no data, schema or volume was
> touched at any point.
>
> **What this is not.** It is not product acceptance of Dido intelligence, Style DNA,
> recommendations, the outfit engine, Saved persistence, multi-brand integrations, merchant
> SaaS or native iOS. None of those were built, changed or evidenced here.

---

## 1. Baseline

| | Value |
|---|---|
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| Starting HEAD | `e29e019` |
| Working tree at start | clean (`git status --short` empty) |
| Web container before | `08a823402a90`, image `9804c80942b1`, started 2026-08-25T14:33:18Z |
| API before | `379cb777cbd4`, started 2026-08-24T14:30:44Z |
| DB before | `efd688150d28`, started 2026-08-24T13:36:58Z |
| Worker before | `9730faa7263d`, started 2026-08-24T14:30:44Z |
| Candidate | `dedunet-consumer-candidate:e29e019` on 13081, image label `dedunet.head=e29e019` |

Every precondition in the plan §2 was checked before any change. `/ready` returned
`{"status":"ready","checks":{"database":"ok","catalog_fixture":"ok"}}` and
`/api/v1/commerce/mode` returned `BRAND_PREVIEW_MODE`, `purchasable: false`.

## 2. The tracked change

**One file: `docker-compose.staging.yml`, the `web` service only.**

1. `dockerfile: apps/web/Dockerfile` becomes `dockerfile: apps/consumer/Dockerfile`.
2. Build arg `API_BASE_URL` **removed** — the consumer client is same-origin and must not
   carry an absolute base. `ADMIN_API_BASE_URL` added in its place, carrying exactly the
   value the classic image previously built the admin surface with, which is why
   `CORS_ORIGINS` needed no change at all.
3. `DEDUNET_API_UPSTREAM: "api:8000"` stated explicitly in an `environment:` block.
4. A tmpfs on `/etc/nginx/conf.d` — see §3. This was **not** in the plan and is the one
   correction made during execution.

The classic configuration is preserved verbatim in a comment block above the changed line,
so the rollback is a revert rather than an archaeology exercise. `apps/web` and all of its
tests remain in the tree, untouched.

## 3. Defect found during execution, and corrected

**The first switch failed.** `dedunet-staging-web-1` entered a restart loop and 13080
refused connections. The cause was in the container log and was unambiguous:

```
20-envsubst-on-templates.sh: line 53:
  can't create /etc/nginx/conf.d/default.conf: Read-only file system
```

The consumer image ships its nginx configuration as a **template** and renders it at
container start, deliberately, so the API upstream is configurable per deployment without
baking a host address into the image. The staging `web` service runs `read_only: true` with
tmpfs on `/var/cache/nginx`, `/var/run` and `/tmp` only. The classic image copied a static
`nginx.conf` in at build time and so never needed that path writable; the consumer image
does.

**Why the candidate did not catch it.** The candidate on 13081 was launched with plain
`docker run`, without `read_only`. Verified directly: `ReadonlyRootfs=false` on that
container. The read-only posture was therefore never exercised against the consumer image
until the cutover itself.

**Correction:** one tmpfs entry, `- /etc/nginx/conf.d:size=1m`. The security posture is
unchanged — the mount is ephemeral RAM re-rendered from the read-only image layer on every
start, the served html directory is still read-only, and `no-new-privileges` is retained.
Staging came up on the next attempt and has been stable since.

**Standing lesson, recorded so it is not relearned:** an additive candidate on a spare port
only evidences the artifact, not the deployment posture it will run under. A candidate that
does not run with the target service's `read_only`, tmpfs and security options has not
tested the thing that will actually serve.

## 4. Topology

| | Before | After |
|---|---|---|
| `:13080/` | 302 to `/storefront/`, classic client, hash routing | consumer client, real path routing |
| `:13080/storefront/` | classic client | — |
| `:13080/admin/` | admin portal, cross-origin API | admin portal, cross-origin API — **unchanged** |
| Consumer to API | `:18080` cross-origin, CORS entry required | **same-origin `/api`**, proxied by nginx to `api:8000` |
| `:13081` | candidate | retained as the acceptance reference during soak |

## 5. Services

| Service | Action | Evidence |
|---|---|---|
| `web` | rebuilt and recreated (twice — see §3) | new container `8e772dedb333` |
| `api` | **untouched** | `379cb777cbd4`, start time unchanged across the whole cutover |
| `db` | **untouched** | `efd688150d28`, start time unchanged |
| `notification-worker` | **untouched** | `9730faa7263d`, start time unchanged |

`docker compose up -d --no-deps web` was used specifically so dependencies could not be
restarted as a side effect. **`docker compose down -v` was never run.** No migration was
required and none was performed; no volume, schema, fixture or catalogue row was touched.

## 6. Artifact provenance

The image serving normal staging is **byte-identical** to the artifact the owner accepted on
a physical iPhone. Verified by SHA-256 of each served file, 13080 against 13081:

| Artifact | Result |
|---|---|
| `/assets/index-B-2mQdH-.js` | MATCH |
| `/assets/index-ZnGo4Um_.css` | MATCH |
| `/assets/router-BIPeleUq.js` | MATCH |
| `/index.html` | MATCH |
| `/tokens.generated.css` | MATCH |
| `/brand.generated.js` | MATCH |

This is what allows the human smoke on 13080 to be **short** rather than a repeat of the
full foundation acceptance: the application is the same bytes, reached over a different
route to the same API.

Also verified on the built image before it took traffic: 9 self-hosted font files present
and served (`HTTP 200`), **zero** references to any external font CDN, **zero** occurrences
of `10.0.0.2`, `:18080` or a localhost port in any consumer bundle, and no secret-shaped
string in the bundle. The client resolves an empty API base and a relative `/api/v1` prefix.

## 7. Post-cutover verification

### Safety — the checks that matter most

| Check | Result |
|---|---|
| `COMMERCE_MODE` | `BRAND_PREVIEW_MODE` |
| `purchasable` | `false` |
| `public_commerce_enabled` | `false` |
| `payments` | `none` |
| Preview banner | present on every route inspected |
| Source Tee commerce CTA | **`NOT AVAILABLE TO BUY`, `disabled`** |
| Server-side cart add | **409** — "this catalogue is in brand preview; nothing is available to purchase" |
| Checkout without auth | **401** |
| `PUBLIC_COMMERCIAL_LAUNCH` | **BLOCKED**, unchanged |

### Browser regression — against the deployed staging URL

`DEDUNET_BASE_URL=http://10.0.0.2:13080`, single worker, run against the real deployment.

| Engine | Result |
|---|---|
| Chromium | **130 passed** |
| WebKit | **130 passed** |
| Mobile Safari viewport | **130 passed** |
| **Total** | **390 passed, 0 failed, 0 flaky, 14.8m** |
| Firefox | **NOT RUN — cannot launch in this environment.** Not claimed as a pass |
| Physical iPhone | **NOT PERFORMED BY THIS AGENT.** Automated WebKit is not a device pass |

The suite asserts page-specific accessible names and visible text on direct load, refresh,
back and forward for every route — a shell-only render fails it.

### Backend and validators

| Check | Result |
|---|---|
| `pytest -q` | **576 passed, 2 skipped** (578 collected) |
| `validate_product_data.py` | exit **0** |
| `validate_candidate_data.py` | exit **0** |
| `validate_candidate_data.py --assess-sellable` | exit **1** — required non-zero |
| `verify_side_a_package.py` | exit 0 — `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| `verify_packaged_assets.py --root packages/brand/assets` | exit 0 — `PACKAGED_BRAND_ASSETS_VERIFIED` |
| `build_brand_package.py --verify-no-drift` | exit 0 — `BRAND_PACKAGE_NO_DRIFT`, seam matches web/admin/consumer |
| `controller_validate.py` | **PASS**, 0 errors, 3 pre-existing warnings (empty CSV templates) |
| `git diff --check` | clean |
| Secret scan, 518 tracked files | 0 hits |
| Mutation testing | **not required** — no registered mutation target changed; every target is a backend Python file and the diff touches only `docker-compose.staging.yml` |

### Auth and session

| Check | Result |
|---|---|
| No token to `/api/v1/me/orders` | **401** |
| Invalid token | **401** "invalid or expired session" |
| Stale token cleared by client on 401 | covered by `safety-guards.spec.ts`, passing on all three engines |
| Unlisted cross-origin `Origin` | **no** `Access-Control-Allow-Origin` returned |
| Admin cross-origin config | unchanged, `/admin/` returns 200 |

### Visual and responsive

Inspected in a real browser against the deployed URL, at 390 and 1280, on Home, Dido, Shop,
Product, Saved and Account. Computed layout, not DOM presence alone.

- Self-hosted fonts **loaded** — Manrope Variable, Bodoni Moda.
- **No horizontal overflow** at either width on any surface inspected.
- **Zero broken images** — Home alone paints 28.
- No empty sections, no raw error text, **no console errors**.
- Account renders 6 inputs, **all 6 labelled** — the Phase 2 defect stays fixed.
- Product media serves `200` through the same-origin proxy.

**Mobile footer (§17 of the brief) — not regressed.** At 390 the primary nav is
`display: none`, the compact footer carries 2 links, and the fixed 5-item bottom tab bar is
present. At 1280 the 10-link expanded footer shows and the tab bar is `display: none`. The
hidden set is removed with `display: none` in both directions, so it leaves the
accessibility tree rather than being merely invisible.

> Screenshots could not be captured: the browser pane does not composite frames in a
> non-interactive session. The inspection above is computed-style and layout measurement.
> Prior visual captures remain in `evidence/phase-3/`, and the served artifact is
> byte-identical to what they were taken from.

## 8. Findings — open, and NOT fixed in this change

### F-1 · Security headers are absent on every HTML document (new, and a regression at this URL)

`X-Frame-Options`, `X-Content-Type-Options`, `X-Robots-Tag` and `Referrer-Policy` are
declared at server level in `apps/consumer/default.conf.template`, but nginx does **not**
inherit `add_header` into a location that declares its own. `location = /index.html` and
`location /assets/` each set `Cache-Control`, so both **drop all four**. Every document the
consumer app serves therefore carries none of them. `/admin/`, which declares no
`add_header`, still returns all four.

**This is a regression at the normal staging URL**, established empirically rather than
inferred: the classic image was rebuilt from committed source and served
`X-Robots-Tag`, `X-Content-Type-Options` and `X-Frame-Options` on `/storefront/`.

It is **pre-existing in the accepted candidate** — 13081 behaves identically — so the
cutover promoted it rather than introduced it.

**Deliberately not fixed here.** Editing the nginx template would break the byte-equivalence
in §6, which is the entire basis for a short human smoke instead of a repeated full
acceptance. It is a small, contained follow-up: add the four headers into the two locations
that override them. **Required before public launch** — the missing `X-Frame-Options`
leaves the app framable.

### F-2 · The product page shows "Not priced", not €72

The brief expected the Source Tee to read **€72**. The deployed consumer client renders
**"Not priced"** with a dedicated `priceAbsent` style.

**Not caused by the cutover** — 13081 renders identically. The catalogue API exposes price
at **variant** level (`7200` EUR minor units on all 18 Source Tee variants, confirmed) and
leaves the product-level price null; the consumer PDP reads the product level. The €72
expectation traces to the *classic* storefront, which displayed it.

No safety consequence: the CTA is disabled and reads `NOT AVAILABLE TO BUY`, and the server
refuses a cart add with 409. Recorded because the owner asked for €72 and would otherwise
see something different on the device. Whether "Not priced" or "€72" is the correct product
behaviour is a **product decision, not a cutover decision**.

### F-3 · The documented test count was stale on arrival

The plan and the acceptance record both state **570 passed, 2 skipped**. The suite at that
same commit yields **576 passed, 2 skipped**. Collection was measured at 578 both with and
without the cutover change, so the change is collection-neutral and this is not a
regression — the figure was written into `e29e019` without re-running after tests were
added. Corrected here rather than repeated.

### Carried forward, unchanged by this cutover

- **Media delivery separation** — `docs/architecture/MEDIA_DELIVERY_SEPARATION.md`. One Home
  load costs ~22 API-origin requests, ~20 of them static media, under the general limiter.
  The limiter was **not** touched and must not be raised to hide this.
- **Trusted proxy / client identity** — under the same-origin proxy the API keys its rate
  limiter on the proxy container's address. `RATE_LIMIT_TRUSTED_PROXY_COUNT=0` and
  `TRUSTED_PROXY_MODE=none` are correct and were left alone. Immaterial on a single-user LAN;
  **not** acceptable for hosted multi-user production.
- **Distributed rate limiting** — buckets remain in process memory, single replica only.
- Saved persistence, Looks as a real outfit object, the multi-brand domain, Dido
  intelligence, and the absent About / Privacy / Terms routes all remain outstanding.

## 9. Rollback

**Proven, not asserted.** The classic image was rebuilt from `apps/web/Dockerfile` during
verification, started, and served `HTTP 200` on `/storefront/`. The proof container and its
image were then removed.

Note that `dedunet-staging-web:latest` now names the consumer image, so the previous image
id `9804c80942b1` is no longer tagged. Rollback is therefore a **rebuild**, in the low
minutes, exactly as the plan anticipated — not a re-tag.

**Procedure:** restore the commented `dockerfile:`/`API_BASE_URL` lines in the `web` service,
drop its `environment:` block, then
`docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps web`.
The `/etc/nginx/conf.d` tmpfs is harmless to leave in place.

**Data risk: none.** No migration, no schema change, no volume touched.

## 10. State

```
ENTERPRISE_CONSUMER_FOUNDATION   = ACCEPTED WITH FOLLOW-UP ITEMS   (unchanged)
STAGING_CUTOVER                  = EXECUTED, PENDING HUMAN SMOKE
PUBLIC_COMMERCIAL_LAUNCH         = BLOCKED                          (unchanged)
```

Normal staging: **`http://10.0.0.2:13080/`**
Acceptance reference, retained for the soak: `http://10.0.0.2:13081/`
