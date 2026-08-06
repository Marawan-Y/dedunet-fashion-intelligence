# DEDUNET Platform Integration — Evidence

| Control | Value |
|---|---|
| Artifact ID | EV-DDN-001 |
| Version | 1.0 |
| Date | 2026-08-06 |
| Owner | Side B technical lead |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| Milestones | I1 → I5 complete |
| Preserved | `EAS_PROJECT_CONFIGURATION_VERIFIED` · `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` |
| **Decision** | **`DEDUNET_INTEGRATION_CONDITIONALLY_VERIFIED`** |

Conditional for one reason, stated up front: **the web and admin browser clients still show
the legacy MERET brand chrome**. That is a deliberate, recorded deferral (see §14), not an
oversight — but it means the integration is not visually complete, and calling it fully
verified would overstate it.

Everything else executed and matched exactly. Public commercial launch remains **BLOCKED**.

---

## 1. Commit confirmation

Captured before any integration file was changed.

```text
git branch --show-current   dedunet/repository-restructure-and-workstreams-a-f
git rev-parse HEAD          02a5796ce820c40c4e87fcf5938deb2f617fc60e
git status --short          (empty)
git status --porcelain -uall   0 lines
```

| Item | Commit |
|---|---|
| Successor-agent takeover documentation | **`577cace`** |
| Workstream F implementation | **`02a5796`** |

Confirmed at that point: working tree clean · HEAD contained Workstream F
(`git merge-base --is-ancestor` returned 0) · no DEDUNET integration started
(`packages/brand`, `scripts/import`, `evidence/dedunet-integration` and the rebrand register
all absent) · no untracked build output and **0** tracked credential-shaped files.

The five `brand-prototype` references outside the handoff were checked individually: all are
documentation, comments or the mobile guard test that asserts no import exists.

---

## 2. Side A integrity — `DEDUNET_HANDOFF_INTEGRITY_VERIFIED`

`scripts/validation/verify_side_a_package.py`, exit 0. Every value asserted **exactly**; the
script is read-only and never repairs the package.

| Check | Result |
|---|---|
| Manifest entries | 54 |
| Checksums verified | **54/54**, 0 missing, 0 mismatched |
| Unmanifested files | **0** |
| Products | **5** |
| Variants | **62** |
| Unique SKUs | **62** |
| Registered assets | **31**, all present on disk |
| Asset identifiers unique | yes |
| JSON files parse | 5/5 |
| SVG files parse as XML | 31/31 |
| Product identifiers | `DDN-TS01` `DDN-SH01` `DDN-TR01` `DDN-OS01` `DDN-SC01` |
| Orphan variants | **0** |
| Duplicate option combinations | **0** |
| MERET/MERYT inside the package | **0** |

Variants per product: TS01 18, SH01 18, TR01 12, OS01 12, SC01 2 = **62**.

Re-verified after all work: still `DEDUNET_HANDOFF_INTEGRITY_VERIFIED`, and
`git status -- handoffs/` is empty. **The immutable delivery was never modified.**

---

## 3. Normalization design and files generated

```
handoffs/incoming/side-a/DEDUNET_Platform_Integration_v1/   IMMUTABLE
  -> scripts/validation/verify_side_a_package.py            integrity gate
  -> scripts/brand/build_brand_package.py                   validate + normalize
  -> packages/brand/                                        GENERATED, committed
  -> scripts/import/import_dedunet.py                       transactional importer
  -> database -> web, admin, mobile, notifications
```

No application reads `handoffs/incoming/` at runtime. The handoff is checksum-protected
evidence whose bytes a consumer must not touch — `.gitattributes` already had to be re-scoped
once to stop Git rewriting them — and Side A ships business shapes (decimal prices, prose
origin, flat CSVs) where the platform contract is integer minor units and typed states.

Generated (13 files):

