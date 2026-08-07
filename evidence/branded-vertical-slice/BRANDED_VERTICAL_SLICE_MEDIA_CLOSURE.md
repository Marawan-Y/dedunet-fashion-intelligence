# DEDUNET branded vertical slice — deployable media closure

**Artifact ID:** EV-BVS-002 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED`
**Date:** 2026-08-07
**Starting HEAD:** `91f7f44`

## Relationship to the earlier result

The vertical slice was accepted as `BRANDED_VERTICAL_SLICE_CONDITIONALLY_VERIFIED`
(`EV-BVS-001`, commit `91f7f44`). **That result stands and is not rewritten.** It was
conditional on exactly three reproduced media defects, L1–L3. This document records their
closure. Everything else from `EV-BVS-001` — the proxy-header correction, Phases A–H, the
commerce, provenance, notification, rate-limiting and restore behaviour — is preserved and
was re-executed, not assumed.

---

## 1. Baseline — the three defects, reproduced before any change

### L1 — brand and product media served nothing in any container

Executed against the running staging container at `91f7f44`
(`scripts/validation/container_media_acceptance.py`):

| Observation | Value |
|---|---|
| resolved runtime media root, read from the container | `/packages/brand/assets` — **outside `/app`** |
| `ls /app/packages` | `No such file or directory` |
| normalized asset files in the image | **0 of 31** |
| registered brand assets returning 200 | **0 / 31** |
| product-media requests returning 200 | **0 / 18** |
| DDN-TS01 media URLs | `[404, 404, 404, 404]` |
| DDN-TS01 media records in the payload | **4**, ordered `front, back, detail, lifestyle`, with Side A alt text and `PROTOTYPE_CONCEPT` |
| hostile paths | all 9 correctly refused |
| acceptance total | **23 / 29** |

The payload was advertising four media URLs the deployment could not serve. The API image
build context was `services/commerce-api`, so `packages/brand/assets` was not merely
uncopied — it was **unreachable**, and no edit inside that context could have fixed it.

Nothing failed loudly: the image built, the container started, `/ready` returned 200.
Readiness does not check media, and a missing asset and a missing asset *root* both
returned 404, so the two were indistinguishable from outside.

### L2 — the web storefront rendered no product media

`apps/web/app.js` contained **no reference to `product.media` anywhere**. Both media
slots rendered the first letter of the product name:

```
app.js:208  el("div", { class: "card__media", "aria-hidden": "true", text: product.name.slice(0, 1) })
app.js:292  el("div", { class: "pdp__media",  "aria-hidden": "true", text: product.name.slice(0, 1) })
```

Measured in the browser on the DDN-TS01 page (web `:13500` → API `:18000`):

| Observation | Value |
|---|---|
| media records offered by the API | 4, with roles and Side A alt text |
| product images rendered | **0** |
| `.pdp__media` placeholder text | `"T"` |

### L3 — the brand mark resolved against the storefront origin

`apps/web/index.html` used root-relative paths for both the brand mark and the favicon:

```
index.html:14  <link rel="icon" href="/api/v1/media/assets/brand-prototype/logos/favicon.svg">
index.html:27  <img class="brand__mark" src="/api/v1/media/assets/brand-prototype/logos/logo-primary.svg">
```

The identical path, measured both ways:

| Origin | Result |
|---|---|
| web origin `:13500` | **404** |
| API origin `:18000` | **200 `image/svg+xml`** |
| shipped nginx storefront `:13080` | **404** |

The only `<img>` on the page was broken. The bytes were being served correctly the whole
time; the browser was asking the wrong host. Mobile never had this defect because it
builds absolute URLs against its configured API base.

---

## 2. Docker architecture correction

### Build-context design

The context is now the **repository root**, because the runtime needs
`packages/brand/assets` and a context rooted at the service can never reach it. Widening a
context is also how `.git`, `.env` and the immutable Side A handoff get shipped by
accident, so it is narrowed straight back down by
**`services/commerce-api/Dockerfile.dockerignore`**.

BuildKit prefers a per-Dockerfile ignore file over the context root's, so the web image —
whose needs are the exact opposite — is unaffected. The file is written **deny everything,
then allow**, matching the media route's own allow-list posture:

* allowed: this service's `app/`, `data/`, `migrations/`, `alembic.ini`, `manage.py`,
  `notification_worker.py`, `docker-entrypoint.sh`, `requirements.txt`;
  `packages/brand/assets/**` plus the two manifests; the asset verifier.
* re-denied afterwards: `tests/`, `__pycache__`, `*.pyc`, `.pytest_cache`, `*.sqlite3`,
  `.env*`.

Adding a file to the image now requires an explicit line. That is the point.

### Build-time refusal

A first stage verifies the package against `assets.json` and `product-media.json` **by
SHA-256** and the runtime stage copies only `--from` that stage, so the manifests and the
verifier never reach the runtime image and a missing or rewritten asset **fails the
build**.

Proven, not asserted — one asset removed:

```
#12  "missing": [ "DDN-TS01-FRONT" ]
#12  "result": "PACKAGED_BRAND_ASSETS_FAILED"
#12 ERROR: process "/bin/sh -c python verify_packaged_assets.py ..." did not complete successfully: exit code: 1
```

The asset was restored and the tree left clean.

### The immutable Side A handoff

Untouched and **not** in the image. Runtime serves the generated package only;
`handoffs/incoming/` remains checksum-protected evidence. Confirmed by filesystem
inspection, not by reading the Dockerfile.

---

## 3. Runtime media-root design

`_MEDIA_ROOT` was computed from `__file__`, which silently encoded *"the API always runs
from a repository checkout"*. In the container it resolved to `/packages/brand/assets`.

Replaced by explicit configuration:

| Mode | Resolution |
|---|---|
| **Docker** | `BRAND_MEDIA_ROOT=/app/brand-assets`, set in the image |
| **Local checkout** | `BRAND_MEDIA_ROOT` unset → `packages/brand/assets` in the repository |
| **Neither available** | refused with a stated reason |

No host-specific absolute path is used, and container execution depends on no bind mount.
The root is validated **at startup** — `app.server` refuses to boot and exits 3 with a
stated reason — and **at first use**, where the route distinguishes:

* **missing asset root → 503** (deployment failure)
* **missing asset → 404** (as before)

Collapsing those into one status is exactly how an image with no assets at all looked
healthy. The startup line is part of the contract:

```json
{"event": "brand_media_root", "media_root": "/app/brand-assets", "configured_by": "BRAND_MEDIA_ROOT"}
```

The read-only runtime filesystem is preserved. No writable asset directory was added;
assets are immutable image content. This was confirmed incidentally when `docker cp` into
the container was **refused as read-only**.

---

## 4. Image filesystem inspection

Inspected on the rebuilt artifact, not inferred from the Dockerfile.

| Check | Result |
|---|---|
| runtime media root resolvable in container | `/app/brand-assets` |
| normalized asset files present | **31** |
| asset bytes vs manifest SHA-256 | **31/31 match**, 0 missing, 0 unexpected, 0 mismatched |
| `/app` contents | `alembic.ini app brand-assets data manage.py migrations notification_worker.py requirements.txt var` |
| `.git` | absent |
| `.env`, `.env.staging` | absent |
| `evidence/` | absent |
| backup dumps | absent |
| Side A immutable handoff | absent |
| `docs/` | absent |
| `tests/` | absent |
| `node_modules` | absent |
| `__pycache__`, `*.pyc`, `*.sqlite3` | absent |
| real `POSTGRES_PASSWORD` value | not present anywhere in the filesystem |
| real `SESSION_SECRET` value | not present |
| real `ADMIN_API_TOKEN` value | not present |
| image size before → after | **73.6 MB → 73.7 MB** (the ~100 KB of SVGs; no unexpected increase) |

Secret **values** were scanned for, not variable names — the names legitimately appear in
`config.py`, `security.py` and `manage.py`, which read them from the environment. Values
were piped via stdin so they never appeared in `argv`.

---

## 5. Container media acceptance

`scripts/validation/container_media_acceptance.py`, run through the real container:

| Check | Before | After |
|---|---|---|
| registered brand assets 200 | 0/31 | **31/31** |
| assets with correct type, `nosniff` and exact byte length | 0/31 | **31/31** |
| product-media requests 200 | 0/18 | **18/18** |
| DDN-TS01 media URLs | `[404×4]` | **`[200×4]`** |
| DDN-TS01 ordering | — | `front, back, detail, lifestyle` |
| every record carries alt text | — | yes |
| every record labelled `PROTOTYPE_CONCEPT` | — | yes |
| hostile paths refused | 9/9 | **9/9** |
| **total** | **23/29** | **29/29** |

Hostile cases still refused after the repackaging: traversal, encoded traversal, nested
traversal, directory listing, the asset root itself, dotfiles, non-image types, a missing
asset, and `/api/v1/media/../app/main.py`. No directory listing exists anywhere.

---

## 6. Web media URL resolution

`apps/web/media-url.js` is now the single place resolving the API base and API-backed
asset URLs. Data requests already went through one helper and assets did not — which is
precisely how they drifted apart.

It handles absolute, protocol-relative, `/api/v1/media`-prefixed, `/api`-prefixed and bare
package paths; normalises trailing slashes; refuses traversal client-side; and returns
`""` rather than a half-built URL, because a half-built URL renders the browser's
broken-image glyph, which tells a customer nothing.

Markup declares **which** asset it wants via `data-asset`; the module assigns **where** it
lives once the API base is known, since the API origin is only knowable at runtime.

`tests/test_web_media_resolver.py` — **11 tests**, executing the real module through Node,
covering all six required cases:

| Required case | Covered by |
|---|---|
| same-origin development | `test_same_origin_development` |
| split-origin web/API | `test_split_origin_web_and_api` (also asserts the storefront port never appears) |
| API base with trailing slash | `test_api_base_with_trailing_slash` (one and three slashes) |
| media path with leading slash | `test_media_path_with_leading_slash` |
| absolute URL | `test_absolute_url_is_returned_unchanged` |
| missing/malformed path | `test_missing_or_malformed_path_returns_empty_string` |

Plus API-base precedence, the port fallback, hydration of `data-asset` elements, and a
guard that no markup reintroduces a root-relative `/api/` reference.

Asserting on the *source text* of a URL builder would prove nothing about the URLs it
builds — which is the entire shape of this defect — so these run the module.

---

## 7. Web brand mark

Uses the normalized API asset-serving route, so it stays governed by the brand package and
its drift verification. No one-off URL scheme was created for the logo.

| Topology | Brand-mark URL | Loaded | Alt |
|---|---|---|---|
| local checkout, web `:13600` → API `:18000` | `http://127.0.0.1:18000/api/v1/media/…/logo-primary.svg` | **yes** | `DEDUNET` |
| split origin (same run, asserted) | never the storefront origin | **yes** | `DEDUNET` |
| Docker/staging, nginx `:13080` → API `:18080` | `http://127.0.0.1:18080/api/v1/media/…/logo-primary.svg` | **yes** | `DEDUNET` |

Favicon resolves the same way. MIME type `image/svg+xml`, `nosniff` present, and no legacy
brand fallback anywhere.

Staging needed one further correction to render at all: its API is published on `18080`
while the client defaulted to `18000`. `apps/web/config.js` is generated from an
`API_BASE_URL` **build argument** — build time, not run time, because the web container's
root filesystem is read-only and nothing may write into the served directory after start.

---

## 8. Web DDN-TS01 gallery

Consumes the **same `product.media`** the mobile Gallery consumes. There is deliberately
no web-only media source.

Measured in the browser (Docker/staging topology):

| Observation | Value |
|---|---|
| images on page | 5 (brand mark + 4 media) |
| loaded | **5** |
| broken | **0** |
| media origin | API origin, never the storefront |
| natural size | 1200×1500 each |
| captions | `Front, Back, Detail, Lifestyle` — API order |
| alt text | Side A wording, verbatim |
| concept note | *"Concept artwork — not product photography."* |
| placeholder letter | gone |

`tests/test_web_gallery.py` — **12 tests** rendering the real gallery in jsdom: four media
rendered, API ordering preserved, resolution against the API origin, verbatim Side A alt
text, the concept label, eager loading, a single media record, zero media (renders nothing
rather than an empty frame), a product with no `media` key, the card front image, and the
card falling back to the initial when there is no media.

Two layout bugs of mine, found by measuring rather than looking:

* lazy thumbnails with `height: auto` collapsed to 0 px, so they never intersected the
  viewport, so lazy never fired, so they never gained a size — a deadlock, not a saving.
  The gallery is eager (four small SVGs the customer opened the page to see) and boxes
  reserve `4 / 5` with `object-fit: contain`, so concept artwork is not cropped.
* card images used `height: 100%` inside a `place-items: center` grid, where a child does
  not stretch, so they collapsed too.

Variant selection, price, evidence disclosures and the reduced-motion rule are unchanged.
The catalogue grid keeps `loading="lazy"` — correct for a list that grows; its URLs were
verified to serve 200 `image/svg+xml` and to load when fetched.

---

## 9. Cross-surface parity — DDN-TS01

| Property | API (authoritative) | Web | Mobile |
|---|---|---|---|
| external product ID | `DDN-TS01` | same product | same product |
| price | `7200` EUR minor units | €72.00 | €72.00 |
| variants | 18 | 18 | 18 |
| media records | 4 | 4 rendered | 4 rendered |
| media order | `0:front, 1:back, 2:detail, 3:lifestyle` | Front, Back, Detail, Lifestyle | Front, Back, Detail, In context |
| media role | front/back/detail/lifestyle | same | same |
| alt text | Side A wording | verbatim | verbatim |
| concept status | `PROTOTYPE_CONCEPT` | "Concept artwork" note | "Concept artwork" note |
| origin | `UNVERIFIED`, intended `EG` | "not verified, no origin claim is made" | same |
| legal | `LEGAL_CLEARANCE_PENDING` | disclosure shown | disclosure shown |
| media loaded / broken | — | 4 / 0 | 4 / 0 |

Layouts differ; **the authoritative content does not**. Mobile labels the lifestyle slot
"In context" in its own UI copy while consuming the same `lifestyle` role — presentation,
not content.

---

## 10. Commerce behaviour preserved

Re-executed in full after the media changes, from a clean database — **137/137**:

| Phase | Result |
|---|---|
| A default product truth | 13/13 |
| B `BRAND_PREVIEW_MODE` | 14/14 |
| C synthetic inventory | 28/28 |
| C.10 preview blocks with stored synthetic stock | 5/5 |
| D customer journey | 38/38 |
| E administration and notifications | 26/26 |
| F rate limiting 7/7 · session 6/6 | 13/13 |

`BRAND_PREVIEW_MODE`: DDN-TS01 visible **with real media now visible**, cart-add refused
409 naming brand preview, checkout blocked, no payment call, zero effective sellability.
`COMMERCE_TEST_MODE`: synthetic inventory still loads only onto `DDN-SRC-CAR-XS`,
0 → 25 → 23 after purchase, order records `commerce_mode_at_checkout = COMMERCE_TEST_MODE`.
`PUBLIC_COMMERCE_MODE`: still refused by configuration.

---

## 11. Backup and restore after the deployment change

No schema change was needed. Re-run end to end:

| Step | Result |
|---|---|
| backup | `dedunet_slice-20260807T080512Z`, 61218 bytes, custom format |
| SHA-256 | `b228ff9a21b549b4543693b99283dd417411b2c8f2230677ae162259b32bc45a` |
| verified before restore | yes |
| isolated restore | `dedunet_slice_rehearsal`, a new database |
| schema parity | `PASS` |
| value parity | **20/20** |
| restored functional | **20/20** |
| `product_media` parity | **18 → 18** |
| order-mode parity | `COMMERCE_TEST_MODE` preserved on every order |
| catalogue | 5 products / 62 variants / 62 SKUs |
| source database | untouched; only the rehearsal database dropped |

`LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED`. No production disaster recovery is claimed.

---

## 12. Mutations

**68 run, 68 detected, 0 survived.** Both compose builds were also verified: the local
`docker-compose.yml` API image builds with the new root context and carries
`BRAND_MEDIA_ROOT=/app/brand-assets` with 31 asset files.

The seven attacks this milestone was required to make, plus the two inherited proxy
guards, each detected by a test that fails for the intended reason — none by an import,
startup or syntax error:

| # | Mutation | Protected behaviour | Failing test | Reason |
|---|---|---|---|---|
| 1 | `M65` verifier stops reporting absent assets | the build refuses an incomplete image | `test_the_verifier_detects_a_missing_asset` | `PACKAGED_BRAND_ASSETS_FAILED` not raised |
| 1b | *(live)* one asset deleted from the package | Docker build fails | build stage | `"missing": ["DDN-TS01-FRONT"]`, exit 1 |
| 2 | `M64` absent media root tolerated | a misdeployment is 503, not 404 | `test_a_missing_root_is_503_not_404` | `assert 404 == 503` |
| 3 | `M66` media resolved against the storefront origin | split-origin resolution | `test_split_origin_web_and_api` | `'/api/v1/media/…' == 'http://127.0.0.1:18080/api/v1/media/…'` |
| 4 | `M68` gallery returns null (placeholder restored) | the product page renders real media | `test_all_four_media_records_are_rendered` | 0 images rendered, expected 4 |
| 5 | `M69` media order inverted | API ordering preserved | `test_api_ordering_is_preserved` | `['Lifestyle', 'Detail', 'Back', 'Front']` |
| 6 | `M67` brand-mark hydration removed | `data-asset` elements are resolved | `test_hydrate_assigns_src_and_href_from_data_asset` | `assert 0 == 2` |
| 7 | `M70` route's `nosniff` removed | assets declare their type authoritatively | `test_the_media_route_sets_nosniff_itself_not_only_the_global_middleware` | header absent on the route's own response |
| — | `M62` `proxy_headers=False` reverted | ASGI proxy trust stays explicit | `test_supported_server_states_its_proxy_boundary_explicitly` | "the ASGI server would interpret forwarded headers" |
| — | `M63` rewritten-peer quarantine removed | a forged peer cannot mint buckets | `test_unsafe_server_still_cannot_be_bypassed` | `[401 × 16]` — the original bypass signature |

All sources restored; the working tree was clean after each run and the suite green before
and after.

### A mutation that survived first, and what it exposed

`M70` initially **survived**. Removing `nosniff` from the media route changed nothing
observable, because `main.correlation_and_access_log` stamps
`X-Content-Type-Options` on *every* response. The redundancy is genuine defence in depth —
and it also meant a request-level assertion could not distinguish which layer was doing
the work, so a real guard was untested while appearing covered.

The guarding test now calls the handler directly, with no middleware in the path, so the
route's own header is asserted on its own. The harness earning its keep: this is exactly
the class of false confidence a mutation harness exists to find.

---

## 13. Full regression

| Check | Result |
|---|---|
| Side A checksum verification | **54/54**, 0 missing, 0 mismatched → `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| Normalized brand drift | `NORMALIZATION_VERIFIED` — 5 / 62 / 62 / 31 / 18 |
| Packaged-asset verification (checkout) | `PACKAGED_BRAND_ASSETS_VERIFIED` |
| Container image build | succeeds; fails when an asset is missing |
| Container filesystem security inspection | clean (§4) |
| Container media requests | **18/18** product media, **31/31** brand assets |
| Normalized-asset existence in image | **31/31**, bytes match manifest SHA-256 |
| Hostile media path tests | 9/9 refused |
| Web brand-mark test | pass in all three topologies |
| Web DDN-TS01 gallery tests | **12/12** |
| Web split-origin media test | pass |
| Web media resolver tests | **11/11** |
| Mobile gallery tests | included in the mobile suite |
| Mobile TypeScript | `tsc --noEmit` clean |
| Mobile complete suite | **117 passed**, 9 suites |
| Mobile mutation harness | **18/18 detected, 0 survived** |
| Expo web export | succeeded |
| Backend SQLite complete suite | **301 passed, 2 skipped** |
| Backend PostgreSQL complete suite | **303 passed** |
| Backend mutation harness | **68/68 detected, 0 survived** |
| Proxy-header boundary tests | 18 tests, included and green |
| SQLite + PostgreSQL concurrency | included in both suites |
| Preview-mode smoke | Phase B 14/14, C.10 5/5 |
| Commerce-test smoke | Phase C 28/28, D 38/38 |
| Notification-worker smoke | worker starts; API readiness unaffected |
| Rate-limit smoke | Phase F 7/7 |
| OpenAPI drift | 30 paths, **NO_DRIFT** |
| Backup and isolated restore | schema `PASS`, values 20/20, functional 20/20 |
| Secret scan | no `.env` in history; none tracked |
| Personal-data scan | no real emails, phone numbers or IBANs in tracked text |
| Customer-facing MERET/MERYT scan | **0** (65 tracked-text hits, all documentation, evidence, the separately-classified legacy seed fixture, or tests that must name the strings they forbid) |
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

## 14. Remaining limitations

Closed by this milestone: **L1, L2, L3**.

Carried forward, unchanged and not erased:

* **L4** — `load-test-inventory` in `PUBLIC_COMMERCE_MODE` prints an uncaught
  `CommerceModeError` traceback instead of the `{"result": "refused"}` JSON. Fails closed;
  cosmetic.
* **L5** — `orders.status` is `varchar(15)` with no enum or `CHECK`; validity is enforced
  by the application enum and transition guards. Identical in source and restored.
* **L6** — runbook R11 still states no notification dispatcher exists (CONFLICT-012).
* **L7** — rate-limit buckets are process-local;
  `MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING`.
* **L8** — no Git remote (CONFLICT-010, owner decision).
* **L9** *(new, minor)* — the catalogue grid's lazy thumbnails could not be observed
  loading under browser automation; their URLs were verified to serve 200 and to load when
  fetched eagerly. The product gallery, which is the parity requirement, is eager and
  fully verified.

Preserved: `EAS_PROJECT_CONFIGURATION_VERIFIED`,
`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`, `EXTERNAL_SMTP_DELIVERY_PENDING`,
`PUBLIC_COMMERCIAL_LAUNCH_BLOCKED`.

Nothing in this closure implemented hosted deployment, real SMTP, a live payment provider,
real stock, public commerce, EAS authentication, store enrolment, trademark clearance,
real product photography, or manufacturing/origin evidence.

---

## 15. Final status

`BRANDED_VERTICAL_SLICE_VERIFIED`

The three defects the conditional acceptance rested on are closed and regression-tested at
the deployed boundary:

* **L1** — 0/31 assets and 0/18 media in the container became **31/31 and 18/18**, with
  bytes matching the manifest by SHA-256 and the build now failing outright if an asset is
  missing.
* **L2** — the web product page renders all four DDN-TS01 media in API order with Side A
  alt text, from the same API media model mobile consumes.
* **L3** — the brand mark and favicon resolve against the API origin and load in local,
  split-origin and Docker/staging topologies.

API, web and mobile agree on the authoritative content. Commerce, provenance, notification,
rate-limiting and restore behaviour were re-executed in full and are unchanged: 137/137
phase checks, 68/68 backend mutations, 18/18 mobile mutations, 301/303 backend tests on
SQLite/PostgreSQL, 117 mobile tests, and a green backup and isolated restore.

L4–L9 remain open, are documented above, and none of them blocks this milestone.

The final team-readiness review has **not** been started.

---

## 16. Rollback

| To undo | Command |
|---|---|
| the whole media closure | `git revert --no-commit f590f56..HEAD && git commit` |
| the web rendering only | `git revert 00022eb` |
| the image packaging only | `git revert f590f56` |

Reverting `f590f56` restores an image that serves no media; reverting `00022eb` restores
the placeholder and the broken brand mark. After either, rebuild both images — the running
containers carry the corrected build.

No database schema changed, and no committed fixture was modified.
