# Phase 2 — Consumer platform foundation, acceptance evidence

**Artifact ID:** EV-P2-001 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED` · **Date:** 2026-08-25
**Starting HEAD:** `5b85fc5` · **Authorized by:** owner, Phase 2 brief
**ADR:** `ADR-0002` §2.0 (approved as revised), `ADR-0003` (frontend architecture)

> `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` remains in force. Phase 2 changed **presentation**.
> It changed no commerce guard, no payment path, no mode, no schema and no API contract.

---

## 1. What was delivered

| Area | Delivered |
|---|---|
| Design system | token layer + semantic layer + component library, built on the Side A tokens |
| Component library | ~35 components across action, form, content, state, overlay, media, Dido |
| Routes | 13 new, 6 preserved |
| Pages | Home, Dido, Discover, Discover/:category, Looks, Look detail, Brands, Brand detail, Saved, My Style, For Brands, Shop, Product detail |
| Navigation | desktop bar (7) + mobile tab bar (5), mobile-first |
| Service layer | 5 interfaces with fixture / unavailable adapters |
| Dido | character, 10 states, animator seam, conversation shell, reduced motion |
| Tests | **+59** (53 consumer platform, +6 security scan coverage) |
| Docs | UX spec, design system, ADR-0003, this evidence |

---

## 2. Verification

All executed at the Phase 2 head, Python 3.14.4, SQLite path.

| Check | Result |
|---|---|
| Backend suite | **493 passed, 2 skipped** (was 434 / 2) |
| Consumer platform suite | **53 passed** |
| Accepted purchase refusal | **19 passed** — unchanged |
| Accepted session expiry | **20 passed** — unchanged |
| Mode notice · gallery · media resolver | **passed** — unchanged |
| Frontend security scan | **12 passed** — now covers 5 client scripts, was 2 |
| Governance validator | **PASS, 0 errors** |
| Handoff envelopes | **PASS, 8/8** |
| Governance tests | **43 passed** |
| Brand package drift | **NO_DRIFT** |
| Side A package | `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| Data validators | exit **0 / 0 / 1** with `ACTIVATION_BLOCKED` verified by reason |
| `git diff --check` | clean |
| Mutations over `apps/web/app.js` | **8 run, 8 detected, 0 survived** |
| Contrast, every text role | **AA pass** — see §5 |

### Test-count delta, explained

`434 → 493` is **+59**:

- **+53** `tests/test_consumer_platform.py`, the new file — 46 platform assertions plus 7
  contrast assertions added after the AA failure in §5 was measured.
- **+6** `test_frontend_security.py`, which is parametrised over the client scripts it
  scans. That list went from 2 files to 5, and 3 × 2 tests = 6.

**No test was weakened, skipped or relaxed.** Four existing harnesses had their script list
updated from `["media-url.js", "app.js"]` to
`["media-url.js", "ds.js", "data.js", "app.js"]`, tracking a real file split. Their
assertions are untouched.

---

## 3. Human-observable verification, desktop browser

Driven in a real browser, not only in jsdom. Every route rendered, and
`document.scrollWidth` never exceeded the viewport.

| Route | h1 | Overflow |
|---|---|---|
| `#/` | DEDUNET | none |
| `#/dido` | Style with Dido | none |
| `#/discover` | Discover | none |
| `#/discover/interview` | Interview Fits | none |
| `#/looks` | Looks *(+ demo badge)* | none |
| `#/look/quiet-interview` | The Quiet Interview | none |
| `#/brands` | Brands | none |
| `#/brand/dedunet` | DEDUNET | none |
| `#/brand/example-partner` | Partner brand (shape demonstration) | none |
| `#/saved` | Saved | none |
| `#/my-style` | My Style | none |
| `#/for-brands` | Reach customers through styling intelligence. | none |
| `#/account` | Account | none |
| `#/orders` *(signed out)* | → Account | none |
| `#/nonsense` | 404 error state | none |

### Responsive, measured

| Viewport | Desktop nav | Tab bar | Rails | Body pad | Overflow |
|---|---|---|---|---|---|
| 375 × 812 | `none` | `grid`, 5 cols | `column` (swipe) | 72px | **none**, scrollWidth 375 |
| 1280 × 800 | `flex`, 7 links | `none` | `row` (grid) | 0 | none |

### Brand tokens live on the page

`--ddn-color-accent` resolves to `#A95122` and flows through `--ds-accent`. The delivered
Side A palette is what renders, not the storefront's former invented one.

### Dido, driven

`asking → thinking → presenting`, `aria-label` updating with the state, live region
announcing *"Dido replied about Work"*, and the reply saying it **cannot style yet**.

### Degradation with no API

`#/shop` with no backend: skeleton → *"Cannot reach DEDUNET / Check your connection and try
again."* with the raw `Failed to fetch` below it and a **Try again** control. Not a blank
page, and not a generic "Load failed".

---

## 4. Accessibility

### Contrast, measured against the delivered tokens

| Pair | Ratio | AA |
|---|---|---|
| text / background | 16.61 | pass |
| text / surface | 18.70 | pass |
| muted / background | 5.95 | pass |
| accent text / accent | 5.40 | pass |
| background / dark surface | 14.38 | pass |
| error / background | 5.82 | pass |
| success / background | 5.59 | pass |

**One role failed on first measurement.** `--ds-text-subtle`, mapped to
`--ddn-color-smoke` (`#7C746A`), measured **4.09:1** — below the 4.5:1 AA threshold for
normal text, and it is used at 14px, which is not "large text". Corrected by remapping the
semantic role, not by editing the delivered token: see §5.

