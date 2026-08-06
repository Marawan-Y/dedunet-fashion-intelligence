# DEDUNET Integration — Final Verification

| Control | Value |
|---|---|
| Artifact ID | EV-DDN-003 |
| Version | 1.0 |
| Date | 2026-08-06 |
| Owner | Side B technical lead |
| Starting HEAD | **`3360667a6d72d6aeca972b39b92ca781458b9901`** |
| Scope | Verification only. No feature work |
| Preserved | `EAS_PROJECT_CONFIGURATION_VERIFIED` · `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` |
| **Decision** | **`DEDUNET_INTEGRATION_VERIFIED`** |

Addendum to `EV-DDN-001` and `EV-DDN-002`. Neither is rewritten.

---

## 1. Clean-state confirmation

```text
branch  dedunet/repository-restructure-and-workstreams-a-f
HEAD    3360667a6d72d6aeca972b39b92ca781458b9901   (expected closure HEAD)
status  (empty)
porcelain -uall  0 lines
```

---

## 2. Complete mutation verification

Run from the clean committed tree with no shortened timeout.

| Metric | Value |
|---|---|
| Registered mutations | **59** |
| Anchors resolved | **59 / 59** |
| Missing anchors | **0** |
| Detected | **59** |
| Survived | **0** |
| Skipped | **0** |
| Harness errors | **0** |
| Source restored | verified — post-run suite **249 passed, 2 skipped**, exit 0 |
| Exit code | **0** |

```text
MUTATIONS RUN: 59
DETECTED:      59
SURVIVED:      0
RESULT: every guard removal was detected by its guarding test.
```

No mutation was removed to obtain this result. The registry moved 55 → 59 by adding four
closure guards; the two that could not be satisfied are disposed of in §4, not deleted to
manufacture a green run.

### A polluted earlier run, discarded

