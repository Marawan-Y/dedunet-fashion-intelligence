# ADR-0002 — Human decision brief

| Control | Value |
|---|---|
| Artifact ID | SOR-BRIEF-001 |
| Version | 1.0 |
| Date | 2026-08-24 |
| Owner | Technical lead (successor agent) |
| Prepared for | Repository owner |
| Subject | `ADR-0002` — repositioning to a fashion intelligence platform |
| ADR status | **PROPOSED**, unmodified. This brief does not change it |
| **Recommendation** | **REVISE ADR-0002 — then accept.** See §19 and §20 |

> This brief was written **after** owner guidance that materially contradicts ADR-0002 §6.
> That contradiction is the reason the recommendation is REVISE rather than ACCEPT, and it is
> stated in full in §20 rather than quietly absorbed into the design below.

---

## 1. The exact decision being asked for

**Approve extending the existing single-brand commerce platform, in place, into a fashion
intelligence platform** — AI stylist, multi-brand fashion network, and merchant SaaS — under
six binding constraints:

1. The commerce core and its 434 tests are a dependency, not a competitor. Styling, brands
   and merchants are added *around* catalogue/cart/checkout/inventory/orders, which do not
   change.
2. `Look` becomes the primary recommendation unit; `Product` stays the primary commerce unit.
   An `OrderLine` may never reference a `Look`.
3. Merchant resources are tenant-owned, and tenancy is enforced in the schema and
   server-side — never from a client-supplied identifier.
4. Commerce routing is explicit and typed. Purchasability is never inferred from stock.
5. The LLM is advisory. It may phrase; it may not originate a fact or cause a write.
6. `PUBLIC_COMMERCE_MODE` stays unreachable by configuration.

### What approval does NOT authorize

| Not approved | Still requires |
|---|---|
| Public commerce | its own decision; `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` unchanged |
| Any paid provider — LLM, hosting, SMTP, search, payments | separate funding decision per provider |
| A brand or trademark position | `LEGAL_CLEARANCE_PENDING`; a marketplace *enlarges* this exposure |
| Any Phase 2+ implementation | each phase has its own acceptance criteria |

---

## 2. Target domain boundaries

Four domains, not three. The owner guidance named three; **platform/global** is separated out
because "no tenant" and "owned by the platform" are different statements and collapsing them
is how a nullable column becomes the de-facto ownership model.

```
  CONSUMER DOMAIN                    owned by a Customer
      Customer · Address · StyleProfile · SizeProfile · BrandPreference
      StylingSession · Recommendation · Look · SavedLook · Cart · Consent

  FASHION NETWORK                    ownership DERIVED from Brand
      Brand · Product · Variant · ProductStyleTag · CommerceRoute · ProductMedia

  MERCHANT SaaS                      owned by a MerchantOrganization
      MerchantOrganization · MerchantMember · MerchantRole
      BrandOwnership · BrandIntegration · merchant inventory and operations
      Subscription · BillingAccount · Entitlement

  PLATFORM / GLOBAL                  owned by DEDUNET, explicitly
      FashionKnowledge · taxonomies · DressCode · ColourCompatibility
      Plan · FeatureFlag · AuditLog
```

**A consumer is not a tenant.** A `Customer` has no organization, cannot be a member of one,
and no consumer row ever carries `organization_id`. Merchant staff are a **separate identity**
(`MerchantMember`), deliberately not the `Customer` table — overloading one table is how a
customer session ends up satisfying a merchant authorization check.

---

## 3. Tenant ownership model

**`MerchantOrganization` is the only tenant root.** Exactly three ownership shapes exist, and
every table declares which one it is:

| Shape | Column | Meaning |
|---|---|---|
| `CONSUMER_OWNED` | `customer_id NOT NULL` | one customer's data |
| `TENANT_OWNED` | `organization_id NOT NULL` | one merchant's data |
| `PLATFORM_OWNED` | *no owner column* | DEDUNET's, by construction |
| `DERIVED` | *no owner column* | ownership resolved through a declared parent |

