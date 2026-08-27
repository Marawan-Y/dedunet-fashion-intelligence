# Staging cutover — execution record

| Field | Value |
|---|---|
| Artifact ID | EV-CUT-001 · **Version** 3.0 |
| Status | **`HUMAN-VERIFIED`** — physical iPhone smoke PASSED 2026-08-27 at `be1d1e2`. `evidence/team-acceptance/STAGING_CUTOVER_IPHONE_ACCEPTANCE.md` |
| History | v1.0 deployed the cutover and **wrongly declared it ready for the human smoke** while two required conditions were failing. The owner rejected that conclusion. v2.0 records the repair |
| Plan | `docs/operations/STAGING_CUTOVER_PLAN.md` (OPS-CUT-001), option **A**, same-origin proxy |
| Authorization | Explicit owner instruction, in session, 2026-08-27 |
| Date | 2026-08-27 |
| Owner | Side B / platform |

> **CORRECTION, 2026-08-27.** Version 1.0 of this document ended in
> `STAGING_CUTOVER_COMPLETE_READY_FOR_HUMAN_SMOKE`. **That conclusion was wrong and was
> rejected by the owner.** Two required cutover conditions were failing at the time it was
> written — the security headers (F-1) and the product price (F-2) — and both were recorded
> in §8 of that same document as known and unfixed. Recording a defect does not satisfy the
> gate that the defect fails. The deployment succeeded; the gate did not.
>
> The state between the cutover and this repair was
> `STAGING_CUTOVER_DEPLOYED` + `STAGING_CUTOVER_BLOCKED_PENDING_REPAIR`.
> Both defects are now repaired and verified on the deployed application; see §11.
>
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

This was true **at the cutover**. It is **no longer true after the repair in §11**, and the
difference is deliberate: fixing F-2 changed the application. The served JS bundle is now
`index-CogdTLIy.js` where the accepted candidate serves `index-B-2mQdH-.js`. The stylesheet
and router chunks are unchanged, because the repair touched no styling and no routing.

The consequence, stated rather than glossed: **the human smoke can no longer lean on
byte-equivalence.** It must actually look at the product page, which is the surface that
changed. `13081` remains the *historical* foundation-acceptance artifact and is deliberately
not rebuilt — it is evidence of what was accepted, not a copy of what is deployed.

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

## 8. Findings at the cutover — F-1 and F-2 since REPAIRED (§11)

> This section is kept **as it was written at the cutover**, so the record shows what was
> known and when. Its conclusion — that F-1 and F-2 could stand open while the gate passed —
> was wrong, and §11 is the repair. The carried-forward items at the end of the section are
> still accurate and still open.

### F-1 · Security headers absent on every HTML document — **REPAIRED, see §11**

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

**Was deliberately not fixed in the cutover**, on the reasoning that editing the nginx
template would break the byte-equivalence in §6 and so the basis for a short human smoke.

**That trade was not mine to make.** Byte-equivalence is a convenience for the review
process; shipping every document without `X-Frame-Options` is a security regression against
a client that did serve it. The convenience was allowed to outrank the defect, and the gate
was declared passed anyway. Repaired in §11.

### F-2 · The product page shows "Not priced", not €72 — **REPAIRED, see §11**

The brief expected the Source Tee to read **€72**. The deployed consumer client renders
**"Not priced"** with a dedicated `priceAbsent` style.

**Not caused by the cutover** — 13081 renders identically. The catalogue API exposes price
at **variant** level (`7200` EUR minor units on all 18 Source Tee variants, confirmed) and
leaves the product-level price null; the consumer PDP reads the product level. The €72
expectation traces to the *classic* storefront, which displayed it.

No safety consequence: the CTA is disabled and reads `NOT AVAILABLE TO BUY`, and the server
refuses a cart add with 409.

