# DEDUNET — Local team acceptance closeout

**Artifact ID:** EV-TA-003 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `LOCAL_TEAM_ACCEPTANCE_PASSED` · **Date:** 2026-08-12
**Accepted baseline at start of this phase:** `7973e6d` (*fix: label test orders in admin*)
**Decided by:** human acceptance manager

> `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` remains fully in force. This document records that the
> **local, internal** acceptance script was executed by a human against fictional data,
> synthetic stock and a sandbox payment adapter, and passed. It is **not**
> `READY_FOR_PUBLIC_LAUNCH`, not production readiness, and not a launch authorization.

---

## 1. Baselines

| | |
|---|---|
| Repository | `C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack` |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| Baseline entering this phase | `7973e6d` |
| Working tree at start | clean |
| Runtime at start | `COMMERCE_MODE=BRAND_PREVIEW_MODE`, `/ready` **200** |
| DEDUNET sellable stock at start | **0 variants** with positive sellable stock |

Verified before anything was changed, so the acceptance state was observed rather than
assumed:

```text
sku              | DDN-SRC-CAR-XS
on_hand          | 0
reserved         | 0
available        | 0
inventory_status | prototype_unavailable
sellable         | f

DEDUNET variants with positive sellable stock : 0
variants typed synthetic_test_stock           : 0
```

## 2. Human acceptance gates

Every gate below was executed manually by the human tester.

| Gate | Result |
|---|---|
| **1** Environment | **PASS** |
| **2** `BRAND_PREVIEW_MODE` storefront | **PASS** |
| **3A** Admin portal | **PASS** (after defect `09a666d`, admin API origin) |
| **3B** Expo / React Native web preview | **PASS** |
| **4A** `COMMERCE_TEST_MODE` | **PASS** |
| **4B** Synthetic inventory guard + loading | **PASS** |
| **4C** Fictional customer + cart | **PASS** |
| **4D** Checkout | **PASS** |
| **4E** Sandbox decline | **PASS** |
| **4F** Sandbox success | **PASS** |
| **4G** Backend test-order provenance | **PASS** |
| **4H** Admin visible `TEST ORDER` / `COMMERCE_TEST_MODE` labelling | **PASS** (after defect `7973e6d`) |
| **4I** Fulfilment | **PASS** |
| **4J** Notification worker | **PASS** |
| **4J** Customer shipped / tracking visibility | **PASS** |
| **4K** Synthetic inventory cleanup | **PASS** |
| **4L** Return to `BRAND_PREVIEW_MODE` | **PASS** |
| **4M** Preview purchase blocking | **PASS** |
| **4N** `PUBLIC_COMMERCE_MODE` activation guard | **PASS — refused, as designed** |

Two acceptance defects were found by the human tester during the run and corrected in their
own commits before acceptance completed:

| Defect | Commit | Summary |
|---|---|---|
| Admin API origin in staging | `09a666d` | The admin portal resolved `:18000` with no runtime config seam while staging published the API on `:18080`; every request failed as *Failed to fetch* before anyone could sign in. |
| Admin test-order label | `7973e6d` | The admin Orders page listed the synthetic order exactly as it would list a real one — paid, EUR 80.90, with a Fulfil button and no mention of `COMMERCE_TEST_MODE` or `is_test_order`. |

Full records: [`ADMIN_API_CONFIGURATION_DEFECT.md`](ADMIN_API_CONFIGURATION_DEFECT.md) and
[`ADMIN_TEST_ORDER_LABEL_DEFECT.md`](ADMIN_TEST_ORDER_LABEL_DEFECT.md).

## 3. Retained acceptance evidence

Both orders are kept deliberately. They are the truthful local record of what was tested,
and deleting them would remove the only evidence that the journey ran.

### Successful acceptance order

```text
order_number              FC-FAFBAB8A
status                    SHIPPED
commerce_mode_at_checkout COMMERCE_TEST_MODE
is_test_order             true
currency                  EUR
subtotal / shipping       7200 / 890 minor units
total                     8090 minor units  (EUR 80.90)
line                      1 × DDN-SRC-CAR-XS  "The Source Tee"  XS / Carbon
```

### Declined acceptance order

