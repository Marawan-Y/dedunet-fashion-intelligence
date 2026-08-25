# DEDUNET design system

| Control | Value |
|---|---|
| Artifact ID | ARCH-P2-002 |
| Version | 1.0 |
| Date | 2026-08-25 |
| Owner | Technical lead (successor agent) |
| Status | **AUTOMATED-TESTED** |
| Source of truth | `packages/brand/` — generated from the immutable Side A delivery |

---

## 1. The finding this system exists to correct

`packages/brand/tokens.css` has existed since the DEDUNET integration, generated from the
Side A package. **The storefront never adopted it.** It carried its own palette —
`--ink`, `--sand`, `--bone`, `--clay` — and nothing checked that the two agreed.

Two palettes, one brand, no drift detection between them.

The design system is built on the delivered tokens and only on them.

---

## 2. Layers

```
tokens.generated.css    --ddn-*    GENERATED. What a colour IS.    Never hand-edited.
design-system.css       --ds-*     Semantic. What a colour is FOR.
components.css                     Components. Reference --ds-* only.
shell.css                          Layout, navigation, Dido surface.
```

**Components never name a colour.** A raw hex below the token layer means a value outside
the delivered palette, which is exactly how a second palette appears. Asserted by
`test_the_design_system_consumes_only_brand_tokens`, which strips comments and fails on any
`#rrggbb` in the component layer.

### Distribution

`apps/web` and `apps/admin` are static files served by nginx from a **read-only**
filesystem with **no build step**, so they cannot `@import` from `packages/`. The generator
emits `tokens.generated.css` into both clients, exactly as it already emitted
`brand.generated.js`.

Drift is checked across **both artefacts in both clients**, and the check is load-bearing:
appending one comment to `apps/web/tokens.generated.css` makes `--verify-no-drift` report
`STALE ['web/tokens.generated.css']` and exit 1.

---

## 3. Tokens

| Group | Tokens |
|---|---|
| Surface | `bg` `surface` `surface-raised` `surface-inverse` `border` `border-strong` |
| Text | `text` `text-muted` `text-subtle` `text-inverse` |
| Accent | `accent` `accent-text` `primary` `primary-hover` `secondary` |
| State | `success` `warning` `error` `info` + a `-wash` for each |
| Type | `font-display` `font-body`, scale `xs → hero`, leading, tracking |
| Space | `space-1 … space-9` (4px base) + section/card gaps |
| Layout | `content-max` `editorial-max` `gutter` |
| Shape | `radius` `radius-button` `radius-input` `radius-pill` `border-width` |
| Elevation | `shadow-sm` `shadow-md` `shadow-lg` |
| Motion | `duration-fast` `duration` `duration-slow` `ease` |
| Z-index | `base` `sticky` `mobilenav` `drawer` `dialog` `toast` |
| Focus | `focus-ring` `focus-offset` |

Two decisions worth naming.

**The delivered radii are 0 and the system honours that.** It is an editorial decision by
Side A, not an omission to be rounded away because rounded corners look modern.

**Every duration routes through the motion tokens**, so `prefers-reduced-motion` is handled
in one media query rather than each component remembering to opt out. State washes are
`color-mix` of the state hue rather than separately picked colours, so a palette change
carries both.

**Z-index is a named scale.** Ad-hoc values are how a dialog ends up behind a sticky header.

---

## 4. Component inventory

| Group | Components |
|---|---|
| Action | `button` (default · primary · accent · ghost · sm · block · busy · disabled), `icon-btn`, `link-btn` |
| Form | `field` (label + hint + error binding), `input`, `textarea`, `select`, `check`, `switch` |
| Content | `card`, product card, look card, brand card, `occasion` card |
| Meta | `badge` (fixture · preview · success · error), `fixtureBadge`, `chip`, `price`, `availability` |
| Shell | `site-header`, `nav`, `mobile-nav`, `site-footer`, `crumbs` |
| Overlay | `dialog`, `drawer`, `toast-region` |
| Feedback | `notice`, `banner`, `alert`, `disclaimer` |
| State | `emptyState`, `errorState`, `offlineState`, `unauthorizedState`, `unavailableState` |
| Loading | `skeleton` (text · title · media), `skeletonCard`, `skeletonGrid`, `btn__spinner` |
| Media | `gallery` with thumbs and captions |
| Dido | `didoFigure`, `didoAnimator`, `didoMessage`, `didoThinking`, `didoOption` |
| Layout | `ds-container`, `ds-section`, `ds-stack`, `ds-row`, `ds-grid`, `ds-rail` |

### Behaviour, not styling

Three components encode a rule rather than an appearance:

**A disabled control looks unavailable.** The storefront previously offered an ordinary
"Add to cart" that the server answered with 409.

**`aria-invalid` drives error styling**, so the visual state and the announced state cannot
diverge.

**`errorState` maps status to a sentence**, and shows the server's own message *below* it
rather than instead of it:

| Status | Copy |
|---|---|
| 0 | Cannot reach DEDUNET |
| 401 | Your session has ended |
| 403 | Not available on this account |
| 404 | Not found |
| 409 | Not available |
| 429 | Too many requests |
| 5xx | DEDUNET had a problem — this is our side, not yours |

§23 forbids a generic "Load failed" where context exists. The status **is** context.

---

## 5. Grid

```css
.ds-grid  { grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr)); }
.ds-rail  { grid-auto-flow: column;  /* swipes on phone, grid from 768px */ }
```

`min(260px, 100%)` is the load-bearing part. Without it a 260px floor overflows a 320px
phone.

---

## 6. Runtime

`ds.js` is a **classic script publishing one global**, not an ES module. Two reasons, and
both are constraints rather than preferences:

1. No build step — nginx serves the directory verbatim.
2. The jsdom harnesses that test the accepted storefront behaviour drive these functions
   directly, which module scope would break.

It is wrapped in an IIFE so it publishes **exactly** `window.DS`. Without that, every
helper is a global — and `app.js` declaring `const el = window.DS.el` collides with
`ds.js`'s `function el`, which is a `SyntaxError` that takes the whole page down.

That is not hypothetical. It shipped, every test passed, and the page was blank. See
`KNOWN_LIMITATIONS` §7.

**No markup sinks.** Every node is `document.createElement`, every string is `textContent`.
`svgEl` builds SVG through `createElementNS` from a fixed internal path table and never
accepts caller markup. The security scan now covers `app.js`, `ds.js`, `data.js`,
`media-url.js` and `admin.js`.
