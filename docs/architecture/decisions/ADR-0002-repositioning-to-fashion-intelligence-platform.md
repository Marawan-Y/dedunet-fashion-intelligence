# ADR-0002 — Repositioning DEDUNET from single-brand commerce to a fashion intelligence platform

| Field | Value |
|---|---|
| Status | PROPOSED — awaiting owner decision |
| Date | 2026-08-24 |
| Owner | Technical lead (successor agent) |
| Supersedes | none |
| Amends | ADR-0001 (scope), which remains in force for its gate-override finding |
| Related | `docs/system-of-record/TEAM_ACCEPTANCE_READINESS_DECISION.md`, `DEDUNET_V1_TARGET_DOMAIN_ARCHITECTURE.md`, `CONFLICT_AND_RESOLUTION_REGISTER.md` |

## Context

A successor mandate directs that DEDUNET become an AI fashion stylist, a personal fashion
intelligence platform, a multi-brand discovery surface, a marketplace, a merchant SaaS and
commerce routing infrastructure — two connected products over roughly sixty domain entities,
sequenced across twenty phases.

The repository it directs this at is not a greenfield. It is a **single-brand, single-tenant
commerce platform with passed local acceptance**, and the mandate explicitly requires that
work be preserved.

## Findings — measured at `41cee4c`, not assumed

Re-derived by executing the repository's own checks, not by reading forward from prior
evidence.

| Measure | Observed |
|---|---|
| Tracked files | 405 |
| Backend suite (SQLite) | **415 passed, 2 skipped** |
| API contract | 31 paths, 31 operations |
| ORM classes in `commerce/models.py` | 23 — 18 tables and 5 status enums |
| Alembic revisions | 5, head `a7c31f9be402` |
| Backend test modules | 24 |
| Mobile test suites | 14 |
| Guard mutations registered | **72** before this phase — the harness has 77 entries after it, and the ids run to M79 because M56 and M57 were never used |
| Working tree at takeover | clean; the LAN staging change was already committed as `41cee4c` |

What the domain actually models today: `Customer`, `Address`, `Product`, `ProductMedia`,
`Variant`, `InventoryItem`, `Cart`, `CartLine`, `Promotion`, `Order`, `OrderLine`,
`Reservation`, `Payment`, `Shipment`, `ReturnRequest`, `Notification`, `AnalyticsEvent`,
`AuditLog`.

Three properties of that list decide everything below.

1. **There is no tenant.** Not one table carries an owning organization. Every row belongs
   to the deployment.
2. **There is no brand.** `Product` belongs to a catalogue, not to a seller. DEDUNET is the
   brand by construction, not by data.
3. **There is no styling domain.** `app/ai_stylist.py` is 68 lines of deterministic scoring
   over the legacy fixture catalogue — colour, category and tag intersection plus a stock
   term. It is a contract demonstration, and its own docstring says so. There is no style
   profile, no occasion model, no outfit, no look, no session, no memory and no feedback.

The mandate's target needs all three. **The gap is a new domain, not a refactor of the
existing one.**

## Decision

**Extend, in place, behind the existing safety envelope. Do not rebuild, do not rebrand the
commerce core, and do not relax any mode, evidence or purchasability guard to make room for
the new domain.**

Concretely:

1. **The commerce core is a dependency of the new platform, not a competitor to it.**
   Catalogue, cart, checkout, inventory, orders, returns, notifications and their 415 tests
   stay exactly as they are. Styling, brands and merchants are added *around* them.

2. **`Look` becomes the primary recommendation unit; `Product` stays the primary commerce
   unit.** These are different objects with different lifecycles. A look is advice and may
   reference products that cannot be bought; an order line is a financial record and may
   never reference a look.

3. **Multi-tenancy is introduced as a schema property, not an application convention.**
   Every merchant-owned row carries its owning organization as a column with a foreign key,
   and authorization is derived server-side from the session. A tenant id accepted from a
   client is a defect, not a shortcut.

4. **Commerce routing becomes explicit and typed.** `HOSTED`, `EXTERNAL`, `REFERRAL`,
   `NON_PURCHASABLE`. Purchasability is never inferred from stock. This generalises the rule
   `modes.assert_purchasable` already enforces rather than replacing it.

