# Known Limitations

Honest inventory of what this build does **not** do. Read before demonstrating it to anyone.

Status vocabulary: `VERIFIED` (executed and evidenced), `IMPLEMENTED_UNVERIFIED` (code exists,
not exercised), `BLOCKED`, `EXTERNALLY_PENDING`, `NOT_STARTED`.

> **Corrected 2026-08-24 at `41cee4c`.** This document had gone stale against five delivered
> workstreams and was recorded as **DISC-01** in
> `docs/system-of-record/SUCCESSOR_AGENT_TAKEOVER_REPORT.md` §11 — the highest-consequence
> documentation defect in the repository, because this is the file explicitly designated as
> the honesty inventory. It previously claimed *"No rate limiting"*, *"Backup and restore —
> NOT_STARTED"*, *"Staging / production deployment — NOT_STARTED"*, *"Nothing dispatches
> them … No message has ever been sent"*, *"PostgreSQL has not been exercised here"* and
> *"81 tests pass"*. Every one of those was false at the time it was read. The corrections
> are marked **[was: …]** so the drift is visible rather than quietly erased. Closes the
> documentation half of CONFLICT-009.

---

## 0. Saved persistence is real (2026-10-01)

Saving looks, products and brands is **implemented and attached to the account**, not to the
browser. Evidence: `evidence/phase-5/SAVED_PERSISTENCE_EVIDENCE.md`.

**The Saved page no longer says "Saving is not built yet", because it is.** Two stale
disclosures were removed with it: a disabled "Save" button on the product page beside
*"Saving is not built. There is nowhere to store it yet."*, and the look detail page's
equivalent. The production disclosure rule cuts both ways — an unbuilt feature must say so,
and a built one must stop saying so.

**A Look is now a real row**, so saves have something with identity to point at. It is still
**curated editorial content composed by a person** — not an outfit engine output, no
reasoning, no scoring, and **no total price or column for one**, because summing prototype
prices would invent a figure. The outfit engine, recommendation engine and Style DNA remain
**NOT STARTED**.

| Item | State |
|---|---|
| **Look copy is duplicated** | the consumer renders look prose from `content.ts` while the database is authoritative for identity. `test_look_slug_parity.py` asserts they agree; converging them is follow-up work |
| **Resume-after-login** | **NOT IMPLEMENTED.** A signed-out save sends the visitor to sign in with a return path; it does not replay the save afterwards |
| **Saved-state fetch is whole-set** | one request returns every saved slug. Far cheaper than a request per card; a customer with thousands of saves would want a windowed contract |
| **No reordering or collections** | a flat list per kind |
| **No admin view of saved items** | deliberate. Saved items are personal data and browsing them is not an operational need |

**Privacy.** Saved rows are deleted with the customer by **two** mechanisms, both needed:
`ondelete=CASCADE` for a hard delete, and an explicit deletion in `erase_customer`, which
pseudonymizes rather than deleting so the cascade would never fire. Saved events carry a slug
and **no customer identifier** — a popularity signal, not a behavioural profile.

**Rollback is not free.** The migration's `downgrade()` destroys customers' saved items. They
are real user data, not derivable from anything, and re-running `upgrade()` does not bring
them back.

**Registration stayed strict.** The browser suite originally registered a customer per test
and failed, because registration is limited to five per hour by design. The limiter was
**not** loosened; test accounts are created out of band with
`manage.py create-test-customer`, credentials from the environment and never defaulted.

---

## 0a. Multi-brand fashion network ACCEPTED (2026-09-30)

**`MULTI_BRAND_FASHION_NETWORK_ACCEPTED`** — human review on a physical iPhone in Safari
against deployed staging at `a1abed3`. Recorded in
`evidence/team-acceptance/MULTI_BRAND_NETWORK_ACCEPTANCE.md`.

The acceptance covers the **domain and its surfaces**. It accepts no commercial
relationship, because none exists, and it is not native iOS acceptance.

## 0b. Multi-brand fashion network implemented (2026-08-27)

Products now belong to **brands**. `Brand` is first-class with an explicit `ownership_type`
(`PLATFORM_CURATED` / `MERCHANT_OWNED` / `EXTERNAL_CURATED`), commerce routing is a separate
axis from ownership, and provenance is modelled rather than assumed. Evidence:
`evidence/phase-4/MULTI_BRAND_NETWORK_EVIDENCE.md`.

**What is real:** the domain, the migration, the brand APIs, the commerce-action contract,
external-URL safety, and the consumer surfaces wired to live data. The five accepted DEDUNET
prototypes belong to a `PLATFORM_CURATED` DEDUNET brand and are `NON_PURCHASABLE`, exactly as
before — verified by a before/after checksum over every variant SKU and price.

