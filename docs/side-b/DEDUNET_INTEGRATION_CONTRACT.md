# DEDUNET Integration Contract

| Control | Value |
|---|---|
| Artifact ID | SB-DDN-001 |
| Version | 1.0 |
| Date | 2026-08-06 |
| Owner | Side B technical lead |
| Status | SELF-VALIDATED |
| Source | `handoffs/incoming/side-a/DEDUNET_Platform_Integration_v1/` (immutable) |
| Consumer | Schema migration, importer, web, admin, mobile, notifications |

Defines how the immutable Side A delivery becomes runtime platform data. Written before any
schema or database change, so the transformation is agreed rather than discovered.

---

## 1. Pipeline

```
handoffs/incoming/side-a/DEDUNET_Platform_Integration_v1/   IMMUTABLE, read-only
    -> scripts/validation/verify_side_a_package.py          integrity gate
    -> scripts/brand/build_brand_package.py                 validation + normalization
    -> packages/brand/                                      GENERATED, committed
    -> scripts/import/import_dedunet.py                     transactional importer
    -> database
    -> web, admin, mobile, notification consumers
```

**No application reads `handoffs/incoming/` at runtime.** Two reasons, both already
demonstrated in this repository: the handoff is checksum-protected evidence whose bytes a
consumer must not touch (`.gitattributes` already had to be re-scoped to stop Git rewriting
them), and Side A's shapes are business artefacts — decimal prices, prose origin, flat CSVs —
while the platform contract is integer minor units and typed states. Normalising once means
exactly one place performs that transformation.

`packages/brand/` is generated and committed. Committed so a consumer build needs no Side A
access and so the diff is reviewable; generated so it can never drift from its source
undetected.

---

## 2. Verified source facts

Established by `scripts/validation/verify_side_a_package.py`, exit 0:

| Fact | Value |
|---|---|
| Checksums | 54/54, 0 missing, 0 mismatched, 0 unmanifested files |
| Products | 5 |
| Variants | 62 |
| Unique SKUs | 62 |
| Registered assets | 31, all present on disk |
| JSON files | 5, all parse |
| SVG files | 31, all parse as XML |
| MERET/MERYT inside the package | 0 |
| Product identifiers | `DDN-TS01`, `DDN-SH01`, `DDN-TR01`, `DDN-OS01`, `DDN-SC01` |
| Variants per product | TS01 18, SH01 18, TR01 12, OS01 12, SC01 2 |
| Orphan variants | 0 |
| Duplicate option combinations | 0 |

---

## 3. Identity

`product_id` (`DDN-TS01` …) is the stable external identity and maps to
**`products.external_product_id`**, unique and immutable. `variant_id`
(`DDN-TS01-CAR-XS` …) maps to **`variants.external_variant_id`**, unique and immutable.

Array position, filename and database insertion order are **never** identity. The internal
integer primary key remains, because orders and cart lines already reference it; it is a
storage detail, not identity.

The importer matches on the external identifier. That is what makes it idempotent and what
prevents a re-run creating a second copy of every product.

---

## 4. Money

Side A carries EUR **major** units (`72`, `74`, `122`, `142`, `192`). The platform stores
integer **minor** units.

Conversion delegates to `app.money.to_minor_units`, which accepts `int`/`str`/`Decimal` and
**rejects binary floats outright**. The importer adds two refusals of its own:

- more than 2 decimal places for EUR — the source contract has no sub-cent prices, so a third
  decimal means the input is wrong, not that it should be rounded away;
- any non-positive result.

A float is refused rather than rounded because `72.00` arriving as `71.99999999999999` must
never become `7199`.

Verified conversions:

```text
72  -> 7200      74  -> 7400      122 -> 12200
142 -> 14200     192 -> 19200
```

Side A's decimal field is retained as `source_price_eur`, explicitly **non-authoritative**.

---

## 5. Typed states

Prose is not a state. Every field below is typed and separately consumable by API, admin, web
and mobile.

| Field | Import value | Meaning |
|---|---|---|
| `publication_status` | `preview` | Visible, not purchasable |
| `sellable` | `false` | Purchase refused regardless of price |
| `inventory_status` | `prototype_unavailable` | Not stock-managed |
| `evidence_status` | `DRAFT` | Supplier documents, samples, tests pending |
| `material_claim_status` | `UNVERIFIED` | Composition stated, not tested |
| `origin_claim_status` | `UNVERIFIED` | No documentary production evidence |
| `legal_brand_status` | `LEGAL_CLEARANCE_PENDING` | Naming risk open |
| `media_status` | `PROTOTYPE_CONCEPT` | Concept art, not product photography |

Side A's prose (`origin`, `intended_material`, `evidence_status` sentences) is preserved in
`source_*` fields as context, never as authority.

