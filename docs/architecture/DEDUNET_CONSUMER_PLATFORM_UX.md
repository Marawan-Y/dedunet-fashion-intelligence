# DEDUNET consumer platform — UX specification

| Control | Value |
|---|---|
| Artifact ID | ARCH-P2-001 |
| Version | 1.0 |
| Date | 2026-08-25 |
| Owner | Technical lead (successor agent) |
| Status | **AUTOMATED-TESTED** — implemented and covered by `test_consumer_platform.py` |
| Phase | 2 — professional design system + consumer platform foundation |
| Related | `ADR-0002` §2.0, `ADR-0003`, `DEDUNET_DESIGN_SYSTEM.md` |

---

## 1. Positioning

DEDUNET is **not primarily a clothing brand**. It is a personal fashion intelligence
platform, and the interface has to say so before any copy does.

> **DEDUNET helps you decide what to wear, then helps you find it.**

The catalogue supports the styling experience. It is one destination inside the platform,
not the platform's identity.

**The single change that carries this** is the landing route:

```diff
- const hash = location.hash || "#/catalog";
+ const hash = location.hash || "#/";
```

A platform whose front door is a product grid is a shop with extra pages, whatever the
navigation says. Everything else in this document follows from what that route now shows.

### What the hero may not do

Tested, not merely intended — `test_the_hero_sells_styling_not_products`:

| Forbidden in the hero | Why |
|---|---|
| "Shop now" | positions the product as goods, not decisions |
| "Buy now" | same |
| "Collection" | brand-store framing |

---

## 2. Sitemap

```
#/                        Home              platform landing
#/dido                    Dido              PRIMARY ACTION — styling conversation shell
#/discover                Discover          18 categories, 3 groupings
#/discover/:category      Discover filtered
#/looks                   Looks             listing
#/look/:slug              Look detail       pieces, prices, reasoning
#/brands                  Brands            listing, all three ownership shapes
#/brand/:slug             Brand detail      story, commerce destination
#/shop                    Shop              catalogue (alias: #/catalog)
#/product/:slug           Product detail    media, sizes, purchasability, related looks
#/cart                    Bag
#/checkout                Checkout
#/orders                  Orders
#/order/:number           Order detail
#/saved                   Saved             looks · products · brands
#/account                 Account           section hub
#/my-style                My Style          Style DNA foundation
#/for-brands              DEDUNET for Brands
#/stylist                 Legacy stylist    preserved
```

`#/catalog` is retained as an alias. The accepted Android and iPhone clients link to it,
and Phase 2 may not invalidate a passed acceptance to tidy a URL.

---

## 3. Navigation

Two different information architectures, **not one shrunk**.

| | Desktop (≥1024px) | Mobile (<1024px) |
|---|---|---|
| Pattern | top bar, 7 links | bottom tab bar, 5 destinations |
| Items | Style with Dido · Discover · Looks · Brands · Shop · Saved · Account | Home · Discover · **Dido** · Saved · Account |
| Dido | accent-coloured, weighted — primary among peers | raised out of the bar at the centre |

**Structurally mobile-first.** `.nav` is `display: none` by default and appears at a
`min-width`; the tab bar is the default and is never hidden by a `max-width`. That
direction is the difference between mobile-first and desktop-shrunk, and
`test_the_mobile_navigation_is_not_a_media_query_afterthought` asserts it in the CSS
rather than trusting the intent.

**Active route** is carried by `aria-current="page"` and the CSS keys off it, so the
visual highlight and the screen-reader announcement are the same fact rather than two that
can drift.

---

## 4. Home

| Region | Content |
|---|---|
| Hero | wordmark · "Personal fashion intelligence." · promise · **Style me with Dido** (primary) · Discover looks (secondary) |
| Occasion picker | "What are you dressing for?" — 11 cards routing to `#/dido?occasion=…` |
| Looks selected for you | **explicit "not built yet"** — see §7 |
| Trending · Editor's picks · under €100 · under €200 | fixture rails, each badged |
| Discover brands | three ownership shapes, consumer labels |
| Meet Dido | character + entry |
| For brands | merchant SaaS entry |

