# Home — visual rebuild after human acceptance failure

**Artifact ID:** EV-P3-003 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED` — **not** human-accepted
**Date:** 2026-08-25 · **Starting HEAD:** `95ce8f2`

> The architecture was **not** rejected. The human verdict preserved the React consumer
> architecture, the browser E2E suite, the same-origin API topology and the accepted safety
> behaviour, and failed the **visual and product execution** of Home.
>
> `PHYSICAL_IPHONE_HOME_ACCEPTANCE = FAIL / PENDING RETEST` ·
> `STAGING_CUTOVER = BLOCKED` · `MULTI_BRAND_PHASE = NOT STARTED`

---

## 1. What the previous Home actually looked like

Read off the captured 390px full-page render, which is the artefact the verdict was given
against.

| Symptom | Measured |
|---|---|
| Page height at 390px | **10,458px** of near-uniform column |
| Hero | ~380px tall, wordmark at 44px, image a thin strip. Documentation scale |
| Occasions | 11 stacked white boxes with 14px labels — form controls, not discovery |
| Product plates | garment occupying ~30% of a pale field, with the artwork's own caption baked in underneath |
| Rhythm | heading → grid, heading → grid, heading → grid, seven times |
| Dido | one dark box among nine sections |
| Typeface | Bodoni Moda and Manrope **never rendered** — no font file shipped |

## 2. The root cause of the "empty beige rectangles"

The delivered product artwork is a 1200×1500 SVG whose **lower quarter is a caption baked
into the image** — the product name in Bodoni, a `FRONT / PROTOTYPE SILHOUETTE` line and a
provenance line. The silhouette itself runs y 250..1180.

Rendering the whole frame in a card put a small garment above illegible duplicate type in a
large pale field. That is what read as unfinished. Nothing was missing; the wrong part of a
real asset was being shown.

`ProductFigure` crops to the subject. For origin fraction `o` and scale `s` the visible
source range is `[o - o/s, o + (1-o)/s]`; at `o = 0.42, s = 1.65` that is `[0.167, 0.773]` —
source y **250..1160**. The whole silhouette bar about 20px of hem, and none of the caption.

**Two earlier attempts got that arithmetic wrong**, each leaving a sliver of caption in
frame as a line of stray type under the garment. Both were caught by looking at the render,
not by any assertion, which is the whole argument for §11 and §40.

## 3. Typography — resolved, not deferred

Bodoni Moda and Manrope are both **SIL OFL 1.1**, so redistribution is permitted and they
are now **self-hosted**, installed through `@fontsource`, bundled and content-hashed by the
build.

Chosen over a font CDN deliberately:

- **no external runtime dependency and no CSP widening**
- the LAN preview and the physical-iPhone acceptance work **with no internet at all**,
  which is the topology those acceptances actually run on
- no third-party request carrying the reader's IP and referrer
- versioned in the lockfile like any other dependency

Only the used subsets ship: display 600 and 500-italic, Manrope variable, latin.

| File | Size |
|---|---|
| `bodoni-moda-latin-600` | 14.95 kB |
| `bodoni-moda-latin-500-italic` | 17.00 kB |
| `manrope-latin-wght` | 24.84 kB |

**~57 kB for the latin set.** Non-latin subsets are separate files behind `unicode-range`
and are never fetched by an English page.

## 4. What changed, section by section

| Section | Before | Now |
|---|---|---|
| Hero | 380px, wordmark-led, text-heavy | Full-bleed dark, `86svh`, campaign statement at up to 112px, **one** dominant CTA with the secondary as a text link, staggered entrance |
| Occasions | 11 stacked form-like boxes | A rail of 3:4 image plates, each carrying **real delivered concept artwork**, with a press state and a styling cue |
| Feature look | did not exist | A split composition: large plate, descriptors, the editorial argument, and the pieces listed with the job each does |
| Dido | one section among nine | **Full-bleed staged moment**: the character runs a real six-state styling sequence while three real catalogue plates assemble beside it, joined by a rule that draws itself |
| Looks | grid | Rail, above the products, each look showing its lead piece in a **different delivered view** so the rail is varied without any plate misrepresenting its look |
| Statement | did not exist | A type-only pause on the raised ground, between two rails |
| Products | the primary grid | A rail **below** looks, framed as the pieces looks are built from (§7) |
| By style | 8 more boxes | A dense typographic list |
| Brands | grid | Rail |
| For brands | pale band | Split dark panel |

**The information architecture is unchanged.** Every accepted element is still present and
in the accepted order (§1).

## 5. Motion

| Moment | Behaviour |
|---|---|
| Hero entrance | Four elements, staggered 60–340ms, plays once |
| Section reveal | `IntersectionObserver`, fires once, then unobserves |
| Occasion press | `scale(0.985)` — touch has no hover to borrow |
| Card press | 1px translate |
| Plate hover | slow push-in, pointer devices only |
| Dido sequence | six states, **starts only when on screen**, runs once and rests |

Everything animates **opacity and transform only**, so it stays on the compositor.
`prefers-reduced-motion` is honoured centrally by zeroing the duration tokens, and the Dido
sequence additionally jumps straight to its final state rather than stepping through six
zero-length holds.

## 6. Defects found by looking, at the five required widths

None of these would have failed an assertion.

| Defect | Cause |
|---|---|
| Hero CTA **clipped behind the mobile tab bar** | `body` reserves the bar for the LAST element; the hero is the first, and the bar sat over its foot |
| Statement broke into `De / cid / e / wh / at / to` at 1440 | **`ch` resolves against the container's inherited body size, not the display type inside it** — a `17ch` column was ~140px wide holding 112px type |
| `A / wardro / be is a / set of` in the editorial statement | the same `ch` mistake, second occurrence |
| Artwork's own "Worth, worn." ghosting under the hero lede | two typographic layers in one space; the crop was applied only above 900px |
| A stray dark bar across the phone hero | the artwork's horizontal rule, cropped to a stub at phone width |
| For-brands artwork **escaping its column and covering the copy** | a scaled image in a grid column with no `overflow: hidden` |
| Two-item brands rail rendering 620px plates | `1fr` columns make card size a function of item count |
| Feature plate swamping its copy | unbounded plate width |

## 7. Verification

| Check | Result |
|---|---|
| Browser suite — Chromium | **135 passed** |
| Browser suite — WebKit | **135 passed** |
| Browser suite — Mobile Safari (iPhone 13 viewport) | **135 passed** |
| No horizontal overflow | 320 · 375 · 390 · 430 · 768 · 1024 · 1280 · 1440 |
| CSS contract | no class renders without a rule |
| Heading outline | one h1, no skipped levels |
| Page height at 390px | 10,458px → **~8,800px**, with far more content in it |

Captures at the five widths §11 names are in `evidence/phase-3/home-visual/` — full page and
first viewport for 390, 430, 768, 1280 and 1440.

## 8. Not claimed

- **No human acceptance.** `PHYSICAL_IPHONE_HOME_ACCEPTANCE` remains FAIL / pending retest.
- **`STAGING_CUTOVER` remains BLOCKED.** The candidate is still additive on 13081.
- **`MULTI_BRAND_PHASE` NOT STARTED.**
- Only **Home** was rebuilt. The remaining consumer screens carry the new component
  treatments where they share components, but have not had their own visual pass.
- Firefox remains **BLOCKED** in this environment.
- LCP, INP and CLS are still **not measured on a device**.
