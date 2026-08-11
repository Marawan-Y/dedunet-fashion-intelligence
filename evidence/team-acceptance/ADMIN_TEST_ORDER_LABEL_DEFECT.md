# Team-acceptance defect — admin test-order label

**Artifact ID:** EV-TA-002 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED` · **Date:** 2026-08-11
**Frozen baseline before this defect:** `09a666d` (*fix: configure admin API origin in staging*)
**Reported by:** human acceptance testing, Test 4H (script step 13)
**Result:** `ACCEPTANCE_DEFECT_FIXED`

`PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` remains in force. Nothing in this correction activates
public commerce, configures real payments, stock, fulfilment or SMTP, alters legal or
trademark status, introduces production credentials, or touches real customer data.

---

## 1. Starting state

| | |
|---|---|
| Repository | `C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack` |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| HEAD | `09a666deec7cec5e1f31cf1b10da6c57c9584de8` |
| Working tree | clean |

Staging was found — and left — in `COMMERCE_TEST_MODE`, `/ready` **200**.

## 2. Human reproduction

The tester reported that the admin Orders page listed the synthetic acceptance order exactly
as it would list a real one: order number, **PAID**, **EUR 80.90**, `1 × DDN-SRC-CAR-XS`, and
a **Fulfil** button — with no mention of `COMMERCE_TEST_MODE` or `is_test_order` anywhere on
the page. The cancelled decline attempt `FC-639D8B8F` was listed the same way.

Reproduced before changing anything, by rendering the frozen `apps/admin/admin.js` in a real
DOM against the acceptance payload:

```text
row 1  "FC-FAFBAB8A1× DDN-SRC-CAR-XSpaid€80.90—FulfilCancel"
row 2  "FC-639D8B8F1× DDN-SRC-CAR-XScancelled€80.90—"

mentionsTestOrder        false
mentionsCommerceTestMode false
resolved API base        http://127.0.0.1:18080      (09a666d seam already correct)
```

Rendered, not read. The provenance fields were present in the input payload and absent from
the output DOM, which is the whole defect and is not visible in a source-text check.

## 3. Backend provenance confirmation

**Not a backend defect.** Confirmed independently at three levels, none of them documentary.

**Serializer** — `services/commerce-api/app/commerce/api.py:538` `_order_payload`:

```python
"commerce_mode_at_checkout": order.commerce_mode_at_checkout,
"is_test_order": order.commerce_mode_at_checkout == "COMMERCE_TEST_MODE",
```

**Live staging database** — both acceptance orders carry the mode:

```text
 order_number |  status   | commerce_mode_at_checkout
--------------+-----------+---------------------------
 FC-639D8B8F  | CANCELLED | COMMERCE_TEST_MODE
 FC-FAFBAB8A  | PAID      | COMMERCE_TEST_MODE
