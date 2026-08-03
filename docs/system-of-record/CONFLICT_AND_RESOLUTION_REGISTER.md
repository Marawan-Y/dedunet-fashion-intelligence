# Conflict and Resolution Register

| Control | Value |
|---|---|
| Artifact ID | SOR-CONF-001 |
| Version | 1.0 |
| Owner | Technical lead |
| Status | SELF-VALIDATED |
| Rule | No material contradiction is resolved silently. Each carries a proposed resolution and an approval state. |

Resolution follows the source-of-truth hierarchy in the human manager approval, §4.

---

## CONFLICT-001 — Git repository root sits above the active project boundary

**Files:** `C:\Users\User\Desktop\Claude\.git`, `Fashion_Commerce_Codex_Multi_Agent_Pack/`,
`Fashion_Commerce_Two_Agent_Execution_Pack/`

**Conflicting values:** §1 names `Fashion_Commerce_Codex_Multi_Agent_Pack` as the only active
project root and forbids executing against `Fashion_Commerce_Two_Agent_Execution_Pack`. §10's
target tree implies the active project *is* the repository root. In fact the Git root is the
**parent** directory and tracks both packs; all four existing commits span that wider root.

**Affected systems:** version control, history preservation, `git mv`, CI checkout paths, release
packaging.

**Proposed resolution:** Keep the existing Git root. Perform all restructuring with `git mv`
inside `Fashion_Commerce_Codex_Multi_Agent_Pack/` only. Treat the sibling pack as untouched
read-only legacy. Do **not** re-initialise a repository inside the active project.

**Reason:** §12 requires history preservation via `git mv`. Re-initialising would discard all four
commits, including the verified baseline this work depends on. Nothing in the sibling pack is read
or written by the active project.

**Risk:** Low. A future extraction to a standalone repository is a separate, clean operation
(`git subtree split`) and is not needed now. Residual risk is cosmetic: the repository contains a
directory the boundary rule says to ignore.

**Owner:** Marawan Younis (secrets and infrastructure)
**Approval status:** PROPOSED — proceeding under the boundary rule; reversible.

---

## CONFLICT-002 — Duplicate source archive inside the active project

**Files:** `platform/poc.zip` (untracked, 143,201 bytes, sha256 `c15c4985…f45a6b`)

**Conflicting values:** §21 requires duplicate source archives to be removed; §9.3 forbids
discarding files blindly.

**Affected systems:** repository hygiene, "no duplicate active source trees".

**Proposed resolution:** Delete. Verified first by content comparison: **71 of 71 files are
byte-identical to the live `platform/poc` tree; 0 differ; 0 exist only in the archive.** It
carries nothing unique.

**Reason:** It is a stale snapshot of the live tree, was never tracked by Git, and is exactly the
"duplicate source archive" §21 names.

**Risk:** None. Content is fully reproducible from the working tree and from Git history.

**Owner:** Technical lead
**Approval status:** RESOLVED — safe to delete, verified duplicate.

---

## CONFLICT-003 — Domain ownership evidence contains personal data

**Files:** `evidence/governance/domain/dedunet.com_ownership_letter.pdf`

**Conflicting values:** §18 requires the file to be copied into the repository and checked for
"password, API token, recovery code or payment secret" — it contains none, and that check passes.
It does contain the registrant's residential address, personal phone number and personal email,
repeated four times.

**Affected systems:** repository privacy posture, any future remote or release package.

**Proposed resolution:** Store as instructed and record the checksum. Do **not** redact
unilaterally. Flag for the owner with two options: keep in full while the repository stays
private, or substitute a redacted copy retaining domain, registrar, IANA number, dates,
registrant name and name servers, with the unredacted original held outside version control.

**Reason:** The instruction is explicit and the data is the owner's own. Altering evidence without
instruction would damage its evidentiary value. Silently committing personal data without saying
so would be worse.

**Risk:** Low today — no remote exists. Rises immediately if a remote is added or a release
package is published.

**Owner:** Marawan Younis (secrets and infrastructure)
**Approval status:** OPEN — awaiting owner decision. Not blocking.

---

## CONFLICT-004 — Side A prices are decimal major units; the platform is integer minor units

**Files:** `handoffs/incoming/side-a/.../data/brand-prototype/product-master.json`
(`prototype_price_eur: 72`), `variant-master.csv` (`price_eur: 72`),
`services/commerce-api/app/money.py`, DEC-010.

**Conflicting values:** `72` (EUR major) versus `7200` (integer minor units).

**Affected systems:** product import, pricing, checkout, order totals.