| File | Contents |
|---|---|
| `brand.json` | name, domain, tagline, four status fields, naming risk, prohibited narrative |
| `tokens.json` | colours, typography, shape, spacing, imagery, motion, flattened CSS variables |
| `tokens.css` | `:root` custom properties, all `--ddn-*` |
| `products.json` | 5, typed states, integer minor units |
| `variants.json` | 62 |
| `product-media.json` | 18, typed roles, deterministic order |
| `assets.json` | 31, with SHA-256 and byte size |
| `collections.json` | First Passage |
| `navigation.json`, `content.json`, `fonts.json` | passed through, validated |
| `NORMALIZATION_REPORT.json` | machine-readable: counts, conversions, states, roles |
| `README.md` | marks the directory generated |

`--check` re-verifies without writing; run again after all work: `NORMALIZATION_VERIFIED`.

---

## 4. Schema changes

Revision **`e4b7a91c2d55`**, additive only.

**products** — `external_product_id` (unique), `collection_id`, `intended_origin`,
`publication_status`, `sellable`, `inventory_status`, `evidence_status`,
`material_claim_status`, `origin_claim_status`, `legal_brand_status`, `media_status`.

**variants** — `external_variant_id` (unique), `sellable`, `inventory_status`,
`evidence_status`.

**product_media** (new) — `product_id`, `asset_id`, `role`, `sort_order`, `path`, `alt_text`,
`status`, `checksum_sha256`.

Two unique constraints, not one: `(product_id, asset_id)` stops an asset attaching twice;
`(product_id, role, sort_order)` stops two assets claiming one slot, which would make gallery
order depend on row order. Plus check constraints on `sort_order >= 0` and the role
vocabulary.

`sellable` **fails closed**. A row created without thinking is not purchasable. The seed and
the admin endpoint opt in explicitly, and the migration backfills pre-existing rows to
`is_active` — a fail-closed default is right for new rows and wrong for existing ones.

**A portability defect caught before it shipped.** The boolean default was first written as
`sa.text("0")`. PostgreSQL rejects an integer default on a boolean column, so that would have
upgraded cleanly on SQLite and failed on the runtime database. Changed to `sa.false()`.

---

## 5. Migration verification — PostgreSQL, executed

| Step | Result |
|---|---|
| Clean database upgrade | 4 revisions applied, 19 tables |
| Populated upgrade (rows created at the PREVIOUS revision via raw SQL) | applied, exit 0 |
| Backfill on previously-populated rows | `legacy-active` → `sellable=t`, `published`; `legacy-draft` → `f`, `draft`; variants inherited |
| Constraints | `uq_product_media_asset`, `uq_product_media_slot`, `ck_product_media_role`, `ck_product_media_sort_order`, FK, PK |
| Indexes | `ix_products_external_product_id`, `ix_variants_external_variant_id`, `ix_product_media_product_id`, `ix_product_media_asset_id` |
| **Downgrade EXECUTED** | `product_media` dropped, every added column dropped, **data preserved** (2 products, 2 variants) |
| Re-upgrade | head restored, backfill still correct |

**Reversibility is claimed only because downgrade was run.**

### A measurement error worth recording

The first populated-upgrade attempt appeared to succeed and then reported
`column "sellable" does not exist`. Two causes, both mine:

1. `manage.py seed` was run against a database at the *old* revision. It calls `create_all`,
   which pre-created `product_media` from the current ORM, so the migration then hit
   `DuplicateTable`.
2. I had piped alembic through `grep 'Running upgrade'`, which **discarded the traceback**.
   The run looked successful while it had failed.

Re-run unfiltered, the cause was visible immediately. This is the fourth measurement-level
false pass recorded in this project, and the reason the populated-upgrade test now populates
with raw SQL rather than the ORM.

---

## 6. Importer

`scripts/import/import_dedunet.py` — dry run, validate-before-write, one transaction,
idempotent on external identity, machine-readable output.

### Dry run (wrote nothing)

