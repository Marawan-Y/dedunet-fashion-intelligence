# Known Limitations

Honest inventory of what this build does **not** do. Read before demonstrating it to anyone.

Status vocabulary: `VERIFIED` (executed and evidenced), `IMPLEMENTED_UNVERIFIED` (code exists,
not exercised), `BLOCKED`, `EXTERNALLY_PENDING`, `NOT_STARTED`.

---

## 1. This is not a real business

MERET is invented. No company, factory, supplier, product, certification or customer exists.
No physical inspection, laboratory test, customer interview, legal, tax or customs conclusion,
registration, contract, payment activation, carrier result or app-store submission has occurred,
and no evidence of any of those exists in this repository.

Material, origin and care fields in the seed data are **illustrative placeholders**.
`country_of_origin` is deliberately the invalid code `XX` so it cannot be mistaken for a
substantiated claim.

## 2. Governance gate is bypassed, not passed

`docs/system-of-record/GATE_REGISTER.md` records **G0 = NO_GO**, failing on three human-only
criteria: founder/IP baseline, named accountable humans, and spending authority. The repository
owner authorized proceeding anyway; that override is recorded in
`docs/architecture/decisions/ADR-0001-scope-contradiction-and-baseline.md`.

Building over a failed gate changed what was built. It did not make the gate pass.

## 3. Open launch blockers

| ID | Risk | State |
|---|---|---|
| SB-RISK-003 | Stored XSS in the browser clients | **CLOSED** — all markup sinks removed; guarded by `test_frontend_security.py`, proven load-bearing by injection |
| SB-RISK-005 | Non-transactional inventory | **CLOSED for the commerce domain** — atomic reservation plus a `reserved <= on_hand` constraint, proven by a 20-thread race. The **legacy** JSON-fixture catalog path remains non-transactional |
| SB-RISK-011 | Secrets shipped in the pack | **PARTIALLY CLOSED** — `.env` is git-ignored and verified absent from history; the file still exists on disk in the source pack |

None of these has a **named human risk owner**. That remains outstanding (CTRL-01).

## 4. Not built

| Area | State | Note |
|---|---|---|
| Android / iOS applications | **`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`** | Updated by Workstream F (2026-08-06). The peer-dependency conflict is resolved, the app is installed from a committed lockfile, type-checks clean, passes 101 tests and 18/18 guard mutations, and the full catalogue → cart → checkout → order journey was driven against a real API on Expo **web**. Still true: **no native binary exists** — no Expo account is available, so nothing has been built for Android or iOS, and there is no signing config, store metadata or device test. Do not describe the mobile app as built or shipped. See `evidence/workstream-f/WORKSTREAM_F_EVIDENCE.md` |
| CI pipeline | **NOT EXECUTED** | A workflow file exists. No runner is available in this environment, so it has never run. A green pipeline is not evidenced |
| Infrastructure as code | **NOT_STARTED** | No Terraform, Kubernetes or Helm. Docker Compose covers local only |
| Staging / production deployment | **NOT_STARTED** | No environment has been provisioned or deployed to |
| Distributed tracing | **PARTIAL** | Correlation IDs propagate and are logged; no OpenTelemetry exporter or trace backend |
| Metrics, dashboards, alerting | **NOT_STARTED** | Structured logs and health/readiness probes only |
| Backup and restore | **NOT_STARTED** | No procedure has been written or rehearsed |
| Performance and load testing | **NOT_STARTED** | No baseline exists. Response times observed locally are not a performance result |
| Accessibility audit | **PARTIAL** | Semantic markup, labels, skip link, visible focus and keyboard-operable controls are implemented; no automated axe run or screen-reader test |
| Visual regression testing | **NOT_STARTED** | |
| Content management | **NOT_STARTED** | No CMS or editable content pages |
| Marketing integrations | **NOT_STARTED** | |
| Customer support workflow | **NOT_STARTED** | No ticketing or support case model |
| Reviews | **NOT_STARTED** | |
| Wishlist | **NOT_STARTED** | |
| Semantic / AI search | **NOT_STARTED** | Search is a SQL `ILIKE` match, not semantic |
| AI customer support | **NOT_STARTED** | |
| Multi-currency | **NOT_STARTED** | Only EUR has a reviewed minor-unit exponent; any other currency raises rather than defaulting |
| Address validation, multiple shipping options | **NOT_STARTED** | Flat-rate shipping with one free threshold |
| Email / SMS / push delivery | **IMPLEMENTED_UNVERIFIED** | Notifications are written to a transactional outbox table. **Nothing dispatches them.** No message has ever been sent |
| Audit log read API | **NOT_STARTED** | Audit rows are written; the portal cannot list them and says so rather than showing an empty table |

## 5. Deliberate design limits

**Payments are sandbox-only.** `SandboxGateway` implements the full `PaymentGateway` contract
including declines, provider errors and idempotent replay. Setting `PAYMENT_PROVIDER` to anything
else raises rather than falling back, so a misconfigured deployment cannot silently process live
money through a mock.

**Shipping is a mock carrier.** Tracking numbers are generated locally. No carrier API is
integrated and no label has been produced.

**The AI stylist is deterministic and rule-based.** It scores the local catalogue. It is not a
language model, invents no product, price or stock, and the store stays fully usable when it
fails. Treat its output as a ranked suggestion, not advice.

**SQLite is the default database.** The models avoid SQLite-only constructs and the same schema
runs on PostgreSQL by changing `DATABASE_URL`, but PostgreSQL has **not** been exercised here.

**Session tokens are HMAC-signed, not encrypted.** They are integrity-protected only. There is no
revocation list, so a stolen token is valid until it expires.

**No rate limiting.** Login, registration and checkout can be called without throttling. This is a
real gap before any public exposure.

## 6. Environment divergence

The runtime here is **Python 3.14.4**, while the Dockerfile and CI matrix target **3.12**. The
suite passes on 3.14; 3.12 has not been exercised in this environment.

The application does **not** auto-load `.env`. Configuration must be supplied as real environment
variables, which is why `CORS_ORIGINS` must be set explicitly.

## 7. Test coverage honesty

81 tests pass. They cover the commerce domain, its failure paths, concurrency, authorization,
privacy and money integrity. They do **not** cover: the browser clients (no JS test runner; only
static source guards), mobile, infrastructure, performance, accessibility automation, or any real
external provider.

The browser journeys described in the delivery report were driven manually through a real browser
and evidenced by database state — they are not automated and will not catch a regression.