---

## 5. Dido

Phase 2 delivers the **surface**, not the engine.

**In:** route, entry page, character container, animation abstraction, ten states,
conversation shell, message components, option cards, thinking state, error state,
reduced-motion fallback, accessibility structure.

**Out** (Phases 7–10): LLM orchestration, recommendation engine, Style DNA persistence,
retrieval, outfit scoring.

### Character direction

Ancient Egyptian **proportion and geometry** — a vertical cartouche frame, a stacked-lintel
head silhouette, a single accent iris. Explicitly not: headdress, gold-mask pastiche,
cartoon pharaoh, tourist iconography. Those are ruled out by the brief and are also what
would date the brand to a gift shop.

Drawn as **inline SVG**: no request, no library, no animation runtime. §24 warns against
adopting a heavyweight animation dependency before measuring its cost; this is the option
that needs no measurement.

`didoAnimator` is the seam. CSS owns what each state looks like, keyed off one
`data-state` attribute, so a later Rive or Lottie renderer implements the same
`setState` contract and no caller changes.

### States

`idle · listening · asking · thinking · styling · comparing · presenting · success · error · offline`

### What it will not do

Choosing an occasion moves the character `asking → thinking → presenting` and answers with
what it can honestly say: *it cannot style yet, and here is what the editorial desk has*.
That exercises the animation seam. It is not a scripted recommendation, and two tests exist
to keep it that way.

---

## 6. Brands

The UI supports all three ADR-0002 ownership shapes, and **never exposes the technical
vocabulary**.

| Model | Consumer label | Commerce destination |
|---|---|---|
| `PLATFORM_CURATED` | DEDUNET selection | per route |
| `MERCHANT_OWNED` | Partner brand | per route |
| `EXTERNAL_CURATED` | External brand | per route |

Ownership and route stay **orthogonal on screen** as well as in the model: the destination
line is derived from `commerce_route`, never from `ownership_type`.

Only DEDUNET is real. The other two state in their own copy that no such brand exists and
none has been approached.

---

## 7. Honesty rules

The two ways a demonstration build starts lying, and the rule against each.

### Fixtures must be unmistakable

Every module rendering demonstration content carries a **fixture badge**. Every record in
the service layer carries `source: "fixture" | "live" | "unavailable"`, so this is
enforceable by test rather than by reviewer memory.

### "Not built" is not "empty"

These are different facts and must not render the same way.

| | Renders as |
|---|---|
| Empty result | empty state — "no looks in this category yet" |
| Capability absent | **unavailable state** — names the capability and the phase it arrives in |

Saved reports *unavailable* rather than reading and writing `localStorage` to look
functional. **A save button that silently forgets is worse than one that admits it is not
built.**

"Looks selected for you" is the module this phase most obviously could have faked.
Personalisation needs Style DNA and a recommendation engine; DEDUNET has neither, so the
module says so. A "selected for you" heading over fixture looks would be a personalisation
claim, which §6 forbids outright.

---

## 8. Preview safety — unchanged

Phase 2 changed presentation. It changed **no commerce guard**.

- Product detail mirrors **both** gates of `modes.assert_purchasable`. In
  `BRAND_PREVIEW_MODE` the control reads **"Not available to buy"**, is `disabled`, and is
  `aria-describedby` a paragraph giving the reason.
- Orders empty state stays mode-derived: *"No orders yet. Purchasing is unavailable while
  this catalogue is in preview."*
- Expired-session 401 clearing is unchanged.

All re-verified: purchase refusal 19 tests, session expiry 20 tests, both green.

---

## 9. Responsive behaviour

