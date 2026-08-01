# HO-A-B-002 — Side A Response to SB-HO-B0-001

| Field | Value |
|---|---|
| HANDOFF-ID / schema / version | HO-A-B-002 / Fashion-Handoff-Envelope / 1.0 |
| Sender / receiver / date | Side A Business/Product Lead / Controller and Side B Platform Lead / 2026-08-01 |
| Responds to | SB-HO-B0-001 v1.0.0; controller disposition in SOR-G0-011 |
| Work package / artifact IDs | G1 M1; A1-DISP-001; A1-PAYLOAD-001; A0-BPC-001; SB-AR-B3-001 |
| Purpose / consuming workflow | Provide atomic Side A dispositions and a strictly non-sellable candidate payload for B3 schema/validator, B7 catalog and B9 local web candidate validation |
| Files / payload / schema | `docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv` (UTF-8 CSV; 65 atomic rows); `docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json` (UTF-8 JSON; schema 0.1.0); `evidence/side-a/g1/EV_A1_001_M1_CONSISTENCY_VALIDATION.md` |
| Readiness status | DRAFT pending receiver disposition |
| Need-by | G1 M1 contract and non-sellable candidate proof; no calendar date overrides acceptance |

## Response disposition

Side A `CONDITIONALLY_ACCEPT`s the SB-HO-B0-001 envelope for G1 schema work only. The matrix contains 64 `CONDITIONALLY_ACCEPT` atomic fields and one `REJECT`: `product.lifecycle_status` as requested with `draft|approved|active|archived`. No field is `ACCEPT` because no requested business value is both complete and approved/evidence-linked. The replacement lifecycle is `fixture|candidate|sample|approved|sellable|retired`; technical publication state must remain separate.

## Confirmed facts

- Controller records SOR-G0-002/007/008/009/010/011 are authoritative for M1.
- `VS-TEE-001`, Germany, black, S/M/L, oversized fit and responsive web are `DRAFT` hypotheses only.
- The candidate has no real product, price, claim, material, origin, content, inventory, policy, operator or fulfilment evidence.
- PoC brand/copy/cotton/origin/prices/positive stock/images/shipping thresholds and stylist output are rejected as business truth.
- G0 remains `BLOCKED` / `NO_GO`; M1 is reversible G1 preparation, not gate advancement.

## Assumptions

The JSON candidate ID, name/category/fit, three `CAND-` SKU strings, variant size/color values, DE/EUR/language/locale values and zero sellable-stock cap exist only to validate schema constraints. They cannot be promoted to approved or sellable without their dependency and evidence gates.

## Questions to Side B

1. Can the validator ingest the payload while treating every `BLOCKED` null as an expected candidate-state condition rather than filling a default?
2. What separate technical publication-state enum will map to the canonical business lifecycle without `active` or `published` implying `sellable`?
3. Will candidate SKU identifiers stay isolated from transactional identifiers, and what controlled migration/mapping will be required after tech-pack approval?
4. Can negative tests prove public catalog, claims, checkout and positive inventory remain disabled for this payload?
5. What machine-readable error format will Side A receive for each atomic field and dependency?

## Acceptance criteria for Side B processing

- Parse both UTF-8 payload files without editing Side A-owned truth.
- Return an explicit disposition/mapping for all 65 atomic fields, preserving Side A owners and dependencies.
- Adopt the canonical business lifecycle or `REJECT` with a field-level alternative that still makes `sellable` the only business activation state.
- Candidate/blocked records never receive generated defaults for name/slug/collection/material/origin/care/claims/operator/measurements/package/inventory/batch/price/policy/fulfilment/content/brand/analytics/operations.
- Demonstrate negative tests for duplicate candidate SKU, missing/expired evidence, unsupported claim, unreleased batch, missing operator, missing approved price, positive stock without batch/QC/location/count evidence, and technical `active/published` without business `sellable`.
- Preserve `gross_minor_units=null`; do not reuse EUR 59 or any PoC price. Preserve business `opening_stock=null` and enforce sellable stock zero.
- No PoC brand, collection, copy, composition, origin, imagery or shipping threshold enters the candidate payload.
- Return exact validation commands, output, limitations and evidence path under Side B ownership.

## Validation procedure and Side A result

Side A parsed the CSV and JSON, checked row/field uniqueness, allowed dispositions/statuses, lifecycle replacement, candidate SKU uniqueness, blocked-null discipline, zero sellable stock, dependency links and prohibited PoC value absence. Result: `SELF-VALIDATED` in EV-A1-001. This validates documentation/data consistency only, not any external reality.

## Impact if late and safe fallback

If not processed, M1 contract/schema alignment remains incomplete and Side B must not freeze the product schema or build public PDP/checkout behavior around the candidate. Safe fallback: retain current PoC values solely as isolated synthetic fixtures, keep public exposure/checkout disabled and continue only contract/test framework work.

## Change control and supersession

Initial response version 1.0; supersedes nothing. It does not alter SB-HO-B0-001 or SB-AR-B3-001. Any Side A business-value change requires a new payload and handoff version with decision/evidence references. Any Side B mapping change requires a versioned receiver response. Neither side silently repairs the other's source truth.

## Receiver result

Pending `ACCEPT`, `CONDITIONALLY_ACCEPT` or `REJECT` from controller/Side B with field-level reasons.
