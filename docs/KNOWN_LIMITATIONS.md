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
| Multi-currency | **NOT_STARTED** | Only EUR has a reviewed minor-unit exponent; any other currency raises rather than defaulting |
| Address validation, multiple shipping options | **NOT_STARTED** | Flat-rate shipping with one free threshold |
| Email / SMS / push **delivery** | **`EXTERNAL_SMTP_DELIVERY_PENDING`** | **[was: "Nothing dispatches them. No message has ever been sent"]** Superseded by Workstream B: a separate `notification-worker` container drains the outbox with claim leases and fencing. The **channel is `console`** — no external SMTP is configured, so no message has left this machine |
| Audit log read API | **NOT_STARTED** | Audit rows are written; the portal cannot list them and says so rather than showing an empty table |

### 4.1 Not built — the fashion-intelligence platform

Recorded here because `ADR-0002` proposes it and none of it exists.

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

**Automated green is not human acceptance.** Local team acceptance and Android native
preview acceptance were performed by a human and are recorded in `evidence/team-acceptance/`.

**iPhone mobile-web acceptance is `HUMAN_ASSERTED_NOT_EVIDENCED`.** A successor brief states
it passed. No acceptance record exists in this repository and no commit in any ref introduces
one. The two UX defects that testing reported are real and are now closed
(`evidence/team-acceptance/IPHONE_WEB_HARDENING_CLOSURE.md`), which corroborates that testing
occurred — a defect report is not an acceptance record, and the gap should be closed by
writing one, not by treating the brief as the record.

**iOS native is `NOT TESTED`** — never built. Do not infer it from the Android result.
