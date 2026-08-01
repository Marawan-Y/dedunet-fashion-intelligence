# One-Product Vertical Slice Input Contract

- Artifact ID: SB-AR-B3-001
- Version/schema: 0.1.0
- Owner: Side B Platform Lead (schema); Side A owns supplied business/product values
- Source inputs/dependencies: Shared Contract; Side B Book sections 6, 20-23, 32; existing PoC templates; SB-AR-B2-001
- Acceptance criteria: every required field has owner, type/format, evidence rule, and field-level acceptance; contract supports exactly one product, its sellable variants, and one selected market.
- Validation procedure/result: reconciled against book product-master groups and Business-Platform Contract; SELF-VALIDATED as a request schema, not accepted product truth.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-005_intake_validation.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: Side A response; B3 schema/validator; B7 catalog; B9 web slice
- Remaining risks/next action: Side A/controller must ACCEPT, CONDITIONALLY_ACCEPT, or REJECT each required field and return evidence IDs; v0.1.0 must not be treated as frozen until processed.

## Envelope requirements

Return one versioned UTF-8 CSV/JSON payload plus evidence manifest. Every value must include `source_artifact_id`, `approval_owner`, `approval_status`, and `effective_version`. Unknown values must be blank with an explicit dependency ID; never use plausible filler.

## Field contract

| Group.field | Required | Owner | Type/format | Field-level acceptance |
|---|---:|---|---|---|
| product.product_id | yes | Side A Product | immutable string | Unique, stable, never display-name-derived after acceptance. |
| product.style_code | yes | Side A Product | string | Unique within brand; owner approves convention. |
| product.name | yes | Side A Brand/Product | localized string | Approved name; no unsupported claim. |
| product.slug | yes | Shared | lowercase hyphen slug | Unique; Side B validates; Side A approves customer wording. |
| product.category | yes | Side A Product | approved enum | One unambiguous taxonomy value. |
| product.collection | yes | Side A Product | ID + display name | Stable ID separate from display text. |
| product.lifecycle_status | yes | Side A Product/Ops | draft/approved/active/archived | `active` requires all evidence/publish gates. |
| product.short_description / long_description | yes | Side A Marketing/Product | localized text | Claims map to approved_claim IDs; copy owner approval recorded. |
| product.fit | yes | Side A Product | enum/text | Matches approved sample/measurement method; evidence ID. |
| material.fibre_composition | yes | Side A Product/QC | structured percentages + permitted names | Totals 100%; supplier/lab/label evidence IDs; external requirements pending qualified review. |
| material.country_of_origin | yes | Side A Ops/Compliance | ISO country + statement | Evidence ID and qualified customs/origin review status; not inferred from packaging location. |
| material.care_instructions | yes | Side A Product/QC | ordered symbols/text/locales | Approved against material/product evidence. |
| compliance.approved_claims | yes | Side A/qualified reviewer | list of claim_id/text/scope/evidence_id/status | Only HUMAN-VERIFIED/EXTERNALLY-VERIFIED claim entries may be publishable. |
| compliance.responsible_operator | yes for sellable path | Side A Legal/Ops | legal name/address/contact/role/evidence | Qualified review and market applicability recorded. |
| variant.sku | yes | Side A Product/Ops | unique string | Globally unique across payload; immutable after transactions. |
| variant.barcode | decision required | Side A Ops | GS1-valid value or explicit `not_assigned` decision | No placeholder presented as registered barcode. |
| variant.size / size_system | yes | Side A Product | enum/text + system/version | Maps to measurements and customer guidance. |
| variant.color / color_code | yes | Side A Product/Brand | name + controlled code | Controlled vocabulary; media mapping present. |
| variant.measurements | yes | Side A Product/QC | named dimensions, decimal value, unit, tolerance, method | Complete for selected category; evidence/approval IDs. |
| variant.weight_g | yes | Side A Ops | positive integer | Measured method/date/owner recorded. |
| package.length_cm/width_cm/height_cm/weight_g | yes | Side A Ops | positive decimals/integer | Packed sellable unit measurement evidence. |
| inventory.location_id | yes for operations | Side A Ops | controlled ID | Maps to selected fulfilment model; no invented warehouse. |
| inventory.opening_stock | yes before beta | Side A Ops | nonnegative integer + as_of timestamp | Human-reconciled count and batch/QC release references. |
| batch.supplier_id/production_batch_id/qc_release_id | yes before beta | Side A Sourcing/QC | stable IDs | Traceable evidence objects; QC status not agent-invented. |
| price.market | yes | Side A Business | ISO country/market ID | Exactly one approved initial market. |
| price.currency | yes | Side A Finance | ISO 4217 | Compatible with merchant/provider plan. |
| price.gross_minor_units | yes | Side A Finance | integer | Approved customer price; no binary float. |
| price.tax_class/net_gross_basis | yes | Side A Finance/qualified adviser | controlled ID/enum | Qualified review reference; Side B does not infer VAT. |
| price.valid_from/valid_to | yes | Side A Finance | RFC 3339 UTC/null | Non-overlapping approved validity. |
| economics.cost_stack/margin_approval_id | dependency | Side A Finance | versioned reference | Needed for go/no-go analytics; sensitive fields may remain restricted, but approval ID is mandatory. |
| market.language/locales | yes | Side A Business | BCP 47 list | Content exists/approved for each public locale. |
| market.eligibility | yes | Side A Business/Legal | allowed country list | Explicitly excludes unreviewed countries. |
| policy.delivery_promise/returns/warranty/support | yes | Side A Ops/Legal/Customer | versioned policy IDs + approved public text | Operationally testable; legal review status and owner recorded. |
| fulfilment.warehouse/carrier/return_address/cutoff | yes before sellable integration | Side A Ops | versioned provider/SOP refs | Account/credential handoff occurs separately through secure channel; test plan exists. |
| content.media_assets | yes for preview | Side A Brand/Marketing | asset ID, URL/path, role, locale, alt text, rights owner, approval/version | No generated/placeholder image represented as real product; rights/approval recorded. |
| brand.tokens | yes before final UI | Side A Brand | versioned token artifact | Approved owner and accessible contrast review input. |
| analytics.business_questions/kpis | yes for instrumentation | Shared | versioned definitions | Owner, formula, source of truth, consent classification, and acceptance event specified. |
| operations.roles/approval_limits/support_hours/severity_contacts | yes before admin/beta | Side A Ops | named role/limit/contact artifact | Named accountable people; enables RBAC/on-call design. |

## Payload-level acceptance

No duplicate product ID, slug, style code, SKU, asset ID, batch ID, or evidence ID. One market only. All sellable variants link to product, price, measurement, package, stock location, batch, QC, and media. Every public claim/copy field links to approved evidence. Unknown mandatory values cause rejection or conditionally accepted draft status; they never receive generated defaults. Side B will return a machine-readable validation report and will not edit the owner’s truth silently.
