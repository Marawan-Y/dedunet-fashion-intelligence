# ADR-0002 — Repositioning DEDUNET from single-brand commerce to a fashion intelligence platform

| Field | Value |
|---|---|
| Status | **REVISED 2026-08-24 per owner decision** — ownership model corrected; direction approved |
| Version | 2.0 (1.0 was the pre-revision proposal) |
| Date | 2026-08-24 |
| Owner | Technical lead (successor agent) |
| Decision input | `ADR-0002_DECISION_BRIEF.md` (SOR-BRIEF-001) and the owner corrections it prompted |
| Supersedes | its own §1.0 ownership model, recorded in §Revision below |
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

3. **Ownership is explicit and per-domain. Tenancy is targeted, not universal.**
   Four domains — platform/global, consumer, fashion network, merchant SaaS — each with its
   own ownership shape (§Ownership below). `organization_id NOT NULL` appears **only on new
   merchant-owned tables, from creation**. **No existing table is retrofitted with a tenant
   column.** A consumer is not a tenant. Authorization is still resolved server-side from the
   session, and a tenant id accepted from a client is a defect, not a shortcut.

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

## Ownership

Four domains. Each declares one ownership shape, and the shape is a **schema** property.

```
PLATFORM / GLOBAL     owned by DEDUNET.            no owner column at all
CONSUMER              owned by a Customer.         customer_id NOT NULL
FASHION NETWORK       owned via Brand.             no owner column; resolved through Brand
MERCHANT SaaS         owned by an organization.    organization_id NOT NULL
```

**A consumer account is not a merchant tenant.** No consumer table carries
`organization_id`, and merchant staff are a separate identity (`MerchantMember`) rather than
an overloaded `Customer` — overloading one table is how a customer session ends up
satisfying a merchant authorization check.

**No nullable tenant column, anywhere.** A nullable `organization_id` makes "platform data"
and "merchant data whose owner was never set" indistinguishable at the schema level, so the
fail-open case becomes invisible to a constraint.

### Brand ownership

`Brand` carries an **explicit classification**. Ownership is never inferred from the
presence or absence of a relationship row.

```
Brand
  ownership_type    PLATFORM_CURATED | MERCHANT_OWNED | EXTERNAL_CURATED   NOT NULL

BrandOwnership                    the merchant relationship, and only that
  brand_id                        UNIQUE, FK -> brands
  merchant_organization_id        NOT NULL, FK -> merchant_organizations
```

**Invariants, enforced by database and application, not by convention:**

| `ownership_type` | Required `BrandOwnership` rows |
|---|---|
| `PLATFORM_CURATED` | **exactly 0** — no merchant owner |
| `EXTERNAL_CURATED` | **exactly 0** — no merchant owner |
| `MERCHANT_OWNED` | **exactly 1** — one valid merchant ownership relationship |

`brand_id` is `UNIQUE` on `BrandOwnership`, so "at most one" is a key constraint. "Exactly
one when `MERCHANT_OWNED`, and none otherwise" is the two-way tie, enforced by a trigger or
a deferred constraint and asserted by tests in both directions — a brand that changes type
without its ownership row changing must fail, and vice versa.

**Absence of a row is not a state.** An earlier draft of this ADR encoded `PLATFORM_CURATED`
as "no `BrandOwnership` row exists". That was rejected on owner review, correctly: absence
cannot distinguish *platform-curated* from *merchant-owned whose ownership row failed to
insert*, and a critical authorization state must not be carried by a missing row. The
classification column is the state; the relationship row is the link.

### Commerce routing is orthogonal to ownership

`CommerceRoute` remains `HOSTED` | `EXTERNAL` | `REFERRAL` | `NON_PURCHASABLE`.

**Never infer ownership from route. Never infer route from ownership.** They answer different
questions — *who controls the data* and *where the money goes* — and every combination below
is legitimate:

| Combination | Meaning |
|---|---|
| `PLATFORM_CURATED` + `NON_PURCHASABLE` | DEDUNET's own prototype catalogue, today |
| `MERCHANT_OWNED` + `HOSTED` | a brand with no website; DEDUNET is its commerce surface |
| `MERCHANT_OWNED` + `EXTERNAL` | the merchant runs its own checkout |
| `EXTERNAL_CURATED` + `REFERRAL` | a brand we list and link to, with no relationship |

Collapsing the two is what forces a brand with no website into the wrong box. Keeping them
separate is what makes that case fall out of the model instead of being special-cased.

The commerce **mode** remains an outer gate over the route: `BRAND_PREVIEW_MODE` collapses
every route to non-purchasable regardless of what a product carries.

### Product and Variant

`Product` and `Variant` **do not receive `organization_id` for tenancy.** They gain
`brand_id`, and merchant authorization for catalogue resources flows through the explicit
`Brand` ownership relationship. Any proposal to put direct organization ownership on another
entity must be **justified per entity**, in writing, against these four domains.

### Existing DEDUNET products

A first-party `Brand` — slug `dedunet`, `ownership_type = PLATFORM_CURATED` — is created, and
the existing accepted products attach to it with `commerce_route = NON_PURCHASABLE`. Their
preview and non-sellable safety state is preserved exactly: `sellable=false`,
`origin_claim_status=UNVERIFIED`, `country_of_origin=XX`, `evidence_status=DRAFT`.