**No table gets a nullable `organization_id`.** That is the specific pattern the owner
guidance rules out, and it is worth naming why: a nullable tenant column makes "platform data"
and "merchant data whose owner we forgot to set" indistinguishable at the schema level, so the
fail-open case is invisible to a constraint and visible only in a query nobody wrote.

---

## 4. Platform / global entities

Owned by DEDUNET, explicitly, with **no owner column at all**:

`GarmentTaxonomy` · `StyleTaxonomy` · `ColourCompatibility` · `DressCode` · `LayeringRule` ·
`MaterialProperty` · `Plan` · `FeatureFlag` · `AuditLog`

Writable only by `internal_admin`, never by a merchant or consumer session. Readable by
everyone. Fashion knowledge is shared infrastructure — a merchant does not own the fact that
a black tie dress code expects a dinner jacket.

`AuditLog` is platform-owned but **carries the acting organization as an attribute**, so a
merchant's actions are attributable without the audit trail becoming merchant-writable.

---

## 5. Consumer-owned entities

`customer_id NOT NULL`, foreign-keyed, never an `organization_id`:

`Address` · `StyleProfile` · `StylePreference` · `SizeProfile` · `BrandPreference` ·
`Occasion` · `StylingSession` · `StylingMessage` · `RecommendationRequest` ·
`Recommendation` · `Look` · `LookItem` · `RecommendationFeedback` · `SavedLook` ·
`FavoriteProduct` · `FavoriteBrand` · `Cart` · `CartLine` · `Consent` · `PrivacyRequest`

**A merchant may never read these.** Not their own customers' style profiles, not looks
containing their products, not styling conversations. A merchant sees **aggregates** —
impressions, clicks, conversions — never an identified consumer's styling data.

This is a privacy position, not only an authorization one: `StyleProfile` is personal data
(body and fit considerations, budget, brand aversions), and a marketplace that resells it is
a different product from the one this ADR proposes.

---

## 6. Merchant / tenant-owned entities

`organization_id NOT NULL`, foreign-keyed to `merchant_organizations`:

`MerchantMember` · `BrandOwnership` · `BrandIntegration` · `Subscription` ·
`BillingAccount` · `Entitlement` · merchant-scoped `Automation` · merchant analytics rollups

**Derived, not columned:** `Product`, `Variant`, `ProductMedia`, `InventoryItem`. Their
ownership resolves through `Brand → BrandOwnership → organization`. See §7 and §12.

---

## 7. How Brand ownership works

A `Brand` has an **explicit ownership kind**, and the merchant link lives in its **own table**
rather than as a nullable column:

```
Brand
  id, slug, name, story, policies
  ownership_kind   PLATFORM_CURATED | MERCHANT_OWNED | EXTERNAL_CONNECTED

BrandOwnership                          exists ONLY for MERCHANT_OWNED
  brand_id         UNIQUE, FK -> brands
  organization_id  NOT NULL, FK -> merchant_organizations
```

The **absence of a row is the platform-curated case**, which is a fact a database can enforce.
A DB constraint ties the two together: `ownership_kind = MERCHANT_OWNED` **iff** a
`BrandOwnership` row exists. Neither can drift without failing.

### Ownership and commerce route are orthogonal

This is the design point that makes the model work, and it is easy to miss:

| | `HOSTED` | `EXTERNAL` | `REFERRAL` | `NON_PURCHASABLE` |
|---|---|---|---|---|
| `PLATFORM_CURATED` | DEDUNET's own brand | — | a brand we list | preview |
| `MERCHANT_OWNED` | we run their checkout | they run their own | — | unpublished |
| `EXTERNAL_CONNECTED` | — | Shopify/Woo/feed | link-out | sync stale |

**Who controls the data** and **where the money goes** are separate questions. Collapsing them
forces a brand without a website into the wrong box, which is exactly the case §8 exists for.

