# DEDUNET Integration Closure — Evidence

| Control | Value |
|---|---|
| Artifact ID | EV-DDN-002 |
| Version | 1.0 |
| Date | 2026-08-06 |
| Owner | Side B technical lead |
| Supersedes status of | `EV-DDN-001` (`DEDUNET_INTEGRATION_CONDITIONALLY_VERIFIED`) |
| Preserved | `EAS_PROJECT_CONFIGURATION_VERIFIED` · `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` |
| **Decision** | **`DEDUNET_INTEGRATION_VERIFIED`** |

`EV-DDN-001` records the integration as it stood and is **not** rewritten. This document
records what closed its conditional.

---

## 1. Gaps this closure resolves

| Gap in `EV-DDN-001` | Status |
|---|---|
| Web and admin chrome still showed MERET | **CLOSED** |
| Product media not fetchable | **CLOSED** — 18/18 resolve |
| Mobile did not render a gallery | **CLOSED** |
| No synthetic-stock loader; nothing transactable | **CLOSED** |
| Test orders not flagged in the data model | **CLOSED** |
| Notification identity not rebranded | **CLOSED** |
| `packages/brand/` drift not enforced | **CLOSED** |
| Legacy fixture visible in the DEDUNET catalogue | **CLOSED** |

---

## 2. Commit confirmation

```text
branch  dedunet/repository-restructure-and-workstreams-a-f
HEAD    2a6267ee09d649be797775af3cd646b4d72f123c
status  (clean, 0 lines including untracked)
```

Accepted integration range `f9b9f5f..2a6267e` verified present before any change.

---

## 3. Brand chrome

Web: title, meta description, favicon, header (Side A `logo-primary.svg`), notice, footer.
Admin: title and header. Both load a **generated** seam, `apps/*/brand.generated.js`, emitted
from `packages/brand` — neither client hard-codes brand strings.

**Active customer-facing legacy references: 0.**

```bash
grep -rniE '\bmeret\b|\bmeryt\b' apps/web/{index.html,app.js,styles.css} \
                                 apps/admin/{index.html,admin.js,styles.css} \
  | grep -vE 'meret_cart|meret_token|meret_role|meret_admin_token|legacy brand prefix'
# -> 0
```

Guarded permanently by `test_no_active_customer_facing_legacy_brand`, which asserts the
scanned files exist so an exclusion cannot empty the check.

### Classified, not replaced

- **Migration-sensitive:** `localStorage` keys `meret_*` → `dedunet_*`, each with a one-time
  migration that moves the value across. Renaming without it signs every session out and
  silently discards a live cart.
- **Demo accounts:** `@meret.example` → `@dedunet.example` in the two seed constants and the
  three test files referencing the literal. Reserved domain; no financial record references
  an email.
- **Untouched:** product names, `MRT-*` SKUs (referenced by `order_lines`, which are
  financial records), database names, and all historical evidence.

`PROVISIONAL_NOT_LEGALLY_CLEARED` is carried in the generated seam for admin and governance,
not as customer marketing.

---

## 4. Asset serving

```
Side A handoff (immutable)
  -> build_brand_package.py : validate + copy + checksum
  -> packages/brand/assets/ : 31 files, byte-verified against source digests
  -> GET /api/v1/media/{path}
```

Runtime never reads `handoffs/incoming/`. Each copy's SHA-256 is re-checked as it is written.

| Check | Result |
|---|---|
| Product media URLs | **18/18 → 200** |
| Brand assets | **31/31 → 200** |
| Content type | `image/svg+xml` (allow-list, not deny-list) |
| `X-Content-Type-Options` | `nosniff` on every response |
| Traversal `../`, encoded, nested | **404** |
| Dotfile probes (`.env`, `.git/config`) | **404** |
| Directory / root | **404** — no listing, no index |
| Missing asset | **404** |
| Non-image inside the package (`tokens.css`, `products.json`) | **404** |

### SVG safety

Validated at **build** time, not filtered at serve time: a build-time refusal is reviewable
in a diff; a serve-time filter has to be right on every request. An SVG is an XML document a
browser executes — active content, not an image.

Rejected: `script`, `foreignObject`, `handler`, `set`, `animate`; `on*` attributes;
`javascript:` URLs; `<!DOCTYPE`/`<!ENTITY>`; any `href`/`src` that is not a fragment or a
`data:` image.

