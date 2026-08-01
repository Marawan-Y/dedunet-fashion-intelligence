# SB-AR-B3-004 Field Disposition — artifact validation

- Artifact ID: SB-EV-G1-004
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `docs/side-b/SIDE_B_BPC_FIELD_DISPOSITION.csv` v2.0.0; HO-A-B-001 v1.0; `docs/system-of-record/CROSS_AGENT_HANDOFF_STATUS.md` conditions 1–6
- Acceptance criteria: exactly 35 unique BPC rows; every row maps to a real schema entity/field; the separate technical publication mapping is present; the ambiguous value `active` is absent; money is integer minor units; zero is the only permitted sellable quantity without evidence links; absent/expired evidence suppresses values and claims; each row names the executable negative test that proves its gate.
- Validation procedure/result: structural parse plus cross-checks against the implementation and the passing test suite; results below.
- Evidence path: this file
- Readiness status: AUTOMATED-TESTED
- Downstream consumer: Side A; controller; work packages B3/B7/B9
- Remaining risks/next action: this validates the *mapping*, not business truth. No field carries an approved value. v1.0.0 is preserved at `docs/side-b/SIDE_B_BPC_FIELD_DISPOSITION_v1_0_0.csv`.

## 1. Why v2.0.0 exists

v1.0.0 satisfied most controller conditions but had two defects:

1. Its `evidence_path` column pointed at `evidence/side-b/g1/SB-EV-G1-004_artifact_validation.md`, **which did not exist**. The artifact cited evidence that had never been produced. (The same was true of `SIDE_B_MONEY_CONTRACT.md` and `SIDE_B_LIFECYCLE_PUBLICATION_CONTRACT.md`, which both cited a non-existent `SB-EV-G1-002_candidate_green.md`.)
2. It carried no explicit **technical publication-state mapping** per field, which is controller condition 1 on HO-A-B-001. The lifecycle vocabulary was correct, but the separate technical dimension was described only in prose elsewhere.

v2.0.0 adds five columns and repairs the evidence reference. v1.0.0 is archived unmodified.

## 2. Structural validation

```text
WORKING DIRECTORY: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack
COMMAND: python -c "import csv; rows=list(csv.DictReader(open('docs/side-b/SIDE_B_BPC_FIELD_DISPOSITION.csv',encoding='utf-8',newline=''))); ..."

rows 35
unique contract ids 35
columns 23
dispositions ['ACCEPT', 'CONDITIONALLY_ACCEPT']
active used anywhere: False
EXIT_CODE: 0
```

- 35 rows, `BPC-A-001` … `BPC-A-035`, all unique.
- No row is `REJECT`; 8 are `ACCEPT` (representation is acceptable as a draft), 27 are `CONDITIONALLY_ACCEPT`.
- The ambiguous lifecycle value `active` appears nowhere.

## 3. Columns added in v2.0.0

| Column | Purpose |
|---|---|
| `max_publication_state_without_evidence` | highest technical publication state reachable while the field's evidence is absent or expired (`hidden` / `preview`) |
| `technical_publication_gate` | what must be true before `public` is permitted for that field |
| `suppression_behavior_when_absent_or_expired` | what the system actually does — suppress the value, block activation, force quantity to zero, drop the asset |
| `authoritative_value_owner` | who owns the truth (never Side B for business values) |
| `executable_negative_test_or_mutation` | the test and mutation ID that prove the gate is real |

## 4. Controller conditions — closure status

### Condition 1 — business lifecycle `fixture|candidate|sample|approved|sellable|retired`, plus a separate technical publication mapping, no ambiguous `active`

**CLOSED.** `BusinessLifecycle` in `backend/app/candidate_activation.py` is exactly that six-value enum with default `fixture`. `PublicationStatus` is a *separate* enum `hidden|preview|public`. Row `BPC-A-003` records `technical_publication_gate = lifecycle_status == sellable`. Enforced by `PUBLIC_REQUIRES_SELLABLE`; proven by `test_publication_cannot_bypass_sellable_lifecycle` and mutation **M12 (DETECTED)**.

The full technical mapping is in `docs/side-b/SIDE_B_LIFECYCLE_PUBLICATION_CONTRACT.md`; every row of the CSV now carries its per-field publication ceiling.

### Condition 2 — candidate ID / category / SKUs / sizes / colour / currency / locales labelled non-authoritative draft

**CLOSED.** Rows `BPC-A-001`, `005`, `013`, `014`, `015`, `021`, `024` each state a DRAFT/non-authoritative constraint and a `suppression_behavior` of "value retained but labelled non-authoritative draft" (or `price record stays null` for currency). The transported record itself carries `synthetic_fixture: true` and `SYNTHETIC_CANNOT_ACTIVATE` blocks activation — mutation **M13 (DETECTED)**.