**The "product decision, not a cutover decision" framing in v1.0 was wrong.** It was not a
decision at all — it was a defect. The root cause (§11) is that the client never read the
variant price it was sent, on the strength of a comment asserting the catalogue had none.
Nothing had decided to hide a price; a wrong premise had been written down and then
believed. Repaired in §11.

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
ENTERPRISE_CONSUMER_FOUNDATION   = LOCKED
STAGING_CUTOVER                  = ACCEPTED
PHYSICAL_IPHONE_STAGING_SMOKE    = PASSED          (2026-08-27, at be1d1e2)
NATIVE_IOS                       = NOT BUILT, NOT TESTED   -- a separate state
PUBLIC_COMMERCIAL_LAUNCH         = BLOCKED                 (unchanged)
```

Sequence, so the history is not flattened into a success:

```
1. cutover deployed            -> first switch restart-looped (§3), corrected, served
2. post-cutover verification   -> found F-1 and F-2
3. v1.0 of this document       -> WRONGLY declared ready for the human smoke
4. owner rejected it           -> STAGING_CUTOVER_BLOCKED_PENDING_REPAIR
5. F-1 and F-2 repaired        -> §11
6. full regression re-run      -> 429 browser, 594 backend
7. human iPhone smoke           -> PASSED on normal staging, 2026-08-27
8. cutover accepted             -> foundation LOCKED; public launch still BLOCKED
```

Normal staging: **`http://10.0.0.2:13080/`**
Acceptance reference, retained for the soak: `http://10.0.0.2:13081/`

---

## 11. The repair — F-1 and F-2

The owner rejected v1.0's conclusion. Both defects were repaired in one focused change; no
other work was mixed in. No later product phase was started.

### F-1 · Security headers — root cause and repair

**Root cause.** nginx does not inherit `add_header` into a location that declares an
`add_header` of its own. The consumer template declared the four security headers once at
server level, which looks correct and is not: `location = /index.html` and
`location /assets/` each set `Cache-Control`, so each discarded all four. Every route in the
SPA is served from `index.html` through the history fallback, so **every document on the
site** carried none of them. `/admin`, which declares no header, kept all four — which is
why the config read as working.

**Repair.** One definition, included where it must apply, rather than four values repeated
in five places:

- `apps/consumer/security-headers.conf` — new. The four headers, each `always`.
- `apps/consumer/default.conf.template` — server-level `include`, plus an `include` in each
  location that declares its own `add_header`.
- `apps/consumer/Dockerfile` — `COPY` to `/etc/nginx/`, **not** into `conf.d`, which is a
  tmpfs at runtime and would be empty at start.

The values are not new policy. `X-Robots-Tag`, `X-Content-Type-Options` and
`X-Frame-Options` are exactly what `apps/web/nginx.conf` served; `Referrer-Policy` was
already declared at server level in the consumer template before the repair.

**One thing the repair got wrong first, and corrected.** The include was initially added to
`location /api/` as well. Measured on a real response, that emitted `Referrer-Policy`
twice — the API sets its own `no-referrer`, which is **stricter** than the document policy —
and the Referrer Policy spec takes the last valid value. The proxy was silently downgrading
the API. `/api/` is now the one **named exemption**, and two tests hold that line: one
asserting the include is absent there, one asserting the API still sets its own baseline
headers, since the exemption is only safe while it does.

**Verified on real HTTP responses from deployed staging**, not asserted from source:

| Response | Headers |
|---|---|
| `/` | all four · `Cache-Control: no-store, must-revalidate` |
| `/shop` (history fallback) | all four · `no-store, must-revalidate` |
| `/product/the-source-tee` | all four · `no-store, must-revalidate` |
| `/index.html` direct | all four · `no-store, must-revalidate` |
| `/admin/` | all four |
| `/assets/index-*.js` | all four · `Cache-Control: public, immutable` **preserved** |
| `/tokens.generated.css` | nosniff, DENY · `no-cache` **preserved** |
| `/api/v1/commerce/mode` | upstream's own nosniff, DENY, **`no-referrer` intact** · `no-store` |

Same-origin `/api` still proxies correctly; `BRAND_PREVIEW_MODE`, `purchasable: false`.
Cache-Control behaviour, the read-only runtime posture and `no-new-privileges` are all
unchanged. Nothing was weakened.

