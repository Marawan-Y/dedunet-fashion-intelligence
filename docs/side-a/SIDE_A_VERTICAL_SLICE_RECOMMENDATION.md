# One-Product Vertical-Slice Recommendation

| Field | Value |
|---|---|
| Artifact ID / version | A0-VS-001 / 1.0 |
| Owner | Side A Product Lead; human approver unassigned |
| Sources / dependencies | A0-INTAKE-001; A-A-001 through A-A-004; DEP-A-002 through DEP-A-009 |
| Acceptance criteria | Selects exactly one product, one market and web-first scope; identifies every hypothesis; defines proof and stop rules |
| Validation / evidence | PASS / EV-A0-002 |
| Status | SELF-VALIDATED |
| Downstream consumer | Controller; Side B B3/B7/B9; Side A A2/A4-A13 |
| Risk / next action | Selection lacks human, customer, factory and product evidence; approve research hypothesis then execute EXT-02 through EXT-08 |

## Recommendation

Use one provisional black oversized crew-neck T-shirt, style ID `VS-TEE-001`, sizes `S`, `M`, and `L`, as the first end-to-end proof for Germany on the web. Do not launch mobile or AI. Do not add a second color or product until G3 criteria pass.

This is a candidate real-product record to be populated from evidence; it is not yet a real product. “100% cotton,” “Egyptian cotton,” “Made in Egypt,” measurements, care, stock, price, supplier and images remain unknown. The PoC's Nile T-shirt may be retained only as a synthetic UX fixture under a clearly synthetic identifier.

## Why this slice

Compared with the sample relaxed shirt and abaya, the T-shirt has fewer construction components, a simpler size/fit explanation, lower likely sample and content burden, and a lower test-price barrier. Black plus three sizes creates only three variants while still proving product-to-variant relationships, measurement data, price, evidence-gated claims, stock, package data and return reasons. Germany is a reversible first-market hypothesis because the source pack already provides a Germany compliance baseline and official operational sources; this is not evidence of German customer demand.

## Provisional record boundary

| Domain | Provisional value | Truth state / activation rule |
|---|---|---|
| Product ID | VS-TEE-001 | Reserved internal candidate ID; controller/Side B must confirm ID format |
| Category | t-shirt | Hypothesis; approve with tech pack |
| Color | Black | Hypothesis; approve against physical sample/color standard |
| Sizes | S/M/L | Hypothesis; approve size chart and fit test |
| Market | DE | Hypothesis; human decision plus legal/tax/compliance review |
| Channel | responsive web | Recommended scope; no mobile dependency |
| Fibre/origin/care | UNKNOWN | Must remain suppressed until DEP-A-004/DEP-A-007 pass |
| Price | UNKNOWN; EUR 59 only a research test point | Requires DEP-A-005 and customer test |
| Stock | 0 sellable | Positive stock only after batch/QC/opening inventory evidence |
| Claims | none | Claims need evidence ID, scope, approver and expiry |
| Images | none approved | Real sample imagery and rights require DEP-A-010 |
| AI | out of scope | Deterministic PoC may remain a technical demo but not launch requirement |

## Vertical-slice journey

Evidence-approved product and variants → gated catalog import → German web PDP → cart/hosted sandbox checkout → order and stock reservation → EU fulfilment and tracking → return/refund → finance and inventory reconciliation. Only schema/fixture work is currently non-blocked; every real-world step remains gated.

## Proof criteria

- One immutable product ID and three unique SKUs reconcile across tech pack, label, batch, QC, catalog, inventory and order.
- Mandatory fields have business owner, verification status and evidence reference.
- Missing or expired material/compliance evidence prevents public claims and sellable activation.
- Gross price, VAT display, delivery and returns are adviser-reviewed and operationally testable.
- One real package completes shipment, return, refund and reconciliation.
- A named human accepts physical fit/quality/content and qualified specialists verify scoped external obligations.

## Stop rules

Stop or replace the slice if sample reproducibility fails; cotton/origin evidence cannot support intended claims; downside contribution margin is non-positive; MOQ or returns exposure exceeds approved risk; target-customer evidence rejects product/price; or no compliant importer/fulfilment route is accepted.