### Condition 3 — integer minor units; EUR 59 is research-only

**CLOSED.** `PriceRecord.gross_minor_units: int = Field(strict=True, gt=0)`; row `BPC-A-020` records "approved business decimal converted exactly; binary float rejected". The candidate fixture's `price` is `null` — EUR 59 is not populated as an approved price. Proven by `test_authoritative_money_rejects_float_minor_units` (mutation **M14 DETECTED**).

**Scope extended beyond the condition:** the float money path that existed in the *legacy catalog and quote* code was also found and removed this cycle — see SB-EV-G1-006 and mutations **M15–M19 (all DETECTED)**.

### Condition 4 — zero is the only permitted sellable quantity until batch/QC/location/count evidence link

**CLOSED.** Row `BPC-A-019`; `CandidateProduct.sellable_quantity` returns `0` unless `lifecycle_status is SELLABLE`; positive `opening_stock` raises `POSITIVE_STOCK_WITHOUT_QC_EVIDENCE`, `POSITIVE_STOCK_WITHOUT_LOCATION` and `POSITIVE_STOCK_WITHOUT_COUNT_EVIDENCE`, each with its own evidence-scope check. Proven by `test_positive_stock_requires_qc_location_and_count_evidence` and mutations **M08, M09, M10 (all DETECTED)**. The shipped candidate has `opening_stock = 0` on all three variants.

### Condition 5 — absent/expired evidence suppresses values and claims, with scope/issuer/approver/expiry validation

**CLOSED.** `EvidenceRecord` carries `status`, `scope[]`, `issuer`, `approved_by`, `issued_at`, `expires_at` and `synthetic_fixture`. `_evidence_errors` emits `MISSING_EVIDENCE`, `EXPIRED_EVIDENCE`, `UNVERIFIED_EVIDENCE` (only `HUMAN-VERIFIED`/`EXTERNALLY-VERIFIED` pass), `SYNTHETIC_EVIDENCE` and `EVIDENCE_SCOPE_MISMATCH`. Duplicate evidence IDs raise `DUPLICATE_EVIDENCE_ID`. Rows `BPC-A-007`, `008`, `010`, `034` and the `suppression_behavior` column record the per-field effect. Proven by `test_missing_required_evidence_prevents_sellable_public_activation`, `test_expired_evidence_prevents_activation`, `test_unsupported_claim_prevents_publication`, `test_expired_claim_prevents_publication`; mutations **M03, M04, M11 (all DETECTED)**.

### Condition 6 — 35-row disposition plus negative tests for the eight named cases

**CLOSED.** The 35 rows are this artifact. Every named negative case has a passing test *and* a mutation proving the test guards it:

| Required case | Test | Mutation | Mutation result |
|---|---|---|---|
| duplicate IDs | `test_duplicate_product_ids_and_skus_are_rejected` | M01 | DETECTED |
| duplicate SKUs | `..._are_rejected`, `test_duplicate_sku_across_distinct_products_is_rejected` | M02 | DETECTED |
| missing evidence | `test_missing_required_evidence_prevents_sellable_public_activation` | M03 | DETECTED |
| expired evidence | `test_expired_evidence_prevents_activation` | M04 | DETECTED |
| unreleased batch | `test_unreleased_batch_prevents_activation` | M05 | DETECTED |
| missing operator | `test_missing_responsible_operator_prevents_activation` | M06 | DETECTED |
| unapproved price | `test_unapproved_price_prevents_activation` | M07 | DETECTED |
| unauthorized positive stock | `test_positive_stock_requires_qc_location_and_count_evidence` | M08, M09, M10 | DETECTED |
| unsupported claim publication | `test_unsupported_claim_prevents_publication`, `test_expired_claim_prevents_publication` | M11 | DETECTED |

## 5. Field-to-implementation cross-check

Every `technical_entity`/`technical_field` pair in the CSV resolves to a real declaration:

| Entity | Fields covered | Source |
|---|---|---|
| `CandidateProduct` | 001–012, 024–028, 033, 035 | `backend/app/candidate_activation.py` |
| `CandidateVariant` | 013–019 | same |
| `PriceRecord` | 020–023 | same |
| `BatchRecord` | 029–030 | same |
| `AssetRecord` | 031–032 | same |
| `EvidenceRecord` | 034 | same |
| `Claim` | 010 | same |
| `Dimensions` | 018 | same |

## 6. What this does not establish

Not one field carries approved business truth. `price` is `null`, `batch` is `null`, `country_of_origin` is `null`, `approved_claims` is empty, `evidence` is empty, `approved_by` is `null`, and every `opening_stock` is `0`. The disposition describes how Side B will *accept and gate* values that do not yet exist. It is not a product record, and it does not authorize any sale, publication or claim.