```json
{"scope":"ALL","planned":{"products":5,"variants":62,"media":18},
 "created":{"products":5,"variants":62,"media":18},
 "conflicts":[],"errors":[],"outcome":"DRY_RUN_OK"}
```

Database still held **0** DEDUNET products afterwards. The dry run opens a read-only session
and rolls back, so it reports what *would* change rather than echoing the file.

### Refusals implemented and tested

Invalid money · orphan variants · duplicate SKUs · duplicate `external_variant_id` ·
duplicate media relationships · duplicate media slots · missing asset files · non-zero
prototype stock · a slug or SKU already owned by a **different** external id.

**Never silently deletes.** A record present in the database but absent from the package is
reported in `orphans_in_database`, not removed — deleting a product would take its order
history's referential integrity with it.

---

## 7. I3 — DDN-TS01 hero product

```json
{"scope":"DDN-TS01","created":{"products":1,"variants":18,"media":4,"inventory":18},
 "conflicts":[],"errors":[],"outcome":"IMPORTED"}
```

| Check | Result |
|---|---|
| Product | `DDN-TS01` / `the-source-tee` |
| `is_active` / `sellable` | `true` / **`false`** — visible, not purchasable |
| States | `preview` · `DRAFT` · `UNVERIFIED` · `XX` · `EG` · `LEGAL_CLEARANCE_PENDING` · `PROTOTYPE_CONCEPT` |
| Variants | 18 |
| Money | 72 EUR major → **7200** minor |
| Media | 4, ordered `front`(0) `back`(1) `detail`(2) `lifestyle`(3) |
| Inventory | 18 rows, **total stock 0** |
| Idempotency | re-run: created 0, updated 18, counts unchanged |
| Preview-mode block | `POST /cart/items` → **409** "this catalogue is in brand preview; nothing is available to purchase" |

API payload verified to carry `external_product_id`, all eight typed states, `intended_origin`
and the ordered `media` array.

---

## 8. I4 — complete catalogue

```json
{"scope":"ALL","created":{"products":4,"variants":44,"media":14,"inventory":44},
 "updated":{"products":1,"variants":18,"media":4},
 "conflicts":[],"orphans_in_database":[],"errors":[],"outcome":"IMPORTED"}
```

Counts read back from the **database**, not the source file:

```text
products      = 5
variants      = 62
unique skus   = 62
product_media = 18
total stock   = 0
sellable      = 0
```

| External id | Slug | Variants | Media | Price (minor) |
|---|---|---|---|---|
| DDN-TS01 | the-source-tee | 18 | 4 | 7200 |
| DDN-SH01 | the-passage-shirt | 18 | 3 | 12200 |
| DDN-TR01 | the-measure-trouser | 12 | 4 | 14200 |
| DDN-OS01 | the-structure-overshirt | 12 | 4 | 19200 |
| DDN-SC01 | the-trace-scarf | 2 | 3 | 7400 |

SH01 and SC01 carry three media because Side A ships no lifestyle asset for them. That is the
source data; the importer does not invent one. 18 product media + 13 brand-level assets = the
31 registered.

**Full idempotency**: re-running the entire import created 0 products, 0 variants, 0 media;
counts unchanged at 5/62/18.

---

## 9. Money

Deterministic conversion delegating to `app.money.to_minor_units`, which rejects binary
floats, plus two refusals of its own: more than two decimals for EUR, and any non-positive
result.

| Source | Minor units |
|---|---|
| `72` / `72.00` | 7200 |
| `74` | 7400 |
| `122` | 12200 |
| `142` | 14200 |
| `192` | 19200 |
| `0.01` | 1 |
| `72.50` | 7250 |

Refused: `72.00` as a **binary float**, `0.1+0.2`, `72.001` (3 decimals), `""`, `"abc"`,
`"-5"`, `"7,2"`, `None`, `"1e3"`.

A float is refused rather than rounded because `72.00` arriving as `71.99999999999999` must
never become `7199`. Side A's decimal survives only as `source_price_eur`, a **string**, so
no float can become authoritative.

