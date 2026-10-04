# Phase 5 — Saved persistence

| Field | Value |
|---|---|
| Artifact ID | EV-P5-001 · **Version** 1.0 |
| Status | **`AUTOMATED-TESTED`** — awaiting human acceptance of the Saved feature |
| Starting HEAD | `1430ee8` |
| Owner | Side B / platform |
| Date | 2026-10-01 |

> `PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**. Saving a product is not buying it: the
> Source Tee is **€72.00**, `NON_PURCHASABLE` and preview before and after, and the server
> still refuses a cart add with 409. A save changes no commerce state.
>
> **Not started:** Style DNA, Dido intelligence, recommendation scoring, the outfit engine,
> merchant SaaS, real payments, media CDN, distributed rate limiting.

---

## 1. Schema

Five new tables. No existing table was altered — not one column was added to `products`,
`variants`, `brands`, `customers` or `orders`.

| Table | Purpose |
|---|---|
| `looks` | curated editorial arrangements, with durable identity |
| `look_items` | one garment's part in a look, plus the editorial reason |
| `saved_looks` | `UNIQUE(customer_id, look_id)` |
| `favorite_products` | `UNIQUE(customer_id, product_id)` |
| `favorite_brands` | `UNIQUE(customer_id, brand_id)` |

**Uniqueness is a database constraint, not an application check.** A double tap on a flaky
connection genuinely races: both requests find no row and both insert. The unique index is
what makes the second harmless, and `test_the_database_refuses_a_duplicate_even_without_the_service`
proves the database refuses it rather than trusting the service to.

**No `organization_id` on any saved table.** A merchant has no business knowing who saved
their products, and a tenant column would put that one query away. Asserted by
`test_no_saved_table_carries_an_organization_column`.

**Indexes:** `customer_id`, the target id, and `created_at` on each saved table — the last
because saved lists sort most-recent-first and sorting a growing list in memory is the N+1's
quieter cousin.

## 2. The Look decision — §11 path A

Looks were a hardcoded array in the consumer bundle, identified by a slug whose only
authority was a TypeScript constant. **Saving against that would have been persistence in
name only**: a row pointing at a string no foreign key could protect, silently wrong the
moment somebody edited the array. That is the fake persistence §11 forbids, so path B
(blocking Saved Looks) was not needed and path A was taken.

**What a `Look` is now:** a real row, composed **by a person**, holding four curated
arrangements of the five real products. Extracted programmatically from the existing
editorial content rather than retyped, so the reviewed prose could not diverge through a
transcription slip.

**What it is NOT, and does not claim to be:** an outfit engine output. `LookItem.role` is
editorial prose, not a computed justification. **There is no total price and no column for
one** — every DEDUNET product is a prototype, so a look total would be a number the platform
invented. Its absence is the same decision the look detail page already stated in words.
Nothing about the recommendation engine, the outfit engine or Style DNA is started.

**A look whose products are not all present is skipped, never built partially.** A two-piece
outfit rendered with one piece is not a reduced look, it is a wrong one.

### One source of truth, and the guard that keeps it honest

The consumer still **renders** look copy from `content.ts`; the database is authoritative for
**identity**. That is two places for the same four looks, with exactly one way to hurt: rename
a slug in `content.ts` and the Looks page keeps working while every save silently 404s.

`test_look_slug_parity.py` asserts the two agree on every slug and on the products each look
is composed of. The duplication is recorded in §9 as a known limitation; the test is what
makes it survivable rather than a trap.

## 3. APIs

| Endpoint | Notes |
|---|---|
| `GET /me/saved` | counts + full state, one request |
| `GET /me/saved/state` | the slug sets — the endpoint that stops Home issuing 20 requests |
| `GET /me/saved/{products,brands,looks}` | paginated, `limit` clamped to 100, `created_at DESC, id DESC` |
| `POST /me/saved/{kind}/{slug}` | idempotent; 200 on both create and no-op |
| `DELETE /me/saved/{kind}/{slug}` | idempotent; unsaving something unsaved succeeds |
| `GET /looks`, `GET /looks/{slug}` | public curated content, read-only |

**Current-user semantics only.** Not one endpoint takes a customer id, in a path, a query or
a body — `test_a_saved_endpoint_never_accepts_a_customer_id` walks the route table and
asserts it. Identity comes from the bearer token via `current_customer`, which already
rejects a soft-deleted account with 401.

**Targets are addressed by slug, not numeric id.** The client already routes by slug, and a
sequential integer in a mutation path is an invitation to walk it.

**200, not 201, on save.** The client cares about the resulting state, not which request
created the row; making it distinguish the two would push it into treating a double tap as
an error.

**Ordering is `created_at DESC, id DESC`.** The timestamp alone is not a total order — two
saves in one transaction share it — and a list whose order wobbles makes pagination skip and
repeat rows.

**Summaries, not full documents.** A saved list of forty products does not carry forty
complete product payloads with every variant, media role and claim status. Asserted by
`test_a_saved_entry_is_a_summary_not_a_full_product_document`.

## 4. Authorization

| Check | Result |
|---|---|
| Anonymous — all 9 endpoints | **401** (parametrised test) |
| Customer A reads B's saved items | **cannot** — B's listing and state are empty |
| Customer A deletes B's row | **cannot** — succeeds as a no-op, A's row survives |
| Soft-deleted customer mutates | **401**, existing behaviour preserved |
| Saved id as an IDOR path | **impossible** — no endpoint accepts an id |

The isolation test uses **two real customers and two real tokens**; the browser version uses
two independent contexts, because a single context could pass by accident through local state.

## 5. Visibility and fixture safety

**Write-time and read-time differ, deliberately.**

You may only save what you could already see: a target failing the catalogue visibility test
answers **404, not 403**, because 403 confirms existence and turns `POST /me/saved/products/…`
into an enumeration oracle for unpublished and fixture content. Verified for an unpublished
product, a legacy product without an external identity in preview mode, an archived brand,
and an unknown slug.

Something **already saved** that later becomes unpublished stays in your list, flagged
`available: false`, with no image and no link — and remains removable. It was yours, and
silent disappearance from your own saved page is worse than being told it is not currently
available. Nothing hidden leaks, because that state is only reachable for a target that was
visible when it was saved.

**A fixture brand cannot be laundered through saved state.** Saving one goes through the same
`brands_visible` gate, and the saved entry carries `is_development_fixture` and
`fixture_notice` exactly as every other brand payload does.

## 6. Privacy and lifecycle

**Saved items are deleted with the customer, by two mechanisms, and both are needed.**

`ondelete=CASCADE` on `customer_id` covers a hard delete. But `erase_customer`
**pseudonymizes** — it keeps the customer row so order history stays reconcilable — so the
cascade never fires. Saved rows are therefore deleted explicitly in the erasure path, exactly
as addresses already are. Without that, an erased customer's taste would remain in the
database indefinitely. Both halves are tested.

**Events carry no customer identifier.** `product_saved` plus a slug is a product-popularity
signal; the same event plus a customer id is a behavioural profile, and this phase has no
consent basis for one. Asserted by
`test_saving_emits_an_event_without_a_customer_identifier`.

**No admin surveillance surface was built.** Internal operators have no view of customer
favourites. Saved items are personal data and browsing them is not an operational need.

## 7. Cross-surface consistency and performance

One shared context holds the saved set; every surface reads it and mutations patch it
locally. Saving on the product page updates the Shop card with **no refetch and no
full-page reload**.

**This is why `GET /me/saved/state` exists.** The obvious design gives each card its own
status request; Home renders more than twenty cards, against an API limited to 300 requests
per minute per client, and this platform already measured 22 API requests for one Home load.
Twenty more for bookmark icons is a rate-limit budget spent on decoration.

**The optimistic update has a real rollback.** The set changes before the request so the icon
responds immediately, and the previous value is restored on failure. An optimistic update
without a rollback is a lie with good latency — the control would show "saved" for a request
the server refused. `applyToggle` never mutates its input, which is what makes the rollback
possible, and that property is unit-tested.

## 8. Migration — `c7a41d9e8b52`

Staged: create the look domain, create the saved domain, seed the looks, then **verify**
(abort on any orphan look item or empty look).

### Integrity, on staging against PostgreSQL

| | Before | After |
|---|---|---|
| products / variants / brands / customers | 6 / 63 / 2 / 3 | **identical** |
| `md5` over every variant SKU and price | `093e0768…f974e2` | **identical** |
| every product's publication / sellable / route | unchanged | **unchanged** |
| looks / look_items | — | 4 / 10 |
| orphan look items | — | **0** |

`diff before.txt after.txt` is **empty**. No catalogue fact drifted.

### Rollback

Exercised both ways on a scratch database: downgrade drops the five tables and leaves
products, variants, prices, brands and customers intact; re-upgrade restores the looks.

**It is not free.** `downgrade()` destroys **customers' saved items** — real user data, not
derivable from anything, and not reconstructible by re-running `upgrade()` (unlike the brand
association, which was). Export the three saved tables first if the rows matter. Stated in
the migration docstring rather than left to be discovered.

## 8b. Verification

| Check | Result |
|---|---|
| Backend `pytest -q` | **701 passed, 2 skipped** (was 657) |
| — saved persistence | 34 |
| — look slug parity | 2 |
| Consumer unit tests | **26 passed** (was 13) |
| Browser E2E vs deployed `:13080` | **488 passed, 0 failed, 1 flaky**, 19.6m — 163 tests each on Chromium, WebKit and the Mobile Safari viewport |
| — new saved E2E | 9 per engine, **27 passing** on all three |
| — the flaky one | the saved refresh test on Chromium, which passed on retry. Named rather than absorbed into the pass count: this suite shares the general API limiter with static media, so an occasional refusal is genuinely possible and reporting a clean 489 would hide the known finding |
| Firefox | **NOT RUN** — cannot launch in this environment. Not claimed |
| `validate_product_data.py` | exit **0** |
| `validate_candidate_data.py` | exit **0** |
| `--assess-sellable` | exit **1**, required non-zero |
| `verify_side_a_package.py` | `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| `verify_packaged_assets.py` | `PACKAGED_BRAND_ASSETS_VERIFIED` |
| `build_brand_package.py --verify-no-drift` | `BRAND_PACKAGE_NO_DRIFT` |
| `controller_validate.py` | **PASS**, 0 errors, 3 pre-existing warnings |
| `git diff --check` | clean |
| Secret scan over tracked files | **0 hits**, including a check that the browser suite's password did not reach tracked source |
| OpenAPI contract | regenerated; **10 new paths**, no existing path changed |
| Mutation testing | **RUN. 18 of 18 guard removals detected, 0 survived** — every mutation registered against `services.py`, the one registered target this phase edited |