**The regression guard (requirement A.10).**
`services/commerce-api/tests/test_consumer_security_headers.py`, 14 tests, pins the
invariant a future edit would break silently:

> every `location` that declares its own `add_header` must also include the contract —
> except the one named, justified exemption.

**The guard was verified to fail.** F-1 was reintroduced by deleting the include from the
`index.html` location alone; two tests failed with the correct diagnosis, and the template
was restored. A guard whose removal nobody notices is not a guard.

`apps/consumer/e2e/security-headers.spec.ts` is the other half — 8 tests asserting the
headers on **real responses from the deployed container**, because correct configuration
does not prove a correct deployment, and that gap is exactly what let F-1 be reported as
"declared at server level" while no document carried them.

### F-2 · Product price — root cause and repair

**Root cause, and it is not a product decision.** `src/api/types.ts` asserted in a comment
that "The five DEDUNET products carry NO price", and `CatalogVariant` was modelled without a
price field to match. The product page therefore read a **product-level** `price_display`
that `/api/v1/catalog/products` has never sent, and every product rendered "Not priced".

The premise was false. The catalogue carries an authoritative price on each **variant** —
all 18 Source Tee variants are `7200` EUR minor units — and the API's own `list_products`
already sorts by `min(v.price_minor_units)`. The price was in the payload the whole time.
Nothing read it.

**The authoritative rule, taken from the domain rather than invented.**
`docs/side-b/SIDE_B_MONEY_CONTRACT.md` rule 6: display values are derived, never
authoritative, and clients format integer minor units "with pure integer/string arithmetic —
no division, so no binary float ever touches an amount". `apps/consumer/src/lib/money.ts`
ports `apps/web/ds.js:money()` verbatim in behaviour, including its degradation path, and
derives the product figure the way the classic client already did — cheapest across
variants:

| Variant prices | Renders |
|---|---|
| one price, or all variants equal | the exact price — `€72.00` |
| several distinct prices | `From €72.00`, built from the lowest |
| none priced, 0, negative or non-integer | the unpriced state — **only** then |

Nothing is hard-coded. `€72` is what the data produces.

**Formatting.** `€72.00`, matching the accepted presentation recorded in
`evidence/branded-vertical-slice/` as `"€72.00"`. An early cut of the repair rendered
`€72.00 EUR`; the symbol already carries the currency, so the redundant code was removed and
the test now asserts the exact string rather than a substring.

**Price is not an offer.** The purchase gate is untouched. On the deployed page:

| Check | Result |
|---|---|
| Source Tee price | **`€72.00`** |
| "Not priced" present | **no** |
| Purchase control | **`NOT AVAILABLE TO BUY`, disabled** |
| Preview banner | present |
| Server cart add | **409** — brand preview |
| `COMMERCE_MODE` | `BRAND_PREVIEW_MODE`, `purchasable: false` |
| Measure Trouser (not special-cased) | `€142.00` |

**Regression tests.** `src/lib/money.test.ts`, 13 tests, covering every case the repair was
specified against — single variant price, same price across variants, multiple prices,
missing price, and a preview non-purchasable product that is priced and still refused —
plus the formatter's padding, sign and degradation paths. `e2e/price.spec.ts`, 5 tests,
covering what a person actually sees, including that no product in the catalogue renders
unpriced.

The "from" and "absent" branches cannot be produced by the current catalogue, which is
uniformly priced. They are covered by the unit tests precisely because the data cannot
exercise them.

### Files changed in the repair

