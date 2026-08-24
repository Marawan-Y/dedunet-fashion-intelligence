# DEDUNET — iPhone mobile-web acceptance

**Artifact ID:** EV-TA-006 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` · **Date:** 2026-08-24
**Decided by:** human acceptance manager
**Scope supplied by:** the human tester, 2026-08-24
**Closes:** CONFLICT-011

> `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` remains fully in force. This records that the DEDUNET
> storefront was exercised in **mobile Safari on a physical iPhone**, against **local
> staging**, in **`BRAND_PREVIEW_MODE`**, using fictional data and a catalogue that cannot be
> purchased. It is not production readiness, not a launch authorization, and — see §6 —
> **not native iOS acceptance in any form**.

---

## 0. Why this record exists

This acceptance was performed before the record was written. The gap was found during the
hardening work that closed the two defects this acceptance reported, and was raised as
**CONFLICT-011**: the brief asserted the acceptance had passed, and

```text
evidence/team-acceptance/               no iPhone record
git log --all -S "IPHONE_MOBILE_WEB"    no commit on any ref
```

The register deliberately refused to close it by writing the record from the brief, because
that would manufacture evidence rather than capture it. The human tester has now supplied the
authoritative scope, and **that** is what this document records. §7 states exactly which
identifying details were and were not supplied, so the record does not overstate its own
precision.

Artifact IDs run in creation order, so this document is `EV-TA-006` even though the
acceptance it records preceded `EV-TA-005`, the hardening closure derived from it.

---

## 1. What was accepted

| | |
|---|---|
| Surface | DEDUNET storefront, **mobile web** |
| Browser | Safari on a **physical iPhone** |
| Target | **local staging** stack, reached over the LAN |
| Commerce mode | **`BRAND_PREVIEW_MODE`** throughout |
| Catalogue | 5 DEDUNET preview products, none purchasable |
| Payment | none reachable — preview mode refuses before any payment call |
| Baseline commit | **not supplied — inferred as `41cee4c`**, see §7 |

### Gates passed

Grouped as the tester supplied them.

| # | Gate | Result |
|---|---|---|
| **Connectivity** | | |
| 1 | LAN connectivity, physical iPhone → local staging | **PASS** |
| 2 | API `/ready` reachable from the device | **PASS** |
| 3 | Storefront reachable from the device | **PASS** |
| 4 | LAN CORS behaviour correct | **PASS** |
| **Catalogue and brand** | | |
| 5 | DEDUNET logo and brand media render | **PASS** |
| 6 | Exactly **five** DEDUNET preview products | **PASS** |
| 7 | Source Tee product detail renders | **PASS** |
| 8 | Price shown as **€72**, correct | **PASS** |
| 9 | Concept product imagery renders | **PASS** |
| 10 | Material and origin caution language present | **PASS** |
| **Preview safety** | | |
| 11 | `BRAND_PREVIEW_MODE` disclosure shown | **PASS** |
| 12 | Product purchase blocked | **PASS** |
| 13 | Cart safety — nothing purchasable enters a bag | **PASS** |
| **Identity** | | |
| 14 | Customer registration | **PASS** |
| 15 | Signed-in Account | **PASS** |
| 16 | Signed-in Orders | **PASS** |
| 17 | Safari session persistence | **PASS** |
| **Session invalidation** | | |
| 18 | Controlled **server-side** account invalidation | **PASS** |
| 19 | Protected request returns an authoritative **401** | **PASS** |
| 20 | Client clears stale authentication state | **PASS** |
| 21 | Backend customer restoration | **PASS** |
| 22 | Safari remains **signed out** after restore and restart | **PASS** |
| **Cleanup** | | |
| 23 | Disposable acceptance customer deleted | **PASS** |
| 24 | Final `BRAND_PREVIEW_MODE` restoration | **PASS** |
| 25 | Final `/ready` = **200** | **PASS** |

Gate 22 is the one worth naming. Restoring the customer server-side did **not** resurrect the
Safari session, which is the correct outcome: the token was already discarded by the client
when the 401 arrived (gate 20), and restoring a row does not un-discard a credential the
browser has thrown away. A session that came back would have meant the client was trusting
stored state over the server's answer.

---

## 2. Corroboration from the repository

The tester supplied observations. Where the repository can independently confirm the state
those observations describe, it is recorded here — separately from the observation itself,
because the two are different kinds of evidence.

| Claim | Corroborated by | Result |
|---|---|---|
| Price **€72** on the Source Tee | `variant-master.csv` — every `DDN-TS01` variant is `price_eur=72,EUR` | **CONFIRMED** |
| Exactly **five** DEDUNET products | `product-master.json` — `DDN-TS01`, `SH01`, `TR01`, `OS01`, `SC01` | **CONFIRMED** |
| Source Tee identity | `DDN-TS01` = "The Source Tee" | **CONFIRMED** |
| Product not purchasable | `inventory_status=prototype_unavailable`, `stock_quantity=0`, `evidence_status=DRAFT` on every `DDN-TS01` variant | **CONFIRMED** |
| Purchase blocked in preview | `modes.assert_purchasable` refuses on the mode gate before any payment call | **CONFIRMED** |
| Preview disclosure shown | `modes.PREVIEW_DISCLOSURE`, served by `/api/v1/commerce/mode`, rendered by `renderCommerceNotice` | **CONFIRMED** |
| Material / origin caution language | `originText()` and `disclaimerFor()`; `country_of_origin=XX`, `origin_claim_status=UNVERIFIED` | **CONFIRMED** |
| Concept imagery | product media carry `status=PROTOTYPE_CONCEPT` | **CONFIRMED** |
| LAN storefront access | `41cee4c` — *fix: support LAN staging storefront access* | **CONFIRMED** |
| 401 clears stale client auth | `clearCustomerAuth()` behind `isSessionRejection()`; guarded by mutation **M74**, detected | **CONFIRMED** |

**What the repository cannot corroborate, and does not claim to:** that a human held a
physical iPhone, that Safari rendered as described, or that the manual invalidation and
restoration steps were performed. Those are the human half of a human acceptance and are
recorded on the tester's authority. The same is true of the Android record; the difference
is that the Android record captured device identity from the device, and this one could not.

---

## 3. Two defects this acceptance reported

Both were recorded, reproduced against the frozen client, and are now closed.

| | Defect | Closure |
|---|---|---|
| **A** | Product detail offered an enabled "Add to cart" in `BRAND_PREVIEW_MODE`. The server refused with 409; the page invited the action anyway | `2f50e11` |
| **B** | Empty order history read "You have no orders yet.", which reads as an invitation where nothing can be placed | `2f50e11` |

Evidence: [`IPHONE_WEB_HARDENING_CLOSURE.md`](IPHONE_WEB_HARDENING_CLOSURE.md) —
19 tests, 5 new guard mutations, 8/8 detected over the changed file, suite 415 → 434.

**Neither defect was blocking**, which is why this acceptance passes with them recorded rather
than failing on them. Both concerned what a screen *offered*; neither concerned what the
server *permitted*, and preview safety (gates 11–13) held throughout.

---

## 4. Regression state at closure

Executed at `37cd6f6`, after the defect corrections.

```text
backend suite          434 passed, 2 skipped
guard mutations        77 registered; 8/8 detected over apps/web/app.js
OpenAPI                no drift, byte-identical
validators             exit 0 / 0 / 1, ACTIVATION_BLOCKED verified by reason
git                    clean
```

---

## 5. What this acceptance does **not** cover

| Item | Status |
|---|---|
| Native iOS application | **`NOT TESTED`** — see §6 |
| Physical Android hardware | **`NOT TESTED`** — Android acceptance ran on an emulator |
| Hosted or public deployment | **NOT PERFORMED** — local staging only, over a LAN |
| Real payment, stock or fulfilment | **NOT PERFORMED** — none is reachable in preview mode |
| `COMMERCE_TEST_MODE` on iPhone | **NOT TESTED** — the whole run was in `BRAND_PREVIEW_MODE` |
| Accessibility audit on device | **NOT TESTED** — no VoiceOver or automated pass |
| Other iOS browsers | **NOT TESTED** |
| The two corrected screens, re-tested on device | **NOT TESTED** — the corrections landed after this acceptance |

That last row matters. This acceptance found defects A and B; the fixes were verified by
automated tests in a rendered DOM, **not** by a human on the device that reported them. A
human re-check of those two screens is outstanding and is not satisfied by the 434 passing
tests.

---

## 6. Native iOS is NOT TESTED — and this record does not become it

Stated separately because it is the single most likely misreading of this document.

```text
NATIVE_IOS_ACCEPTANCE            NOT TESTED
Apple signing                    NOT TESTED
TestFlight                       NOT TESTED
App Store submission             NOT TESTED
Apple Developer Program          DEFERRED — FUNDING
```

**Mobile web in Safari is not the native application.** They share a commerce contract and
nothing else: no binary was built, no bundle identifier was signed, no provisioning profile
exists, no Expo/EAS iOS build was requested, and no Apple account is available to request one.
Apple Developer Program membership is deferred for **funding**, not for technical readiness,
and that is an owner decision this acceptance does not touch.

A future reader must not aggregate this record with
`NATIVE_ANDROID_PREVIEW_ACCEPTANCE_PASSED` into a claim that "mobile is accepted". Android is
an emulator preview, iOS mobile web is this document, and native iOS is nothing at all.

---

## 7. Precision of this record — what was and was not supplied

Recorded so the record cannot be read as more precise than it is.

| Detail | Supplied |
|---|---|
| Surface, browser, device class (physical iPhone, Safari) | **YES** |
| Commerce mode (`BRAND_PREVIEW_MODE`) | **YES** |
| Target environment (local staging, over LAN) | **YES** |
| 25 gates with results | **YES** |
| Explicit exclusions | **YES** |
| **iPhone model** | **NO** |
| **iOS / Safari version** | **NO** |
| **Commit the acceptance ran against** | **NO** — inferred |
| **Date the testing occurred** | **NO** — this record is dated to its writing |

**The commit is inferred, not stated.** `41cee4c` is the best-supported inference: LAN
storefront access is exactly what that commit added, so the acceptance cannot predate it; and
the two defects it reported existed at `41cee4c` and were fixed in `2f50e11`, so it cannot
postdate `2f50e11`. That bounds it to a two-commit window and is recorded as an inference.

CONFLICT-011's proposed resolution asked for device, iOS version, commit and mode. **Mode was
supplied; device model, iOS version and commit were not.** The substantive gap — an
acceptance with no record at all — is closed, and the residual gap is a matter of
reproducibility detail rather than of whether the acceptance happened. It is recorded here
rather than raised as a new conflict, because the acceptance manager owns the record and has
now written it.

---

## 8. Decision

# `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED`

Physical iPhone Safari, local staging over LAN, `BRAND_PREVIEW_MODE`, 25 gates, two
non-blocking defects found and since corrected.

**Unchanged by this record:**

```text
PUBLIC_COMMERCIAL_LAUNCH_BLOCKED
DEDUNET_PLATFORM_V1_PRODUCTION_BLOCKED
NATIVE_IOS_ACCEPTANCE = NOT TESTED
Apple Developer Program = DEFERRED — FUNDING
```