### Deployed verification, staging `http://10.0.0.2:13080/`

| Check | Result |
|---|---|
| Anonymous `GET /me/saved/state` | **401** |
| Save Source Tee | `{"saved":true,"created":true}` |
| Save again | `{"saved":true,"created":false}` — idempotent |
| Save DEDUNET brand, save a look | both 200 |
| `GET /me/saved` counts | `{products: 1, brands: 1, looks: 1}` |
| Unsave, then unsave again | `removed: true`, then `removed: false` — both 200 |
| Save a preview-hidden product | **404** |
| `GET /looks` | 4 curated looks |
| Security headers on `/` | **4/4** |
| `COMMERCE_MODE` | `BRAND_PREVIEW_MODE`, `purchasable: false` |

### Mutation testing

`services.py` is a registered mutation target and this phase edited it — the saved-item
deletion inside `erase_customer` — so §37 applies. All **18** mutations registered against
that file were run with `--only`:

```
M24 M25 M26 M28 M29 M30 M32 M33 M34 M35
M36 M37 M38 M39 M40 M41 M52 M61
MUTATIONS RUN: 18 · DETECTED: 18 · SURVIVED: 0
```

Two matter most here. `M28_erased_customer_never_emailed` guards the erasure path this phase
changed, and `M52_cart_enforces_purchasability` guards the purchase gate a save must never
affect. Both removals were still detected by their guarding tests.