```text
order_number              FC-639D8B8F
status                    CANCELLED
commerce_mode_at_checkout COMMERCE_TEST_MODE
```

### Fulfilment and tracking

```text
 order_number |   carrier    | tracking_number |   status
--------------+--------------+-----------------+------------
 FC-FAFBAB8A  | mock-carrier | TRK2CC820AABF   | IN_TRANSIT

audit_logs: order.fulfil × 1
```

`mock-carrier` is the point: no carrier integration exists and none was implied.

### Notification evidence

```text
      template      | status | rows | max_attempts
--------------------+--------+------+--------------
 order_confirmation | sent   |    4 |            2
 order_shipped      | sent   |    1 |            1

channel: email × 5     (console sender — EXTERNAL_SMTP_DELIVERY_PENDING)
```

Five notifications dispatched, all reaching `sent`. `max_attempts = 2` on the confirmations
shows the retry path executing rather than being bypassed. The channel is the console
sender: **no mail left the machine**, and no SMTP credential exists in the repository.

### Synthetic inventory cleanup

```text
DDN-SRC-CAR-XS   on_hand 0   reserved 0   available 0
                 inventory_status prototype_unavailable   sellable false

variants typed synthetic_test_stock : 0
```

The 25 synthetic units loaded for the journey are gone, and the variant is back to the
prototype state it holds in preview mode. The stock was **typed** throughout, never a bare
number, which is what made this cleanup verifiable rather than merely plausible.

### Preview restoration

`COMMERCE_MODE=BRAND_PREVIEW_MODE`, `/ready` **200**, and the DEDUNET catalogue intact:
5 products, DDN-TS01 with 18 variants and 4 ordered media, `origin_claim_status=UNVERIFIED`,
`country_of_origin=XX`, `media_status=PROTOTYPE_CONCEPT`,
`legal_brand_status=LEGAL_CLEARANCE_PENDING`, `evidence_status=DRAFT`, and no "made in"
claim anywhere in the payload.

### `PUBLIC_COMMERCE_MODE` guard proof

```text
CommerceModeError: PUBLIC_COMMERCE_MODE cannot be enabled by configuration.
Public commercial launch is BLOCKED.
```

The mode is not reachable by configuration. Reaching it requires a code change *and* the
documented activation gate — which is the whole design, and it held under a deliberate
attempt.

### Temporary credential cleanup

The human tester's temporary `acceptance-admin@dedunet.example` account was deleted and the
deletion verified (`temporary_admin_count=0`); the temporary password variables were
removed. Confirmed independently in this phase by aggregate, without reading any identity:

```text
   role   | accounts
----------+----------
 admin    |        1
 customer |        2
```

No administrator account was created during this phase, and no password was handled.

## 4. Post-acceptance issues found and corrected in this phase

Both were found by human acceptance *after* the functional gates passed. Neither affected
transaction correctness; both were surfaces telling a customer something untrue.

### Issue A — the storefront banner was not mode aware

`apps/web/index.html` shipped a fixed sentence and nothing ever revised it:

> "Prototype storefront. Preview only — nothing here is available to purchase, and no real
> order is placed or card charged."

The entire sandbox journey — synthetic stock, cart, declined payment, successful payment,
fulfilment — ran underneath a banner insisting nothing was available to purchase. The
commerce behaviour was correct; the page was lying about it.

Reproduced before changing anything, by rendering the frozen bundle against the real
payload:

```text
static notice   "Prototype storefront. Preview only — nothing here is available to
                 purchase, and no real order is placed or card charged."
in COMMERCE_TEST_MODE: unchanged
```

**Root cause.** The mode was authoritative in `app/commerce/modes.py` and used correctly by
every guard, but it was never exposed to a client. No browser could ask which mode it was
in, so the banner was a constant.

**Correction.** One authoritative source for both the mode and its wording:

| File | Change |
|---|---|
| `app/commerce/modes.py` | per-mode disclosure copy + `describe()` |
| `app/commerce/api.py` | `GET /api/v1/commerce/mode`, unauthenticated, read-only |
| `apps/web/index.html` | notice element carries mode-independent text until the mode resolves; the `<meta name="description">` carried the same fixed "nothing is available to purchase" claim and was made mode-independent too |
| `apps/web/app.js` | `renderCommerceNotice` / `loadCommerceNotice` |
| `apps/web/styles.css` | `.notice__headline`, `.notice__line` |
| `apps/mobile/src/api/{types,commerce}.ts` | `CommerceMode` type + `getCommerceMode` |
| `apps/mobile/src/store.ts` | `commerceMode` state, loaded per API base |
| `apps/mobile/src/brand.ts` | `commerceNotice()`; `SANDBOX_NOTICE` reduced to what is true in every mode |
| `apps/mobile/src/screens/CatalogScreen.tsx` | renders the resolved disclosure |
| `packages/contracts/openapi/openapi.json` | regenerated — 30 → 31 paths |

What each mode now says:

```text
BRAND_PREVIEW_MODE
  Preview only.
  Nothing here is available to purchase.
  No order or payment can be completed.

COMMERCE_TEST_MODE
  Internal commerce test mode.
  Only synthetic test inventory is available.
  Payments use the sandbox adapter.
  No real card is charged.
  No real stock or fulfilment is involved.

refused / unknown mode
  Commerce is unavailable.
  This deployment's commerce mode is not permitted.
  Nothing here is available to purchase.
```

Decisions worth stating:

* **The copy is served, not written per client.** Two browser bundles each keeping their own
  sentences is how one stays wrong after the other is fixed. A test asserts the two modes
  share no sentence at all.
* **Derived from the mode, never inferred from inventory.** A client reasoning "there is
  stock, so this must be commerce-test" would be right today and wrong the first time a
  preview catalogue carries a non-zero count. A test asserts the notice code never consults
  stock, variants or products.
* **A refused mode is its own outcome.** `PUBLIC_COMMERCE_MODE` makes `current_mode()`
  raise; the endpoint answers 200 with the BLOCKED disclosure rather than 500, because a
  client receiving an unexplained error keeps whatever its markup shipped with — which is
  the defect being closed. **The refusal itself is untouched**: every purchase path still
  calls `current_mode()` and still raises, and a test asserts exactly that.
* **The fallback claims nothing mode-specific.** Shown before the mode resolves and if it
  never does, so it says only what holds in both permitted modes.
* **`payments` has no "real" value.** It is `"none"` or `"sandbox"`. The mobile client
  rejects any other value as malformed rather than rendering it.

### Issue B — authenticated UI stayed stale after an authoritative 401

The tester's sequence:

1. the customer signed in earlier
2. the stored token later became invalid
3. `GET /api/v1/me/orders` → **401** `{"detail": "invalid or expired session"}`
4. the orders page said **"You have no orders yet."**
5. the account page said **"Signed in as customer."**
6. signing in again returned the order history correctly

Backend authentication rejection was **correct at every step**. Reproduced against the
frozen bundle:

```text
ordersViewAfter401     "You have no orders yet.Browse the collection"
accountViewAfter401    "AccountSigned in as customer. …"
stillClaimsSignedIn    true
tokenStillInStorage    present
```

**Root cause.** `viewOrders()` ended in `.catch(() => [])`, which turned every failure —
including the 401 that ends the session — into an empty list. So a rejected request rendered
as a factual claim about the customer's order history, the dead token stayed in
`localStorage`, and nothing anywhere cleared authentication state.

**Correction.** One rule, in one place: *the server rejecting an authenticated request is
the only thing that ends a session.*

| File | Change |
|---|---|
| `apps/web/app.js` | `clearCustomerAuth()`, `isSessionRejection()`, 401 handling inside `api()`, `requireSignIn()`, `viewOrders`/`viewOrder` no longer swallow failures, Sign out reuses the same clearing |

* **Narrow on purpose.** Only a 401 answered to a request that actually carried our
  credentials. Transport failures never produce a status; 429 means the request was not
  evaluated; 5xx means the server failed rather than refused; 403 is authenticated but not
  permitted; and a 401 from `POST /auth/login` is a failed sign-in with no session in play.
  Signing a customer out because their connection dropped would be a worse defect than the
  one being fixed, since it would fire during ordinary flaky-network use.
* **The cart survives.** The basket is the device's, not the session's — the mobile client
  already worked this way. Losing it would turn a re-authentication into lost work.
