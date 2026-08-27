# Phase 4 — Multi-brand fashion network

| Field | Value |
|---|---|
| Artifact ID | EV-P4-001 · **Version** 1.0 |
| Status | **`AUTOMATED-TESTED`** — awaiting human acceptance of the new brand behaviour |
| Starting HEAD | `1176143` |
| Owner | Side B / platform |
| Date | 2026-08-27 |

> `PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**. This phase changed the **domain**: products
> now belong to brands, and brands carry explicit ownership, commerce routing and provenance.
> Nothing became purchasable. The five accepted DEDUNET prototypes are `NON_PURCHASABLE`
> before and after, and the server still refuses a cart add with 409.
>
> **Not started, and not touched:** Saved persistence, Style DNA, Dido intelligence, the
> recommendation and outfit engines, merchant SaaS.

---

## 1. Architecture

Three concepts kept deliberately separate, because collapsing any two is how a marketplace
starts making claims it cannot support.

| Concept | Answers | Where |
|---|---|---|
| **Ownership** | who is accountable for this brand | `Brand.ownership_type`, `BrandOwnership` |
| **Commerce route** | how, and whether, a product can be bought | `Product.commerce_route` |
| **Provenance** | where the information came from and when | `Brand.provenance_source`, `last_checked_at`, `availability_confidence` |

**Ownership and routing are orthogonal and neither is inferred from the other.** The tempting
shortcut — "merchant-owned implies we host the sale" — is wrong the first time a merchant
keeps their own checkout, and wrong silently.
`test_commerce_route_is_independent_of_ownership_in_both_directions` exercises six
combinations and asserts neither axis predicts the other.

**The commerce mode remains the outer gate.** A route is a *capability*, never a permission.
`commerce_action()` applies three gates in a fixed order — mode, then the product's sellable
flag, then the route — and a test asserts that ordering, because reversing the first and
third would let a `HOSTED` product look purchasable in a preview deployment.

## 2. Schema

New tables — `brands`, `brand_ownership`, `merchant_organizations`.

`products` gains `brand_id` (**NOT NULL**, FK, `ondelete RESTRICT`), `commerce_route`,
`external_buy_url`, `availability_confidence`, `availability_checked_at`,
`source_last_synced_at`.

**No `organization_id` was added to `products` or `variants`.** Catalogue authorization
resolves through `Brand` ownership. A tenant column on an existing table would have to be
nullable during backfill, and a nullable tenant column cannot distinguish "platform-owned"
from "nobody set it" — the cross-tenant read the target architecture calls the programme's
worst credible defect.

Two constraints do real work rather than documenting intent:

- `brand_ownership.brand_id` is **UNIQUE**, so "at most one owner" is a database key.
- `ck_brand_fixture_never_published` forbids a development fixture being published **at the
  database level**, so the production gate survives a direct `UPDATE`.

The other half of the ownership rule — "exactly one owner when merchant-owned, none
otherwise" — is a biconditional across two tables. `assert_ownership_consistent` enforces it
on writes and `verify_ownership_invariants` sweeps the whole table, because a per-write check
can only see writes that went through it.

## 3. Migration — `f5c2a8d13b70`

Staged, because `brand_id` must end NOT NULL over a populated table:

1. create the three tables
2. insert the two canonical brands **inside the migration**
3. add `brand_id` **nullable** plus the route and provenance columns
4. backfill — external identity present → DEDUNET; otherwise → the fixture brand
5. **verify**, and abort the transaction with a readable sentence if any row is unattached
6. only then `NOT NULL` + foreign key

Stage 5 is the one that matters: without it stage 6 fails with a constraint error that names
no rows, and on SQLite batch mode could rebuild the table and fail later.

### Applied to staging, on PostgreSQL

```
[entrypoint] applying migrations
INFO  [alembic.runtime.migration] Running upgrade a7c31f9be402 -> f5c2a8d13b70,
      Multi-brand fashion network: Brand, ownership, commerce route and provenance