---

## 8. A brand with no website

This is a **core capability**, not an edge case, and it is `MERCHANT_OWNED` + `HOSTED`.

```
dedunet.com/brands/{brand_slug}
```

DEDUNET supplies the entire commerce surface: brand page and story, product catalogue with
media, variants, inventory, hosted cart and checkout, order routing to the merchant, policies,
analytics, and eligibility for Dido recommendation.

The merchant supplies products and fulfilment. They need no domain, no storefront, no payment
processor and no integration. **This falls out of the model rather than being special-cased** —
`HOSTED` is the same route DEDUNET's own first-party brand uses, so the merchant's checkout is
the checkout that already has 434 tests behind it.

---

## 9. Migration of existing `Product` / `Variant` / `Order`

**The existing data does not move.**

| Entity | Migration |
|---|---|
| `Product`, `Variant`, `ProductMedia`, `InventoryItem` | gain `brand_id NOT NULL` after backfill to the DEDUNET house brand. **No owner column** |
| `Order`, `OrderLine`, `Payment`, `Reservation`, `Shipment`, `ReturnRequest` | **untouched.** Not one column added |
| `Customer`, `Address`, `Cart`, `CartLine` | **untouched** |
| `Promotion`, `Notification`, `AnalyticsEvent`, `AuditLog` | **untouched** in this phase |

**Orders are deliberately deferred.** In a marketplace an order can span several merchants, and
the choice — one order with merchant-scoped lines, or split orders at checkout — is a real
decision. It does not have to be made now: **no order can span two merchants until a second
merchant exists**, and there are currently zero. Making it early would add columns to the
financial record, which is the table this codebase is most careful with (orders copy their
descriptive fields precisely so history cannot be rewritten).

Recommended when it *is* needed: `OrderLine` carries the fulfilling organization; `Order` stays
consumer-owned; merchants read a scoped view of their own lines.

---

## 10. Is `tenant_id` added to existing tables? Exactly which?

# None of the eighteen.

This is the single largest change from ADR-0002 as written, and it follows directly from the
owner guidance.

| Existing table | Domain | Owner column added |
|---|---|---|
| `Customer`, `Address` | consumer | **no** |
| `Cart`, `CartLine` | consumer | **no** |
| `Product`, `Variant`, `ProductMedia` | fashion network | **no** — `brand_id`, ownership derived |
| `InventoryItem` | derived from brand | **no** |
| `Order`, `OrderLine`, `Payment`, `Reservation`, `Shipment`, `ReturnRequest` | deferred | **no** |
| `Promotion`, `Notification`, `AnalyticsEvent`, `AuditLog` | platform | **no** |

`organization_id` appears **only on new merchant tables**, where it is `NOT NULL` from the
first migration because those tables start empty.

**The consequence is large and good:** the "nullable → backfill → predicate → NOT NULL"
migration that ADR-0002 called *"the single largest correctness risk in the programme"* is
**not required at all**. There is no retrofit over live rows, because no existing row is
merchant-owned. That risk is eliminated, not managed.

---

## 11. How the existing DEDUNET prototype products are represented

```
Brand
  slug            dedunet
  name            DEDUNET
  ownership_kind  PLATFORM_CURATED       <- first-party; no BrandOwnership row
  commerce_route  NON_PURCHASABLE        <- while BRAND_PREVIEW_MODE holds
```

All 5 products (`DDN-TS01`, `SH01`, `TR01`, `OS01`, `SC01`) and their 62 variants attach to it.
`sellable=false`, `origin_claim_status=UNVERIFIED`, `country_of_origin=XX` and
`evidence_status=DRAFT` are **preserved exactly**.

**No merchant organization is created for DEDUNET.** Inventing a tenant to hold first-party
data would put a fake row at the root of the authorization model and make "is this
merchant-owned?" un-askable. Zero organizations exist after this migration, which is the
correct count when zero merchants have onboarded.

