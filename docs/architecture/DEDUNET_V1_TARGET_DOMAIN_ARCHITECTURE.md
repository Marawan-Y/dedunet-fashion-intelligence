# DEDUNET V1 — Target domain architecture

| Control | Value |
|---|---|
| Artifact ID | ARCH-P1-001 |
| Version | 1.0 |
| Date | 2026-08-24 |
| Owner | Technical lead (successor agent) |
| Status | **PROPOSED** — design only. Nothing in §3–§8 is implemented |
| Baseline | `41cee4c`, backend suite 415 passed / 2 skipped |
| Decision | `ADR-0002` |

> **Read this as a target, not a description.** Everything marked `EXISTS` is verified and
> running. Everything marked `NEW` is proposed and has no code, no migration and no test.
> The distinction is load-bearing: this programme's failure mode is a document that reads
> like an inventory and is actually a wish list.

---

## 1. What exists today

Measured at `41cee4c`.

```
apps/web/          static storefront, 1 021 lines of app.js, hash router, 8 routes
apps/admin/        static operations portal, 482 lines of admin.js
apps/mobile/       Expo/React Native, 7 screens, 14 test suites
services/commerce-api/
  app/commerce/    18 tables, 5 status enums, one-directional layering
                   api -> services -> {inventory, pricing, payments} -> models -> db
  app/ai_stylist.py   68 lines, deterministic scoring over the legacy fixture catalogue
  app/rate_limit.py   token bucket, process-local
  migrations/      5 revisions, head a7c31f9be402
  tests/           24 modules, 415 passed / 2 skipped
```

Three properties of the existing domain constrain every decision below.

| Property | Consequence for the target |
|---|---|
| **No tenant column anywhere** | Nothing to retrofit: every existing row belongs to a platform-curated first-party brand, so **no existing table receives an owner column**. Tenancy applies only to new merchant tables |
| **No brand entity** | `Product` belongs to a catalogue, not a seller. Brand must become first-class before a marketplace is possible |
| **No styling domain** | Style profile, occasion, look, session, memory and feedback are all new. `ai_stylist.py` is a contract demo, not a foundation |

---

## 2. The two products

```
                        SHARED SERVICES
      identity · style profile · Dido · recommendation · outfit
      brands · catalogue · search · commerce routing · saved
      notifications · analytics · automation · billing · audit
                              |
              +---------------+---------------+
              |                               |
   A. CONSUMER FASHION PLATFORM     B. DEDUNET FOR BRANDS (merchant SaaS)
      style me / discover / looks      onboarding / catalogue / inventory
      brands / shop / saved / account  orders / analytics / integrations / billing
```

They share a database and an API, and they do **not** share an authorization model. A
customer session may never reach a merchant endpoint and a merchant session may never read
another tenant's rows. See §6.

---

## 3. Domain map

`EXISTS` = implemented and tested at `41cee4c`. `NEW` = proposed, no code.

### 3.1 Identity and access

| Entity | State | Note |
|---|---|---|
| `Customer` | EXISTS | PBKDF2 + HMAC session tokens, no revocation list |
| `Address` | EXISTS | |
| `MerchantOrganization` | NEW | the **only** tenant root. Consumers are never tenants |
| `MerchantMember` | NEW | user ↔ organization, carries the role |
| `MerchantRole` | NEW | `merchant_admin`, `merchant_user` |
| `InternalRole` | NEW | `internal_admin`, `support_operator` — never tenant-scoped, always audited |

The existing `Customer` is deliberately **not** reused as the merchant user. A merchant
identity has an organization, a role and a different session lifetime; overloading one table
is how a customer session ends up satisfying a merchant authorization check.

### 3.2 Styling

| Entity | State | Note |
|---|---|---|
| `StyleProfile` | NEW | the Style DNA root, one per customer |
| `StylePreference` | NEW | weighted dimensions (Minimal 70 / Classic 30), mixtures allowed |
| `SizeProfile` | NEW | top, bottom, shoe, fit preference |
| `BrandPreference` | NEW | preferred / avoided, per customer |
| `Occasion` | NEW | occasion, dress code, formality, setting, desired impression |
| `StylingSession` | NEW | one conversation |
| `StylingMessage` | NEW | one turn, with the structured extraction it produced |
| `RecommendationRequest` | NEW | the structured styling request — the LLM's *output*, the engine's *input* |
| `Recommendation` | NEW | one engine run, carries the algorithm version |
| `Look` | NEW | **the primary recommendation unit** |
| `LookItem` | NEW | one garment slot within a look |
| `RecommendationFeedback` | NEW | too expensive / wrong jacket / more formal … |