```

**Deployed API image, run against that live database** — the exact response body the admin
endpoint returns, produced by the deployed serializer itself:

```json
{
  "order_number": "FC-FAFBAB8A",
  "status": "paid",
  "commerce_mode_at_checkout": "COMMERCE_TEST_MODE",
  "is_test_order": true,
  "currency": "EUR",
  "subtotal_minor_units": 7200,
  "shipping_minor_units": 890,
  "tax_minor_units": 1292,
  "total_minor_units": 8090,
  "lines": [{ "sku": "DDN-SRC-CAR-XS", "product_name": "The Source Tee",
              "size": "XS", "color": "Carbon", "quantity": 1,
              "unit_price_minor_units": 7200, "line_total_minor_units": 7200 }],
  "shipments": []
}
```

Backend test-order provenance: **PASS**. It matches what the human tester observed over HTTP.

## 4. Root cause

`viewOrders()` in `apps/admin/admin.js` built each row from `order_number`, `lines`,
`status`, `total_minor_units` and `shipments` only. **`is_test_order` and
`commerce_mode_at_checkout` were never read.**

The backend has recorded both since the `a7c31f9be402_order_commerce_mode_provenance`
migration; the renderer was never extended to consume them. So the provenance existed, was
correct, was transmitted on every response — and stopped at the last hop, the one where a
person makes the decision.

This is a different failure from the two configuration defects closed earlier in this
programme, and worth naming as such: nothing was misconfigured and nothing was wrong in
isolation. A field was simply never displayed, and the surface that omitted it is the one an
operator uses to decide whether to commit stock.

## 5. Correction

Read the provenance the API already sends and show it on the row, next to the order number,
above the Fulfil control.

| File | Change |
|---|---|
| `apps/admin/admin.js` | `TEST_COMMERCE_MODE` constant; `isTestOrder(order)` predicate; `testOrderMarker(order)` node builder; the marker rendered in the Order cell of each row. |
| `apps/admin/admin.css` | `.provenance`, `.tag--test`, `.provenance__mode` — an amber bordered badge, distinct from the green `tag--ok` status tag. |
| `services/commerce-api/tests/test_admin_order_provenance.py` | **new** — 26 tests rendering the real bundle in a real DOM. |
| `scripts/validation/mutation_guard_check.py` | **new** mutation `M72`. |

Operator-facing result, per row:

```text
FC-FAFBAB8A
[TEST ORDER]  COMMERCE_TEST_MODE
1× DDN-SRC-CAR-XS
```

Design decisions worth stating:

* **Either signal alone labels the row.** `is_test_order === true` **or**
  `commerce_mode_at_checkout === "COMMERCE_TEST_MODE"`. The boolean is derived from the mode
  server-side so they always agree today; requiring both would make the label depend on that
  derivation never being dropped from a projection.
* **Strict on both.** Only an exact `true` and the exact mode string count. JSON that has
  been through a form encoder arrives as the string `"false"`, which is truthy, and as
  `0`/`1`, which are not booleans. A loose check would brand real orders as tests — the
  mirror-image defect, and no less serious, because an operator who learns the badge is
  unreliable stops reading it. The mode string is the backstop that lets the check stay
  strict safely.
* **The raw mode string, not a paraphrase.** `COMMERCE_TEST_MODE` is the wording of the audit
  record and of acceptance script step 13. Showing it unchanged lets an operator match the
  screen to both without trusting that a friendlier phrasing means the same thing.
* **In the Order cell, above the buttons.** Reading the row top-to-bottom reaches the
  provenance before the eye arrives at **Fulfil**. A separate column would sit two columns
  away and show `—` on every real order.
* **Text, not colour.** "TEST ORDER" is a text node, so it survives colour blindness, a
  monochrome display and a screen reader. Verified in the deployed page's accessibility tree.
* **Absent is not a test.** Missing or null provenance renders an ordinary unlabelled row —
  silence, not a guess — and never throws.

Nothing else was touched: no backend provenance semantics, no payment behaviour, no
inventory behaviour, no order status, no fulfil/cancel semantics, no storefront behaviour,
no mobile behaviour, no API auth, no credentials. `FC-FAFBAB8A` was **not** fulfilled.

### Deliberately not fixed here

The storefront top banner still reads *"Prototype storefront. Preview only — nothing here is
available to purchase…"* while staging is in `COMMERCE_TEST_MODE`. It is misleading and it is
recorded, but it is a separate issue and is not the blocking acceptance defect. Mixing it
into this commit would make both harder to review and to revert.

## 6. Test evidence

`tests/test_admin_order_provenance.py` — **26 passed**. It renders the real
`apps/admin/admin.js` through jsdom, the same mechanism `test_web_gallery.py` already uses
for the storefront. A source-text assertion cannot establish that a badge reaches the
screen, and "the backend field is correct" was already true while the defect was live.

| Required property | Tests |
|---|---|
| A — `is_test_order` + mode renders an unmistakable **TEST ORDER** | `test_the_acceptance_order_is_labelled_a_test_order`, `test_the_label_sits_in_the_same_cell_as_the_order_number` |
| B — `COMMERCE_TEST_MODE` is visibly represented | `test_the_commerce_mode_is_shown_verbatim`, `test_both_signals_appear_when_the_api_sends_both`, `test_either_provenance_signal_alone_is_enough` (2 cases), `test_the_flag_alone_still_labels_even_with_no_mode_string` |
| C — a normal non-test order gets no badge | `test_a_real_order_gets_no_test_label`, `test_the_marker_is_absent_not_empty_for_a_real_order`, `test_the_predicate_is_strict_about_what_counts` (12 inputs) |
| D — missing optional provenance does not crash | `test_incomplete_payloads_render_without_throwing` (3 cases), `test_an_order_with_no_provenance_keys_is_not_labelled`, `test_an_order_with_no_lines_still_labels_and_renders` |
| E — existing PAID rendering unchanged | `test_paid_rendering_is_unchanged` |
| F — existing CANCELLED rendering unchanged | `test_cancelled_rendering_is_unchanged`, `test_the_acceptance_pair_renders_together_as_the_operator_sees_it` |
| G — Fulfil and Cancel functionally unchanged | `test_the_paid_row_still_offers_fulfil_and_cancel`, `test_fulfil_still_posts_to_the_fulfil_endpoint`, `test_cancel_still_posts_to_the_cancel_endpoint` (both buttons really clicked in the DOM against a stubbed transport) |
| H — no XSS / `innerHTML` regression | `test_hostile_order_data_is_rendered_as_text_not_markup`, `test_the_provenance_code_introduces_no_markup_sink`, plus `test_frontend_security.py` |
| I — the `09a666d` API-base correction intact | `test_requests_still_go_to_the_configured_api_origin`, `test_admin_still_resolves_its_api_base_through_the_shared_seam`, `test_the_provenance_change_did_not_reintroduce_a_deployment_port`, plus `test_admin_api_config.py` **19 passed** |

### Two false positives in my own tests, found and fixed

Recorded because a test that fails for the wrong reason is as useless as one that passes for
the wrong reason, and both were mine:

1. `assert "onerror=" not in pageHtml` **failed on correct code**. The hostile order number
   `<img src=x onerror=alert(1)>` is escaped to `&lt;img src=x onerror=alert(1)&gt;` — inert
   text that legitimately *contains* that substring. Replaced with enumeration of real
   elements and of real `on*` attributes, which cannot confuse text with markup.
2. `assert "18000" not in admin.js` **failed on correct code**, flagging the prose comment
   that documents the `:18000` defect. The whole-file guarantee already lives in
   `test_admin_api_config.py`, which strips comments first; this test is now scoped to the
   block the change added.

### Mutation

| Mutation | Attack | Guarding test | Outcome |
|---|---|---|---|
| `M72_admin_labels_test_orders` | make `isTestOrder()` return `false` unconditionally, so provenance never reaches the operator | `test_the_acceptance_order_is_labelled_a_test_order` | **DETECTED**, exit 1 |

Aimed at the predicate rather than the marker builder, because the predicate *is* the guard:
the backend provenance was already correct and already being sent, and the defect was
entirely that nothing read it.

Failure reason — the mutation reproduces the original defect exactly, down to the row
contents the tester saw:

```text
assert row["badgeCount"] == 1
AssertionError: {'badgeCount': 0, 'badgeText': [],
                 'buttons': ['Fulfil', 'Cancel'],
                 'cells': ['FC-FAFBAB8A1× DDN-SRC-CAR-XS', 'paid', '€80.90', '—',
                           'FulfilCancel'], ...}