```

### Migration integrity — before vs after

A backup was taken first — 58 226 bytes, held in `backups/` and **deliberately not committed**.

> It was briefly staged for this commit and caught before it landed: a `pg_dump` of this
> platform contains the customer table, including **PBKDF2 password hashes**. That is
> credential material even though it is hashed, and it does not belong in version control.
> `.gitignore` now refuses `evidence/**/*.sql` so the next one cannot be added by accident.

| | Before | After |
|---|---|---|
| products | 6 | **6** |
| variants | 63 | **63** |
| product media | 18 | **18** |
| inventory items | 63 | **63** |
| `md5(sku:price …)` over every variant | `093e07688e9b342aa932c20192f974e2` | **`093e07688e9b342aa932c20192f974e2`** |

Per accepted product — identical in both captures:

| External id | Slug | Publication | Sellable | Inventory | Variants | Price | Media |
|---|---|---|---|---|---|---|---|
| DDN-TS01 | the-source-tee | preview | **f** | prototype_unavailable | 18 | **7200** | 4 |
| DDN-SH01 | the-passage-shirt | preview | f | prototype_unavailable | 18 | 12200 | 3 |
| DDN-TR01 | the-measure-trouser | preview | f | prototype_unavailable | 12 | 14200 | 4 |
| DDN-OS01 | the-structure-overshirt | preview | f | prototype_unavailable | 12 | 19200 | 4 |
| DDN-SC01 | the-trace-scarf | preview | f | prototype_unavailable | 2 | 7400 | 3 |

`diff before.txt after.txt` is **empty**. No product disappeared, no price changed, no variant
was lost, no sellable or preview state moved. The Source Tee remains **€72.00**,
`NON_PURCHASABLE`, preview, non-sellable.

### Assignment

```
dedunet                        5 products   NON_PURCHASABLE
internal-development-fixtures  1 product    NON_PURCHASABLE
orphan products = 0 · merchant_organizations = 0 · brand_ownership rows = 0
```

**No `MerchantOrganization` was invented to own DEDUNET.** Inventing one would make the
first-party brand indistinguishable from a tenant's, which is the distinction
`ownership_type` exists to preserve.

The sixth product is `restore-test-item`, the backup-restore runbook's fixture. It is not
DEDUNET's, and rather than invent a plausible company for it — the "fake partner presented as
real" failure this phase forbids — it belongs to an unmistakable development-fixture brand
that the database forbids publishing.

## 4. Rollback — stated honestly

**Not "drop the new tables, zero impact".** Once `products.brand_id` exists, `downgrade()`
**drops that column**, so the product-to-brand association is destroyed rather than detached.

Exercised on a scratch database: downgrade, then re-upgrade.

| After downgrade | Result |
|---|---|
| products / variants / prices | **intact** |
| `brands`, `brand_ownership`, `merchant_organizations` | dropped |
| `products.brand_id`, `commerce_route` | dropped |
| re-`upgrade()` | association **reconstructed identically** |

Recovery works *only* because the assignment is derivable from `external_product_id`. Once an
operator assigns a brand by hand that ceases to be true, and from that point a downgrade needs
a data export first. Recorded so nobody discovers it under pressure.

## 5. APIs

| Endpoint | Notes |
|---|---|
| `GET /api/v1/brands` | pagination (`limit` clamped to 100), `q`, `country`, `sort`; fixtures sort last |
| `GET /api/v1/brands/{slug}` | brand + its catalogue; **404 not 403** for a hidden brand |
| `GET /api/v1/admin/brands` | internal inspection, behind the admin session |

`GET /api/v1/catalog/products` and `/{slug}` are **purely additive** — `brand`,
`commerce_route`, `commerce_action` and `availability` were added and **no existing key
changed**. `test_product_payload_is_purely_additive` pins the pre-phase key set transcribed
from `be1d1e2`, so the admin client, the Android preview and the accepted consumer build keep
working.

### What a consumer is never told

`ownership_type` is an internal accountability concept. Consumers receive
`relationship_label` instead — `DEDUNET`, `Brand-managed`, `External brand` — none of which
claims a partnership, agreement, authorisation or integration, because none exists. The
merchant organisation behind a brand is **never serialised** to a consumer; leaking it would
hand every visitor a tenant enumeration. Both are asserted by tests, including one that scans
the rendered page for the enum strings.

### Availability is a confidence, never a fact

There is no `IN_STOCK`. `availability_confidence` is one of `UNKNOWN`,
`REPORTED_AVAILABLE`, `REPORTED_UNAVAILABLE`, `VERIFIED_AVAILABLE`, and the payload carries
an explicit `is_fact` that is true only for the last. Nothing in this catalogue sets it.

## 6. Commerce action contract

One server-side decision, rendered by every client. The platform already learned this once:
`apps/web` computed a purchase gate in the browser, the API computed its own, and the page
offered a purchase the server refused with a 409.

| Route | Customer sees | State today |
|---|---|---|
| `NON_PURCHASABLE` | Not available to buy | every DEDUNET prototype |
| `EXTERNAL` | Buy from {Brand} | implemented, no data uses it |
| `REFERRAL` | View at {Brand} | implemented, no data uses it |
| `HOSTED` | — | **declarable but refused**: no merchant commerce exists |

`HOSTED` is deliberately unreachable. An enum value is not a feature, and there is no seller,
settlement or fulfilment behind a hosted sale for a brand the platform does not own.

The consumer product page combines the server action with the **accepted** client gate
one-directionally: the control is disabled if *either* refuses. That makes the change
incapable of being more permissive than the human-verified behaviour it inherits.

## 7. External link safety

A new attack boundary: the first place a URL supplied by *data* reaches an anchor a customer
clicks.

- **Allow-list, not deny-list** — `https` only. A deny-list of "javascript, data, file"
  misses `vbscript:`, `blob:` and whatever ships next.
- Validated at **write time**, so bad data cannot enter a row — render-time validation is one
  forgotten call site away from an exploit.
- `http://` is refused too: a buy link downgraded to cleartext is one a network attacker can
  rewrite.
