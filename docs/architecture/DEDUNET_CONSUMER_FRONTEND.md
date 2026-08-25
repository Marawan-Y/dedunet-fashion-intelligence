# DEDUNET consumer frontend — architecture and design language

| Field | Value |
|---|---|
| Artifact ID | ARCH-CONSUMER-002 · **Version** 1.0 |
| Status | `AUTOMATED-TESTED` — not human-accepted on any device |
| Owner | Side B / platform |
| Supersedes | the `apps/web` half of `DEDUNET_DESIGN_SYSTEM.md` |
| ADR | `ADR-0004` (decided), supersedes `ADR-0003` |

---

## 1. Where the code is

```
apps/consumer/
  index.html                 loads the generated token layer, then the bundle
  public/                    GENERATED — tokens.generated.css, brand.generated.js
  src/
    design-system/           reset, semantic token layer, document defaults
    components/              the component library (CSS Modules)
    api/                     typed client, endpoints, session
    app/                     shell, router, commerce mode, error boundaries
    features/                one directory per route
    lib/                     async state, brand seam
  e2e/                       Playwright — the browser-level acceptance suite
  Dockerfile                 multi-stage; runtime is static nginx, read-only
  nginx.conf                 history fallback, cache policy
```

`apps/web` (classic) and `apps/admin` are unchanged and still served. The admin portal is
**not** migrated: separate surface, own acceptance, no reported defect.

## 2. The layer separation, and why it exists

```
tokens.generated.css   GENERATED from the Side A delivery. Immutable. Brand VALUES.
design-system/tokens   Semantic ROLES over those values. Everything reads roles.
design-system/base     Document defaults. Element selectors, two utility classes.
components/*.module    Component styling. Hashed at build.
```

Nothing outside `tokens.css` refers to a `--ddn-*` value. That is what made the Phase 2 AA
contrast failure a one-line fix: `--ddn-color-smoke` measured 4.09:1 against the page
background on 14px text, and the correction repointed the **role** rather than editing a
delivered brand value. `--ds-text-subtle` must never point back at it, and a backend test
asserts that.

### CSS Modules are the structural fix for the Phase 2 defect

At `9b63791`, `index.html` stopped loading `styles.css` while `app.js` kept emitting its
class names. Seventeen classes rendered with nothing behind them.

A CSS Module cannot do this. `styles.pdp__thumbs` is either a compiled, hashed name or
`undefined` — and `undefined` renders **no class attribute at all** rather than an unstyled
one. The failure mode becomes a missing style on one element instead of a page of naked
form controls, and the CSS contract test in the E2E suite catches even that.

This is why global class names are kept to two (`sr-only`, `skip-link`), both of which are
contracts with assistive technology rather than visual styling.

## 3. The design language

Derived entirely from the delivered Side A token set. The brand is **architectural, not
soft**: every radius token is `0`, so the system is drawn with hairline rules and hard
corners rather than rounded cards.

| Role | Decision |
|---|---|
| Ground | `#F6F1E7` warm sand. Surfaces are white and raised sand, never grey |
| Ink | `#14120F` near-black |
| Accent | `#A95122` terracotta — used for the promise line, Dido, and one CTA per view |
| Display | Didone, tracked **-0.022em**. Negative tracking at display size is what makes a serif read as fashion typography rather than as a large book face |
| Eyebrow | 12px, `0.16em` tracking, uppercase. The single most load-bearing editorial device on the platform |
| Rhythm | 112px between sections on desktop, 72px on a phone — from the delivered tokens |
| Measure | 700px for prose, 1280px for layout. Long copy is never set at layout width |
| Elevation | Restrained. Drop shadows over sand read as grey smudge, so hierarchy comes from the ground and the rules |

**Egyptian reference is geometry, not iconography.** No scarabs, no pharaoh, no tourism
motifs. It appears as the cartouche proportion in Dido's frame, the doubled rule at a tight
offset, and the horizontal passage-line rhythm taken from the delivered pattern asset.

### Typography renders in fallback faces

`fonts.json` names Bodoni Moda and Manrope. **No font file ships and no webfont is linked**,
so both resolve to their declared fallbacks. Adding a Google Fonts link would put an
external network dependency and a CSP widening into a preview build served over a LAN, which
is the topology the iPhone acceptance uses. Deferred decision, recorded in
`KNOWN_LIMITATIONS.md`, not an oversight.

