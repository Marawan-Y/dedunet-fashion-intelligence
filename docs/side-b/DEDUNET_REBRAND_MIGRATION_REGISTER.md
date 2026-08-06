# DEDUNET Rebrand Migration Register

| Control | Value |
|---|---|
| Artifact ID | SB-DDN-002 |
| Version | 1.0 |
| Date | 2026-08-06 |
| Owner | Aya Ashraf (brand claims and naming risk), technical lead executing |
| Status | SELF-VALIDATED |
| Resolves | CONFLICT-008 (controlled migration, no repository-wide replacement) |

Every tracked occurrence of `MERET` / `MERYT`, classified before anything is changed.

**No uncontrolled find-and-replace.** `MERET` appears in test fixtures, seed constants and
demo credentials, where a blind replace would break assertions and logins simultaneously —
and in historical evidence, where rewriting it would falsify the record.

Baseline: **29 tracked files**, established with
`git grep -lI -iE '\bMERET\b|\bMERYT\b'`.

---

## Classification

### A — Customer-facing, must change

| File | Occurrences | Disposition |
|---|---|---|
| `apps/web/index.html` | 4 | Page title, meta description, header wordmark, footer |
| `apps/web/app.js` | 3 | Demo-credential hints and copy shown to a shopper |
| `apps/web/styles.css` | 1 | Comment only — cosmetic, low priority |
| `apps/admin/index.html` | 2 | Portal title and header |
| `apps/admin/admin.js` | 2 | Demo-credential hints |
| `apps/admin/styles.css` | 1 | Comment only |

**Status: NOT YET CHANGED.** These surfaces still carry the legacy brand. The change is
deliberately deferred to the branded end-to-end slice, which the manager has not authorised.
What this integration delivered instead is the *seam*: the API now ships `external_product_id`
and the typed states, `packages/brand/` holds the normalized identity, tokens, navigation and
copy, and the mobile client already reads its brand from a single module (`src/brand.ts`).
Rewriting the web and admin chrome without that seam in place would be the uncontrolled
replacement CONFLICT-008 forbids.

### B — Internal technical identifier

| File | Occurrences | Disposition |
|---|---|---|
| `services/commerce-api/app/commerce/seed.py` | 5 | Demo product names, slugs, SKU prefix `MRT-*`, demo e-mail domain |
| `services/commerce-api/manage.py` | 1 | Log line naming the seeded dataset |

The MERET seed is the **legacy demonstration catalogue**, not DEDUNET. It stays. Its SKUs
(`MRT-TEE-BLK-S` …) are referenced by existing orders, cart lines and 215 backend tests.
Renaming them would rewrite financial records that must reconcile.

**Decision:** keep the MERET fixture as an explicitly-labelled legacy demo dataset. DEDUNET
products are distinguished by `external_product_id IS NOT NULL`, never by name matching.

### C — Migration-sensitive identifier

| Identifier | Current | Decision |
|---|---|---|
| Database name (`commerce`, `dedunet_staging`) | mixed | **No change.** Renaming a live database is a migration with downtime and a restore path, not a text edit |
| SKU prefix `MRT-*` | legacy rows | **No change.** Referenced by `order_lines`, which are financial records |
| Demo credentials `*@meret.example` | legacy seed | **No change** while the MERET fixture exists. `.example` is reserved and unroutable |
| Mobile bundle IDs | `com.dedunet.store` | **Already DEDUNET** (Workstream F) |
| Expo slug / EAS project | `dedunet` / `72b0a18d-…` | **Already DEDUNET** (Workstream F) |
| npm package name | `dedunet-mobile` | **Already DEDUNET** (Workstream F) |

Changing a bundle identifier after a store submission would create a *new application* and
strand existing installs. These were set correctly before any submission, which is the only
cheap moment to do it.

### D — Historical evidence — must NOT change

