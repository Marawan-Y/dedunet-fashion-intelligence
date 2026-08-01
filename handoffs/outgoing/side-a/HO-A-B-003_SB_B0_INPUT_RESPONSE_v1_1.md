# HO-A-B-003 — Side A Response to SB-HO-B0-001, v1.1 (condition-closure evidence)

| Field | Value |
|---|---|
| HANDOFF-ID / schema / version | HO-A-B-003 / Fashion-Handoff-Envelope / 1.1 |
| Sender / receiver / date | Side A Business/Product Lead / Controller and Side B Platform Lead / 2026-08-01 |
| Responds to | SB-HO-B0-001 v1.0.0; the six controller conditions recorded in SOR-G0-011 `docs/system-of-record/CROSS_AGENT_HANDOFF_STATUS.md` |
| Supersedes | HO-A-B-002 v1.0 (`handoffs/outgoing/side-a/HO-A-B-002_SB_B0_INPUT_RESPONSE_v1.md`), retained as history |
| Work package / artifact IDs | G1 M1; A1-DISP-001; A1-DISP-002; A1-PAYLOAD-001; A0-EXT-001; A0-BPC-001; SB-AR-B3-001 |
| Purpose / consuming workflow | Prove field by field that all six controller conditions on SB-HO-B0-001 are closed, and supply the atomic and instance-level dispositions plus the strictly non-sellable candidate payload for B3 schema/validator, B7 catalog and B9 local web candidate validation |
| Files / payload / schema | `docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv` (A1-DISP-001 v1.0, UTF-8 CSV, 65 atomic field rows, unchanged); `docs/side-a/SB_HO_B0_001_VARIANT_INSTANCE_DISPOSITIONS.csv` (A1-DISP-002 v1.0, UTF-8 CSV, 9 instance rows, new); `docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json` (A1-PAYLOAD-001 v0.1.1, UTF-8 JSON, metadata-only change); `evidence/side-a/g1/EV_A1_002_M1_CONDITION_CLOSURE_VALIDATION.md` |
| Readiness status | DRAFT pending receiver disposition |
| Need-by | G1 M1 contract and non-sellable candidate proof; no calendar date overrides acceptance |

## Response disposition

Unchanged from HO-A-B-002. Side A `CONDITIONALLY_ACCEPT`s the SB-HO-B0-001 envelope for G1 schema work only. A1-DISP-001 contains 64 `CONDITIONALLY_ACCEPT` atomic fields and one `REJECT` — `product.lifecycle_status` as requested with `draft|approved|active|archived`. A1-DISP-002 adds 9 `CONDITIONALLY_ACCEPT` instance rows. No field is `ACCEPT`, because no requested business value is both complete and approved/evidence-linked. The replacement business lifecycle is `fixture|candidate|sample|approved|sellable|retired`; any technical publication state must remain separate and must not imply `sellable`.

## Condition-by-condition closure against SOR-G0-011