---

## 6. Origin

```text
country_of_origin   = XX          deliberately invalid ISO code
intended_origin     = EG
origin_claim_status = UNVERIFIED
```

`XX` cannot be mistaken for a substantiated origin. **"Made in Egypt" is never rendered as a
verified claim**, and intended production is never converted into actual origin. Web and
mobile suppress the public origin sentence entirely while `origin_claim_status` is
`UNVERIFIED`; the mobile client already enforces this in `src/origin.ts` and is guarded by a
test asserting no input can produce the substring "made in".

---

## 7. Media

`products.image_url` is retained as a derived, **non-authoritative** convenience for legacy
consumers and is not the model. Media lives in a `product_media` table:

| Column | Notes |
|---|---|
| `external_product_id` | owner |
| `asset_id` | Side A asset identity, e.g. `DDN-TS01-FRONT` |
| `role` | `front` `back` `detail` `lifestyle` `campaign` `collection` |
| `sort_order` | deterministic; role order then asset id |
| `path` | package-relative |
| `alt_text`, `status`, `sha256` | from the asset register |

18 product-media records normalize from the 31 registered assets; the remaining 13 are
brand-level (logos, favicon, app icon, pattern, hero, email, social). Only TS01, TR01 and
OS01 carry a `lifestyle` asset — SH01 and SC01 have three each, which is the source data, not
a gap.

Uniqueness is enforced on `(product_id, asset_id)` and on `(product_id, role, sort_order)`, so
a duplicate media relationship is rejected rather than producing a doubled gallery.

**Concept SVGs remain prototype media** and must never be presented as final product
photography. `media_status = PROTOTYPE_CONCEPT` carries that, and every asset is marked
`human_review_required`.

---

## 8. Inventory

All 62 imported variants: `stock_quantity = 0`, `sellable = false`,
`inventory_status = prototype_unavailable`.

The importer **refuses** a non-zero prototype stock rather than silently zeroing it — a
source that suddenly carries stock is a change to be reviewed, not normalised away. Having a
price does not make a product purchasable; `sellable` does, and it is `false`.

---

## 9. Commerce modes

| Mode | Products visible | Stock | Checkout | Payment |
|---|---|---|---|---|
| `BRAND_PREVIEW_MODE` | yes | 0 | **blocked** | never called |
| `COMMERCE_TEST_MODE` | yes | explicit synthetic only | sandbox | sandbox only |
| `PUBLIC_COMMERCE_MODE` | — | — | **blocked** | — |

`PUBLIC_COMMERCE_MODE` is refused at configuration load. There is deliberately **no
configuration value that can enable public commerce**; enabling it requires a code change plus
the existing activation gate, so no environment variable can turn a prototype into a shop.

Synthetic stock belongs only to `COMMERCE_TEST_MODE` and must not leak into preview.

---

## 10. Schema gaps identified

| Gap | Resolution |
|---|---|
| No stable external identity on `products` / `variants` | add `external_product_id`, `external_variant_id`, both unique |
| Single `image_url` cannot hold 4 media roles | add `product_media` table (CONFLICT-007) |
| No typed evidence or publication states | add the eight fields in §5 |
| No `intended_origin` | add; `country_of_origin` stays `XX` |
| Variant carries no inventory/evidence state | add `inventory_status`, `evidence_status`, `sellable` |
| No collection entity | `collection_id` on product; collection data ships in `packages/brand/` |
| No commerce mode | add `COMMERCE_MODE` setting, default `BRAND_PREVIEW_MODE` |

---

## 11. Migration plan

One Alembic revision, additive only:

- new columns are nullable or carry server defaults, so an existing populated database
  upgrades without rewriting rows;
- `product_media` is a new table;
- unique indexes on `external_product_id`, `external_variant_id`, and the two media pairs;
- downgrade drops exactly what upgrade added.

**Reversibility is proven by executing `upgrade → downgrade → upgrade` on PostgreSQL**, not by
asserting it. No existing column is dropped, renamed or retyped, so no data migration is
required and the legacy MERET seed continues to load unchanged.

---

## 12. Importer contract

Dry run · validate before writing · single transaction · idempotent on external identifiers ·
updates approved mutable fields · never duplicates products, variants or media · never
silently deletes · reports conflicts explicitly · rejects invalid money, orphan variants,
missing assets and duplicate SKUs · preserves immutable external identifiers · emits
machine-readable output.

---

## 13. Out of scope

The branded end-to-end purchase journey, Apple/Google distribution, real payment activation,
external SMTP, hosted cloud deployment and public commerce all remain out of scope and
blocked. Workstream F's statuses are preserved unchanged:
`EAS_PROJECT_CONFIGURATION_VERIFIED`, `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`.