**`Look` is advice; `Order` is a financial record.** A look may contain items that cannot be
bought. An `OrderLine` may never reference a `Look` — orders copy their descriptive fields
today precisely so a past order cannot be altered by a later edit, and a look is mutable
advice.

### 3.3 Fashion knowledge

| Entity | State | Note |
|---|---|---|
| `GarmentTaxonomy` | NEW | garment kinds and slots |
| `StyleTaxonomy` | NEW | the style dimensions themselves |
| `ColourCompatibility` | NEW | |
| `DressCode` | NEW | formality bands and their garment expectations |
| `LayeringRule` | NEW | |
| `MaterialProperty` | NEW | factual properties only |

Every knowledge row carries a **claim class**, and the claim class decides how the client may
phrase it:

```
FACT              verifiable and attributable        may be stated
HEURISTIC         common styling practice            must be framed as a convention
PREFERENCE        this user's stated choice          must be attributed to the user
MODEL_INFERENCE   the model's guess                  must be marked as a suggestion
```

This is the same discipline `originText()` already applies in the storefront: a payload state
decides what prose is permitted, and no surface invents a claim the data does not carry.

### 3.4 Marketplace

| Entity | State | Note |
|---|---|---|
| `Product` | EXISTS | gains `brand_id` and `commerce_route`. **No owner column** — ownership derived via `Brand` |
| `Variant` | EXISTS | |
| `InventoryItem` | EXISTS | atomic reservation preserved unchanged |
| `ProductMedia` | EXISTS | |
| `Brand` | NEW | first-class. `ownership_type`: `PLATFORM_CURATED` / `MERCHANT_OWNED` / `EXTERNAL_CURATED` |
| `BrandIntegration` | NEW | Shopify / Woo / custom API / feed, plus sync state |
| `ProductStyleTag` | NEW | links catalogue to the style taxonomy |
| `ProductAttribute` | NEW | |
| `CommerceRoute` | NEW | see §5 |
| `ReferralLink` / `ReferralEvent` | NEW | |

### 3.5 Commerce, saved content, platform

`Cart`, `CartLine`, `Promotion`, `Order`, `OrderLine`, `Reservation`, `Payment`, `Shipment`,
`ReturnRequest`, `Notification`, `AnalyticsEvent`, `AuditLog` all **EXIST** and are
**completely unchanged** by this architecture. Not one of them receives an owner column: carts
are consumer-owned by `customer_id` already, orders are deferred (§6.7), and the rest are
platform-owned.

New: `SavedLook`, `FavoriteProduct`, `FavoriteBrand`, `Refund`, `Fulfilment`, `Automation`,
`Subscription`, `BillingAccount`, `Plan`, `Entitlement`, `FeatureFlag`, `Consent`,
`PrivacyRequest`.

---

## 4. The styling pipeline

```
  user turn
     |
     v
  CONVERSATION            Dido. Natural language in, natural language out
     |
     v
  CONTEXT EXTRACTION      LLM -> StylingRequest, schema-validated, rejected if invalid
     |
     v
  CANDIDATE RETRIEVAL     structured query over products / brands / knowledge
     |
     v
  CONSTRAINT FILTER       deterministic. budget, size, availability, dress code, exclusions
     |
     v
  RANKING                 explicit weighted score, configurable, versioned
     |
     v
  OUTFIT COMPOSITION      slot-filling into complete looks
     |
     v
  COMPATIBILITY VALIDATION  colour, formality, layering, seasonality
     |
     v
  EXPLANATION             LLM phrases the rationale over facts it did not choose
     |
     v
  FEEDBACK -> PROFILE UPDATE
```

**The LLM appears exactly twice, at both ends, and never in the middle.** It turns prose into
a structured request, and it turns a decided look into prose. Every decision between those
two points is deterministic, testable without a model, and reproducible from a
`Recommendation` row and its algorithm version.

### 4.1 Ranking

Starting weights, configurable and versioned per `Recommendation`:

| Factor | Weight |
|---|---|
| Style match | 25% |
| Occasion match | 20% |
| Budget fit | 15% |
| Colour compatibility | 15% |
| Fit preference | 10% |
| Availability | 10% |
| Brand preference | 5% |