- Protocol-relative `//evil.example` refused — no scheme to verify.
- Outbound links carry `rel="noopener noreferrer nofollow"` and `target="_blank"`, decided by
  the server. Without `noopener` the opened page can navigate the customer's tab (reverse
  tabnabbing).
- A route promising a destination with an unusable URL is **refused outright**, not rendered
  as a dead button.

13 rejection cases and 3 acceptance cases are parametrised in `test_multi_brand_network.py`.

## 8. Consumer integration

The locked foundation was **not** redesigned. No router, design system, navigation or Home
layout change. What changed is where brand data comes from.

| Surface | Before | After |
|---|---|---|
| Brands page | hardcoded array of 2 | `/api/v1/brands`, with real product counts |
| Brand detail | `brandBySlug` over that array | `/api/v1/brands/{slug}` with loading / 404 / error / empty states |
| Home brand rail | same array | same cards, real data |
| Product page | hardcoded link to `/brand/dedunet` | follows the product's own brand |
| Shop | every card labelled "DEDUNET" | real attribution + a brand filter (shown only when there is a choice) |

**A partnership claim was removed.** `commerceRouteLabel("REFERRAL")` returned *"Available
through a partner"* — a partnership that has never existed, sitting in a switch statement in
the browser bundle. The whole client-side enum-to-copy translation went with it: the server
now supplies `relationship_label`, so there is one vocabulary in one auditable place.

The development fixture is labelled on every surface it appears on — a badge on the card, a
mark on the Home rail, and a **sentence** under the heading on its own page, because a badge
can be cropped out of a screenshot.

## 9. Admin

`GET /api/v1/admin/brands` gives an internal operator what a consumer is deliberately denied:
raw `ownership_type`, the merchant organisation behind a merchant-owned brand, the fixture
flag, provenance, product count and the commerce routes actually in use.

**Read-only, and the admin portal UI is not extended.** Reassigning brand ownership needs the
audited write path Phase 5 builds; shipping a mutation without it would be the merchant SaaS
starting early. Scoped to inspection deliberately.

## 10. Verification

| Check | Result |
|---|---|
| Browser E2E vs deployed `:13080` | **462 passed, 0 failed, 21.5m** — Chromium 154, WebKit 154, Mobile Safari viewport 154 (was 143 each) |
| — new brand E2E | 11 per engine |
| Firefox | **NOT RUN** — cannot launch in this environment. Not claimed |
| Backend `pytest -q` | **657 passed, 2 skipped** (was 594) |
| — multi-brand domain | 43 |
| — brand API + compatibility | 18 |
| Consumer unit tests | 13 passed |
| Migration integrity | before ≡ after, checksum identical |
| Rollback | exercised: downgrade + re-upgrade reconstructs exactly |
| Ownership invariants on staging | 0 violations, 0 orphan products |

### Deployed verification, staging `http://10.0.0.2:13080/`

| Check | Result |
|---|---|
| `/api/v1/brands` | 2 brands, correct counts, fixture flagged |
| `/api/v1/brands/dedunet` | 5 products, provenance "Written by DEDUNET" |
| Brands page | renders both, **no enum leak**, no partnership claim, 0 broken images |
| Brand detail | h1 DEDUNET, 5 product cards, badges correct |
| Product page | **€72.00**, `NOT AVAILABLE TO BUY` disabled, brand link → `/brand/dedunet` |
| Outbound link on a non-purchasable product | **none rendered** |
| Commerce mode | `BRAND_PREVIEW_MODE`, `purchasable: false` |

## 11. Security — unchanged and re-verified

The repaired header contract, same-origin `/api`, preview commerce safety, auth/session
behaviour, rate limiting and XSS protections are all untouched. No change was made to the
media rate-limit architecture, the trusted-proxy model, the distributed limiter, TLS or cloud
deployment — those remain open and recorded.

## 12. Known limitations

- **No real external brand integration exists.** `EXTERNAL` and `REFERRAL` are implemented
  and tested but **no data uses them**; nothing here is a partnership, an integration or an
  agreement. `LEGAL_CLEARANCE_PENDING` is unchanged.
- **`HOSTED` is not reachable.** Declarable only, until merchant commerce exists.
- **`MerchantOrganization` is a stub** — the tenant root with no billing, plans,
  entitlements, seats or portal. Phase 5.
- **No brand sync exists.** `last_checked_at` / `last_synced_at` are modelled and never
  written, because nothing checks or syncs anything yet. They are null, not stale.
- **Admin is read-only** and the portal UI is not extended.
- The ownership biconditional is enforced by application code plus a sweep, not by a database
  trigger; `brand_id UNIQUE` covers the "at most one" half in the database.
- Firefox still cannot launch in this environment.
