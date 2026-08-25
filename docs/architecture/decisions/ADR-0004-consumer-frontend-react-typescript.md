# ADR-0004 — Consumer frontend: React + TypeScript on a build stage

| Field | Value |
|---|---|
| Status | **DECIDED** — authorized by the repository owner, 2026-08-25 |
| Date | 2026-08-25 |
| Owner | Principal architect (successor agent) |
| Supersedes | **`ADR-0003`** — classic scripts, no build step |
| Related | `ADR-0002` §2.0, `DEDUNET_DESIGN_SYSTEM.md`, `DEDUNET_CONSUMER_PLATFORM_UX.md` |
| Starting HEAD | `9b63791` |

## Context

Phase 2 delivered a consumer platform on classic scripts under `ADR-0003`. It passed 493
backend tests and failed human acceptance. The successor audit at `9b63791` reproduced the
failures in a real browser against the running staging container, whose assets were verified
byte-identical to HEAD.

### What was actually wrong

**Twenty-seven empty image wells.** Home, Discover, Looks, Look detail, Brands and Brand
detail render `.card__media` slots containing no `img` and no `svg`. Zero images on every
editorial route of a fashion platform.

**A stylesheet was dropped from the document and six routes lost their CSS.** `index.html`
stopped loading `styles.css`; `app.js` kept emitting its class names. Walking
`document.styleSheets` at runtime found **17 classes used with no rule in any loaded
stylesheet** — `two`, `form`, `btn--quiet`, `totals`, `tag`, `tag--ok`, `recommendation`,
`card__image`, `h6` and the entire `pdp__*` family. Account and Orders render unstyled form
controls. Product detail computes `.pdp__thumbs` to `display:block`, producing a 2,366px
thumbnail stack and a 4,766px page.

**None of that was detectable by any existing test**, and the suite was green throughout.

### Honesty about causation

**No defect above was caused by classic scripts.** A dropped `<link>`, unported components
and empty media slots would have happened identically in any framework. This ADR does not
pretend the architecture caused the Phase 2 failure — it did not.

### Why `ADR-0003` is nevertheless superseded

`ADR-0003`'s central technical premise is **wrong**:

> "There is no build stage and no place to add one without changing the container's security
> posture."

A multi-stage Dockerfile builds in one stage and copies static output into the nginx stage.
The runtime root filesystem stays read-only and is never written to after start. The
constraint is real about **runtime writes** and false about **build stages**, so the
migration question was closed on a basis that does not hold.

Two further pressures are real:

- Classic scripts share one top-level scope. That has already taken the entire page down
  once, when `ds.js` and `app.js` each declared `el` — a `SyntaxError` no jsdom test could
  see, because those harnesses `window.eval` each file into its own scope.
- The next milestone is a motion system, ten Dido states, filters that actually filter,
  Look assembly and saved state. Manual `#main` replacement is where that becomes
  expensive, and it is cheaper to migrate **before** that build than after it.

## Decision

**Build the consumer web application as a React + TypeScript single-page application,
compiled by Vite, served as static files by the same nginx image on a read-only root
filesystem.**

The runtime security posture is unchanged: static assets, no server-side rendering, no
runtime writes, no dependency tree evaluated in the customer's browser beyond the compiled
bundle.

### Non-negotiable conditions of this migration

1. **The browser E2E suite is written first.** Playwright encodes the accepted safety guards
   — preview-mode purchase refusal, session expiry, 401 stale-token clearing, commerce-mode
   disclosure, media resolution — as browser tests, and they must pass against the new
   application before cutover. jsdom is not sufficient and never was.
2. **A CSS contract test** fails the build when a class is emitted with no matching rule.
   The Phase 2 defect must be impossible to reship.
3. **No commerce guard, payment path, mode, schema or API contract changes.** This is a
   presentation-layer migration. `PUBLIC_COMMERCIAL_LAUNCH` stays **BLOCKED**.
4. **The classic app stays served until the replacement is green**, so there is a working
   baseline to diff against and a rollback that is one Compose change.
5. **Backend regression stays at 493 passed / 2 skipped** throughout.

## Consequences

**Accepted.**

- A build stage now exists. It must be secured, updated and audited, and it introduces a
  dependency tree that did not previously exist.
- The six jsdom harnesses that drive `apps/web/*.js` are invalidated at cutover and are
  replaced by Playwright equivalents. The eight `app.js` guard mutations must be re-pointed.
- Three human acceptances — local team, Android preview, iPhone mobile web — must be
  re-earned for the web surface. Two were already invalidated by Phase 2 and are recorded
  as `NOT TESTED` in `KNOWN_LIMITATIONS.md`, so this ADR adds one.
- `apps/admin` is **not** migrated. It is a separate surface with its own acceptance and no
  reported defect; migrating it here would widen the blast radius for no gain.

**Gained.**

- Type safety against the OpenAPI contract (31 paths, 30 schemas) rather than untyped
  `fetch`.
- Component composition and reactive state for the motion system, Dido states and filters.
- Module scope. The class of failure that blanked the page in Phase 2 becomes a compile
  error.
- Real browser coverage across Chromium, WebKit and Firefox, which is what the accepted
  behaviour should have been tested through from the start.

**Rejected alternatives.**

| Alternative | Rejected because |
|---|---|
| Repair in place, revisit later | Defensible — no defect was architecture-caused — but it builds the premium surfaces on manual DOM and then migrates them, doing the expensive work twice |
| Keep `ADR-0003` closed | Leaves a decision standing on a premise that is technically false |
| Next.js / SSR | Requires a Node runtime in production; the read-only static nginx image is a security property worth keeping, and nothing here needs SSR while the build is `noindex` |
| Migrate `apps/admin` too | Widens blast radius; no reported defect; separate acceptance |

## Revisit when

- SSR or SEO becomes a requirement, which cannot happen before public launch is unblocked.
- The bundle is measured as the bottleneck on a real device.