> A first attempt appeared to run and did not: the mutation ids had been written to a file
> with Windows line endings, so every `--only` argument carried a trailing `
` and the
> harness answered "No mutation matches" eighteen times. Each returned exit 2, which the
> loop recorded — so the run reported itself as having done nothing rather than quietly
> reporting success. A second gap followed: `while read` dropped the final id because the
> file had no trailing newline, leaving 17 of 18 run. Both are noted because "the mutation
> suite passed" would have been a true sentence about a suite that executed nothing.

## 9. Known limitations

| Item | State |
|---|---|
| **Look copy is duplicated** | the consumer renders look prose from `content.ts` while the database is authoritative for identity. Guarded by `test_look_slug_parity.py`; converging the two is follow-up work |
| **Resume-after-login is not implemented** | a signed-out save sends the visitor to sign in with a return path; it does **not** replay the save afterwards. §6 permits this, and nothing implies otherwise |
| **Saved-state fetch is whole-set** | `GET /me/saved/state` returns every saved slug. Cheap for realistic sets and far cheaper than per-card requests; a customer with thousands of saves would want a windowed contract |
| **No saved-item reordering or collections** | a flat list per kind |
| **Admin has no saved-items view** | deliberate; see §6 |
| **Look save has no per-item state** | you save the arrangement, not individual garments within it |
| Firefox | **BLOCKED** — cannot launch in this environment |