5. **The LLM is advisory and never authoritative.** It may phrase an explanation. It may not
   originate a product, price, size, stock level, brand relationship, material fact, origin
   fact or merchant integration, and it may not cause a write. Every fact in a rendered look
   comes from structured system data. This is the same rule `originText()` and
   `disclaimerFor()` already apply to prose in the storefront, extended to a new source of
   prose.

6. **`PUBLIC_COMMERCE_MODE` stays unreachable by configuration.** Nothing in this
   repositioning is a reason to touch it. Production-grade code and public commercial launch
   remain two decisions, and this ADR makes only the first.

## What this ADR deliberately does not decide

- **It does not authorize public commerce.** `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` is unchanged
  and every blocker in the readiness decision §11 remains open.
- **It does not adopt a paid provider.** No LLM vendor, hosting platform, SMTP service,
  search engine or payment processor is selected here. Provider abstractions with local
  adapters are the deliverable; activation is a separate gate.
- **It does not rewrite the brand.** DEDUNET remains `LEGAL_CLEARANCE_PENDING`. Becoming a
  multi-brand platform does not resolve the trademark position of the platform's own name —
  it enlarges it, because a marketplace makes brand claims on behalf of others.

## Consequences

**Accepted.**

- The domain roughly quadruples. Sixty-odd entities against today's eighteen, across
  identity, styling, knowledge, marketplace, merchant, billing and automation.
- Multi-tenancy is retrofitted onto a schema that has never had it. Every existing
  merchant-relevant table needs a nullable-then-backfilled-then-constrained owner column, in
  that order, and every existing query needs an ownership predicate. This is the single
  largest correctness risk in the programme.
- The test suite must grow a category it does not have: **tenant isolation**. Absent that,
  every new endpoint is an IDOR waiting to be reported.
- Documentation must not drift again. CONFLICT-009 — `README.md` and
  `docs/KNOWN_LIMITATIONS.md` describing a pre-workstream MERET-era platform — was closed
  alongside this ADR, and `KNOWN_LIMITATIONS.md` §4.1 now lists this ADR's entire domain as
  `NOT_STARTED` so the target cannot be mistaken for progress. Every phase below has to keep
  that section accurate as it lands work, or the honesty inventory becomes stale in the
  opposite direction — overstating rather than understating.

**Rejected alternatives.**

- **Greenfield rebuild.** Discards 415 backend tests, 72 guard mutations, passed local team
  acceptance and passed Android native preview acceptance. The mandate forbids it and the
  evidence is the asset.
- **A styling layer bolted onto the storefront client.** Puts recommendation logic in a
  browser bundle where it cannot be tenant-scoped, rate-limited, audited or tested, and
  where an LLM response would be one `innerHTML` away from the stored-XSS class this
  codebase has already closed once.
- **Deferring multi-tenancy to "after V1".** Tenancy is a schema property. Retrofitting it
  after merchant data exists means a migration over live rows with no owner, which is
  exactly the shape of migration this programme has already committed to avoid.

## Preserved states — none of these may be weakened by work under this ADR

```text
LOCAL_TEAM_ACCEPTANCE_PASSED
NATIVE_ANDROID_PREVIEW_ACCEPTANCE_PASSED
NATIVE_POST_ACCEPTANCE_HARDENING_VERIFIED
PUBLIC_COMMERCIAL_LAUNCH_BLOCKED
MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING
LEGAL_CLEARANCE_PENDING
```

A phase that cannot proceed without weakening one of these is blocked, not permitted.

**`IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` is deliberately absent from that list.** An earlier
draft of this ADR included it. The token exists in no tracked file and in no commit on any
ref — see **CONFLICT-011**. A state that cannot be pointed at cannot be preserved, and listing
it here would have made a brief's assertion look like a repository fact. The two UX defects
that acceptance reported are real and are closed
(`evidence/team-acceptance/IPHONE_WEB_HARDENING_CLOSURE.md`); the acceptance record itself is
owed by the human tester.
