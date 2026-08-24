# iPhone mobile-web acceptance — hardening closure (issues A and B)

**Artifact ID:** EV-TA-005 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED` · **Date:** 2026-08-24
**Frozen baseline before this correction:** `41cee4c` (*fix: support LAN staging storefront access*)
**Reported by:** human acceptance testing — physical iPhone Safari, `BRAND_PREVIEW_MODE`
**Result:** `IPHONE_WEB_HARDENING_CLOSED`

`PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` remains in force. Nothing here activates public commerce,
configures real payments, stock, fulfilment or SMTP, alters legal or trademark status,
introduces production credentials, or touches real customer data. No commerce guard was
changed — this correction is entirely about what two screens *offer*, not about what the
server permits.

---

## 1. Starting state

| | |
|---|---|
| Repository | `C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack` |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| HEAD before | `41cee4c72f629b190fa7e1ea4bab879d9c045220` |
| Working tree | clean, including untracked |
| Backend suite before | **415 passed, 2 skipped** |
| Guard mutations before | **72** |

The two skips are the same PostgreSQL-only tests as every prior milestone.

## 2. What was reported

Human acceptance on physical iPhone Safari passed overall — catalogue, product images,
product detail, preview safety, registration, session persistence, expired-session handling,
stale-token clearing and cleanup all succeeded. Two non-blocking UX defects were recorded.

**A. Product detail offered an enabled "Add to cart" in `BRAND_PREVIEW_MODE`.**
The server refuses every purchase in preview mode with 409 before a payment call is reached,
so the control's only possible outcome was a rejection. The page had an evidence banner
directly above the button reading *"Preview only — this piece is not available to buy"*,
and then offered to buy it.

**B. The empty order history read "You have no orders yet."**
In preview mode nothing can be placed, so the sentence reads as an invitation to do
something the deployment has already decided to refuse.

Both are the same class this programme keeps closing — a surface asserting something the
mode does not support. Both were already fixed on the **native** client (`1a90c10`,
`4e4f8c0`) and in the **storefront banner**. These are the same two defects, one surface over.

## 3. Reproduction before changing anything

Rendered rather than read. The frozen `apps/web/app.js` was driven in jsdom against the
payloads `/api/v1/commerce/mode` and `/api/v1/catalog/products/{slug}` actually return.

```text
BRAND_PREVIEW_MODE, product sellable:true
  add button label      "Add to cart"
  add button disabled   false            <- the defect
  reason next to it     (none)

BRAND_PREVIEW_MODE, empty order history
  rendered text         "You have no orders yet."   <- the defect
```

## 4. The rule being mirrored

`app/commerce/modes.py::assert_purchasable` refuses on **two independent gates**:

```python
if is_preview_mode():          # MODE gate    — refuses everything, whatever the product says
    raise PurchaseBlocked(...)
if not sellable:               # PRODUCT gate — refuses this product, in any mode
    raise PurchaseBlocked(...)
```

The storefront now mirrors both, in the same order.

**This is stricter than the native client.** `apps/mobile/src/screens/ProductScreen.tsx`
mirrors only the product gate (`product.sellable === false`). That is correct today solely
because every product in the current preview catalogue also carries `sellable: false` — a
property of the seed, not a rule the server enforces. A preview catalogue carrying a
sellable product would show an enabled "Add to bag" on native and a disabled one on web.
Recorded as **`NATIVE_MIRRORS_ONE_GATE`** in §8; not fixed here, because changing the native
client is a separate surface with its own acceptance.

## 5. What changed

`apps/web/app.js` only. No backend file, no migration, no contract change.

| Change | Purpose |
|---|---|
| `state.commerceMode` + `KNOWN_MODES` | the resolved mode, validated against the two selectable modes rather than stored raw |
| `recordCommerceMode()` | records the mode; separate from rendering the notice so the two halves of the response fail independently |
| `modeReady` + `awaitCommerceMode()` | one boot request, awaitable by the views that need it, bounded at 2 s |
| `purchaseRefusal()` / `refusalText()` | mirrors both gates; returns the reason, not a boolean |
| product detail | label `Not available to buy`, `disabled`, `aria-describedby` → the reason |
| `ordersEmptyMessage()` | three mode-derived messages, no shared sentence |

### 5.1 Why the mode is awaited rather than read

`route` and `loadCommerceNotice` are both `DOMContentLoaded` listeners and `route` is
registered first, so a customer opening `#/orders` or a product URL **directly** renders the
page before the mode has been asked for. Reading `state.commerceMode` synchronously would
have left the mode-specific copy unreachable on exactly the path the defect was reported
on — a hard load of the page — and shipped the neutral fallback as the real behaviour.

The wait is bounded at 2 s because `api()` has no timeout. An unbounded await would let a
hanging `/api/v1/commerce/mode` hold a route in `loading()` indefinitely, which is the blank
page `route`'s own catch exists to prevent. On expiry the view proceeds with the neutral
wording, which is the correct thing to say when the deployment has not answered.

The populated order history does **not** wait. Only the empty branch needs the mode, and an
order list that stalls behind a disclosure request would be a regression introduced by a copy
fix.