| Breakpoint | Width | Behaviour |
|---|---|---|
| base | <480 | tab bar; single-column; rails swipe horizontally |
| sm | ≥480 | grids begin to fill |
| md | ≥768 | rails become grids; filters go horizontal; hero CTAs size to content |
| lg | ≥1024 | **desktop header appears, tab bar disappears**; detail pages go two-column with sticky media |
| xl | ≥1280 | content caps at `--ds-content-max` (1280px) |

**The grid rule that matters:**

```css
grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr));
```

Without `min(…, 100%)` a 260px floor overflows a 320px viewport. Verified: at 375×812 the
document `scrollWidth` is 375 — **no horizontal overflow**.

---

## 10. Accessibility

Target: WCAG 2.2 AA where practical.

| Requirement | Implementation |
|---|---|
| Landmarks | one `header`, `main`, `footer`; every `nav` has `aria-label` |
| Heading order | exactly one `h1` per page, asserted |
| Skip link | `.skip` → `#main`, visible on focus |
| Focus | `:focus-visible` with a 2px accent ring, never removed |
| Target size | 44px floor on buttons, chips, size selectors, tab bar |
| Labels | `field()` binds `for`, and hint/error via `aria-describedby` |
| Errors | `aria-invalid` **drives** the styling, so visual and announced state cannot diverge |
| Status | one polite live region (`#ds-live`); several competing regions is how a message ends up announced by none |
| Reduced motion | all durations route through `--ds-duration-*`, zeroed in one media query; Dido's iris animation explicitly stilled |
| Dido | `role="img"` with an `aria-label` naming the current state; state changes announced |

### Measured contrast

Against the delivered Side A tokens:

| Pair | Ratio | AA (4.5:1) |
|---|---|---|
| text / background | **16.61** | pass |
| text / surface | **18.70** | pass |
| muted / background | **5.95** | pass |
| subtle / background | **5.95** | pass *(was 4.09 — see below)* |
| accent text / accent | **5.40** | pass |
| background / dark surface | **14.38** | pass |
| error / background | **5.82** | pass |
| success / background | **5.59** | pass |

**One role failed on first measurement and was fixed.** `--ds-text-subtle` mapped to
`--ddn-color-smoke` (`#7C746A`) at **4.09:1** — below the AA floor for normal text, on the
14px copy that explains what is fixture content and why a control is disabled. Remapped at
the semantic layer to `--ddn-color-textsecondary` (5.95:1). The delivered token set is
unchanged; `--ddn-color-smoke` stays available for non-text use.

Guarded by seven contrast assertions, parametrised over every text role so the next one
added is measured too. See `evidence/phase-2/PHASE_2_CONSUMER_PLATFORM_EVIDENCE.md` §5.

### Not done

No automated axe run, no screen-reader pass, no keyboard walkthrough of every route by a
human. Structural accessibility is implemented and asserted; **audited accessibility is
not claimed.**

---

## 11. Service boundaries

`data.js` defines the interfaces later domains plug into. Each has exactly one
implementation today:

| Service | Implementation | Real in |
|---|---|---|
| `LooksService` | FIXTURE | Phase 9 |
| `BrandsService` | FIXTURE | Phase 4 |
| `SavedService` | UNAVAILABLE | later |
| `StyleProfileService` | UNAVAILABLE | Phase 6 |
| `DidoService` | UNAVAILABLE | Phase 7/10 |

When a real endpoint lands, its service swaps its implementation **here**. No page changes.
That is the whole point of the boundary, and it is why no speculative backend was built to
satisfy a frontend mock.

---

## 12. What Phase 2 did not build

Non-goals, restated so a reader cannot mistake the shell for the system:

LLM orchestration · recommendation scoring · outfit optimization · vector search · fashion
knowledge engine · merchant tenancy migrations · merchant portal backend · external brand
integrations · hosted merchant checkout · subscriptions · real payments · production cloud ·
app stores.