| File | Occurrences |
|---|---|
| `evidence/workstream-a/WORKSTREAM_A_EVIDENCE.md` | 1 |
| `evidence/workstream-b/WORKSTREAM_B_EVIDENCE.md` | 3 |
| `evidence/workstream-b/WORKSTREAM_B_LEASE_FENCING_EVIDENCE.md` | 1 |
| `evidence/workstream-e/WORKSTREAM_E_EVIDENCE.md` | 2 |
| `evidence/workstream-f/WORKSTREAM_F_EVIDENCE.md` | 2 |
| `evidence/restructuring/BASELINE_BEFORE_RESTRUCTURE.md` | 1 |
| `docs/architecture/CURRENT_REPOSITORY_AUDIT.md` | 2 |
| `docs/architecture/RESTRUCTURE_COMPLETION_REPORT.md` | 1 |
| `docs/system-of-record/SUCCESSOR_AGENT_TAKEOVER_REPORT.md` | 2 |
| `docs/system-of-record/CONFLICT_AND_RESOLUTION_REGISTER.md` | 4 |

**Frozen.** These record what was true when the work was executed. An evidence file stating
that a command ran against a brand that did not exist at the time is worse than a stale name.
The restructure evidence already establishes this principle.

### E — Test fixture

| File | Occurrences |
|---|---|
| `services/commerce-api/tests/test_notifications.py` | 17 |
| `services/commerce-api/tests/test_rate_limit.py` | 3 |
| `services/commerce-api/tests/test_commerce_e2e.py` | 3 |
| `services/commerce-api/tests/conftest.py` | 1 |
| `apps/mobile/src/__tests__/brand.test.ts` | 2 |

**Keep.** These assert against the legacy seed by name; changing the seed and the assertions
together would prove nothing about either. The mobile occurrences are the *guard* that
forbids the legacy brand in application source — it must contain the string in order to
search for it.

### F — Obsolete / removable

| File | Occurrences | Disposition |
|---|---|---|
| `README.md` | 7 | **Stale, already registered as CONFLICT-009.** Describes a MERET-era platform |
| `docs/KNOWN_LIMITATIONS.md` | 1 | Same; partially corrected by Workstream F |
| `docs/operations/RUNBOOKS.md` | 1 | Refers to the seed dataset; correct in context |

### G — Introduced deliberately by this integration

| File | Purpose |
|---|---|
| `scripts/validation/verify_side_a_package.py` | Asserts the Side A package contains **no** MERET/MERYT |
| `services/commerce-api/migrations/.../e4b7a91c2d55_*.py` | Comment explaining the legacy seed keeps loading |
| `docs/side-b/DEDUNET_INTEGRATION_CONTRACT.md` | Names the legacy surface it must not touch |

---

## Central brand seam

| Surface | Seam | State |
|---|---|---|
| Mobile | `apps/mobile/src/brand.ts` | **DONE.** Guarded: the literal appears in exactly one module |
| Normalized package | `packages/brand/brand.json`, `tokens.json`, `tokens.css`, `navigation.json`, `content.json` | **DONE** |
| API | `external_product_id` + typed states | **DONE** |
| Web | none yet | **OPEN** — deferred with §A |
| Admin | none yet | **OPEN** — deferred with §A |
| Notification identity | `NOTIFICATION_*` / sender identity | **OPEN** — `EXTERNAL_SMTP_DELIVERY_PENDING`, so no message has ever been sent under either brand |

---

## What must NOT be claimed

- Domain ownership of `dedunet.com` is **not** trademark clearance.
- `LEGAL_CLEARANCE_PENDING` stands; the `DeDeNet` conflict remains a disclosed high
  preliminary risk.
- DEDUNET must **not** be described as a historically verified Egyptian or pharaonic weaving
  goddess. Side A's own copy disclaims this explicitly, and a test asserts both that the
  blocked claim is absent and that the disclaimer survives normalization.
- The approved narrative credits **Dedun/Dedwen, a Nubian deity documented in Egyptian
  sources**. That attribution must not be flattened to "Egyptian".

---

## Residual risk

Web and admin still show the legacy brand to anyone who opens them. That is visible and
recorded rather than hidden, and it is safe precisely because public commercial launch is
`BLOCKED`. It must close before any branded end-to-end slice is demonstrated to a third party.