**Load-bearing proven**: mutations M53 and M54 remove the float and decimal refusals; both are
detected.

---

## 10. Media

18 records, roles from the Side A asset-id suffix, `sort_order` assigned by role order then
asset id — deterministic across builds.

Validated: file exists · belongs to a valid product · role in the allowed vocabulary ·
order deterministic and starting at 0 · duplicate relationship rejected (database constraint,
test-proven) · duplicate slot rejected · invalid role rejected.

All 18 carry `status = PROTOTYPE_CONCEPT`. Concept SVGs are **never** presented as product
photography — web, mobile and the disclaimer copy all say so explicitly.

---

## 11. Evidence states and origin

Every imported product: `publication_status=preview`, `sellable=false`,
`inventory_status=prototype_unavailable`, `evidence_status=DRAFT`,
`material_claim_status=UNVERIFIED`, `origin_claim_status=UNVERIFIED`,
`legal_brand_status=LEGAL_CLEARANCE_PENDING`, `media_status=PROTOTYPE_CONCEPT`.

Origin: `country_of_origin=XX`, `intended_origin=EG`, `origin_claim_status=UNVERIFIED`.

**No surface renders "Made in".** Asserted three ways: the normalized package contains no
such string; the API response contains none; and `originStatement()` is exhaustively tested
across every combination of country code, claim status and intended origin.

`origin_claim_status` and `intended_origin` must be read **together**. Reading
`intended_origin` alone would render "EG" as a factual origin — the conversion of intent into
fact CONFLICT-006 forbids. Reading `country_of_origin` alone would show a customer the literal
placeholder `XX`, which the web client previously did.

The approved narrative is preserved: Dedun/Dedwen credited as **a Nubian deity documented in
Egyptian sources**, with Side A's own disclaimer that DEDUNET does not claim to be an ancient
textile-goddess name. Domain ownership is recorded as **not** trademark clearance.

---

## 12. Commerce modes

| Mode | Behaviour verified |
|---|---|
| `BRAND_PREVIEW_MODE` | products visible, stock 0, not sellable, **cart add → 409**, no payment call |
| `COMMERCE_TEST_MODE` | legacy sandbox commerce works; DEDUNET prototypes **still blocked** by `sellable=false` |
| `PUBLIC_COMMERCE_MODE` | **refused at configuration load** |

```text
COMMERCE_MODE=PUBLIC_COMMERCE_MODE -> CommerceModeError:
  "PUBLIC_COMMERCE_MODE cannot be enabled by configuration. Public commercial launch is
   BLOCKED: brand legal clearance is pending and product origin, material and evidence
   states are UNVERIFIED."
public_commerce_enabled() -> False
COMMERCE_MODE=YOLO_MODE -> refused
```

There is **no configuration value that enables public commerce.** Two independent gates: the
mode blocks every purchase in preview whatever the product says; `sellable` blocks a prototype
in any mode. Both run at the **cart boundary** and again **before the payment gateway is
contacted**, so a blocked purchase makes no payment call at all.

Refusing only at checkout would imply the item was purchasable right up to payment.

---

## 13. Consumer surfaces

| Surface | Result |
|---|---|
| **API** | ships `external_product_id`, all typed states, `intended_origin`, ordered `media`; no "made in" |
| **Mobile** | reads typed states; add button disabled with "Not available to buy"; preview banner; `originStatement` states intended production as a plan. tsc 0, 106 tests, 18/18 mutations |
| **Admin** | prototype rows labelled `[DDN-TS01 · PREVIEW — NOT SELLABLE · evidence DRAFT]` — a priced line with zero stock is otherwise indistinguishable from ordinary sold-out inventory and invites an operator to "fix" it by adding units |
| **Web** | origin sentence suppressed rather than printing `XX`; material marked "(stated, not tested)"; preview banner; prototype disclaimer |
| **Web/admin brand chrome** | **STILL LEGACY** — see §14 |

