# Side A Intake Report

| Field | Value |
|---|---|
| Artifact ID / version | A0-INTAKE-001 / 1.0 |
| Owner | Side A Business/Product Lead |
| Sources / dependencies | Full repository inspection; A0-PLAN-001; EV-A0-001 |
| Acceptance criteria | Inventories available artifacts, facts, gaps, contradictions, assumptions and risks; rejects unsupported external claims |
| Validation / evidence | PASS / EV-A0-002 |
| Status | SELF-VALIDATED |
| Downstream consumer | Controller, Side B, A1-A12 owners |
| Risk / next action | No external evidence was supplied; execute EXT-01 through EXT-10 and process HO-A-B-001 |

## Repository intake

The supplied pack contains the binding operating instructions, machine-readable Side A and Side B books, human-reference PDF/DOCX duplicates, controller prompts, and a FastAPI/static web/Expo PoC. Before this cycle, `docs/side-a/`, `evidence/side-a/`, and `handoffs/incoming/side-a/` contained no files. There was no Git repository at this project path, so no history or baseline commit was available.

## Authoritative facts

- The intended business direction is premium clothing manufactured and packaged in Egypt for Europe, subject to evidence.
- The operating model mandates one country, one narrow vertical slice, and web-first scope.
- The PoC code presents three sample products and nine unique sample SKUs, with JSON persistence and deterministic recommendations.
- The PoC explicitly excludes live payments, VAT, customs, identity, transactional orders, stock reservations, carrier labels, refunds and legal pages.
- Germany-specific compliance planning sources are included in the books.
- No signed agreement, legal entity, named accountable human, product specification, sample, supplier/factory record, material evidence, lab result, cost, price approval, inventory record, registration, carrier result, payment activation, customer interview or campaign result is present.

## Rejected unsupported claims

The PoC's product names, brand/collection name, “100% cotton,” “Made in Egypt,” product descriptions, prices, stock quantities, images, stylist rationale and delivery quotation are synthetic fixtures. None may be promoted to active/sellable product truth or customer-facing claim. The phrase “real product data” in PoC copy conflicts with the book's explicit sample-data limitation and is rejected as external evidence.

## Contradictions and parsing limitations

- The operating manual defines G0 as workspace/register initialization; the roadmap also requires founder/IP agreement, named owners and spending limit. Side A applies the stricter combined rule.
- The books refer to a root `/work_packages/side_a` workspace, but Side A write boundaries permit only Side A-owned paths; work-package files are therefore placed under `docs/side-a/work_packages/side_a/`.
- Source PDFs/DOCX duplicate the Markdown books and were inventoried but not treated as machine authority.
- Some source text displays encoding artifacts; semantic meaning remains recoverable from Markdown structure.

## Recommended reversible direction

Use `VS-TEE-001`, a black oversized crew-neck T-shirt in S/M/L, as the sole physical/digital proof; Germany as the initial market hypothesis; an EU-held controlled batch as the operating hypothesis; and web only. This reduces construction, assortment, content, returns, and platform complexity. It is a learning choice, not customer validation.

## Missing inputs and blockers

The critical gaps are governance; customer/price evidence; real design and tech pack; factory and sample evidence; fibre/origin/RSL/lab evidence; landed economics; merchant/importer/tax/customs model; labels/GPSR/packaging assessment; fulfilment/test shipment; rights/trademark; and production payment/finance operations. Each has a complete action dossier in `EXTERNAL_ACTION_DOSSIERS.md`.

## Official-source planning signals checked 2026-08-01

Eurostat reports that clothing, shoes and accessories remain the leading online goods category in the EU, supporting a web-first demand-test channel but not this brand or Germany specifically. EU textile guidance requires fibre-composition labelling and local-language presentation. Germany's Central Agency Packaging Register states online retailers placing packaged goods on the German market face registration and, depending on packaging, system-participation/reporting obligations. German Customs explains EORI relevance for customs participants. These are planning signals only; qualified advisers must determine the actual obligations for the selected entity and flow.