* **One definition of "signed out."** The Sign out button calls the same
  `clearCustomerAuth()` the rejection path does; a test asserts the session keys are removed
  in exactly one place.

**The mobile client already implemented this policy correctly** — `store.ts` →
`handleFailure` cleared the session on `unauthorized` and on nothing else, and its docstring
already named the exact bug ("a signed-out session that still shows an account page"). It
was **not changed**. Tests were added to pin it, because the web client has now been aligned
to it and an unnoticed regression there would reopen the defect on the surface that never
had it.

## 5. Tests added

| Suite | Count | Covers |
|---|---|---|
| `tests/test_commerce_mode_disclosure.py` | **18** | per-mode copy, no shared sentences, no real-payment claim, blocked/unknown mode, disclosure ≠ authorization |
| `tests/test_storefront_mode_notice.py` | **25** | the notice rendered in a real DOM per mode, unusable/failed responses, XSS, mode never inferred from inventory |
| `tests/test_storefront_session_expiry.py` | **20** | the acceptance sequence end to end, the full non-auth failure matrix, the predicate over every status |
| `apps/mobile/src/__tests__/commerce-mode.test.tsx` | **34** | endpoint validation, wording selection, catalogue rendering, and the existing mobile 401 policy |

Explicitly proven, per the phase requirements:

* `BRAND_PREVIEW_MODE` renders preview messaging — and `COMMERCE_TEST_MODE` does not
* `COMMERCE_TEST_MODE` renders test/sandbox messaging
* the modes cannot share misleading copy — asserted on both the served copy and the rendered
  notice
* no real-payment or real-shipping claim appears in test mode
* an unknown or blocked public mode does not render normal-commerce messaging
* a 401 invalid/expired session clears auth, and the account view becomes signed-out
* a subsequent protected request stops and requires signing in rather than retrying
* network error, timeout, 429, 5xx, 403, 404 and 409 do **not** sign a customer out
* a successful request preserves auth
* the previous stale-token acceptance scenario is reproduced verbatim as a test

### Mutations

| Mutation | Attack | Guarding tests | Outcome |
|---|---|---|---|
| `M73_commerce_modes_do_not_share_disclosure_copy` | point `COMMERCE_TEST` at the preview wording, so both modes say the same thing | `test_no_sentence_is_reused_between_the_two_modes`, `test_preview_copy_never_appears_in_test_mode` | **DETECTED** |
| `M74_expired_session_is_cleared_on_401` | stop clearing the session when an authenticated 401 arrives | `test_the_account_view_no_longer_claims_the_customer_is_signed_in`, `test_an_expired_session_clears_the_stored_token` | **DETECTED** |

`M73` collapses commerce-test onto the preview wording, which is the acceptance symptom
exactly rather than an arbitrary edit. `M74` targets the clearing rather than the predicate:
`isSessionRejection` is narrow by design and its own tests cover the statuses that must not
sign a customer out, so what `M74` proves is that the narrow condition is actually wired to
the state change — the half that was missing.

Both failed for exactly the intended reason, reproducing what the tester saw:

```text
M73  AssertionError: modes share disclosure sentences:
       ['No order or payment can be completed.', 'Nothing here is available to purchase.']

M74  AssertionError: AccountSigned in as customer.View my ordersDownload my dataSign out
     assert True is False
     AssertionError: assert 'stale-token-not-a-credential' is None
```

`M74`'s message is literally the string the human tester reported. Neither is an import
error, a syntax error, or an unrelated test. The harness restored both files and re-ran the
full suite green (`415 passed, 2 skipped`) after each, and `git diff` confirmed no mutation
residue: the only `MUTATED` strings left in the tree are inside the mutation *definitions*.

The mobile harness runs separately: **18 run, 18 detected, 0 survived**. `M7` there —
*"a dropped connection is reported as an expired session, signing the customer out"* — is
the pre-existing guard on the mobile side of Issue B, and it still detects.

## 6. Regression