## 10. Notes on two things that went wrong

**The browser suite registered a customer per test, and every dependent test failed.** The
cause was the application being right: registration is limited to **five per hour**
("account farming; an hour window because legitimate humans register once"), so nine
registrations in one run is exactly what that limiter exists to refuse.

> Loosening a real abuse control so a test suite is convenient is the wrong trade. The
> accounts are now created out of band by `manage.py create-test-customer` — the same
> pattern the administrator already uses — and the suite signs in, which is limited to 10
> per 60s and comfortably accommodates two logins.

Credentials come from the environment and are **never defaulted**; a password committed to
the repository would be a weak credential in tracked source, so the suite skips itself with a
clear reason when the variables are absent.

**Two stale disclosures had to be removed, and finding them was the point.** The product page
carried a **disabled** "Save" button beside *"Saving is not built. There is nowhere to store
it yet."*, and the look detail page carried its own version. Both are gone.

> The production disclosure rule cuts both ways. An unbuilt feature must say so; a built one
> must stop saying so. Leaving those sentences up would have been the same defect pointing in
> the other direction — and leaving the disabled buttons beside working ones would have given
> each page two save controls, one of which never works.

## 10b. Two defects the browser suite exposed, and what they cost

**A refetch race that only WebKit showed.** The Saved list refetched when the saved SET
changed — which happens **optimistically**, the moment the control is tapped and before the
DELETE has committed. The refetch could therefore be served the row the server was still
removing, and because the set did not change again, nothing triggered a second fetch: the
list sat showing an item the count said was gone.

Chromium hid it completely. WebKit and the Mobile Safari viewport failed on it
**consistently**, on both engines, every run.

> **An optimistic update is a claim about the future; a list must follow the past.** The fix
> was to have lists depend on a version that advances only once a mutation has **settled**
> against the server — success or rollback — rather than on the optimistic set. Running three
> engines is what turned a silent, intermittent staleness into a reproducible failure.