---

## 14. Controlled rebrand — the conditional

`docs/side-b/DEDUNET_REBRAND_MIGRATION_REGISTER.md` classifies all **29** tracked files
carrying MERET/MERYT: customer-facing, internal identifier, migration-sensitive, historical
evidence, test fixture, obsolete.

**Web and admin chrome is deliberately not rewritten.** The seam came first — the API ships
external identity and typed states, `packages/brand/` holds the normalized identity, tokens,
navigation and copy, and mobile already reads its brand from one guarded module. Rewriting the
chrome without that seam is precisely the uncontrolled replacement CONFLICT-008 forbids.

Explicitly kept: the MERET seed (legacy demo dataset), `MRT-*` SKUs (referenced by
`order_lines`, which are financial records), `*@meret.example` credentials, and database
names. Historical evidence is frozen.

**This is why the decision is `CONDITIONALLY_VERIFIED`.** Anyone opening the storefront today
still sees the legacy brand. It is safe only because public launch is BLOCKED, and it must
close before any branded slice is shown to a third party.

---

## 15. Backup and isolated restore — and a gap this integration created

DEDUNET was imported into the **real staging database** (migrated to head first), then the
existing tooling was run.

**The first rehearsal reported PASS while never checking `product_media` at all.**
`CRITICAL_TABLES` in `backup_manager.py` is an explicit list of 18 — deliberately explicit, so
a table vanishing from a dump is a failure rather than something the comparison quietly skips.
That design is right, and it means a **new** table must be added to the list. My schema change
silently narrowed the backup guarantee.

Fixed, then re-run:

```text
revision      : e4b7a91c2d55
products      : source 6  restored 6   match
variants      : source 63 restored 63  match
product_media : source 18 restored 18  match
result        : PASS      failures: []
```

(6 and 63 include the Workstream D rehearsal fixture alongside the 5/62 DEDUNET records.)

The restore also exercised the guard that refuses a non-empty target without `--force`, which
correctly blocked a re-run until `cleanup` was issued.

---

## 16. Operational parity

| Check | Result |
|---|---|
| Local staging | 4/4 services healthy, `/ready` **200** |
| Notification worker | unaffected; cycles healthy, outbox drained |
| Rate limiting | unaffected — 10×401 then 3×429 on the staging login endpoint |
| Staging DB port | still unpublished; the temporary local forward used for the import was removed |

---

## 17. Regression results

| Check | Result |
|---|---|
| Mobile dependency matrix | `Dependencies are up to date` |
| Mobile TypeScript | exit **0** |
| Mobile tests | **106 passed** |
| Mobile mutations | **18/18 detected, 0 survived** |
| Expo web export | exit 0 |
| SQLite backend suite | **219 passed, 1 skipped** |
| PostgreSQL backend suite | **220 passed** |
| Backend mutation harness | **55 run, 55 detected, 0 survived** |
| OpenAPI drift | **NONE** |
| Side A manifest | **54/54**, handoff untouched |
| Brand package reproducible | `NORMALIZATION_VERIFIED` |
| Secret scan | 0 real values, 0 credential patterns across 327 tracked files |
| Personal-data scan | 0 non-reserved e-mail addresses in new artifacts |
| Backup + isolated restore | PASS, 19/19 tables |

Backend grew from 167/168 to 219/220 — **52 new tests**, no existing test weakened, deleted
or skipped.

### Two guards that were not guards

**M55 survived the first mutation run.** Removing the non-zero-stock refusal from the
normalizer changed nothing, because the zero-stock test reads
`packages/brand/variants.json` — a **committed artifact** the mutation never regenerates. A
test that cannot observe its guard is not a guard. Three tests now exercise the normalizer
directly (non-zero stock refused, orphan refused, duplicate SKU refused) and M55 is detected.