| Check | Result |
|---|---|
| Storefront mode-copy tests | **25 passed** |
| Storefront session-expiry tests | **20 passed** |
| Commerce-mode disclosure tests | **18 passed** |
| Admin order-provenance tests | **26 passed** |
| Admin API configuration tests | **19 passed** |
| Admin security tests | **11 passed** |
| Frontend security tests | **6 passed** |
| Web resolver + gallery | **23 passed** |
| Mobile typecheck | **clean** (`tsc --noEmit`) |
| Mobile suite (jest) | **151 passed**, 10 suites |
| Mobile mutation harness | **18 run, 18 detected, 0 survived, 0 errors** |
| Backend SQLite full suite | **415 passed, 2 skipped** |
| Backend PostgreSQL full suite | **417 passed** |
| Backend mutation harness (full) | **72 run, 72 detected, 0 survived** (70 inherited + `M73` + `M74`) |
| OpenAPI drift | **expected drift, regenerated** — 30 → 31 paths, the new `/api/v1/commerce/mode` only |
| Product / candidate data validation | 3 products, 9 SKUs valid; `current_state_valid: true`, `sellable_public_eligible: false` |
| DEDUNET catalogue truth (Phase A) | **13/13 passed** |
| Preview purchase-block smoke (Phase B) | **14/14 passed** against staging — see §6.1 |
| Staging readiness | `/ready` **200**, `/health` **200**, mode `BRAND_PREVIEW_MODE` |
| Git status | clean after the three commits |

The full backend harness was run after the two targeted ones: **72 mutations, 72 detected, 0
survived** — the 70 inherited guards plus `M73` and `M74`. Baseline and restored suites both
`415 passed, 2 skipped`, so no pre-existing guard was weakened by this change, and `git diff`
confirms the only `MUTATED` strings left in the tree are inside the mutation definitions.

### 6.1 Phase B target discrepancy — reported, not adjusted

`scripts/validation/branded_slice_journey.py` hard-codes `BASE = "http://127.0.0.1:18300"`.
That is a **developer API process, not the staging deployment under test** — started
2026-08-08 18:04, four days before this phase, and running code that predates it (it answers
**404** on `/api/v1/commerce/mode`). Run as written, Phase B reports **13/14**:

```text
[FAIL] refusal names brand preview - The Source Tee is not available for purchase
```

That is a **precondition mismatch, not a regression**. The check requires the target API to
be in `BRAND_PREVIEW_MODE`; the `:18300` process is in the default `COMMERCE_TEST_MODE`, so
the *product* gate refuses the prototype instead of the *mode* gate. Both refuse — the
message differs because a different gate fired first. This change cannot have caused it: the
process predates the change and does not contain it.

The same 14 assertions, in the same order, run against the staging deployment on `:18080`:

```text
{'total': 14, 'passed': 14, 'failed': 0}
[PASS] refusal names brand preview - this catalogue is in brand preview; nothing is
       available to purchase
```

Phase A (`--phase truth`) passes **13/13** as written, because its precondition — no test
inventory — now holds after the acceptance cleanup. It was unrunnable in the previous phase
for exactly that reason.

**The committed script was not modified**, and the `:18300` process was not stopped or
restarted; it belongs to another session. The discrepancy is recorded so the next runner
knows the harness points somewhere other than the deployment they are testing.

*(While replicating, two checks initially failed in my own replication because it read
headers from `dict(response.headers)`. uvicorn emits lowercase header names, so
`"Content-Type"` missed `content-type`. My harness bug, not a defect — corrected to use the
case-insensitive message object, after which the media checks pass. Recorded because a check
that fails for the wrong reason is as misleading as one that passes for the wrong reason.)*

Suite deltas are exactly the new tests. Backend SQLite `352 → 415` (+63 = 18 + 25 + 20),
PostgreSQL `354 → 417` (+63), mobile `117 → 151` (+34). No test was weakened, skipped or
relaxed; the two SQLite skips are the same pre-existing PostgreSQL-only pair and do not
appear in the PostgreSQL run. Warnings are errors (`pytest.ini`), so "passed with warnings"
cannot be reported as green.

The PostgreSQL suite ran against an isolated throwaway `postgres:16-alpine` container on host
port 55432, created for the run and removed afterwards. No existing volume, stack or database
was touched, and the generated password was held in a scratch file that was deleted.

### Mobile mutation anchor repaired