All 30 committed SVGs pass. The validator is proven load-bearing by five synthetic hostile
documents, each of which it rejects.

---

## 5. Web and mobile media

Web renders primary and additional media with Side A alt text, deterministic order, a
concept-media label and no broken URLs.

Mobile gains `src/components/Gallery.tsx`: ordered strip, per-image failure placeholder that
leaves the rest of the gallery working, Side A alt text preferred over generated labels, and
**nothing rendered at all** when there is no media rather than a broken image.

12 gallery tests: four-media DDN-TS01, order preserved, single image, empty media, failed
image, accessibility labels, absolute URL construction, concept labelling, and no "made in".

---

## 6. Legacy-catalogue isolation

Scoped by **mode**, not by a second setting that could disagree with the first:

| Mode | Catalogue |
|---|---|
| `BRAND_PREVIEW_MODE` | exactly the **5** DEDUNET products |
| `COMMERCE_TEST_MODE` | legacy demo + DEDUNET (what the sandbox needs) |

Applied to the listing **and** the detail endpoint — filtering only the list leaves every
legacy product reachable by direct URL, which is a filter a deep link walks around. Verified:
`/catalog/products/oversized-crew-tee-black` → **404** in preview.

Nothing is deleted. Admin retains full visibility and labels prototype rows
`[DDN-TS01 · PREVIEW — NOT SELLABLE · evidence DRAFT]`.

DEDUNET visible counts: **5 products / 62 variants / 62 unique SKUs.**

---

## 7. Synthetic test inventory

`manage.py load-test-inventory --confirm-test-only` · `clear-test-inventory`

| Guard | Result |
|---|---|
| Refuses `BRAND_PREVIEW_MODE` | ✅ |
| Refuses `PUBLIC_COMMERCE_MODE` | ✅ (refused by `current_mode()` itself) |
| Refuses without `--confirm-test-only` | ✅ |
| Typed as `synthetic_test_stock` | ✅ never inferred from a quantity |
| Idempotent | ✅ sets, never accumulates |
| Cleanup restores zero stock + `sellable=false` | ✅ |
| Never touches origin / material / evidence / legal | ✅ |
| Unknown SKU refused rather than loading nothing | ✅ |

**Effective sellability is computed at request time** from mode AND inventory state. A
variant carrying synthetic stock is unbuyable the instant preview is selected — no database
cleanup, no window. A test flips the mode mid-flight and asserts the second `add_to_cart`
raises while the first succeeded.

Not loaded during staging startup.

---

## 8. Test-order provenance

`orders.commerce_mode_at_checkout`, recorded at purchase so a later mode change cannot
reclassify an order that already happened. API exposes it plus `is_test_order`.

Existing orders migrate to **`LEGACY_UNCLASSIFIED`** — the only honest value. They predate
modes: `PUBLIC_COMMERCE_MODE` would fabricate a commercial history, `COMMERCE_TEST_MODE`
would be a guess.

```text
populated upgrade -> FC-OLD2 | LEGACY_UNCLASSIFIED
orders labelled PUBLIC_COMMERCE_MODE : 0
new test-mode order                  : COMMERCE_TEST_MODE, is_test_order true
```

---

## 9. Notification identity

Subjects carry `DEDUNET —` and any order not positively known to be public commerce is
prefixed **`[TEST ORDER]`**. Safe default: over-disclose. A test order that reads like a real
confirmation is the one notification defect a customer cannot detect for themselves.

Delivery semantics untouched: at-least-once, claim leases, stale-worker fencing,
erased-customer suppression, maximum attempts. `EXTERNAL_SMTP_DELIVERY_PENDING` preserved —
no real message has been sent.

---

## 10. Brand-package drift enforcement

`build_brand_package.py --verify-no-drift` rebuilds into a temporary directory and compares
bytes; the committed package is never mutated.

Fails on: differing files, missing files, extra files, count mismatch, and a stale
`brand.generated.js` in either client.

**Proven load-bearing three ways** — tampering a package file, deleting one, and staling the
seam each produce `BRAND_PACKAGE_DRIFT_DETECTED` and exit 1; the clean tree exits 0.

It immediately caught a real defect: Git line-ending normalization rewrote the copied SVG
bytes and broke their checksums. Fixed with a `packages/brand/assets/** -text` rule — the same
class of bug that already forced the handoff rule.

Status: **`CI_CONFIGURATION_UPDATED_AND_VALIDATED_LOCALLY`.** Not `CI_EXECUTED_ON_GITHUB`;
no runner and no remote exist.