**Proposed resolution:** Convert during import via the existing `to_minor_units()`, which accepts
`int`/`str`/`Decimal` and **rejects binary floats**. Never parse a price through `float`. The
incoming package stays unmodified; conversion happens in the importer.

**Reason:** §16 mandates integer minor units; `money.py` already enforces exact conversion or
failure. `72 → 7200` is exact.

**Risk:** Low, provided no `float()` appears on the path. Guarded by existing money tests and a
new importer test.

**Owner:** Ahmed Younis (inventory and financial integrity)
**Approval status:** RESOLVED — deterministic conversion.

---

## CONFLICT-005 — Variants are not inline in the product master

**Files:** `product-master.json` (5 products, `variants: []` on every one),
`variant-master.csv` (62 rows).

**Conflicting values:** The JSON implies a nested model; the authoritative variant data is a
separate flat CSV keyed by `product_id`.

**Affected systems:** product import, SKU uniqueness, inventory seeding.

**Proposed resolution:** Treat `variant-master.csv` as authoritative for variants and join on
`product_id`. Verified: 62 rows, 62 unique SKUs, zero duplicates, zero orphans
(18/18/12/12/2 across the five products).

**Reason:** The CSV is complete and internally consistent; the empty JSON arrays are a
serialisation choice, not missing data.

**Risk:** Low. A naive importer reading only the JSON would silently create five products with no
purchasable variants — the importer must fail loudly if the join yields zero variants.

**Owner:** Technical lead
**Approval status:** RESOLVED.

---

## CONFLICT-006 — Side A origin wording versus the mandated origin state

**Files:** `product-master.json` (`origin: "Intended Egypt production; factory and
country-of-origin evidence pending."`), human approval §16.

**Conflicting values:** Prose intent versus the required typed state
`country_of_origin = XX`, `intended_origin = EG`, `origin_claim_status = UNVERIFIED`.

**Affected systems:** product schema, storefront display, AI grounding, claim gating.

**Proposed resolution:** Import Side A's prose into a non-authoritative descriptive field and set
the typed fields to the mandated values. `XX` is an intentionally invalid ISO code so it cannot be
mistaken for a substantiated origin. Never render "Made in Egypt" as verified.

**Reason:** §16 is higher in the hierarchy than the Side A delivery. Side A's own wording already
says evidence is pending, so the two are aligned in intent.

**Risk:** Low. Highest-consequence failure would be publishing an unverified origin claim; the
typed state plus display gating prevents it.

**Owner:** Aya Ashraf (brand claims and naming risk)
**Approval status:** RESOLVED.

---

## CONFLICT-007 — Single-image model versus multi-media delivery

**Files:** `product-master.json` (`imagery: [FRONT, BACK, DETAIL, LIFESTYLE]`),
`asset-register.csv` (31 assets), current `Product.image_url` single column.

**Conflicting values:** Four-plus media records per product versus one `image_url` string.

**Affected systems:** product schema, storefront PDP, mobile, admin, migrations.

**Proposed resolution:** Add a `product_media` table with `role` (front/back/detail/lifestyle/
campaign/collection) and ordering. Retain `image_url` temporarily as a derived primary-image
convenience, marked non-authoritative, then remove it once all consumers read `product_media`.

**Reason:** §16 states the single-image model must not remain the only authoritative
representation. All 31 registered assets exist on disk and all imagery references resolve.

**Risk:** Medium — a schema change touching web, mobile and admin. Mitigated by keeping the legacy
column during transition and migrating consumers one at a time.

**Owner:** Technical lead
**Approval status:** PROPOSED — scheduled for M7, not R0.

---

## CONFLICT-008 — Legacy MERET brand references in live platform source

**Files:** 19 files, of which 12 are live source; the remainder are runtime artefacts
(`__pycache__`, `commerce.sqlite3`) that are not version-controlled.

**Conflicting values:** Customer-facing MERET identity versus the selected DEDUNET brand.

**Affected systems:** storefront, admin, seed data, tests, docs.

**Proposed resolution:** Controlled migration per §17 via
`docs/side-b/DEDUNET_REBRAND_MIGRATION_REGISTER.md`, classifying every reference before changing
it. **No repository-wide find-and-replace.** Customer-facing values change first; technical
identifiers migrate separately with rollback. Explicitly **not** part of R0, which must be
behaviour-preserving.

**Reason:** §13 forbids brand changes in the restructuring commit; §17 forbids uncontrolled
replacement.

**Risk:** Medium if done carelessly — `MERET` appears in test fixtures and seed constants where a
blind replace would break assertions and demo credentials simultaneously.

**Owner:** Aya Ashraf (brand claims), with technical lead executing
**Approval status:** PROPOSED — scheduled for M7.