**No `MerchantOrganization` is created to hold first-party DEDUNET data.** Inventing a tenant
would put a fabricated row at the root of the authorization model and make "is this
merchant-owned?" un-askable. Zero organizations after migration is the correct count when
zero merchants have onboarded.

### Future order boundary — guidance, not work

Existing `Order` tables are **not redesigned** for hypothetical multi-merchant checkout, and
no speculative multi-merchant work is implemented.

Recorded as a forward constraint: **a customer order that eventually spans multiple merchants
requires separate merchant fulfilment and accounting boundaries, not one ambiguous tenant
owner on the whole customer order.** A likely future shape is

```
CustomerOrder -> MerchantFulfillmentGroup -> OrderLines
```

The trigger is the second merchant with hosted commerce. Until then no order can span two
merchants, and adding columns to the financial record early is the opposite of the care this
codebase takes with it.

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
- **The tenancy retrofit is eliminated, not managed.** The §1.0 draft called it "the single
  largest correctness risk in the programme": a nullable-then-backfilled-then-constrained
  owner column on every existing merchant-relevant table. Under the revised model **no
  existing table receives an owner column at all**, because every existing row belongs to a
  platform-curated first-party brand and no existing row is merchant-owned. There is no
  migration over live data, and rollback of all merchant work becomes "drop the new tables,
  zero impact".
- What replaces it is a smaller, sharper risk: **ownership derived through `Brand` must never
  be resolved ad hoc.** One resolution path, one scoping helper, and a query that cannot be
  written unscoped — see the test category below.
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
- **`organization_id` on every table** — the §1.0 model. Makes consumers into tenants,
  requires a nullable column on platform data, and forces a backfill-and-constrain migration
  over live order rows to solve a problem no existing row has. Rejected on owner review.
- **Encoding `PLATFORM_CURATED` as the absence of a `BrandOwnership` row.** Also §1.0, also
  rejected on owner review. Absence cannot distinguish a platform-curated brand from a
  merchant-owned one whose ownership row failed to insert, and an authorization state must
  not be carried by a missing row.
- **Denormalising `organization_id` onto `Product`.** Two sources of truth for one fact.
  Drift between a product's owner and its brand's owner is silent, and silence there is a
  cross-tenant read.

## Preserved states — none of these may be weakened by work under this ADR

```text
LOCAL_TEAM_ACCEPTANCE_PASSED
NATIVE_ANDROID_PREVIEW_ACCEPTANCE_PASSED
NATIVE_POST_ACCEPTANCE_HARDENING_VERIFIED
IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED
PUBLIC_COMMERCIAL_LAUNCH_BLOCKED
MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING
LEGAL_CLEARANCE_PENDING
```

A phase that cannot proceed without weakening one of these is blocked, not permitted.

**`IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` was restored to this list on 2026-08-24**, when
`EV-TA-006` was written from tester-supplied scope and **CONFLICT-011** closed. It was
correctly absent while the acceptance existed only as an assertion in a brief: a state that
cannot be pointed at cannot be preserved. It can now be pointed at.

**These remain outside the list and cannot join it by inheritance:**

```text
NATIVE_IOS_ACCEPTANCE       NOT TESTED      no iOS binary has ever been built
Apple signing / TestFlight  NOT TESTED
Apple Developer Program     DEFERRED — FUNDING
```

Mobile web in Safari is not the native application. The Android emulator preview, the iPhone
mobile-web acceptance and native iOS are three distinct states and no two may be aggregated.

---

## Revision record

**§2.0 — 2026-08-24.** Owner decision: *revision required; general direction approved subject
to corrections.* Prompted by `ADR-0002_DECISION_BRIEF.md`, which reported the disagreement
between §1.0 and the owner's ownership guidance rather than resolving it unilaterally.

| # | §1.0 said | §2.0 says |
|---|---|---|
| 1 | tenancy is near-universal; every merchant-owned row carries `organization_id` | four explicit domains; tenancy targeted at merchant-owned resources only |
| 2 | existing tables get a nullable→backfill→`NOT NULL` owner column | **no existing table is retrofitted.** New merchant tables are `NOT NULL` from creation |
| 3 | consumer tables implicitly in scope for tenancy | **a consumer is not a tenant.** No consumer table carries `organization_id` |
| 4 | `Product` "gains tenancy" | `Product`/`Variant` gain `brand_id` only; authorization flows through `Brand` ownership |
| 5 | `PLATFORM_CURATED` = absence of a `BrandOwnership` row | explicit `Brand.ownership_type`, with `PLATFORM_CURATED` / `MERCHANT_OWNED` / `EXTERNAL_CURATED` and enforced invariants |
| 6 | `EXTERNAL_CONNECTED` | renamed `EXTERNAL_CURATED` |
| 7 | order tenancy unresolved | explicitly deferred, with the future `CustomerOrder → MerchantFulfillmentGroup → OrderLines` shape recorded as guidance only |
| 8 | `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` omitted from preserved states | restored — `EV-TA-006` exists and CONFLICT-011 is closed |

**What did not change:** the six decision constraints other than ownership, the phase
sequence, the AI safety boundary, the commerce-mode guarantees, and both platform decisions.

**Net effect: the revision removes work, removes risk and removes a migration.** The largest
risk §1.0 named no longer exists, because it was an artefact of a design that has been
replaced rather than a property of the problem.