| File | Change |
|---|---|
| `apps/consumer/security-headers.conf` | **new** — the four headers, one definition |
| `apps/consumer/default.conf.template` | server + 3 location includes; `/api/` exempt, with the reason |
| `apps/consumer/Dockerfile` | COPY the contract to `/etc/nginx/` |
| `apps/consumer/src/lib/money.ts` | **new** — formatter and the price rule |
| `apps/consumer/src/lib/money.test.ts` | **new** — 13 unit tests |
| `apps/consumer/src/api/types.ts` | variant price modelled; the false comment corrected |
| `apps/consumer/src/features/shop/ProductPage.tsx` | price derived from variants |
| `apps/consumer/vite.config.ts` | vitest scoped to `src/`, node environment |
| `apps/consumer/e2e/security-headers.spec.ts` | **new** — 8 deployed-response tests |
| `apps/consumer/e2e/price.spec.ts` | **new** — 5 tests |
| `services/commerce-api/tests/test_consumer_security_headers.py` | **new** — 14 tests |

No backend application source was changed. No compose change was needed for the repair.

### Regression after the repair

| Check | Result |
|---|---|
| Browser E2E vs deployed `:13080` | **429 passed, 0 failed, 0 flaky, 16.9m** |
| — Chromium | **143 passed** |
| — WebKit | **143 passed** |
| — Mobile Safari viewport | **143 passed** |
| — Firefox | **NOT RUN** — cannot launch in this environment. Not claimed |
| Backend `pytest -q` | **594 passed, 2 skipped** |
| Consumer unit tests | **13 passed** |
| `validate_product_data.py` | exit 0 |
| `validate_candidate_data.py` | exit 0 |
| `--assess-sellable` | exit **1**, required non-zero |
| `verify_side_a_package.py` | `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| `verify_packaged_assets.py` | `PACKAGED_BRAND_ASSETS_VERIFIED` |
| `build_brand_package.py --verify-no-drift` | `BRAND_PACKAGE_NO_DRIFT` |
| `controller_validate.py` | **PASS**, 0 errors, 3 pre-existing warnings |
| `git diff --check` | clean |
| Secret scan, 519 tracked files | 0 hits |
| New bundle: LAN address or secret | 0 occurrences |
| Mutation testing | **not required** — no registered target changed; every target is under `services/commerce-api/app/` and the diff touches only `apps/consumer/` and one test file |

Backend went 576 to 594. Accounted for exactly: 14 new header-contract tests, plus 4 from
the existing XSS-sink and javascript-URL scans automatically picking up the two new consumer
source files — the frontend security guard extending itself over new code, as designed.

Browser went 130 to 143 per engine: 8 header tests and 5 price tests.

### Deployed surfaces, re-inspected

| Surface | Result |
|---|---|
| Home | h1 correct, 28 images, **0 broken**, no overflow, fonts loaded |
| Dido | h1 "Style with Dido", 0 broken, no overflow |
| Shop | h1 "Shop", 6 images, 0 broken, no overflow |
| Source Tee | **`€72.00`**, `NOT AVAILABLE TO BUY` disabled, preview banner |
| Account | 6 inputs, **all 6 labelled**, 0 broken |
| Orders | signed out, redirects to sign in — accepted behaviour |
| Console errors | **none** |
| API / DB / worker | start times **unchanged** through cutover and repair |

### Services

`web` rebuilt and recreated. `api`, `db` and `notification-worker` untouched — start times
still 2026-08-24, across both the cutover and the repair. No migration, no schema change, no
volume touched.

### Still open, and unchanged by this repair

Media delivery separation · trusted proxy / client identity · distributed rate limiting ·
Saved persistence · Looks as a real outfit object · the multi-brand domain · Dido
intelligence · the absent About / Privacy / Terms routes.

**The physical-iPhone smoke on `http://10.0.0.2:13080/` PASSED on 2026-08-27**, at
`be1d1e2`, on the repaired application — Home, Dido, Shop, the Source Tee at **€72.00** and
`NOT AVAILABLE TO BUY`, Account, mobile navigation and preview safety, all PASS. Recorded in
`evidence/team-acceptance/STAGING_CUTOVER_IPHONE_ACCEPTANCE.md`.

`STAGING_CUTOVER = ACCEPTED`. `ENTERPRISE_CONSUMER_FOUNDATION = LOCKED`.

It was a **web** application in Safari on an iPhone. That is **not** native iOS acceptance,
and it is **not** public-launch readiness. Native iOS remains a separate untested state and
`PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**.