Recorded rather than quietly fixed, because a design system whose contrast is asserted by
intention rather than measurement is how an inaccessible palette ships.

### Structural

Landmarks (one header / main / footer, every `nav` labelled) · one `h1` per page · skip
link · `:focus-visible` rings · 44px target floor · labels bound via `for` · hints and
errors via `aria-describedby` · `aria-invalid` driving error styling · one polite live
region · `prefers-reduced-motion` zeroing every duration centrally and stilling Dido.

### Not done

No automated axe run. No screen-reader pass. No human keyboard walkthrough of every route.
**Structural accessibility is implemented and asserted; audited accessibility is not
claimed.**

---

## 5. A contrast defect found and fixed

`.ds-subtle` renders at `--ds-text-sm` (14px) in `--ds-text-subtle`. Measured 4.09:1
against the page background — a real AA failure on text used for the "not built yet" notes,
the fixture explanations and the save-unavailable hints. Exactly the copy a customer needs
to read to understand what is and is not real.

**Fixed at the semantic layer**, by pointing `--ds-text-subtle` at the same token as
`--ds-text-muted`. The Side A token set is unchanged — it is generated and immutable, and
`--ddn-color-smoke` remains available for non-text use where contrast does not apply.

Verified on the live page after the fix:

```text
--ds-text-subtle   #625B51    computed colour on .ds-subtle    #625b51
font-size          14px       ratio against background          5.95:1
```

That is the layer separation earning its keep: an AA failure was a one-line remap of a
**role**, not an edit to a delivered brand value.

**Guarded against regression.** Seven contrast assertions were added, parametrised over
every text role so the next one added is measured too, plus a specific guard that
`--ds-text-subtle` may not point back at `--ddn-color-smoke`. Proven load-bearing:
restoring the original mapping makes
`test_the_semantic_layer_does_not_use_the_low_contrast_token_for_text` fail.

---

## 6. Guard mutations

`apps/web/app.js` is a mutation target and it changed, so all 8 mutations over it were
re-run.

| ID | Guard | Result |
|---|---|---|
| M68 | product gallery renders media | **DETECTED** |
| M69 | gallery preserves API ordering | **DETECTED** |
| M74 | expired session cleared on 401 | **DETECTED** |
| M75 | preview mode refuses the purchase invitation | **DETECTED** |
| M76 | non-sellable product refuses the invitation | **DETECTED** |
| M77 | the refusal reaches the control | **DETECTED** |
| M78 | empty order history does not promise what preview refuses | **DETECTED** |
| M79 | an unstated mode is not adopted as a working one | **DETECTED** |

```text
8 run, 8 detected, 0 survived
```

**This is the evidence that the refactor preserved the guarantees, not just the tests.**
`app.js` grew from 1,021 to ~1,750 lines, its primitives moved to another file and its
router changed shape. Every accepted safety guard still fails its suite when removed, which
is a stronger statement than the suite being green: green would also be true if the guards
had stopped being reachable.

No mutation target other than `apps/web/app.js` was changed, so the other 69 entries were
not re-run.

---

## 7. A bug the tests did not catch

`ds.js` declared `function el` at top level; `app.js` declared `const el = window.DS.el`.
Two top-level declarations of one identifier in classic scripts is a **`SyntaxError` that
stops the entire page**.

**Every jsdom test passed. The page was blank.**

jsdom's harnesses `window.eval` each file, which gives each its own scope. A browser loading
real `<script>` tags shares one top-level scope and does not.

Found by opening the page in a browser — not by any test. Fixed by wrapping `ds.js` and
`data.js` in IIFEs so each publishes exactly one global, and guarded by
`test_each_client_script_publishes_exactly_one_global_namespace`.

**The lesson is recorded because it generalises:** a jsdom suite verifies what a function
renders, not that the page loads. Phase 2 added twelve routes' worth of behaviour behind a
failure mode no amount of that suite would have surfaced. Visual verification is not
optional for a frontend phase.

---

## 8. Preview safety — re-verified, unchanged

| Property | State |
|---|---|
| Product detail in `BRAND_PREVIEW_MODE` | "Not available to buy", `disabled`, reason via `aria-describedby` |
| Both gates of `assert_purchasable` mirrored | yes — mode gate and product gate independently |
| Orders empty copy | mode-derived, three variants, no shared sentence |
| Expired-session 401 clearing | unchanged |
| DEDUNET 5-product preview catalogue | unchanged |
| Commerce guards, payments, modes | **not touched** |

---

## 9. Not done in Phase 2

| Item | Status |
|---|---|
| Physical iPhone Safari regression | **NOT TESTED** — no device access in this environment |
| Android emulator regression | **NOT TESTED** — not run this phase |
| Automated accessibility audit | **NOT RUN** |
| Visual regression snapshots | **NOT BUILT** — §31 permits an alternative; route-level DOM assertions and measured layout were used instead |
| Dido LLM orchestration | **NOT STARTED** — Phase 7/10 |
| Recommendation engine, outfit scoring | **NOT STARTED** — Phase 8/9 |
| Merchant backend, tenancy migrations | **NOT STARTED** — Phase 4/5 |
| Saved / Style DNA persistence | **NOT STARTED** — Phase 6 |

**iPhone and Android are `NOT TESTED` this phase.** Phase 2 changed every consumer surface
those acceptances covered, so their passed states describe a build that no longer exists on
the web surface. This is stated as a limitation rather than assumed to carry forward.

---

## 10. Result

**`PHASE_2_CONSUMER_PLATFORM_AUTOMATED_VERIFIED`** — on automated evidence and desktop
browser verification.

**Not** human acceptance on mobile hardware. See §9.