`M15` in `apps/mobile/scripts/mutation_check.mjs` rotted when the catalogue notice became
mode aware: it anchored on `message={SANDBOX_NOTICE}`, which is now
`message={commerceNotice(commerceMode)}`. The harness reported `ANCHOR ROTTED` rather than
passing, which is the behaviour that makes it trustworthy. The anchor was updated to the new
expression; **the guard is unchanged** — a catalogue screen must always disclose what this
build is — and the same guarding test still fails on the same missing `testID`.

### Dependency warnings — recorded, not acted on

`npm install` reports vulnerabilities in `apps/mobile`. **No dependency was changed in this
phase**, `npm audit fix` was not run, and nothing was upgraded — per the phase scope.
Recorded so the finding is not lost:

```text
npm audit --json     755 dependencies
                     critical 0 · high 11 · moderate 7 · low 0 · info 0   (18 total)
```

Two root advisories account for the chain:

| Package | Severity | Advisory | Reaches the tree via |
|---|---|---|---|
| `image-size` | high | ICNS, JXL and HEIF parsers allow denial of service through infinite loops | `metro` → `@expo/metro*`, `@react-native/community-cli-plugin`, `expo`, `react-native` |
| `uuid` | moderate | missing buffer bounds check in v3/v5/v6 when `buf` is supplied | `xcode` → `@expo/config-plugins` → `expo` |

Both sit in the **build and native-tooling chain** (Metro bundler, Expo CLI, Xcode project
generation) rather than in code the shipped client executes at runtime. That is a reason to
schedule the upgrade deliberately, **not** a reason to call it harmless: `react-native` and
`expo` are themselves flagged transitively, and the assessment above is from the dependency
graph, not from a reachability audit. Upgrading crosses the Expo SDK matrix
(`npm run deps:check`) and belongs in its own change with its own regression run.

A separate, unrelated `DeprecationWarning [DEP0190]` is emitted by Node during
`npm run mutations` (the harness spawns a child process with `shell: true`). Pre-existing,
not introduced here, and recorded rather than silenced.

### 6.3 Runtime verification

Both images were rebuilt (`api` and `web` — the API carries the new endpoint). The database,
the notification worker, the retained orders and the inventory were untouched.

**`BRAND_PREVIEW_MODE`**

| Check | Result |
|---|---|
| `/ready` | **200** |
| `/api/v1/commerce/mode` | `BRAND_PREVIEW_MODE`, `purchasable=false`, `payments=none`, `public_commerce_enabled=false` |
| storefront banner in a real browser | **"Preview only. Nothing here is available to purchase. No order or payment can be completed."** — `role="note"` preserved, no mention of sandbox |
| DEDUNET products render | **5** product cards |
| `DDN-SRC-CAR-XS` | `available=0`, `sellable=false`, `prototype_unavailable` |
| cart add | **409** *"this catalogue is in brand preview; nothing is available to purchase"* |

**`COMMERCE_TEST_MODE`** — banner only; **no order was created and no checkout was replayed**

| Check | Result |
|---|---|
| banner in a real browser | **"Internal commerce test mode. Only synthetic test inventory is available. Payments use the sandbox adapter. No real card is charged. No real stock or fulfilment is involved."** |
| still claims nothing is purchasable? | **no** — the false sentence is gone |

**Issue B, end to end against the live API**

Driven with a **deliberately invalid synthetic token**; the retained acceptance customer was
never signed in and no real session was touched.

| Step | Observed |
|---|---|
| account view before | *"Signed in as customer."* — the stale state reproduced |
| live `GET /api/v1/me/orders` | **401** `{"detail":"invalid or expired session"}` — the real server, not a stub |
| after the rejection | routed to `#/account`, banner *"Your session has expired. Please sign in again."*, sign-in form rendered |
| still claims signed in? | **no** |
| claims "You have no orders yet"? | **no** |
| stored token / role | **cleared** |
| cart token | **preserved** |

Browser storage was cleared afterwards, and the runtime was returned to
**`BRAND_PREVIEW_MODE`**, `/ready` **200** — the state the deployment is in now.

## 7. Remaining blockers

Unchanged by this phase, and none was attempted:

| Blocker | Status |
|---|---|
| Native EAS preview binary | `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` (project config verified) |
| Apple publisher membership / identity | `DEFERRED — PUBLISHER IDENTITY PENDING` |
| Google Play publisher identity | `DEFERRED — PUBLISHER IDENTITY PENDING` |
| External SMTP delivery | `EXTERNAL_SMTP_DELIVERY_PENDING` |
| Hosted production cloud | `DEFERRED — LOCAL STAGING ONLY` |
| Real payment provider activation | not activated |
| Real inventory activation | not loaded |
| Real fulfilment activation | not established |
| Product-origin substantiation | `origin_claim_status = UNVERIFIED`, `country_of_origin = XX` |
| Material / composition substantiation | stated intention, not tested |
| Product evidence approval | `evidence_status = DRAFT` |
| Legal / trademark clearance | `LEGAL_CLEARANCE_PENDING` |
| Human risk-owner approvals | `ASSIGNMENT_RECORDED — HUMAN ACCEPTANCE PENDING` |

## 8. Documentation corrected

| Document | Correction |
|---|---|
| `docs/system-of-record/TEAM_ACCEPTANCE_READINESS_DECISION.md` | new §0 recording `LOCAL_TEAM_ACCEPTANCE_PASSED` and a status history. The original §1 decision is **kept verbatim** as the dated record of what was decided on 2026-08-07. |
| `apps/mobile/README.md` | status line updated; the claim that DEDUNET media, catalogue and copy are "not imported" corrected — they are, and human acceptance 3B confirmed it. The **tokens and fonts** half of that claim is still true and was left standing. |
| `apps/mobile/src/brand.ts` | same correction, as a dated status note beside the placeholder palette it still describes accurately. |
| `apps/mobile/scripts/mutation_check.mjs` | `M15` anchor updated to the mode-aware notice expression; the guard is unchanged (see §6). |

Nothing historical was rewritten. Prior evidence documents record what was true when they
were written and are left alone; corrections are additive and dated.

## 9. Rollback

Three focused commits:

| Commit | Scope |
|---|---|
| `1a90c10` | `fix: make commerce banners mode aware` — issue A, backend + web + mobile |
| `315bd83` | `fix: clear stale customer auth on 401` — issue B, web only |
| *this one* | `docs: close local team acceptance` — closeout, readiness status, stale docs |

`apps/web/app.js` carries both corrections, so it was split deliberately rather than
committed once: the file was reset to `HEAD`, the notice code re-applied and committed
alone, then the session-policy code restored and committed on top. Each commit's tests were
run against its own intermediate state (`49 passed` for the banner-only tree), so neither
revert leaves a half-applied file.

One packaging detail, stated rather than smoothed over: **both** mutation registrations
(`M73` and `M74`) landed in `315bd83`, because they are two entries in one harness file.
Reverting `1a90c10` alone therefore leaves `M73` registered against code that no longer
exists and the harness will report `ANCHOR ROTTED` for it — loudly, which is the correct
failure mode. Remove that entry as part of such a revert.

```bash
git revert 315bd83 1a90c10
cd services/commerce-api && python -B manage.py export-openapi && cd -   # 31 -> 30 paths
COMMERCE_MODE=BRAND_PREVIEW_MODE \
  docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build api web
```

Both images are involved: the banner commit adds `/api/v1/commerce/mode` to the **API** image
and the notice code to the **web** image, so reverting one without rebuilding the other
leaves a storefront asking an endpoint that is no longer there — which it survives, by
design, falling back to the mode-independent sentence.

`COMMERCE_MODE` must be passed explicitly on the way back up. It is declared in the compose
file with an empty default, so a plain restart applies `DEFAULT_MODE` — `COMMERCE_TEST_MODE`
— and silently leaves preview mode.

Reverting the banner commit restores the fixed preview-only sentence in every mode; reverting
the auth commit restores the stale-session behaviour. No database, schema, migration, order,
payment or inventory row is involved in either direction. The documentation commit is text
only.

## 10. Acceptance position after this phase

```text
Local team acceptance          PASSED  (human, 2026-08-12)
Post-acceptance issue A        FIXED   (mode-aware commerce banners)
Post-acceptance issue B        FIXED   (stale customer auth cleared on 401)
Public commercial launch       BLOCKED (unchanged)
Native preview binary          EXTERNALLY PENDING (unchanged)
```