## 4. The motion system

Every duration and easing is a token. No component owns a duration.

| Category | Token | Applied to |
|---|---|---|
| Interaction | `--ds-duration-instant` 90ms | button press |
| Hover, focus | `--ds-duration-fast` 160ms | nav, chips, fields |
| Transition | `--ds-duration-base` 240ms | page transition, card hover, Dido turns |
| Reveal | `--ds-duration-slow` 420ms | image fade-in, Dido aperture |

`prefers-reduced-motion` zeroes the durations **centrally**, in `tokens.css`. A component
cannot forget to honour it because it never had a duration of its own to forget. Dido stills
completely rather than slowing, and stays legible because its states are geometry rather
than animation.

## 5. Dido

`DidoFigure` takes one input — a `DidoState` from a 13-value union — and returns a picture.
It exposes no timeline, no frame and no duration, so **replacing SVG with Rive, Lottie or
WebGL is a change to the body of one function** and to nothing that calls it. That is the
renderer abstraction §10 asks for, and the whole of it.

V1 is inline SVG deliberately: a few hundred bytes, inherits design-system colour through
`currentColor`, no runtime, and it costs a phone nothing.

**Dido is a shell and says so on screen.** The conversation, the state machine, the
one-question-at-a-time flow, the live region and the reduced-motion behaviour are real and
worth having early. What Dido will not do is invent a recommendation: at the end of the flow
it states that it cannot style anyone yet, and lists the inputs it would need with the
honest state of each.

## 6. Routing

**Real paths, not hashes.** A hash router never asks the server for a route, which is why it
appears to work everywhere and also why it cannot produce a URL a server, a crawler or a
native app can resolve.

The cost is one requirement on the host — a history fallback, so `/discover` serves
`index.html` rather than 404. It is in `nginx.conf` and native to the dev server. **Its
absence fails only on reload and deep links**, never while clicking, which is how that defect
reaches production; the E2E suite reloads every route for exactly that reason.

Route-level code splitting via `lazy()`. Each page is a 1–8 kB chunk.

## 7. Measured budgets

Production build, gzip:

| Asset | Raw | Gzip |
|---|---|---|
| `index` (React + shell + design system) | 203.1 kB | **64.6 kB** |
| `router` | 102.6 kB | **34.7 kB** |
| `index.css` | 16.0 kB | **3.9 kB** |
| Largest route chunk (Dido) | 8.4 kB | 3.3 kB |
| Whole `dist/`, excluding sourcemaps | 429.3 kB | — |

**Initial load for Home is ~108 kB gzip.** Not yet measured on a device: LCP, INP and CLS
have no numbers, and §28 is therefore only partly satisfied. The layout reserves space for
every image through `aspect-ratio` and explicit intrinsic sizes, which is where CLS is
usually won or lost, but that is a design decision rather than a measurement.

## 8. Functional states

Every async surface renders loading, success, empty and error, and the error copy is
**specific per status** — 401, 403, 404, 409, 429, 5xx and transport failure each get their
own sentence, because "something went wrong" tells a customer nothing about whether waiting,
signing in or giving up is the right response. The raw failure is shown beneath it so a
report is actionable.

No blank page: a render failure anywhere in the tree is caught by the router's error element
rather than leaving React's white screen.

## 9. What is real and what is not

| Surface | State |
|---|---|
| Catalogue, product detail, search, filters, sort | **Real** — the live API, filters that filter, counts from the filtered array |
| Sign in, register, sign out, session | **Real** — the commerce API, accepted 401 semantics preserved |
| Purchase gate | **Real** — mirrors the server's two gates, refusal reason bound to the control |
| Looks | **Composed** — real products, real imagery, real attribution; the *curation* is by hand and every surface says so |
| Occasions, style cuts | **Real navigation**, category-rule filtering. Not a styling model |
| Brands | DEDUNET is real. The second entry is a labelled structure demonstration and is **not a partner** |
| Saved | **Not built.** No store, and it does not write to `localStorage` to look functional |
| My Style | **Not built.** No profile, no inferred signals, and deliberately **no percentages** |
| Dido | **Shell.** Conversation real, intelligence absent, stated on screen |
| Prices | **Absent.** Every DEDUNET piece is a prototype with no commercial price; a look shows "Not priced" and says why |