The commerce mode remains an **outer gate** over the route: `BRAND_PREVIEW_MODE` collapses
every route to `NON_PURCHASABLE` regardless of what a product carries.

---

## 12. Authorization boundary — how cross-tenant access becomes impossible

Five layers. The first two are the load-bearing ones; the rest are backstops.

**1 — The organization comes from the session, never the request.** Not from a body, path,
query or header. A request carrying an organization identifier is answered as if it had not:
the value is ignored, and a test proves it is ignored rather than merely rejected.

**2 — The repository layer cannot express an unscoped merchant query.** Merchant reads go
through a scoping helper that takes the session's organization as a required argument. There
is no "remember to add the filter" — the unscoped query is not a thing you can write, so the
failure mode becomes a compile/import error rather than a silent full-table read.

**3 — Derived ownership resolves through one function.** `Product` has no owner column, so
merchant access resolves `product → brand → BrandOwnership → organization` in exactly one
place. One join to audit, not one per endpoint.

**4 — Not-found, not forbidden.** A cross-tenant read returns **404**. A 403 confirms the row
exists, which is an information leak in a marketplace where competitors are tenants.

**5 — Tenant isolation is a test category, not a review item.** Every merchant endpoint gets a
two-organization test asserting 404, and guard mutations that remove a scope predicate must be
detected — the same discipline the 77 existing mutations apply.

**Consumer data is outside this model entirely.** No merchant session can reach it by any
scoping, because there is no organization column to scope by.

---

## 13. Migration sequence

Each step is independently deployable and independently reversible.

| # | Step | Reversible | Note |
|---|---|---|---|
| 1 | Create `brands`; insert the DEDUNET house brand | yes — drop table | no existing row touched |
| 2 | `Product.brand_id` **nullable**; backfill all 5 to DEDUNET | yes — drop column | |
| 3 | `Product.brand_id` **NOT NULL** | yes — relax | only after step 2 is verified |
| 4 | Add `commerce_route`, defaulting `NON_PURCHASABLE` | yes | **fail-closed default**, matching `sellable` |
| 5 | Create merchant tables — organizations, members, ownership, integrations | yes — drop | start empty, `organization_id NOT NULL` from birth |
| 6 | Add the scoping helper + tenant-isolation test category | yes | **no endpoint before this** |
| 7 | Merchant endpoints, one resource at a time | yes | each with its two-organization test |

Steps 1–4 are the fashion network and touch existing data. Steps 5–7 are merchant SaaS and
touch none of it. **Step 6 before step 7 is the rule that matters** — shipping a merchant
endpoint before the isolation category exists is how the first IDOR ships.

`Order` and its related tables are absent from this sequence on purpose (§9).

---

## 14. Rollback strategy

| Scope | Rollback |
|---|---|
| Steps 5–7 (merchant) | drop the new tables. **Zero impact** — no existing row references them |
| Step 4 (`commerce_route`) | drop the column; purchasability falls back to `sellable` + mode, which is today's behaviour |
| Step 3 (`NOT NULL`) | relax the constraint; no data change |
| Steps 1–2 (`brands`, `brand_id`) | drop the column then the table; the 5 products revert to a catalogue with no brand |
| The whole ADR | `git revert` the migrations. No irreversible migration is proposed |

Rollback is cheap here **only because nothing is retrofitted onto existing rows**. Under
ADR-0002's original tenancy retrofit it would not have been: a backfilled-then-constrained
column over live order data is the migration this programme has committed to avoid.

---

## 15. Compatibility with existing APIs and clients

**Additive only. All 31 existing endpoints keep their contract.**

| Surface | Impact |
|---|---|
| Storefront (`apps/web`) | none required. Gains brand data it may ignore |
| Admin (`apps/admin`) | none required |
| Mobile (`apps/mobile`) | **none required** — important, because the Android acceptance is a passed state and a forced client change would invalidate it |
| OpenAPI contract | new paths added; existing paths unchanged; drift check stays green |
| Existing 434 tests | must stay green **unchanged**. A test needing a rewrite is reviewed as a possible weakening |