**Three failures that were not about this feature.** An earlier full-suite run reported three
failures. The API log settled it: **8 × 429**, of which **7 were static media requests**
(`/api/v1/media/assets/...`) and one was a saved mutation refused as collateral.

That is the **already-recorded** media-delivery finding — static product media shares the
general 300-per-minute API limiter, and one page load costs roughly twenty media requests.
§24 of this phase's brief says not to touch it, and it was not touched.

> **The limiter was not raised and no assertion was weakened.** What changed is that this
> suite stopped adding avoidable load: `expectSignedIn` was loading a full media-heavy page
> on every test purely to confirm a token, and the per-test reset was clearing both accounts
> when one was in use. Reducing request rate rather than relaxing the check is the same
> decision the repository already made when it dropped the browser suite to one worker.

## 10c. A broken build inherited from Phase 4, and what it was really about

The first CI run on the published repository failed the `backend` job on all three Python
versions. Not flakiness, and **not this phase**:

```
HARNESS ERROR: anchor for M60_legacy_hidden_in_preview matched 2 times
in app/commerce/api.py (expected exactly 1)
```

`M60` anchors a mutation on the single line implementing "preview mode hides the legacy
catalogue" and requires it to appear exactly once in its target file. **Phase 4 added a second
copy** in the brand detail endpoint (`b8079bc`), making the anchor ambiguous, and the harness
refused to run rather than mutate a line it had guessed at.

> **That is the guard registry working.** A mutation that cannot identify the line it is meant
> to remove proves nothing, so stopping is the correct behaviour. The build did not fail
> because a test broke; it failed because a *guard could no longer be trusted*, which is the
> more useful signal of the two.

**Why nobody saw it for a phase.** The repository was created after Phase 4, so CI had never
run on that commit. The first run happened on the publication commit, and that run's outcome
was not checked — the decision at the time was "I'm not going to poll it for an hour", which
left a known-unverified build behind. The breakage then sat through an accepted phase.

**The underlying defect was duplication, not the anchor.** By the time CI caught it, the rule
existed in **four** places: the catalogue listing, the brand detail endpoint, `brand_api`'s
count and cover maps, and the saved-items service. Every copy was correct. The problem is what
four copies of a *visibility* rule mean — the fifth surface carries a fifth, and the first one
anybody forgets shows a customer the legacy catalogue.

So the rule moved into `app/commerce/catalog_scope.py`, once, with three entry points
(`visible_products`, `apply_preview_scope`, `is_visible`) for the three shapes callers need.
`M60` was retargeted to that module: the guard is unchanged, only its address is.

**Full harness after the fix: 77 mutations run, 77 detected, 0 survived, 0 harness errors**, with the post-restore suite green at 701. This is the whole registry, not the 18 `services.py` mutations run earlier in the phase.

Two gaps in the PostgreSQL parity job's expected-table set were closed while here: the five new saved/look tables, and `product_media`, which had existed since the DEDUNET media phase and was never checked. That check compares `expected - actual`, so a table missing from the list is a table nobody notices is missing. All 26 tables are now covered, with no phantom entries.

## 11. Sensitive backup status — §26

The Phase 4 pre-migration PostgreSQL dump contained customer rows including **PBKDF2 password
hashes**. It was never committed (caught while staged, and `.gitignore` now refuses
`evidence/**/*.sql`).

Its rollback window closed when the multi-brand network was accepted on 2026-09-30, so it was
**removed**: overwritten three times with random bytes, then deleted. Its contents were never
read or printed.

> Honest caveat: overwrite-then-delete defeats casual recovery but is **not** a guarantee on
> an SSD with wear levelling, where the original blocks may persist until the controller
> reuses them.

One older backup remains at `backups/dedunet_slice-20260807T004046Z.dump`, from the
backup-and-restore runbook work. It is gitignored, untracked, predates this phase, and shows
no credential material on inspection. It was left in place rather than deleted, because it is
not this phase's artifact to remove.

**No database dump is included in this evidence.**
