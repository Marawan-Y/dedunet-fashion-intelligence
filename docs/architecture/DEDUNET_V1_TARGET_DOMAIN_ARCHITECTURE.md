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
| **No tenant column anywhere** | Multi-tenancy is a schema change over every merchant-owned table, not a service-layer convention |
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
| `MerchantOrganization` | NEW | the tenant root. Every merchant-owned row resolves to exactly one |
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
| `Product` | EXISTS | gains `brand_id`, `commerce_route`, tenancy |
| `Variant` | EXISTS | |
| `InventoryItem` | EXISTS | atomic reservation preserved unchanged |
| `ProductMedia` | EXISTS | |
| `Brand` | NEW | first-class. Three models: connected, hosted, curated |
| `BrandIntegration` | NEW | Shopify / Woo / custom API / feed, plus sync state |
| `ProductStyleTag` | NEW | links catalogue to the style taxonomy |
| `ProductAttribute` | NEW | |
| `CommerceRoute` | NEW | see §5 |
| `ReferralLink` / `ReferralEvent` | NEW | |

### 3.5 Commerce, saved content, platform

`Cart`, `CartLine`, `Promotion`, `Order`, `OrderLine`, `Reservation`, `Payment`, `Shipment`,
`ReturnRequest`, `Notification`, `AnalyticsEvent`, `AuditLog` all **EXIST** and are unchanged
by this architecture except where tenancy applies.

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

## 6. Multi-tenancy

The largest correctness risk in the programme, because it is retrofitted.

**Rules.**

1. Every merchant-owned table carries `organization_id`, `NOT NULL`, foreign-keyed to
   `merchant_organizations`.
2. The organization is resolved **from the session, server-side**. A tenant id in a request
   body, query string, path or header is ignored — and, where it could plausibly be trusted,
   rejected loudly rather than silently.
3. Every merchant query carries an ownership predicate. Not "the service adds one" — the
   repository layer refuses a query that does not have one.
4. Cross-tenant access is a test category, not a review checklist item. Every merchant
   endpoint gets a two-organization test that asserts 404 (not 403 — a 403 confirms the row
   exists).

**Migration order**, for each existing table that becomes merchant-owned:

```
1. add organization_id  NULLABLE           reversible, no behaviour change
2. backfill                                every existing row -> the DEDUNET house org
3. add the ownership predicate to queries   deployed and verified while the column is still nullable
4. add NOT NULL + FK                       only after 3 is proven
```

Step 3 before step 4 is deliberate. Enforcing the constraint first turns a missed query into
a 500 in production; enforcing it last turns a missed query into a failing test.

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