New response fields are **additive and optional**. A client that ignores `brand` and
`commerce_route` keeps working, which is what lets the native app stay on its accepted build
while the platform moves.

---

## 16. Main risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Cross-tenant read** | **Critical** | Five layers, §12. Isolation as a test category before any endpoint |
| 2 | **Derived ownership forgotten in a query** | **High** | The scoping helper makes the unscoped query unwritable; one resolution function to audit |
| 3 | Consumer styling data leaking to merchants | **High** | No organization column on consumer tables; merchants get aggregates only |
| 4 | LLM originating a price, stock level or product | **High** | Model output is schema-validated input to deterministic code; every fact from structured data |
| 5 | Commerce modes weakened to let merchants sell | **High** | Mode stays an outer gate over route; `PUBLIC_COMMERCE_MODE` unreachable |
| 6 | `Order` tenancy decided too early or too late | Medium | Deferred with a stated trigger: the second merchant |
| 7 | Rate limiting is process-local (L7) | Medium | Styling and recommendation are the expensive endpoints; **worsens** with this ADR |
| 8 | Scope: 60+ entities, 18 phases unstarted | Medium | Phase gates; nothing merges without its acceptance criteria |
| 9 | Marketplace enlarges brand-legal exposure | Medium | `LEGAL_CLEARANCE_PENDING` — external counsel, not engineering |
| 10 | No Git remote (L8) | Medium | Every result still lives on one machine. CONFLICT-010 |

---

## 17. Alternatives considered and rejected

| Alternative | Rejected because |
|---|---|
| **Greenfield rebuild** | Discards 434 tests, 77 mutations and three passed human acceptances. The evidence *is* the asset |
| **`organization_id` on every table** (ADR-0002 as written) | Contradicts the owner guidance. Makes consumers into tenants, requires a nullable column on platform data, and forces a backfill-and-constrain migration over live order rows |
| **Nullable `Brand.organization_id`** | Cannot distinguish "platform-curated" from "merchant-owned, owner not set". The fail-open case becomes invisible to a constraint |
| **Denormalised `organization_id` on `Product`** | Two sources of truth for one fact. Drift between product owner and brand owner is silent and is a cross-tenant read |
| **Reusing `Customer` for merchant staff** | A customer session could satisfy a merchant check. Separate identity, separate lifetime |
| **Splitting orders per merchant now** | Solves a problem no data has. Zero merchants exist |
| **Styling logic in the browser client** | Cannot be tenant-scoped, rate-limited or audited; an LLM response one `innerHTML` from the XSS class already closed |
| **Deferring tenancy to "after V1"** | Tenancy is a schema property. Retrofitting after merchant data exists is the migration §10 now avoids entirely |

---

## 18. What becomes hard to reverse once approved

Honestly assessed. Most of this ADR is cheap to undo; three things are not.

| Item | Reversibility | Why |
|---|---|---|
| **`Brand` as a required parent of `Product`** | **Hard** | Once catalogue, recommendations and routing key off brand, removing it is a redesign, not a revert |
| **Ownership model shape** (derived vs. columned) | **Hard** | Every merchant query, every isolation test and every audit assumes one shape. Changing it later touches all of them |
| **The consumer/merchant identity split** | **Hard** | Two identity tables with different sessions; merging them later means migrating live credentials |
| Public brand-page URLs (`/brands/{slug}`) | **Hard-ish** | External links and SEO; slugs become quasi-permanent |
| Everything else — routes, merchant tables, styling domain | **Easy** | Additive, droppable, no existing row depends on them |

**What stays fully reversible and must remain so:** commerce modes, the purchasability gates,
`PUBLIC_COMMERCE_MODE` being unreachable, and the existing 31-endpoint contract.

---