| # | Controller condition | Side A closure | Where proven | State |
|---|---|---|---|---|
| 1 | Germany and `VS-TEE-001` may be returned only as DRAFT research/candidate hypotheses, not selected launch/product truth | `product.product_id=VS-TEE-001`, `price.market=DE`, `market.eligibility=["DE"]`, `market.language`, `market.locales` and `price.currency=EUR` each carry `approval_status=DRAFT` in the payload and `candidate_value_state=DRAFT` with `disposition=CONDITIONALLY_ACCEPT` in the matrix. No entry in either file carries `ACCEPT`, `approved` or `HUMAN-VERIFIED`. Matrix replacement actions require human authorization and qualified advice before market activation | A1-DISP-001 rows `product.product_id`, `price.market`, `price.currency`, `market.language`, `market.locales`, `market.eligibility`; A1-PAYLOAD-001 `candidate_values`; EV-A1-002 check K1 | CLOSED |
| 2 | Unknown mandatory external fields must carry their dependency/evidence status; blank or plausible filler is not acceptable and does not prevent a draft schema response | All 52 unsupported fields are present as explicit entries with `value=null`, `approval_status=BLOCKED` and at least one `DEP-A-*` dependency ID. Zero blocked entries are non-null, zero are missing a dependency ID and none is omitted. The draft schema response was still delivered in full | A1-PAYLOAD-001 `blocked_or_unknown_fields`; A1-DISP-001 `evidence_or_dependency_ids`; EV-A1-002 checks C7 and K2 | CLOSED |
| 3 | Reject the `draft\|approved\|active\|archived` business lifecycle vocabulary; use the canonical business lifecycle; Side B owns a separate technical-state mapping | `product.lifecycle_status` is the single `REJECT` row; its `replacement_action` states the canonical enum verbatim. The payload publishes `canonical_business_lifecycle`, `current_business_lifecycle=candidate` and `technical_active_or_published_implies_sellable=false`, and requires a separate Side B publication enum | A1-DISP-001 row `product.lifecycle_status`; A1-PAYLOAD-001 `activation_controls`; EV-A1-002 check K3 | CLOSED |
| 4 | Break grouped fields into atomic response rows or clearly enumerate each nested field so validation errors are field-specific | Two-part closure. (a) Every nested field is enumerated to leaf level: `product.collection.id`/`.display_name`; all five `compliance.responsible_operator.*`; all four `package.*`. No group placeholder row exists for these. (b) The variant array was the residual ambiguity: matrix rows `variant.sku`, `variant.size` and `variant.color` carried three pipe-joined instance values each, so a validator error could not identify the failing instance. A1-DISP-002 now supplies 9 instance-level rows (`variants[0..2].sku/size/color`) that match the payload's instance fields one to one. Fields that remain structurally undefined — `variant.measurements`, `economics.cost_stack`, `content.media_assets`, `analytics.*`, `operations.roles`, `policy.*` — are not enumerated because their approved internal structure does not yet exist; each is a single explicit `BLOCKED` null with its dependency ID, and Side A will enumerate their leaves in the version issued after DEP-A-003/005/006/008/010 evidence defines them | A1-DISP-001 (nested leaves); A1-DISP-002 (instance rows, new in v1.1); EV-A1-002 checks K4a, K4b, K4c | CLOSED IN v1.1 — was PARTIAL in HO-A-B-002 |
| 5 | Do not return `Origin`, PoC product copy, cotton/origin assertions, prices, positive stock, imagery or shipping thresholds as approved values | A scan of every candidate value for the PoC brand name, PoC collection and copy identifiers, `100% cotton`, `Egyptian cotton`, `Made in Egypt`, the PoC image host, the PoC price and free-shipping wording returns zero hits. `price.gross_minor_units=null`, `inventory.opening_stock=null`, `activation.sellable_stock_cap=0`, `content.media_assets=null`, `policy.delivery_promise=null`. The payload also lists all nine rejected PoC truths explicitly | A1-PAYLOAD-001 `explicitly_rejected_as_truth`, `blocked_or_unknown_fields`; EV-A1-002 checks C9 and K5 | CLOSED |
| 6 | Return a complete field/group disposition and a minimal candidate payload whose blocked fields are explicit | 65 of 65 requested atomic fields have exactly one permitted disposition, owner, state, dependency, reason, gate impact and replacement action, with no duplicates, no missing fields and no unexpected fields. The matrix field set and the payload field set are identical. The payload is minimal: 21 DRAFT candidate entries and 52 explicit BLOCKED nulls, no defaults and no invented structure | A1-DISP-001; A1-PAYLOAD-001; EV-A1-002 checks C4, C5, C8, K6 | CLOSED |

Conditions 1, 2, 3, 5 and 6 were already satisfied by HO-A-B-002 v1.0 and are re-proven here by independent re-execution. Condition 4 was only partially satisfied by HO-A-B-002 and is closed by this version.

## Confirmed facts

- Controller records SOR-G0-002/005/007/008/009/010/011 are authoritative for M1.
- `VS-TEE-001`, Germany, black, S/M/L, oversized fit and responsive web are `DRAFT` hypotheses only.
- The candidate has no real product, price, claim, material, origin, content, inventory, policy, operator or fulfilment evidence.
- PoC brand/copy/cotton/origin/prices/positive stock/images/shipping thresholds and stylist output are rejected as business truth.
- G0 remains `BLOCKED` / `NO_GO` on DEP-001 (governance, Side A dossier EXT-01) and DEP-011 (controlled source repository, Side B/workspace owned). M1 is reversible G1 preparation, not gate advancement.
- No factory visit, sample inspection, laboratory test, customer interview, legal/tax/customs conclusion, registration, contract, payment activation, carrier result or production operation has occurred or is claimed anywhere in Side A's artifacts.

## Assumptions

