# HO-A-B-001 — G0 Vertical-Slice Business Inputs and Dependency Request

| Field | Value |
|---|---|
| HANDOFF-ID / schema / version | HO-A-B-001 / Fashion-Handoff-Envelope / 1.0 |
| Sender / receiver / date | Side A Business/Product Lead / Controller and Side B Platform Lead / 2026-08-01 |
| Work package / artifact IDs | A0; A0-VS-001; A0-BPC-001; A0-DEP-REG-001 |
| Purpose / consuming workflow | Align B3 master-data contract and B7/B9 non-sellable one-product web slice without inventing business truth |
| Files / payload | docs/side-a/SIDE_A_VERTICAL_SLICE_RECOMMENDATION.md; docs/side-a/SIDE_A_BUSINESS_PLATFORM_CONTRACT.csv; docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv |
| Status | DRAFT pending receiver disposition |

## Confirmed facts

The repository PoC uses synthetic JSON product data and has no production commerce flow. No Side A external evidence was supplied. Side A owns product, price, claim, market, policy and operating truth; Side B owns implementation schemas and runtime. Web-first, one-product scope is binding program direction.

## Assumptions

Germany, `VS-TEE-001`, black, sizes S/M/L, controlled EU stock and EUR 59 as a research test point are reversible hypotheses only. They are not approved market, product, inventory, price or legal facts.

## Exact requests to Side B

1. Return `ACCEPT`, `CONDITIONALLY_ACCEPT`, or `REJECT` for each BPC field, with field-level reason, proposed technical type/constraint and any required additional business input.
2. Demonstrate a lifecycle/evidence gate in the proposed schema: fixture/candidate records and records missing mandatory evidence cannot become sellable or expose claims/positive stock/live checkout.
3. Preserve immutable product/SKU IDs, audited state transitions, evidence references, price history, batch/QC linkage and locale/market scoping.
4. Provide Side A with versioned template constraints for tokens/assets, content/media, analytics and operational roles; do not finalize UI, live checkout, tax, delivery promises or AI.
5. Keep the existing PoC product values visibly synthetic. Do not silently rename them to `VS-TEE-001` or treat their price/stock/cotton/origin statements as approved.

## Questions

- Which BPC fields are already representable, which require schema changes, and which should be separate entities?
- What exact identifier, enum, decimal, locale, temporal and evidence-reference constraints does Side B recommend?
- How will the API prevent absent/expired evidence or unreleased batches from reaching public/sellable states?
- What import-error format and data-clinic procedure will Side A receive?

## Field-level acceptance criteria

- All 35 contract fields receive explicit receiver disposition.
- Required/blocked fields cannot be satisfied with empty strings, guessed defaults or PoC values.
- `lifecycle_status` defaults to `fixture` or `candidate`, never `sellable`.
- Sellable activation requires product approval, market eligibility, approved gross price/tax treatment, evidence-backed material/origin fields, released batch/QC, positive reconciled stock, approved content/rights and applicable policy/operator records.
- Claims render only when claim scope, evidence ID, approver and expiry are valid.
- Stock is zero for sellable purposes until batch/location/QC evidence exists.
- Receiver documents validation errors and does not silently repair Side A truth.

## Validation/review procedure

Side B parses `SIDE_A_BUSINESS_PLATFORM_CONTRACT.csv`, returns a 35-row disposition matrix, maps each accepted field to schema/API/import validation, and provides negative tests for missing evidence, duplicate SKU, expired claim, unreleased batch, missing operator and unapproved price. Controller compares the response to shared ownership boundaries.

## Need-by / impact / fallback

Need by G1 data-contract alignment; target sequencing is the first product-data clinic, not a calendar override. If late, do not freeze production schema or build public PDP/checkout. Safe fallback: keep the PoC unchanged as a non-public synthetic fixture and continue external dossiers.

## Change control and supersession

This is version 1.0 and supersedes nothing. Side A changes business truth through a new version and decision reference. Side B may propose constraints but must not alter Side A-owned values. Receiver response must reference this handoff ID/version and be routed through the controller.

## Receiver result

Pending: `ACCEPT`, `CONDITIONALLY_ACCEPT`, or `REJECT` with field-level reasons.