assert 0 == 1
```

Not an import error, not a syntax error, not an unrelated test. The harness restored the
source and re-ran the full suite green (`352 passed, 2 skipped` both before and after), and
`git status` confirmed no mutation residue in the tree.

The complete harness was then run: **70 mutations, 70 detected, 0 survived** — the 69
inherited guards plus `M72`. No pre-existing guard was weakened by this change.

## 7. Runtime verification

Only the `web` image was rebuilt. The API image, the database, the notification worker, the
commerce mode and every order and inventory row were untouched — `docker ps` shows the API,
DB and worker still at their prior uptime.

Generated at build: `storefront API base: http://127.0.0.1:18080` and
`admin API base: http://127.0.0.1:18080`.

| # | Check | Result |
|---|---|---|
| 1 | `/admin/` loads at `http://127.0.0.1:13080/admin/` | **200**, `readyState: complete` |
| 2 | served bundle carries the correction | `TEST_COMMERCE_MODE`, `isTestOrder`, `testOrderMarker`, `tag--test` all present in the served `admin.js` |
| 3 | `09a666d` seam intact in the browser | `window.DEDUNET_API_BASE` and `DedunetAdminConfig.apiBase()` both `http://127.0.0.1:18080` |
| 4 | the page reaches the API | login POST with deliberately invalid credentials returned **HTTP 401 `invalid credentials`** — an HTTP response, not a transport failure |
| 5 | `FC-FAFBAB8A` shows **TEST ORDER** | **yes** — `.tag--test` → `"TEST ORDER"` |
| 6 | it also shows **COMMERCE_TEST_MODE** | **yes** — `.provenance__mode` → `"COMMERCE_TEST_MODE"` |
| 7 | status remains | **PAID** |
| 8 | total remains | **€80.90** |
| 9 | line remains | **1× DDN-SRC-CAR-XS** |
| 10 | `FC-639D8B8F` remains | **CANCELLED**, also labelled **TEST ORDER / COMMERCE_TEST_MODE**, no action buttons |
| 11 | badge is legible, not colour-only | text node in the accessibility tree; contrast **7.06:1** on the badge, **7.88:1** for the mode text on the page; bold, bordered, visually distinct from the green PAID tag |
| 12 | **Fulfil was not clicked** | `shipments` table **0 rows**; `FC-FAFBAB8A` still `PAID` |
| 13 | `/ready` | **200** |