These are a starting model, not a tuned one. They are recorded per recommendation so a
result can be explained after the weights change, and so an A/B arm is attributable.

### 4.2 Output

Three looks — `SAFE`, `BEST_MATCH`, `DISTINCTIVE` — each carrying its items, prices in
integer minor units, availability, commerce route, occasion rationale, style rationale and
alternatives.

Conversational modification operates on the look, not the conversation: *too expensive*
preserves style and reduces cost; *not the jacket* replaces one slot; *more formal* moves the
formality band and re-solves only the slots that violate it.

---

## 5. Commerce routing

Four routes, typed, stored on the product:

| Route | Customer sees | Fulfilment |
|---|---|---|
| `HOSTED` | Add to bag | DEDUNET cart, checkout, order, fulfilment |
| `EXTERNAL` | Buy from {Brand} | leaves the platform; DEDUNET records the click, not the sale |
| `REFERRAL` | View at {Brand} | as above, with attribution |
| `NON_PURCHASABLE` | Not available to buy | nothing |

**Purchasability is never inferred from stock.** This generalises the rule
`modes.assert_purchasable` already enforces: a prototype does not become purchasable merely
because it has a price, and a curated product does not become purchasable merely because the
source page says "in stock".

The commerce mode remains an outer gate over all four. `BRAND_PREVIEW_MODE` collapses every
route to `NON_PURCHASABLE` regardless of what the product carries — and the storefront must
mirror both gates, which is what the Phase 0 hardening closed.

Availability on `EXTERNAL` and `REFERRAL` products is a **confidence with a timestamp**, never
a fact. `last_checked_at` and `availability_confidence` are required columns; a client may not
render "in stock" for a route DEDUNET does not control.

---

## 6. Ownership and tenancy

Revised 2026-08-24 per owner decision. `ADR-0002` §2.0 is authoritative; this expands it.

### 6.1 Four ownership shapes

| Domain | Shape | Column |
|---|---|---|
| **Platform / global** | owned by DEDUNET | **none** |
| **Consumer** | owned by a customer | `customer_id NOT NULL` |
| **Fashion network** | owned via `Brand` | **none** — resolved through `Brand` |
| **Merchant SaaS** | owned by an organization | `organization_id NOT NULL` |

**No existing table is retrofitted with a tenant column.** `organization_id` appears only on
**new** merchant tables, `NOT NULL` from creation, because those tables start empty. The
nullable→backfill→constrain migration the earlier draft described is not required and is not
performed.

**A consumer is not a tenant.** No consumer table carries `organization_id`, and no merchant
session can reach consumer data by any scoping — there is no column to scope by.

**No nullable tenant column anywhere.** Nullable `organization_id` cannot distinguish platform
data from merchant data whose owner was never set, so the fail-open case becomes invisible to
a constraint.

### 6.2 Brand ownership — explicit classification

```
Brand.ownership_type   PLATFORM_CURATED | MERCHANT_OWNED | EXTERNAL_CURATED   NOT NULL

BrandOwnership         the merchant relationship only
  brand_id                    UNIQUE, FK -> brands
  merchant_organization_id    NOT NULL, FK -> merchant_organizations
```

| `ownership_type` | `BrandOwnership` rows |
|---|---|
| `PLATFORM_CURATED` | **0** |
| `EXTERNAL_CURATED` | **0** |
| `MERCHANT_OWNED` | **exactly 1** |

Enforced by database and application, asserted in **both** directions: changing the type
without changing the ownership row must fail, and changing the ownership row without the type
must fail. `brand_id UNIQUE` makes "at most one" a key constraint; the two-way tie makes
"exactly one when merchant-owned, none otherwise" a checked invariant.

**Absence of a relationship is not a state.** It cannot distinguish *platform-curated* from
*merchant-owned whose ownership row failed to insert*, and an authorization state must never
be carried by a missing row.

### 6.3 Route is orthogonal to ownership

Never infer one from the other. All four combinations are legitimate — see `ADR-0002`. The
commerce **mode** remains an outer gate over the route.

### 6.4 Derived ownership for catalogue resources

`Product`, `Variant`, `ProductMedia` and merchant `InventoryItem` carry **no owner column**.
Merchant authorization resolves:

```
product -> brand -> BrandOwnership -> merchant_organization
```

in **exactly one function**. One join to audit, not one per endpoint. Any proposal to put
direct organization ownership on another entity must be justified **per entity** against these
four domains.

### 6.5 Enforcement