### 5.2 The three empty-history messages

```text
BRAND_PREVIEW_MODE   No orders yet. Purchasing is unavailable while this catalogue
                     is in preview.
COMMERCE_TEST_MODE   No orders yet. Sandbox test orders you place will appear here.
unresolved/refused   No orders yet. Orders you place will appear here once this
                     deployment allows purchasing.
```

Wording identical to the native client's `ordersEmptyDetail`. Two surfaces describing the
same deployment differently is a defect even when both sentences are true.

The third case is deliberate and promises nothing. Promising sandbox ordering there would
reintroduce the defect for exactly the window in which the client cannot know better;
promising preview would understate a live sandbox.

## 6. Tests

**New:** `services/commerce-api/tests/test_storefront_purchase_refusal.py` — 19 tests,
rendered in a real DOM.

Coverage that matters:

| Case | Why it is there |
|---|---|
| preview mode, **sellable** product | isolates the MODE gate. A client mirroring only the product gate passes every other case against today's seed and fails this one |
| commerce-test mode, non-sellable product | isolates the PRODUCT gate |
| the two reasons differ | two different facts about the deployment; a customer told the wrong one is misinformed |
| **commerce-test mode, sellable product, still enabled** | without it, "disable the button" passes the whole file by disabling it everywhere and makes the internal commerce-test journey unperformable |
| unresolved mode + sellable product → **enabled** | the one place this client is permissive, and deliberately so: the mode gate cannot be evaluated against a mode nobody has stated |
| hanging mode request, product and orders | proves the bound. Asserts `"Loading"` is gone, not merely that a promise settled |
| customer **with** orders, mode hanging | proves the populated branch acquired no dependency |
| six views cost the same as two | proves the mode is not re-requested per view |

**Amended:** `test_storefront_session_expiry.py`. Its probe matched the retired sentence
`"You have no orders yet"`. Left alone it would have passed against a string the client can
no longer produce — green for the wrong reason and blind to the defect returning. Re-anchored
on the `"No orders yet"` stem all three variants share. **This is the only existing test
touched, and it was made stricter, not looser.**

## 7. Guard mutations

Five added, 72 → **77**.

> **Counted, not inferred from the highest id.** The harness registers **77** entries and its
> ids run to `M79`, because **M56 and M57 were never used**. An earlier draft of this document
> said "74 → 79" by reading the last id as the count. Recorded rather than silently corrected,
> because a count taken from a label instead of from the data is the same error class this
> file exists to close.

| ID | Guard removed | Result |
|---|---|---|
| M75 | the MODE gate in `purchaseRefusal` | **DETECTED** |
| M76 | the PRODUCT gate in `purchaseRefusal` | **DETECTED** |
| M77 | the refusal reaching the control (`disabled`) | **DETECTED** |
| M78 | preview's empty-history wording, collapsed onto sandbox | **DETECTED** |
| M79 | mode validation, so any string becomes a mode | **DETECTED** |

### 7.1 The first run was discarded, and why

`apps/web/app.js` was edited **while the harness was running** — a one-line comment
correction, made during M78. The harness captures the original source, writes a mutation,
then restores what it captured, so a concurrent write can be silently reverted or can land on
top of mutated source. The edit happened to survive and every guard anchor was intact
afterwards, but **M78's result from that run cannot be trusted**, because the file it was
measuring was being changed underneath it.

The whole first pass was therefore discarded and **all eight mutations that target
`apps/web/app.js` were re-run cleanly**, with no concurrent writes. That set deliberately
includes the three *pre-existing* ones, because an edit to this file could have broken their
anchors without breaking the suite:

```text
M68 web_product_gallery_renders_media              DETECTED
M69 web_gallery_preserves_api_ordering             DETECTED
M74 expired_session_is_cleared_on_401              DETECTED
M75 preview_mode_refuses_the_purchase_invitation   DETECTED
M76 non_sellable_product_refuses_the_invitation    DETECTED
M77 the_refusal_reaches_the_control                DETECTED
M78 empty_order_history_does_not_promise...        DETECTED
M79 an_unstated_mode_is_not_adopted...             DETECTED

8 run, 8 detected, 0 survived
```

Recorded rather than quietly re-run, because "the result was obtained under conditions that
could have corrupted it" is exactly the kind of thing a passing number hides.

M75 and M76 mutate the two gates **independently**. A single mutation over a collapsed
condition could not tell which half was load-bearing.

M77 is aimed at the wiring, not the predicate — the same shape as M74. `purchaseRefusal`
keeps working and the reason paragraph still renders; only the control stops reflecting it,
which is exactly the state that shipped.

M78 collapses preview onto the commerce-test wording, which is the native acceptance symptom
exactly rather than an arbitrary edit.

## 8. Recorded, not fixed