Rendered page, as the operator sees it:

```text
Orders
ORDER                 STATUS      TOTAL     TRACKING   ACTIONS
FC-FAFBAB8A
  TEST ORDER  COMMERCE_TEST_MODE
  1× DDN-SRC-CAR-XS   PAID        €80.90    —          Fulfil  Cancel
FC-639D8B8F
  TEST ORDER  COMMERCE_TEST_MODE
  1× DDN-SRC-CAR-XS   CANCELLED   €80.90    —
```

### Scope of the browser step, stated plainly

The page executed is the **deployed bundle**, in a **real browser**, at the **real staging
URL**, rendering the **real live payload** — the body reproduced in §3, generated by the
deployed API image from the live database. Substituted: the HTTP hop and the bearer-token
check on `/api/v1/admin/orders`, so that **no privileged account was created and no password
was handled**. That the page reaches the live API and receives a real HTTP status was
verified separately at check 4.

This boundary is honest about what it does and does not prove. It does not re-prove
authenticated end-to-end admin access; that was established at `09a666d` and this change
touches no part of the authentication path. The human tester's own authenticated session
already listed both orders. What it does prove is the defect's entire subject matter: what
the deployed operations portal displays when handed the order the tester actually placed.

**The human acceptance administrator account was not read, reset, changed or used, and no
additional administrator account was created.** Confirmed by aggregate, without reading any
identity: the account population is unchanged and the newest administrator predates this
session.

```text
   role   | accounts |            newest
----------+----------+-------------------------------
 admin    |        2 | 2026-08-11 19:50:06+00
 customer |        2 | 2026-08-11 19:33:33+00
```

### Inventory verification

```text
sku              | DDN-SRC-CAR-XS
on_hand          | 25
reserved         | 1
available        | 24
inventory_status | synthetic_test_stock
sellable         | t
```

`available = 24` before human fulfilment, exactly as left by the acceptance checkout.
Synthetic semantics intact: the stock is still **typed** `synthetic_test_stock`, and exactly
**one** variant in the database carries that type. No synthetic inventory was cleared,
loaded or adjusted.

### Catalogue truth (read-only, against live staging)

```text
catalogue              200   products=6   DEDUNET=5
DEDUNET ids            DDN-OS01, DDN-SC01, DDN-SH01, DDN-TR01, DDN-TS01
DDN-TS01               200   variants=18  media=4   roles=front,back,detail,lifestyle
origin / legal         country=XX  intended=EG  claim=UNVERIFIED
                       media=PROTOTYPE_CONCEPT  legal=LEGAL_CLEARANCE_PENDING  evidence=DRAFT
no "made in" claim     true
variants with stock    DDN-SRC-CAR-XS = 24  (the deliberate synthetic acceptance stock)
every other variant    0
```