1. The organization is resolved **from the session, server-side**. A tenant id in a body,
   query string, path or header is ignored, and a test proves it is ignored rather than
   merely rejected.
2. **The repository layer cannot express an unscoped merchant query.** Scoping is a required
   argument, so the unscoped query is not writable — the failure mode becomes an import error
   rather than a silent full-table read.
3. Cross-tenant reads answer **404, not 403**. A 403 confirms the row exists, which leaks
   existence to a competitor.
4. **Tenant isolation is a test category**, established *before* the first merchant endpoint.
   Every merchant endpoint gets a two-organization test; guard mutations that remove a scope
   predicate must be detected.

### 6.6 Migration and rollback

No step touches existing rows for tenancy purposes.

```
1  create brands; insert the DEDUNET first-party brand      no existing row touched
2  Product.brand_id nullable; backfill all 5 to DEDUNET
3  Product.brand_id NOT NULL                                 only after 2 is verified
4  add commerce_route, default NON_PURCHASABLE               fail-closed default
5  create merchant tables, organization_id NOT NULL          start empty
6  scoping helper + tenant-isolation test category           BEFORE any endpoint
7  merchant endpoints, one at a time                         each with its isolation test
```

Rollback of steps 5–7 is **drop the tables, zero impact** — no existing row references them.
Step 6 before step 7 is the rule that matters: shipping a merchant endpoint before the
isolation category exists is how the first IDOR ships.

### 6.7 Future order boundary — guidance only

Existing `Order` tables are **not redesigned**, and no speculative multi-merchant checkout is
implemented. Recorded as a forward constraint: an order spanning multiple merchants requires
separate merchant fulfilment and accounting boundaries, not one ambiguous tenant owner on the
customer order. Likely shape:

```
CustomerOrder -> MerchantFulfillmentGroup -> OrderLines
```

Trigger: the second merchant with hosted commerce. Until then no order can span two merchants.

---

## 7. AI safety boundary

The model is advisory. It may never, directly or through a tool call:

```
charge a payment          change stock            publish a merchant
change a price            refund a payment        change permissions
modify an entitlement     create an order         alter an audit record
```

Every one of those is a deterministic service function behind an authorization check, and the
model's output is an *input* to it at most.

**The model may not originate facts.** Product existence, prices, stock, sizes, brand
relationships, material composition, origin and merchant integrations come from structured
system data. A rendered look whose price did not come from a `Variant` row is a defect
regardless of whether the number happens to be right.

**Degradation is bounded.** If the LLM provider is unavailable: the site, catalogue, brands,
account, saved content, merchant portal and checkout all keep working, and Dido alone
degrades — to structured retrieval without natural-language phrasing, and if that is also
unavailable, to an honest statement that styling is temporarily unavailable. One provider
outage may not become a platform outage.

---

## 8. What this architecture does not solve

Recorded here rather than discovered later.

| Item | Status |
|---|---|
| Rate limiting across replicas | `MULTI_REPLICA_DEPLOYMENT_BLOCKED_…` still stands. Buckets are process-local; the styling and recommendation endpoints make this worse, not better, because they are the expensive ones |
| LLM provider | none selected, none funded. The abstraction is the deliverable; activation is a gate |
| Vector search / embeddings | not selected. Retrieval starts structured-only, which is sufficient for a catalogue of this size and avoids a paid dependency |
| Hosted infrastructure | none. Local Compose only |
| Git remote | none (L8). Every verified result exists on one machine |
| Brand legal clearance | `LEGAL_CLEARANCE_PENDING`, and a marketplace enlarges the exposure |
| Public commerce | `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED`, unchanged by anything here |

---

## 9. Traceability

| Mandate deliverable | Where it lands |
|---|---|
| A Product specification | §2, §4 here + `ADR-0002` |
| B System architecture | this document |
| J Data model | §3 here; migrations in Phase 4–6 |
| E Recommendation architecture | §4.1, expanded in Phase 8 |
| F Outfit engine | §4.2, expanded in Phase 9 |
| G Fashion knowledge | §3.3, expanded in Phase 10 |
| H Marketplace | §3.4, §5, expanded in Phase 4 |
| I Merchant SaaS | §3.1, §6, expanded in Phase 5 |
| L Security architecture | §6, §7, expanded in Phase 12 |
| C, D, K, M–AD | their own phases; not authored here |

Deliverables C, D, K and M through AD are **not** written yet, and this document does not
stand in for them.