## 19. Recommendation

# REVISE ADR-0002, then accept

**The direction is right. The ownership section is not.**

Accept without change and you approve a migration plan the owner guidance has already
contradicted — §6 of the ADR calls the tenancy retrofit *"the single largest correctness risk
in the programme"*, and under the corrected model **that retrofit does not happen at all**.
Approving a document whose largest stated risk is an artefact of a design we no longer intend
would put a known-wrong plan into the system of record.

**Three edits, all confined to ownership:**

1. **§6 (Multi-tenancy)** — replace "every merchant-owned table carries `organization_id`"
   with the four ownership shapes (§3) and derived ownership through `Brand` (§7). Delete the
   four-step backfill migration; it is not needed.
2. **§3.4 / §3.5 (Domain map)** — `Product` gains `brand_id` and `commerce_route`, **not**
   tenancy. State explicitly that no existing table receives an owner column.
3. **Preserved states** — add `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED`, now that `EV-TA-006`
   exists and CONFLICT-011 is closed. It was correctly omitted while unevidenced.

The other six constraints in §1, the phase sequence, the AI safety boundary and the commerce
guarantees need **no change** and are recommended for approval as written.

---

## 20. Disagreement between ADR-0002 and the product vision

One disagreement, and it is material.

**ADR-0002 §6 says:**

> "Every merchant-owned row carries its owning organization as a column with a foreign key…
> Every existing merchant-relevant table needs a nullable-then-backfilled-then-constrained
> owner column, in that order, and every existing query needs an ownership predicate. This is
> the single largest correctness risk in the programme."

**The owner guidance says:**

> "Do not assume every record in the platform should carry `tenant_id`… Consumer accounts are
> not merchant tenants… Design ownership explicitly rather than relying on nullable tenant
> columns everywhere."

These are not reconcilable by interpretation. The ADR proposes tenancy as a **near-universal
property**; the guidance proposes it as a **targeted one** protecting merchant resources only.

### Where the ADR is wrong

- It treats `Product` as merchant-owned. Under the guidance `Product` is **fashion network** —
  ownership is derived from `Brand`, which may have no merchant at all.
- It implies consumer tables get tenancy. They must not; a consumer is not a tenant.
- Its four-step retrofit assumes existing rows need owners. **None do** — every existing row
  belongs to a platform-curated first-party brand.
- It has no answer for a **platform-curated** brand, which has no organization. The ADR's
  only available shape is a nullable column, which the guidance rules out.

### Where the ADR is right, and should be kept

- Tenant identity resolved server-side, never from the client.
- Cross-tenant access as a test category, not a review checklist item.
- Tenancy as a **schema** property rather than a service-layer convention. The guidance
  sharpens *which* rows it applies to; it does not weaken the enforcement.

### What the correction buys

| | ADR-0002 as written | With the guidance |
|---|---|---|
| Existing tables gaining an owner column | most of them | **none** |
| Migration over live rows | required, called the largest risk | **not required** |
| Platform-curated brands | unrepresentable without a nullable column | first-class |
| Consumers | ambiguous | explicitly not tenants |
| Rollback of merchant work | entangled with existing data | **drop tables, zero impact** |

**The guidance makes the design both safer and smaller.** That is why the recommendation is to
revise rather than to accept-with-notes: the revision removes work, removes risk, and removes
a migration — and none of that is visible if the ADR is approved as it stands.

---

## Decision required

```
[ ] ACCEPT ADR-0002 as written
[ ] REVISE ADR-0002 per §19, then accept        <- recommended
[ ] REJECT
```

Unchanged by any of the three:

```text
PUBLIC_COMMERCIAL_LAUNCH_BLOCKED
DEDUNET_PLATFORM_V1_PRODUCTION_BLOCKED
NATIVE_IOS_ACCEPTANCE = NOT TESTED
Apple Developer Program = DEFERRED — FUNDING
LEGAL_CLEARANCE_PENDING
```