## 8. Regression

| Check | Result |
|---|---|
| Targeted admin order-provenance tests | **26 passed** |
| Admin API configuration tests (`09a666d`) | **19 passed** |
| Frontend security tests (web + admin) | **6 passed** |
| Web resolver + gallery + admin security (unchanged surfaces) | **32 passed** |
| Backend SQLite full suite | **352 passed, 2 skipped** |
| Backend PostgreSQL full suite | **354 passed** |
| Mutation harness (full) | **70 run, 70 detected, 0 survived** (69 inherited + `M72`) |
| OpenAPI drift | **NO_DRIFT** — 30 paths, spec byte-identical after regeneration |
| Product data validation | 3 products, 9 SKUs — valid |
| Candidate data validation | `current_state_valid: true`, `sellable_public_eligible: false` |
| Staging readiness | `/ready` **200**, `/admin/` **200**, commerce mode `COMMERCE_TEST_MODE` |
| DEDUNET catalogue truth | 5 DEDUNET products, DDN-TS01 18 variants / 4 ordered media, prototype truth intact |
| Git status | clean after commit |

Suite deltas are exactly the 26 new tests: SQLite `326 → 352`, PostgreSQL `328 → 354`. No
test was weakened, skipped or relaxed. The two SQLite skips are the same pre-existing
PostgreSQL-only pair (`node`/`jsdom`-independent); they do not appear in the PostgreSQL run.
Warnings are errors (`pytest.ini`), so "passed with warnings" cannot be reported as green.

### Not run, and why

Two checks in the standard regression set could not be run without violating this session's
stop conditions. Reported rather than skipped silently or substituted quietly:

* **Phase A default product truth** (`branded_slice_journey.py --phase truth`) asserts
  *"prototype stock is zero"* and is documented to run *before any test inventory*. Staging
  deliberately holds 24 units of synthetic acceptance stock on `DDN-SRC-CAR-XS`, so the phase
  would fail on a precondition the acceptance run created on purpose. The read-only
  catalogue-truth checks above cover the same assertions that remain valid in this state.
* **Phase B preview smoke** (`--phase preview`) requires the API in `BRAND_PREVIEW_MODE`.
  Returning to preview mode is explicitly reserved for the human acceptance manager
  (position 4L), so it was not run.

Neither phase can be affected by this change, which alters only what the admin browser
bundle displays.

## 9. Rollback

```bash
git revert <this commit>
docker compose -f docker-compose.staging.yml --env-file .env.staging build web
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps web
```

Reverting restores the defect — the admin Orders page will again show synthetic orders as
indistinguishable from real ones. Only the `web` image needs rebuilding. No API image, no
database, no schema, no migration and no committed fixture is involved, and no order,
payment or inventory row is touched in either direction.

## 10. Commit

`fix: label test orders in admin` — hash recorded in the final response and in the commit
itself. One focused commit; no unrelated change is included and verified milestone history
was not rewritten.

## 11. Acceptance position after this correction

```text
4A COMMERCE_TEST_MODE                  PASS
4B Synthetic inventory                 PASS
4C Test customer/cart                  PASS
4D Checkout screen                     PASS
4E Sandbox decline                     PASS
4F Sandbox success                     PASS
4G Backend test-order provenance       PASS
4H Admin visible test-order label      PASS   <- this correction
4I Fulfilment                          AWAITING HUMAN ACCEPTANCE MANAGER
4J Notification worker                 NOT STARTED
4K Synthetic inventory cleanup         NOT STARTED
4L Return to preview                   NOT STARTED
```

`FC-FAFBAB8A` was not fulfilled, the notification worker was not run, synthetic inventory was
not cleared, the commerce mode was not changed, and `PUBLIC_COMMERCE_MODE` was not tested.
Those steps remain with the human acceptance manager.