---

## 11. Migration

Revision `a7c31f9be402`, additive. Verified on PostgreSQL by **execution**: clean upgrade,
populated upgrade with correct `LEGACY_UNCLASSIFIED` backfill, index created, **downgrade
executed** (column dropped, orders preserved), re-upgrade to head.

---

## 12. Regressions

| Check | Result |
|---|---|
| Side A checksums | **54/54**, handoff untouched |
| Brand-package drift | **NO_DRIFT** |
| SQLite backend suite | **249 passed, 1 skipped** |
| PostgreSQL backend suite | **250 passed** |
| Mobile TypeScript | exit **0** |
| Mobile tests | **117 passed** |
| Expo web export | exit 0 |
| OpenAPI | one path added (`/api/v1/media/{asset_path}`), 30 total, contract committed |
| Active legacy-brand scan | **0** |
| Staging / rate limiting / notification worker | unaffected |

Backend grew 219 → 249 (**30 closure tests**). No existing test weakened, deleted or skipped.

---

## 13. A flake found, measured, and not papered over

`test_concurrent_reservation_never_oversells` failed once during closure work.

Investigated rather than retried:

- Rate: **1 failure in 40 runs** (~2.5%), SQLite only. The PostgreSQL suite passes it.
- The failure is on the **winner-count** assertion, which counts in-process booleans. The
  test never reaches its database assertion.
- A direct 60-run probe of the actual invariant found **0 overselling** and **0** mismatches
  between reported wins and `reserved`.

Conclusion: a test-harness artifact of threads sharing one in-memory SQLite connection via
`StaticPool`, not a defect in the reservation guard. **The test was not weakened, retried or
marked flaky** — it is recorded here as a known limitation.

I could not establish whether it predates this work: my attempt to measure at `HEAD` stashed
`packages/brand`, so those runs failed on missing files rather than on concurrency. That
comparison is therefore **not** claimed.

---

## 14. Known limitations

- **`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`** — no native binary; unchanged.
- **`LEGAL_CLEARANCE_PENDING`** and `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` — unchanged and
  unreachable by configuration.
- The SQLite concurrency flake above.
- Media is served by the **API**, not a CDN or nginx. Fine locally; a hosted deployment
  should serve static assets from the edge.
- Concept SVGs are served inline. `nosniff` is set and the content is build-validated, but no
  `Content-Security-Policy` is applied to the media response.
- The web client renders media but has no lightbox, zoom or responsive `srcset`.
- Mobile renders SVGs through `Image`, which relies on platform SVG support; this was
  verified in tests and on Expo **web**, not on a device.
- Synthetic inventory has no expiry — it persists until `clear-test-inventory` is run.
- Test orders are marked in data, API and notification subject, but the customer-facing web
  order view does not yet display the marker.
- Fonts remain manifest-only; no binary ships.
- `--verify-no-drift` is wired into local validation and CI configuration, but CI has still
  never executed.

---

## 15. Rollback

Additive throughout.

```bash
cd services/commerce-api && python -m alembic downgrade e4b7a91c2d55   # order provenance
git revert --no-edit <closure range>
```

Downgrade is executed and preserves orders. Reverting restores the previous chrome and
removes the media route; `packages/brand/assets` is regenerated by the build.

---

## 16. Commit range

| Commit | Milestone |
|---|---|
| `31b2e07` | brand chrome |
| `f17dad3` | media serving and rendering |
| `f901848` | synthetic inventory and order provenance |
| (this) | notification identity, drift enforcement, closure tests, evidence |

Closure range: **`2a6267e..HEAD`**. Integration range `f9b9f5f..2a6267e` unchanged.

---

## 17. Decision

**`DEDUNET_INTEGRATION_VERIFIED`**

Every conditional from `EV-DDN-001` is closed and independently verified. Zero active
customer-facing legacy references; 18/18 media and 31/31 assets serve with correct types,
`nosniff` and every unsafe path refused; the DEDUNET catalogue shows exactly 5/62/62 with the
legacy fixture hidden from listing and deep link alike; synthetic stock is typed, confirmed,
idempotent, cleanable and powerless in preview; orders carry honest provenance; notifications
carry the DEDUNET identity and mark test orders; brand drift is enforced and proven
load-bearing.

Public commercial launch remains **BLOCKED**. This closure prepares the branded vertical
slice; it is not that slice.