An earlier attempt reported `HARNESS ERROR: source was not restored cleanly`. Cause: I was
editing `test_commerce_e2e.py` while the harness ran in the background, so it observed a
half-written file. That run is discarded, not reported. The clean run above replaces it, and
the working tree was checked for mutation residue afterwards (0 `MUTATED:` markers outside the
harness's own definition strings).

---

## 3. Individual closure-guard attacks

Each was applied alone, and the failure was read to confirm the intended reason rather than a
non-zero exit.

| ID | Protected behaviour | Mutation | Expected failing test | Actual | Failure reason | Restored |
|---|---|---|---|---|---|---|
| **M58** | synthetic inventory refuses outside `COMMERCE_TEST_MODE` | `if mode != modes.COMMERCE_TEST:` → `if False:` | `test_synthetic_inventory_refuses_preview_mode` | same | `TestInventoryRefused` not raised in preview | ✅ |
| **M59** | synthetic inventory refuses without confirmation | `if not confirmed:` → `if False:` | `test_synthetic_inventory_refuses_without_confirmation` | same | loaded without `--confirm-test-only` | ✅ |
| **M60** | preview catalogue excludes the legacy fixture | drop the `external_product_id IS NOT NULL` filter | `test_preview_mode_shows_only_dedunet_products` | same | legacy product leaked into the DEDUNET catalogue | ✅ |
| **M61** | non-public order marked in the notification subject | drop the `[TEST ORDER]` prefix | `test_order_notifications_carry_the_dedunet_identity` | same | subject lacked the marker | ✅ |
| **M49–M55** | public-mode refusal, preview block, non-sellable refusal, cart boundary, float rejection, decimal rejection, zero-stock refusal | see registry | respective DEDUNET tests | same | each as stated | ✅ |

None failed from a syntax error, import error, missing file, missing anchor, broken runner or
unrelated test: the whole-registry run reports **0 harness errors** and **0 missing anchors**,
and the restored suite is green.

---

## 4. M56 / M57 disposition

**`REDUNDANT_DEFENCE_LAYER — BEHAVIOUR VERIFIED BY HOSTILE-PATH TEST`**

These are **not** detected mutations and are not counted as such. They were removed because
the media route layers four independent controls, so removing any one leaves the externally
observable result unchanged — another control still blocks the request. A permanently
unsatisfiable entry would make the harness report failure forever and destroy its signal.

The controls, in order:

1. raw `..` / absolute / backslash early exit,
2. dot-segment rejection,
3. `is_relative_to(_MEDIA_ROOT)` containment (the real control),
4. `is_file()` — a directory is a 404, never a listing,
5. media-type allow-list.

`test_unsafe_or_missing_media_paths_are_refused` plus `test_media_route_never_serves_a_non_image`
cover every required behaviour end to end:

| Required behaviour | Case | Result |
|---|---|---|
| traversal | `../../../../etc/passwd` | 404 |
| encoded traversal | `..%2f..%2fbrand.json` | 404 |
| containment escape | `../brand.json` | 404 |
| absolute path | leading `/` rejected before resolution | 404 |
| directory access | `assets/brand-prototype/logos` | 404 |
| directory listing refusal | no index, no autoindex anywhere | 404 |
| root | `/api/v1/media/` | 404 |
| missing asset | `.../nope.svg` | 404 |
| hidden / unrelated file | `.env`, `assets/../../../.git/config` | 404 |
| invalid extension / type | `../tokens.css`, `../products.json`, `../NORMALIZATION_REPORT.json` | 404 |

Confirmed: removing any one internal branch does not change the externally observable
security result, because an independent control still blocks it.

---

## 5. SQLite concurrency flake — root cause and resolution

### Investigation

My first hypothesis — that only the reported winner *count* was unreliable — was **wrong**,
and restructuring the assertions around it made the rate worse (**11 failures in 120**).
Capturing the actual error gave the real cause:

```text
sqlite3.InterfaceError: bad parameter or other API misuse
```

The shared in-memory test engine is `StaticPool` with `check_same_thread=False`, which hands
**every session the same `sqlite3.Connection`**. Python's `sqlite3` does not support
concurrent statement execution on one connection. Twenty threads executing `UPDATE` on it is
driver misuse, and it surfaced as either an `InterfaceError` or a `rowcount` read from another
thread's statement — one polluted run reported *"6 threads were told they won but only 5 units
were reserved"*, which is exactly that.

The database was never wrong. The conditional
`UPDATE ... WHERE on_hand - reserved >= :qty` guarantees the invariant regardless of how the
driver is abused, and a direct 60-run probe found **0 overselling** and **0** win/`reserved`
mismatches.

### Resolution — deterministic, and stronger

The test now runs against a **file-backed SQLite database with a normal connection pool**, so
each thread gets its **own** connection. The driver misuse disappears, which makes both the
database invariant **and** the winner count deterministic. The assertions are therefore
stronger than the original, not weaker:

1. `reserved <= on_hand` — never oversold;
2. `sum(wins) == reserved` — successful reservations equal committed quantity;
3. `sum(wins) == 5` — exactly the available quantity succeeded;
4. `failures == []` — no thread exception is swallowed;
5. no dependence on `StaticPool` scheduling.

A second test, `test_concurrent_reservation_winner_count_is_exact_on_postgresql`, asserts the
exact winner count under **real per-connection row locking**, on its own engine.

Nothing was removed, retried, skipped or marked flaky.

### Stress result

```text
runs                     : 120
passes                   : 120
failures                 : 0
overselling incidents    : 0
winner/reserved mismatch : 0
thread exceptions        : 0
```

(Before the fix, the same 120-run stress produced **11** failures.)

### A second defect this exposed

Adding the PostgreSQL winner-count test caused **6 notification tests to fail in the full PG
suite while passing 38/38 in isolation**: twenty concurrent sessions borrowed from the shared
pool starved the tests that ran afterwards, which use `FOR UPDATE SKIP LOCKED` and their own
threads. Fixed by giving that test its own engine and pool. PG suite: **251 passed**.

---

## 6. Final regression results

| Check | Result |
|---|---|
| SQLite backend suite | **249 passed, 2 skipped** |
| PostgreSQL backend suite | **251 passed** |
| Backend mutation harness | **59 run, 59 detected, 0 survived, 0 errors** |
| Mobile TypeScript | exit **0** |
| Mobile tests | **117 passed** |
| Mobile mutation harness | **18 detected, 0 survived, 0 errors** |
| Expo web export | exit 0 |
| Side A checksums | **`DEDUNET_HANDOFF_INTEGRITY_VERIFIED`** (54/54) |
| Brand-package drift | **`BRAND_PACKAGE_NO_DRIFT`** |
| OpenAPI drift | **NONE** |
| Staging readiness | `/ready` **200** |
| Rate-limit smoke | 10×401 then 2×429 |
| Notification-worker smoke | healthy, outbox drained |
| Product-media asset smoke | **18/18** + **31/31** → 200, `nosniff` |
| Secret scan | **0** over 367 tracked files |
| Personal-data scan | **0** non-reserved addresses |
| Active customer-facing MERET/MERYT | **0** |

The 2 SQLite skips are the two PostgreSQL-only tests (`FOR UPDATE SKIP LOCKED`, exact winner
count) — both execute on PostgreSQL.

### Catalogue counts

```text
products      : 5
variants      : 62
unique SKUs   : 62
product media : 18
assets        : 31
```

---

## 7. Remaining limitations

Unchanged from `EV-DDN-002` §14, plus:

- The SQLite concurrency test now writes a temporary database file rather than using the
  shared in-memory engine. Marginally slower; deterministic in exchange.
- The rest of the suite still runs on the shared `StaticPool` in-memory engine. Any future
  multi-threaded test must use its own engine, or it will hit the same driver misuse.
- `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` and `LEGAL_CLEARANCE_PENDING` unchanged.
- `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` unchanged — no native binary.
- CI remains `CI_CONFIGURATION_UPDATED_AND_VALIDATED_LOCALLY`; no runner and no remote exist.

---

## 8. Rollback

Verification-only. The single behavioural change is test-side.

```bash
git revert --no-edit <this commit>
```

Reverting restores the previous concurrency test, which reintroduces the ~9 % flake. No
application code, schema, migration or contract changed in this milestone.

---

## 9. Decision

**`DEDUNET_INTEGRATION_VERIFIED`**

59/59 mutations detected with none surviving, no missing anchors and no harness error; every
closure guard individually attacked and confirmed to fail for its intended reason; M56/M57
disposed of as redundant defence layers with their behaviour verified by a ten-case
hostile-path test; the SQLite concurrency flake root-caused to driver misuse, fixed
deterministically with stronger assertions, and stressed 120/120; and the full regression
sweep green with 0 customer-facing legacy references and exact catalogue counts of 5/62/62/18.

Public commercial launch remains **BLOCKED**. The branded end-to-end vertical slice has not
been started.