**A test of mine failed for the right reason.** I first asserted the word "goddess" appeared
nowhere in the normalized copy. It does — precisely because Side A's copy *disclaims* the
narrative: "DEDUNET does not claim to be an ancient textile-goddess name". Banning the word
would have forced deleting the sentence that keeps the brand story safe. The guard now asserts
the blocked **claim** is absent and the **disclaimer** is present.

**A fixture that passed only on SQLite.** My API test flushed instead of committing. In-memory
SQLite shares one connection via `StaticPool` so the request session saw the rows; PostgreSQL
gives each session its own connection and returned 404. Fixed by committing, as the existing
`seeded` fixture already does. Caught only because both engines are run.

---

## 18. Known limitations

**Legal and commercial**

- `LEGAL_CLEARANCE_PENDING`. The `DeDeNet` conflict is a disclosed high preliminary risk.
  Domain ownership is not trademark clearance.
- `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED`, and unreachable by configuration.
- No product may be presented as sellable. Prices exist; purchasability does not.
- Material, composition, origin and manufacturing remain evidence-gated. `country_of_origin`
  is `XX` and must stay so until documentary production evidence exists.
- All 31 assets are `human_review_required` and remain concept artwork.

**Technical**

- **Web and admin still show the legacy MERET chrome.** The conditional.
- Notification lifecycle identity is not yet rebranded; `EXTERNAL_SMTP_DELIVERY_PENDING`, so
  no message has ever been sent under either brand.
- `COMMERCE_TEST_MODE` synthetic inventory is *permitted* by design but **no synthetic stock
  loader was built** — no DEDUNET product can be transacted at all today.
- Test orders are not yet flagged as test orders in the data model; that lands with the
  branded slice.
- `packages/brand/` is committed and generated. Nothing yet fails CI if it drifts from the
  handoff; `--check` must be run deliberately.
- Fonts are manifest-only. No font binary ships.
- No DEDUNET product has an `image_url` that a browser can fetch — media paths are
  package-relative and no asset-serving route exists.
- Mobile does not yet render the `media` gallery; it reads the states only.
- `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` — unchanged, no native binary.

---

## 19. Rollback

Additive throughout. To reverse:

```bash
# 1. data
python scripts/import/import_dedunet.py   # (no un-import; delete by external_product_id)
# 2. schema
cd services/commerce-api && python -m alembic downgrade c2f8d1b40e77
# 3. code
git revert --no-edit <integration range>
```

Downgrade has been **executed** and preserves all pre-existing data. Reverting restores the
MERET-only catalogue; the legacy seed was never modified and 167 of the 219 backend tests
predate this work and still pass unchanged.

The importer creates no orphan state: products, variants, media and inventory are written in
one transaction.

---

## 20. Commit range

| Milestone | Commit |
|---|---|
| I1 — validation and contract | `f9b9f5f` |
| I2 — schema and normalized brand package | `eb553ec` |
| I3 — hero product DDN-TS01 | `6111fc5` |
| I4 — complete catalogue + rebrand register | `3aad46f` |
| I5 — restore parity, guards, evidence | this commit |

Range: **`f9b9f5f..HEAD`**, on top of Workstream F `02a5796` and takeover `577cace`.

---

## 21. Decision

**`DEDUNET_INTEGRATION_CONDITIONALLY_VERIFIED`**

The Side A package verified 54/54 and was never modified. 5 products, 62 variants, 62 unique
SKUs and 18 media records imported with exact counts, zero stock and nothing sellable. Money
converts deterministically with binary floats refused. The migration is reversible **because
downgrade was executed**. Three commerce modes behave correctly and public commerce cannot be
switched on. Backup and isolated restore preserve DEDUNET data across 19/19 tables. 219 SQLite
/ 220 PostgreSQL backend tests, 106 mobile tests, 55/55 and 18/18 mutations detected with none
surviving, no OpenAPI drift, clean secret and personal-data scans.

It is **conditional** because the web and admin brand chrome is still MERET. That deferral is
deliberate and recorded, but the integration is not visually complete and should not be
described as such.