| ID | Item | Classification |
|---|---|---|
| `NATIVE_MIRRORS_ONE_GATE` | `ProductScreen.tsx` mirrors the product gate only. Correct against the current seed; would show an enabled "Add to bag" for a sellable product in a preview catalogue | **NON_BLOCKING** — separate surface, separate acceptance. Web is now the stricter of the two |
| Catalogue grid | Cards do not offer an add control at all, so neither gate applies there. Unchanged | not a defect |
| **CONFLICT-011** | The iPhone acceptance itself had no record in this repository when this document was written | **RESOLVED 2026-08-24** — see §8.1 |

### 8.1 The acceptance that produced these defects is not evidenced

Searched before this document was written, not assumed:

```text
evidence/team-acceptance/     LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md
                              NATIVE_ANDROID_PREVIEW_ACCEPTANCE.md
                              (no iPhone equivalent)
git log --all -S "IPHONE_MOBILE_WEB"   -> no commit in any ref
```

The testing almost certainly happened: the two reported defects are specific, real and were
reproducible against the frozen client, and `41cee4c` (*support LAN staging storefront
access*) is consistent with someone reaching staging from a phone on the LAN.

But **a defect report is not an acceptance record**, and the *scope* of what passed cannot be
reconstructed — which device, which iOS version, which commit, which commerce mode, and
whether the eleven checks named in the brief were the whole script or a subset. The Android
closeout names its emulator, API level and build id; nothing comparable exists here.

Recorded as **CONFLICT-011**, owner: human acceptance manager. Deliberately **not** resolved
by writing the missing record on the tester's behalf — that would manufacture evidence, which
is worse than the gap.

> **RESOLVED 2026-08-24.** The human tester supplied the authoritative scope and the record was
> written from it: [`IPHONE_MOBILE_WEB_ACCEPTANCE.md`](IPHONE_MOBILE_WEB_ACCEPTANCE.md)
> (`EV-TA-006`, `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED`, 25 gates). The refusal above is what
> made that record worth having: it was supplied by the person who ran the test, not
> reconstructed from a brief by the agent that needed it to exist. Ten of its claims were then
> independently corroborated against repository data — €72, five products, non-purchasability,
> the mode gate, the caution language and M74 among them.
>
> Residual and non-blocking: iPhone model, iOS version and the acceptance commit were not
> supplied; the commit is recorded as an inference bounded to a two-commit window.

**This document still does not claim to close the iPhone acceptance.** It closes the two UX
defects that acceptance reported. `EV-TA-006` is the acceptance record, and the two are
deliberately separate artifacts.

## 9. Verification status

All executed at `41cee4c` + this change, on Python 3.14.4, SQLite path.

| Check | Expected | Observed | Verdict |
|---|---|---|---|
| New suite | 19 passed | **19 passed** | **PASS** |
| Web-facing suites (5 modules) | green | **74 passed** | **PASS** |
| Full backend suite | 415 + 19 = 434, 2 skipped | **434 passed, 2 skipped** | **PASS** |
| Mutations over `app.js` | 8 run, 8 detected, 0 survived | **8 / 8 / 0** | **PASS** |
| Harness total | 72 + 5 = 77 registered | **77** | **PASS** |
| `validate_product_data.py` | exit 0 | **exit 0** | **PASS** |
| `validate_candidate_data.py` | exit 0 | **exit 0** | **PASS** |
| `--assess-sellable` | non-zero, `ACTIVATION_BLOCKED` | **exit 1**, `ACTIVATION_BLOCKED` + `SYNTHETIC_CANNOT_ACTIVATE` | **PASS** |
| OpenAPI drift | none | **none** — byte-identical re-export, contract clean | **PASS** |
| `node --check apps/web/app.js` | clean | **clean** | **PASS** |
| `MUTATED` markers left in `app.js` | 0 | **0** | **PASS** |

### 9.1 Test-count delta, explained

`415 → 434`: **+19**, all from `tests/test_storefront_purchase_refusal.py`, the new file. The
two skips are the same two PostgreSQL-only tests as every prior milestone.

**No test was weakened, skipped or relaxed.** One existing test was **amended and made
stricter** (§6): its probe matched the retired sentence and would otherwise have passed
against a string the client can no longer produce.

### 9.2 Not run, and why

Stated rather than implied.

| Check | Status | Reason |
|---|---|---|
| PostgreSQL suite | **NOT RE-RUN** | needs a throwaway container; no backend file, model or migration was touched, so the SQLite and PostgreSQL paths cannot diverge on this change |
| Full 77-mutation harness | **NOT RE-RUN** | ≈5 min per entry ≈ 6.5 h. The 8 that target the changed file were run; the other 69 target files this change does not touch |
| Mobile suite / `tsc` | **NOT RUN** | no mobile file was touched. `NATIVE_MIRRORS_ONE_GATE` (§8) is recorded, not fixed |
| Human acceptance of this fix | **NOT TESTED** | it changes two screens a human reported. A human should confirm them |
| Staging deployment | **NOT PERFORMED** | no stack was started, stopped or redeployed during this correction |

### 9.3 Result

**`IPHONE_WEB_HARDENING_CLOSED`** — for the two UX defects, on automated evidence.

**Not** an iPhone acceptance pass. See §8.1 and CONFLICT-011: the acceptance that reported
these defects still has no record, and this document does not become one.