**What is NOT real, stated plainly because a marketplace is easy to overclaim:**

| Item | State |
|---|---|
| **A real external brand integration** | **DOES NOT EXIST.** `EXTERNAL` and `REFERRAL` are implemented and tested; **no data uses them**. Nothing here is a partnership, integration or agreement |
| **`HOSTED` checkout** | **DECLARABLE, NOT REACHABLE.** Refused by `commerce_action` until merchant commerce exists. An enum value is not a feature |
| **`MerchantOrganization`** | a stub tenant root. No billing, plans, entitlements, seats or portal — Phase 5 |
| **Brand sync** | **NOT BUILT.** `last_checked_at` / `last_synced_at` are modelled and never written. They are null, not stale |
| **Admin** | read-only inspection endpoint; the portal UI is **not** extended |
| Availability | a **confidence with a timestamp**, never a fact. There is no `IN_STOCK` |

**A partnership claim was found and removed.** The consumer bundle contained
`commerceRouteLabel("REFERRAL") -> "Available through a partner"` — a relationship that has
never existed, in a switch statement in the browser. Relationship wording now comes from the
server so there is one auditable vocabulary. `LEGAL_CLEARANCE_PENDING` is unchanged.

**Development fixtures cannot be published.** A database check constraint forbids it, and the
API hides fixtures entirely once public commerce is enabled. The sixth database product — the
backup-restore runbook's row — belongs to an unmistakable fixture brand rather than to an
invented company.

**Migration rollback is not free.** `downgrade()` drops `products.brand_id`, destroying the
product-to-brand association. Products, variants and prices survive; the association is
reconstructible only while it remains derivable from `external_product_id`.

---

## 0a. Consumer foundation accepted, then LOCKED at the staging cutover

**`ENTERPRISE_CONSUMER_FOUNDATION = LOCKED`** as of 2026-08-27.

Two human reviews, both on a physical iPhone in Safari, and they are different events:

| Date | Target | Result |
|---|---|---|
| 2026-08-26 | the additive **candidate** on 13081 | `ACCEPTED WITH FOLLOW-UP ITEMS` — `evidence/team-acceptance/ENTERPRISE_CONSUMER_FOUNDATION_ACCEPTANCE.md` |
| 2026-08-27 | **normal staging** on 13080, at `be1d1e2` | `PHYSICAL_IPHONE_STAGING_SMOKE_PASSED` · `STAGING_CUTOVER_ACCEPTED` — `evidence/team-acceptance/STAGING_CUTOVER_IPHONE_ACCEPTANCE.md` |

The second was required because the F-2 repair changed the application, so the deployed
bundle is deliberately no longer byte-identical to the accepted candidate.

**A web application in Safari on an iPhone is not native iOS.** `NATIVE_IOS` remains **NOT
BUILT, NOT TESTED** — a separate state, never implied by either record.

**Read the scope, not the headline.** The acceptance covers rendering on the device,
routing, Home, the Dido **shell**, the Looks and Brands and Saved **foundations**, Shop,
Account, mobile navigation, responsive presentation and preview safety.