The JSON candidate ID, name/category/fit, three `CAND-` SKU strings, variant size/color values, DE/EUR/language/locale values and the zero sellable-stock cap exist only to validate schema constraints. They cannot be promoted to approved or sellable without their dependency and evidence gates.

## Questions to Side B

1. Can the validator ingest the payload while treating every `BLOCKED` null as an expected candidate-state condition rather than filling a default?
2. What separate technical publication-state enum will map to the canonical business lifecycle without `active` or `published` implying `sellable`?
3. Will candidate SKU identifiers stay isolated from transactional identifiers, and what controlled migration/mapping will be required after tech-pack approval?
4. Can negative tests prove public catalog, claims, checkout and positive inventory remain disabled for this payload?
5. What machine-readable error format will Side A receive for each atomic field, each variant instance and each dependency?
6. New in v1.1: does the instance-level file A1-DISP-002 give the granularity Side B needs to emit per-variant validation errors, or does Side B require a different instance key convention than `variants[n].field`?

## Acceptance criteria for Side B processing

- Parse all three payload files as UTF-8 without editing Side A-owned truth.
- Return an explicit disposition/mapping for all 65 atomic fields and all 9 variant instance rows, preserving Side A owners and dependencies.
- Adopt the canonical business lifecycle or `REJECT` with a field-level alternative that still makes `sellable` the only business activation state.
- Candidate/blocked records never receive generated defaults for name/slug/collection/material/origin/care/claims/operator/measurements/package/inventory/batch/price/policy/fulfilment/content/brand/analytics/operations.
- Demonstrate negative tests for duplicate candidate SKU, missing/expired evidence, unsupported claim, unreleased batch, missing operator, missing approved price, positive stock without batch/QC/location/count evidence, and technical `active`/`published` without business `sellable`.
- Emit per-instance validation errors keyed to `variants[n].field`, not to the parent field alone.
- Preserve `gross_minor_units=null`; do not reuse EUR 59 or any PoC price. Preserve business `opening_stock=null` and enforce sellable stock zero.
- No PoC brand, collection, copy, composition, origin, imagery or shipping threshold enters the candidate payload.
- Return exact validation commands, output, limitations and evidence path under Side B ownership.

## Validation procedure and Side A result

Side A independently re-executed the checks in Python 3.14.4 rather than re-asserting the earlier PowerShell run: CSV parse and column integrity for eight Side A CSVs, JSON parse, allowed-status enforcement across every register and payload entry, allowed-disposition enforcement, duplicate artifact/field/evidence/dependency ID detection, on-disk existence of every non-URL evidence path, blocked-null and dependency-link discipline, candidate SKU uniqueness, zero sellable-stock cap, matrix/payload field-set equality, prohibited PoC value scan, an unsupported-completion-language scan across all 27 Side A owned files, an eight-element completeness audit of all 10 external-action dossiers, and six condition-closure checks K1-K6. Exact commands, full output and limitations: `evidence/side-a/g1/EV_A1_002_M1_CONDITION_CLOSURE_VALIDATION.md`. Result: `SELF-VALIDATED`. This validates documentation and data consistency only; it validates no external reality.

## Impact if late and safe fallback

If not processed, M1 contract/schema alignment remains incomplete and Side B must not freeze the product schema or build public PDP/checkout behavior around the candidate. Safe fallback: retain current PoC values solely as isolated synthetic fixtures, keep public exposure and checkout disabled, and continue only contract and test-framework work.

## Change control and supersession

Version 1.1 supersedes HO-A-B-002 v1.0, which remains on disk as history and must not be deleted. Changes in this version: (1) added A1-DISP-002, the 9-row variant instance disposition file, closing controller condition 4; (2) added the explicit condition-by-condition closure table; (3) added acceptance criterion and question 6 covering per-instance error keys; (4) A1-PAYLOAD-001 bumped 0.1.0 → 0.1.1 for metadata only — response reference, instance-file link and evidence path — with no business value, status, dependency or null added, changed or removed, and every field entry retaining `effective_version` 0.1.0. A1-DISP-001 v1.0 is byte-for-byte unchanged, so the 65-field contract Side B is already validating against is not disturbed. This handoff does not alter SB-HO-B0-001 or SB-AR-B3-001. Any Side A business-value change requires a new payload and handoff version with decision and evidence references. Neither side silently repairs the other's source truth.

## Receiver result

Pending `ACCEPT`, `CONDITIONALLY_ACCEPT` or `REJECT` from controller/Side B with field-level reasons.
