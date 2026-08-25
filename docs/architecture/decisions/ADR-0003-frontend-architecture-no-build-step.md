# ADR-0003 — Frontend architecture: classic scripts, no build step

| Field | Value |
|---|---|
| Status | **DECIDED** — implemented in Phase 2 |
| Date | 2026-08-25 |
| Owner | Technical lead (successor agent) |
| Supersedes | none |
| Related | `ADR-0002` §2.0, `DEDUNET_DESIGN_SYSTEM.md`, `DEDUNET_CONSUMER_PLATFORM_UX.md` |

## Context

Phase 2 turns a 1,021-line single-file storefront into a platform: a design system, a
component library, a service layer and thirteen routes. That is the size at which most
teams reach for a framework and a bundler.

Three constraints already exist in this repository and none of them is negotiable.

**nginx serves `apps/web` verbatim, from a read-only root filesystem.** The Dockerfile
copies the directory and bakes the API base in at build time precisely because nothing may
write into the served directory after start. There is no build stage and no place to add
one without changing the container's security posture.

**Five passing jsdom test suites drive the storefront's functions directly.** They are what
the accepted purchase-refusal, session-expiry, mode-disclosure, gallery and media-resolution
behaviour is tested through. They work by `window.eval`-ing each script and calling
`window.viewProduct(…)`. ES module scope would break every one of them.

**Three human acceptances are passed states** — local team, Android native preview, iPhone
mobile web. A framework migration would invalidate all three and they would have to be
re-earned before Phase 2 could close.

## Decision

**Keep classic scripts and hand-authored CSS. Add structure through file separation and a
token-driven design system, not through a framework.**

```
tokens.generated.css   GENERATED brand tokens
design-system.css      semantic layer + reset + layout primitives
components.css         component library
shell.css              navigation, page layouts, Dido
media-url.js           asset resolution           (existing)
ds.js                  element factory, components, Dido    -> window.DS
data.js                service interfaces, fixtures         -> window.DedunetData
app.js                 router and views
```

`index.html`'s script order **is** the module graph. There is no bundler to derive one, so
the list is explicit and the test harnesses mirror it.

### Each new file publishes exactly one global

`ds.js` and `data.js` are IIFEs exposing only `window.DS` and `window.DedunetData`.

This is not stylistic. Classic scripts share one top-level scope, so without the wrapper
every helper becomes a global — and `app.js` declaring `const el = window.DS.el` collides
with `ds.js`'s `function el`. Two top-level declarations of one identifier is a
`SyntaxError` that stops the whole page.

**It shipped exactly that way and every test passed**, because `window.eval` gives each
file its own scope in jsdom and a browser loading real `<script>` tags does not. It was
found by opening the page. A test now asserts the wrapping.

## Consequences

**Accepted.**

- No JSX, no reactive state, no component lifecycle. Views re-render by replacing
  `#main`'s children, which is adequate at this size and measurable if it stops being.
- More manual DOM code than a framework needs. The `el()` factory keeps it terse, and it
  is the same factory that guarantees no markup sink.
- Many small HTTP requests instead of one bundle. Acceptable over LAN and localhost, which
  is every supported topology today; if hosted deployment lands, HTTP/2 or a concatenation
  step at image build addresses it without changing source.
- Load order matters and is unenforced by tooling. Mitigated by the explicit list in
  `index.html`, the mirrored list in four harnesses, and the one-namespace-per-file test.

**Gained.**

- Zero build tooling to secure, update or audit; no dependency tree in the customer's
  browser at all.
- The read-only container is unchanged.
- All five jsdom suites keep working, so **the accepted behaviour stayed tested through the
  refactor** rather than being re-established afterwards.
- Loads on a phone with no framework runtime, which is the device the acceptance ran on.

**Rejected alternatives.**

| Alternative | Rejected because |
|---|---|
| React + Vite | Requires a build stage, breaks the read-only image, invalidates five test suites and three passed acceptances, and adds a runtime to a page whose heaviest feature is an SVG |
| ES modules, no bundler | Breaks every jsdom harness, and native module loading over many small files is slower than classic scripts here |
| Web Components | Adds a shadow-DOM boundary the jsdom harnesses would have to pierce, for encapsulation that one namespace per file already provides |
| Keep everything in `app.js` | ~4,000 lines in one file; the split is the point |

## Revisit when

Any one of these makes this decision worth reopening:

- A build stage is introduced for another reason (asset hashing, i18n extraction).
- Views need shared reactive state that manual re-render cannot serve.
- The frontend is measured as the bottleneck on a real device.

Until then, the constraints above still hold and the architecture follows from them.