It does **not** cover, and must never be promoted into: Dido AI intelligence, Style DNA, the
recommendation engine, the outfit engine, **Saved persistence**, real multi-brand
integrations, merchant SaaS, public commerce, or native iOS. This is **not**
production-platform acceptance. `PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**.

### Conditions attached to the acceptance

| Item | State |
|---|---|
| **Saved persistence** | **Must be implemented before production exposure.** No store, no endpoint, no model exists |
| **A Look as a real outfit object** | reasoning, pricing and modification actions — future phase |
| **Multi-brand domain** | not implemented; the second brand entry is still a labelled demonstration |
| **Dido intelligence** | not built |
| **About / Privacy / Terms** | **no routes exist.** Named as footer essentials at acceptance and deliberately NOT linked, because linking a customer to a 404 to look complete is the failure this programme keeps closing. Required for public launch |
| Mobile footer | **closed in this cycle** — compact below 900px, expanded on desktop |

### Two standing rules were added

`docs/architecture/PRODUCTION_DISCLOSURE_RULE.md` — the prototype's truthfulness about
unbuilt capability is to be **preserved during development**, and before production V1 every
surface carrying implementation language must either become genuinely functional or be
removed from the journey. Deleting the disclosure and leaving the dead surface is faking
completion and is forbidden. It is enforced as a mechanical release gate, not a style guide.

`docs/architecture/MEDIA_DELIVERY_SEPARATION.md` — one Home load costs 22 requests to the
API origin, 20 of them static media, against a 300-per-minute-per-IP limiter that covers
them. **The limiter was not changed and must not be raised to hide this.** Static media
delivery is to be separated from business-API abuse protection as a future platform action.

### Cutover

**Executed and ACCEPTED 2026-08-27.** Staging serves the enterprise consumer client
(`apps/consumer`) on 13080 over a same-origin `/api` proxy, and the human iPhone smoke on
that deployment has passed. The candidate remains on 13081 as the acceptance
reference during the soak. `apps/web`, its harnesses and its guard mutations all remain in
the tree and keep passing — the rollback path was rebuilt from committed source and proven
to serve, not merely assumed. Record:
`evidence/staging-cutover/STAGING_CUTOVER_EXECUTION.md`.

**The physical-iPhone smoke on the normal staging URL PASSED** on 2026-08-27 at `be1d1e2`,
after the repairs below: Home, Dido, Shop, the Source Tee at €72.00 and NOT AVAILABLE TO
BUY, Account, mobile navigation and preview safety.

**Two defects were found after the cutover and are now REPAIRED.** The cutover was first
reported as ready for the human smoke while both were open; the owner rejected that, and the
repair is recorded in `evidence/staging-cutover/STAGING_CUTOVER_EXECUTION.md` §11.

**F-1, security headers.** `X-Frame-Options`, `X-Content-Type-Options`, `X-Robots-Tag` and
`Referrer-Policy` were absent on **every HTML document**, because nginx does not inherit
`add_header` into a location that declares its own and both `location = /index.html` and
`location /assets/` set `Cache-Control`. The classic client served three of them, so it was
a regression at this URL. **Fixed** with a single included contract file, verified on real
HTTP responses, and guarded by `test_consumer_security_headers.py` — which was itself
verified to fail when the defect is reintroduced. `/api/` is a named exemption: the API sets
its own stricter `no-referrer`, and including the document contract there downgraded it.

**F-2, product price.** The product page rendered **"Not priced"** for every product. The
client read a product-level `price_display` the catalogue endpoint never sends, on the
strength of a comment asserting the catalogue had no prices; the authoritative price is on
each **variant** (`7200` minor units for the Source Tee). **Fixed** by deriving the product
price from variants through `src/lib/money.ts` — exact price when variants agree, `From
<lowest>` when they differ, unpriced only when none is priced. The Source Tee now reads
**€72.00**. Nothing about purchasability changed: the CTA is still disabled and reads NOT
AVAILABLE TO BUY, and the server still refuses a cart add with 409. A price is a statement
about cost, not an offer.

---

## 0. The consumer web client was replaced (2026-08-25)

`ADR-0004` supersedes `ADR-0003`. The consumer web application is now React + TypeScript
built by Vite (`apps/consumer`), replacing the classic-script client in `apps/web`.

**Why**, stated plainly: the Phase 2 client failed human acceptance, and the successor audit
reproduced two defects in a real browser at `9b63791`.

| Defect | Evidence |
|---|---|
| 27 empty image wells across Home, Discover, Looks, Look detail, Brands and Brand detail | Zero `img` and zero `svg` inside every `.card__media` on those routes |
| 17 class names rendered with no rule in any attached stylesheet | `index.html` stopped loading `styles.css`; `app.js` kept emitting its class names |

The second is why Account rendered raw form controls with labels running into fields, and
why the product page computed `.pdp__thumbs` to `display:block` and stood **4,766px** tall.
**493 backend tests passed throughout.** No test looked at the relationship between what the
document emits and what the stylesheets define, and none looked inside an image well.

**Neither defect was caused by classic scripts.** A dropped stylesheet link and unported
components would have happened in any framework. `ADR-0003` was superseded because its
central premise — that no build stage could be added without changing the container's
security posture — is **wrong**: a multi-stage Dockerfile builds in a discarded stage and
the runtime root filesystem stays read-only. The migration was authorized on that basis, not
on the defects.

### What this invalidates

| Item | State |
|---|---|
| Six jsdom harnesses driving `apps/web/*.js` | Still passing, still pointed at the **classic** client, which is still served. They do not cover `apps/consumer` |
| 8 guard mutations over `apps/web/app.js` | Unchanged and still valid **for the classic client** |
| Local team acceptance · Android preview · iPhone mobile web | Already `NOT TESTED` against the web surface since Phase 2. This does not change that; it adds a third client that has never been on a device |
| `apps/admin` | **Not migrated.** Separate surface, own acceptance, no reported defect |

### What replaced the missing coverage

A Playwright suite (`apps/consumer/e2e`) that drives the built application in a real browser
across Chromium, WebKit, Firefox and an iPhone viewport. It encodes the accepted commerce
guarantees at the browser level — preview-mode purchase refusal, the refusal reason reaching
the disabled control, mode disclosure, 401 stale-token clearing, signed-out orders redirect,
and a sweep asserting no surface offers a purchase this deployment would refuse.

It also carries a **CSS contract test**: it walks the DOM and every attached stylesheet and
fails when a class is emitted with no rule behind it. The Phase 2 defect cannot recur
silently. It caught a real one during the migration — react-router's `NavLink` appends its
own `active` class, which this design system never defines.

**The suite was run against the classic client first**, to record a baseline and prove the
accepted guards were captured rather than asserted: **16 failed, 110 passed**, and the
failures were precisely the defects above.

### Not fixed, and deliberately

**The brand display typeface does not render.** `fonts.json` names Bodoni Moda (display) and
Manrope (body), both Google Fonts. No font file ships in the brand package and no webfont is
linked, so both resolve to their declared fallbacks — Didot/Georgia and Arial/Helvetica.
Adding a Google Fonts link would put an external network dependency and a CSP widening into
a preview build that is served over a LAN, which is the topology the iPhone acceptance uses.
**The typography renders in fallback faces and the brand face has never been seen.** This is
a deferred decision, not an oversight.

---

## 1. This is not a real business

DEDUNET is a brand identity under development. **[was: "MERET is invented"]** — the brand was
migrated under CONFLICT-008 and MERET no longer appears on any customer-facing surface. What
has not changed is the substance: no company, factory, supplier, product, certification or
customer exists. No physical inspection, laboratory test, customer interview, legal, tax or
customs conclusion, registration, contract, payment activation, carrier result or app-store
submission has occurred, and no evidence of any of those exists in this repository.

Brand legal status is **`LEGAL_CLEARANCE_PENDING`**. Side A discloses a `DeDeNet` naming
conflict as a high preliminary risk. Nothing in this repository resolves it.

Material, origin and care fields in the seed data are **illustrative placeholders**.
`country_of_origin` is deliberately the invalid code `XX` so it cannot be mistaken for a
substantiated claim, and `origin_claim_status` is `UNVERIFIED`.

## 2. Governance gate is bypassed, not passed

`docs/system-of-record/GATE_REGISTER.md` records **G0 = NO_GO**, failing on three human-only
criteria: founder/IP baseline, named accountable humans, and spending authority. The
repository owner authorized proceeding anyway; that override is recorded in
`docs/architecture/decisions/ADR-0001-scope-contradiction-and-baseline.md`.

Building over a failed gate changed what was built. It did not make the gate pass.

Four risk owners are now **named** in `RISK_OWNER_REGISTER.md` v2.0, but **not one has
personally accepted their assignment** — all four remain `PENDING`. GOV-1 and GOV-3 must both
close before any residual risk can be formally accepted.

## 3. Open launch blockers

| ID | Risk | State |
|---|---|---|
| SB-RISK-003 | Stored XSS in the browser clients | **CLOSED** — all markup sinks removed; guarded by `test_frontend_security.py`, proven load-bearing by injection |
| SB-RISK-005 | Non-transactional inventory | **CLOSED for the commerce domain** — atomic reservation plus a `reserved <= on_hand` constraint, proven by a 20-thread race. The **legacy** JSON-fixture catalog path remains non-transactional |
| SB-RISK-011 | Secrets shipped in the pack | **PARTIALLY CLOSED** — `.env` is git-ignored and verified absent from history; the file still exists on disk in the source pack |
| — | **Local staging credentials were exposed in prior acceptance logs and chat.** Rotate before exposing the environment beyond this machine | **OPEN** |

**[was: "None of these has a named human risk owner"]** — owners are now named; see §2 for
what that does and does not mean.

## 4. Not built

| Area | State | Note |
|---|---|---|
| iOS native application | **`NOT TESTED` / BLOCKED** | No iOS binary has ever been built. Apple Developer membership is deferred — there is no budget for paid membership — so there is no signing config, no store metadata and no device test. **Do not infer iOS status from the Android result** |
| Android native application | **`NATIVE_ANDROID_PREVIEW_ACCEPTANCE_PASSED`** | **[was: no native binary exists]** A preview APK was built through EAS and exercised on an emulator (Pixel 9, Android 16, API 36), including two post-acceptance corrections verified on build `f7c7352b-…`. **Physical Android hardware is `NOT TESTED`** and nothing is published to any store |
| CI pipeline | **NOT EXECUTED** | A workflow file exists. No runner is available and **there is no Git remote to push to**, so it has never run. A green pipeline is not evidenced and must not be claimed |
| Git remote | **NOT_STARTED** | Zero remotes configured. Every verified result in this programme exists on one machine, inside one working copy. This is a single point of failure for all delivered work (L8, CONFLICT-010) |
| Infrastructure as code | **NOT_STARTED** | No Terraform, Kubernetes or Helm. Docker Compose covers local only |
| Hosted staging / production | **NOT_STARTED** | **[was: "Staging / production deployment — NOT_STARTED"]** Partially superseded: a **local** standalone staging stack exists and is verified (Workstream E). No *hosted* environment has been provisioned, and there is no TLS, DNS or public networking |
| Distributed tracing | **PARTIAL** | Correlation IDs propagate and are logged; no OpenTelemetry exporter or trace backend |
| Metrics, dashboards, alerting | **NOT_STARTED** | Structured logs and health/readiness probes only |
| Backup and restore | **`LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED`** | **[was: NOT_STARTED]** Superseded by Workstream D: `pg_dump` custom-format, SHA-256 verified, restored into an isolated database. **Not** production DR — not scheduled, not offsite, not encrypted at rest, no geographic redundancy. **RPO is "time since someone last ran one by hand."** RTO evidence is a 2.02 s rehearsal on a 51 KB dump and is not a production RTO |
| Performance and load testing | **NOT_STARTED** | No baseline exists. Response times observed locally are not a performance result |
| Accessibility audit | **PARTIAL** | Semantic markup, labels, skip link, visible focus and keyboard-operable controls are implemented; no automated axe run or screen-reader test |
| Visual regression testing | **NOT_STARTED** | |
| Content management | **NOT_STARTED** | No CMS or editable content pages |
| Marketing integrations | **NOT_STARTED** | |
| Customer support workflow | **NOT_STARTED** | No ticketing or support case model |
| Reviews / Wishlist | **NOT_STARTED** | |
| Semantic / AI search | **NOT_STARTED** | Search is a SQL `ILIKE` match, not semantic |
| Visual regression testing | **NOT_STARTED** | Phase 2 used route-level DOM assertions and measured layout instead. §31 permits an alternative; brittle screenshot testing was deliberately not adopted |
| Automated accessibility audit | **NOT_RUN** | Structural accessibility is implemented and asserted (landmarks, heading order, focus, targets, labels, live region, reduced motion) and contrast was measured. No axe run and no screen-reader pass — **audited accessibility is not claimed** |
| Multi-currency | **NOT_STARTED** | Only EUR has a reviewed minor-unit exponent; any other currency raises rather than defaulting |
| Address validation, multiple shipping options | **NOT_STARTED** | Flat-rate shipping with one free threshold |
| Email / SMS / push **delivery** | **`EXTERNAL_SMTP_DELIVERY_PENDING`** | **[was: "Nothing dispatches them. No message has ever been sent"]** Superseded by Workstream B: a separate `notification-worker` container drains the outbox with claim leases and fencing. The **channel is `console`** — no external SMTP is configured, so no message has left this machine |
| Audit log read API | **NOT_STARTED** | Audit rows are written; the portal cannot list them and says so rather than showing an empty table |

### 4.1 Not built — the fashion-intelligence platform

Recorded here because `ADR-0002` (**approved as revised**) describes it. **Phase 2 built
the consumer platform's front end. None of the engines behind it exist.**

> **What Phase 2 did build**, so the two are not confused: a token-driven design system on
> the delivered Side A brand tokens, ~35 components, thirteen routes, desktop and mobile
> navigation, Discover / Looks / Brands / Saved / My Style / For Brands, and the Dido
> experience **shell**. See `docs/architecture/DEDUNET_CONSUMER_PLATFORM_UX.md`.
>
> Every surface that needs an engine it does not have says so on screen and is covered by a
> test that it says so. `SavedService` reports *unavailable* rather than writing to
> `localStorage` to look functional; "Looks selected for you" states that personalised
> selection is not built rather than labelling fixture looks as a personal selection; and
> Dido answers that it cannot style yet rather than scripting a recommendation.

| Area | State |
|---|---|
| Style profile / Style DNA / size profile | **NOT_STARTED** |
| Occasion model, styling session, conversational memory | **NOT_STARTED** |
| `Look` / `LookItem` / outfit engine | **NOT_STARTED** |
| Weighted recommendation engine with versioned scoring | **NOT_STARTED** |
| Fashion knowledge base and claim classes | **NOT_STARTED** |
| `Brand` as a first-class entity | **NOT_STARTED** — `Product` belongs to a catalogue, not a seller |
| Merchant organizations, multi-tenancy, entitlements, SaaS billing | **NOT_STARTED** — **no table carries an owning organization** |
| Typed commerce routes (hosted / external / referral / non-purchasable) | **NOT_STARTED** |
| LLM integration of any kind | **NOT_STARTED** — no provider selected, none funded |

## 5. Deliberate design limits

**Commerce modes.** `BRAND_PREVIEW_MODE` (nothing purchasable) and `COMMERCE_TEST_MODE`
(synthetic stock, sandbox payments, orders marked as tests) are selectable.
**`PUBLIC_COMMERCE_MODE` is refused by configuration** — setting it raises rather than
enabling public commerce. Reaching it requires a code change *and* the activation gate.

In `PUBLIC_COMMERCE_MODE` the API still starts and `/ready` still returns **200** while every
commerce request returns **500** (L10). The security property is intact and fail-closed, but
readiness lying is a hardening item before public launch.

**Payments are sandbox-only.** `SandboxGateway` implements the full `PaymentGateway` contract
including declines, provider errors and idempotent replay. Setting `PAYMENT_PROVIDER` to
anything else raises rather than falling back, so a misconfigured deployment cannot silently
process live money through a mock.

**Shipping is a mock carrier.** Tracking numbers are generated locally. No carrier API is
integrated and no label has been produced.

**The AI stylist is deterministic and rule-based.** `app/ai_stylist.py` is 68 lines that score
the legacy fixture catalogue on colour, category, tag overlap and stock. It is not a language
model, invents no product, price or stock, and the store stays fully usable when it fails.
Treat its output as a ranked suggestion, not advice. It is **not** a foundation for the
styling platform in §4.1 — it is a contract demonstration, and its own docstring says so.

**PostgreSQL 16 is what every Compose stack runs.** **[was: "SQLite is the default database …
PostgreSQL has not been exercised here"]** Superseded by Workstream A. SQLite is still the
default when `DATABASE_URL` is unset — a bare local run and the fast unit-test path both use
it — so "the default" and "the runtime" are different things here and the distinction matters
when reading a test result. `conftest.py` refuses to run the suite against a PostgreSQL URL
without the explicit `COMMERCE_TEST_DATABASE_URL` opt-in, so an exported `DATABASE_URL` cannot
point the suite — including its `drop_all` — at a real database.

**Session tokens are HMAC-signed, not encrypted.** They are integrity-protected only. There is
no revocation list, so a stolen token is valid until it expires.

**Rate limiting exists and is process-local.** **[was: "No rate limiting"]** Superseded by
Workstream C: a stdlib token bucket with endpoint-specific policies, verified live
(10 × 401 → 4 × 429, with `/ready` exempt). The limit is **per process**, so N workers means
N × the effective limit:
**`MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING`** (L7). Local
staging runs exactly one API process, which is the configuration that was verified.

**Notifications are at-least-once.** Lease fencing protects database state; it cannot un-send
a message a provider has already accepted.

**`orders.status` has no database `CHECK` constraint** (L5). Validity is application-enforced
through an enum at six call sites, and no endpoint accepts a status for writing. The gap
matters only for direct SQL. Defence-in-depth debt; blocks public launch, not team acceptance.

## 6. Environment divergence

The runtime here is **Python 3.14.4**, while the Dockerfile and CI matrix target **3.12**. The
suite passes on 3.14; 3.12 has not been exercised in this environment.

The application does **not** auto-load `.env`. Configuration must be supplied as real
environment variables, which is why `CORS_ORIGINS` must be set explicitly.

## 7. Test coverage honesty

**415 tests pass and 2 are skipped** on the SQLite path, executed at `41cee4c` on 2026-08-24.
**[was: "81 tests pass"]** The two skips are PostgreSQL-only guarantees (`FOR UPDATE SKIP
LOCKED`). The PostgreSQL suite result is **carried forward on prior evidence** and was not
re-executed for this correction.

**[was: "They do not cover: the browser clients (no JS test runner; only static source
guards)"]** — no longer true. The browser clients are now rendered in jsdom and asserted on
the resulting DOM: mode disclosure, media gallery, media resolution, admin API configuration,
admin test-order labelling, session expiry, and purchase refusal. Mobile has 14 Jest suites
and its own mutation harness.

What the suite still does **not** cover: infrastructure, performance, accessibility
automation, any real external provider, cross-tenant isolation (there are no tenants), and
any LLM behaviour (there is no LLM).

**77 guard mutations** are registered in `scripts/validation/mutation_guard_check.py` — the
ids run to M79 because M56 and M57 were never used, so the highest id is not the count. Each
removes one safety guard and requires its guarding test to fail. A guard whose removal nobody
notices is not a guard.

**Phase 2 invalidated the web half of the mobile acceptances.** The Android emulator and
physical-iPhone acceptances passed against the pre-Phase-2 storefront. Phase 2 replaced
every consumer surface on the web, so those results describe a build that no longer exists
there and **both are `NOT TESTED` against the current web client**. The native Android
binary is unaffected — no mobile file was changed — but its web-parity claims are not.
Re-running them is outstanding.

**One frontend defect is worth remembering rather than only fixing.** `ds.js` and `app.js`
each declared a top-level `el`, which in classic scripts is a `SyntaxError` that stops the
whole page. Every jsdom test passed and the page was blank: those harnesses `window.eval`
each file into its own scope, and a browser sharing one top-level scope does not. It was
found by opening the page. A jsdom suite verifies what a function renders, not that the
page loads — see `evidence/phase-2/PHASE_2_CONSUMER_PLATFORM_EVIDENCE.md` §7.

**Automated green is not human acceptance.** Local team acceptance and Android native
preview acceptance were performed by a human and are recorded in `evidence/team-acceptance/`.

**iPhone mobile-web acceptance is `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED`** — 25 gates on a
physical iPhone in Safari, against local staging over the LAN, in `BRAND_PREVIEW_MODE`,
recorded at `evidence/team-acceptance/IPHONE_MOBILE_WEB_ACCEPTANCE.md` (CONFLICT-011 closed).
Two non-blocking UX defects were found and have since been corrected. **The corrected screens
have not been re-checked on the device that reported them** — automated tests are not that
check.

**iOS native is `NOT TESTED`** — never built. No signing, no TestFlight, no App Store, Apple
Developer Program `DEFERRED — FUNDING`. Do not infer it from the Android result, and do not
infer it from the iPhone *mobile-web* result either: Safari is not the native application.

**CI had been green over 546 of 703 tests.** The jsdom browser-client harnesses self-skip when
Node is absent, the backend job installed Python only, and **pytest exits 0 when every selected
test is skipped** — so 157 tests skipped, the run passed, and the mutation harness read the
exit code alone and reported nine perfectly good guards as `SURVIVED`. Among the tests not
running were the preview purchase refusal and stale-session clearing on 401, two behaviours
this programme treats as accepted. Fixed on `26c3120`: Node and jsdom are installed, a step
fails if those harnesses skip, and the harness has a third `INCONCLUSIVE` verdict that fails
the run instead of being folded into either column.

**No single CI job runs the whole suite, and the green badge does not say otherwise.** On run
#7 the three `backend` legs run 701 of 703 — skipping the two row-locking tests that need real
PostgreSQL — and the `postgres` job runs 548, skipping the 155 jsdom harnesses because it has
no Node. The two sets are complementary and their union is the full 703, so every test executes
somewhere in the run, but **no individual job is evidence for the whole suite**. Deliberate:
putting Node on the `postgres` job would buy a fourth run of tests with no database in them.
Cite CI by run id and by job, never by badge.

**The matrix runs twice per push.** `on: [push, pull_request]` triggers two complete runs of
the same commit when a PR is open — for `26c3120`, runs #6 and #7, six backend legs, and the
77-mutation harness executed six times. Costs ~12 minutes of duplicated mutation execution per
push and buys nothing. Tracked as `R-018`; recorded rather than fixed so that the run which
proved the CI fix is the configuration that ships.

**A green build says nothing about what the device is served.** On 2026-10-07 a physical iPhone
acceptance failed on a stale disclosure, with the code, the database, the API and CI all
correct: port 13080 was reaching `dedunet-consumer-candidate` — a six-week-old cutover
rehearsal container, tagged with a commit the publication history rewrite had already removed —
instead of the staging web container, which had served no request at all since it started.
A host restart had crossed the Docker port map. Nothing in this repository caused it and no
check here would have caught it, because every signal the repository produces describes the
code rather than the deployment. Before a device acceptance, compare the `ETag` from the
acceptance URL against the serving container's own, and query containers by IP rather than by
`localhost` — `localhost` resolved to `::1` and reached a different relay than the LAN address
the phone uses. Tracked as `R-019`;
`evidence/phase-5/SAVED_ACCEPTANCE_DEPLOYMENT_INCIDENT.md`.

**The Saved acceptance passed on the retest, and the stale-deployment finding stands.** The
physical iPhone Safari acceptance passed on 2026-10-07 against the repaired deployment, all
eleven gates including persistence across a Safari restart — `SAVED_PERSISTENCE_ACCEPTED`,
`evidence/team-acceptance/SAVED_PERSISTENCE_IPHONE_ACCEPTANCE.md`. The failed first attempt is
kept in that record rather than tidied away, because an acceptance log showing only the
successful attempt would imply the deployment had always been correct. The stale candidate
**container** has been removed and its **images** kept as rollback material, exactly one
container now publishes 13080, and a probe through the LAN URL reaches it. What is *not* fixed
is the class of failure: **no automated check asserts deployment provenance**, so
`docs/operations/DEPLOYMENT_PROVENANCE_GATE.md` is a procedure a person has to actually run.
`R-019` stays open on that automation.

**Style DNA stores what a customer said and nothing else.** Every row carries
`source = USER_EXPLICIT`, pinned by a database CHECK on all six preference tables, so an
inferred preference cannot be written by a code path that forgot the distinction — it would
take a migration somebody reviews. Saved items are **not** an input: a save is an act of
interest rather than a statement of preference, and people save things to decide against
them. Inference needs its own source, confidence, explanation, correction path, consent and
decay, and none of those exists, so nothing infers. The page says so where a customer will
read it, because every other platform does infer.

**Nothing uses the Style DNA profile yet.** Dido does not read it, the catalogue does not
filter or rank on it, and no recommendation engine exists. Dido's capability copy says
"Stored, not yet applied" rather than "Not built", which was the previous wording and became
false the moment a customer could record a preference — and rather than "applied", which is
not true either. Stored and applied are different states.

**Sizes are never converted, between systems or between brands.** `EU 50 = UK 40 = M` is
approximately true across brands and exactly true within none. A customer who knows two
systems states both, and both are kept as stated.

**A style preference is not a product claim.** "I prefer cotton" is a fact about the
customer and authorizes nothing about any garment: composition stays "stated, not verified"
until supplier documents and testing say otherwise.

**The deployment provenance gate caught a stale deployment on its first real use.** The
staging web build failed on three TypeScript errors, `docker compose build` reported success
through a pipe that swallowed the exit code, `up -d` recreated from the six-week-old image,
and the deployed artifact contained no Style DNA. Healthy containers, a correct API and
green CI all agreed nothing was wrong. Only the artifact-identity checks disagreed. If a
build command's output is piped, its exit code must still be checked.

**Style DNA is accepted and locked, and nothing uses it.** The physical iPhone Safari
acceptance passed on 2026-10-08, all thirteen gates — `STYLE_DNA_ACCEPTED`,
`evidence/team-acceptance/STYLE_DNA_IPHONE_ACCEPTANCE.md`. The two gates that carry the
meaning are that **disabling personalisation preserved every value** and that **a saved item
survived Style DNA deletion**: a control that quietly deleted while claiming to disable, or a
delete that took the Saved list with it, would both look correct until a customer noticed
something gone. What is accepted is a record of what a customer said. Dido reads none of it,
the catalogue does not rank on it, and no recommendation exists.

**The provenance gate caught a second stale deployment, and `R-019` is still open.** On its
first real use the gate found that the staging artifact had no Style DNA in it: the consumer
build had failed on three TypeScript errors, `docker compose build` reported success through
a pipe that swallowed the exit code, and `up -d` recreated from a six-week-old image. Healthy
containers, a correct API and green CI all agreed nothing was wrong. Twice now the only thing
that disagreed was an artifact-identity check. **The gate passing by hand is not the same as
being automated**, so `R-019` stays open — and a build command's exit code must be checked
even when its output is piped.

**Safari on an iPhone is not native iOS, and an emulated viewport is not even Safari.** The
Style DNA acceptance was performed in mobile Safari; the automated "Mobile Safari" Playwright
project is a desktop browser emulating a viewport and is weaker evidence again. Neither is
native-iOS acceptance. iOS native has still never been built.

**Dido understands a styling brief. It does not pick the clothes.** Phase 7 built a
conversational intake: it reads free text, applies accepted Style DNA when personalisation is
on, detects contradictions and produces a structured Styling Brief. There is no
recommendation ranking, no product scoring, no outfit generation and no fashion RAG — none
has a schema, an endpoint, a stub or a flag, and every API response carries a `capabilities`
block saying so rather than leaving the boundary to UI copy one refactor from disappearing.

**The interpreter proposes and never decides.** Everything a language model returns is a
candidate, validated against the taxonomy and re-parsed for money before it can enter a
brief. A model that returns an unknown occasion or a float budget changes nothing. The
deterministic interpreter is the fallback *and* what CI runs, so no test in the phase needs an
API key — a phase whose tests require paid credentials is a phase whose tests nobody runs.

**Two home-page overclaims were removed, and the second was the larger one.** The Dido
animation ran through `searching`, `assembling` and `presenting`, none of which exists; an
animation of a catalogue search is a stronger claim than any sentence, because nobody reads a
caption as carefully as they watch a thing move. While verifying that fix, the hero two
sections above was found still saying Dido *"builds complete looks"*. Fixing the smaller
overclaim and walking past the larger one would have been worse than leaving both.

**The old Dido disclosure had to be removed, which is the awkward half of the disclosure
rule.** *"This is the conversation, not the intelligence"* was true and became false; leaving
it would understate the platform exactly as the rule forbids overstating it. What replaced it
states the boundary that still holds — understanding is not recommending — before the
conversation and again at completion, which is the moment a customer expects an outfit.

**A disabled input loses focus, and that was a real accessibility defect.** The Dido textarea
was disabled while a message was in flight, so anyone typing and pressing Enter was thrown out
of the box on every message — worse for keyboard and screen-reader users than anyone else. It
is `readOnly` with `aria-busy` now. Found by a browser test, not by review.
