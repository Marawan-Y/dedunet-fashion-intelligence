# One-Product Vertical Slice

| Control | Value |
|---|---|
| Artifact ID | SOR-G0-009 |
| Version | 1.0 |
| Owner | Controller; business values owned by Side A; schema/runtime owned by Side B |
| Status | SELF-VALIDATED |
| Sources | A0-VS-001; A0-BPC-001; SB-AR-B3-001; both G0 intakes |
| Dependency IDs | DEP-001 through DEP-010 |
| Acceptance criteria | Exactly one product, one market and web channel; hypotheses and unknowns explicit; proof journey, activation gate, stop rules, validation and handoffs defined |
| Validation | Cross-side contract reconciliation passed with conditions in `CROSS_AGENT_HANDOFF_STATUS.md` |
| Consumer | Side A A1-A13; Side B B1-B9/B19/B20; G1 review |
| Risk / next action | Candidate is not a real or approved product; complete the first G1 schema/validation milestone and external dossiers |

## Definition

- Candidate ID: `VS-TEE-001` (reserved planning identifier; not an approved style code).
- Product hypothesis: black oversized crew-neck T-shirt.
- Variant hypotheses: S, M and L; candidate SKU strings remain non-authoritative until identifier policy and tech pack approval.
- Initial market hypothesis: Germany (`DE`).
- Channel: responsive web only.
- Fulfilment hypothesis: controlled EU-held batch, pending evidence.
- Sellable stock: `0`.
- Fibre, origin, care, measurements, supplier, batch, QC, price, tax, claims, images, rights, merchant/importer, policies, carrier and warehouse: unknown/blocked.
- Mobile, generative AI, additional styles/colors/markets and public launch: non-scope.

## Canonical lifecycle

`fixture -> candidate -> sample -> approved -> sellable -> retired`

Transitions require an audited named approver and evidence bundle. Side B may maintain separate technical publication/deployment states, but neither `active` nor `published` may bypass `sellable` business eligibility.

## First G1 proof

The initial milestone is intentionally non-sellable:

1. Reconcile all 35 Side A contract fields with Side B types/mappings.
2. Validate one candidate product with three unique candidate variants.
3. Prove negative cases: missing/expired evidence, duplicate SKU, unreleased batch, missing operator, unapproved price, positive stock without QC/location evidence and unsupported claims all prevent sellable/public activation.
4. Prove the local backend/validator and an isolated Compose runtime are attributable to this checkout.

## Eventual end-to-end proof

Evidence-approved product -> gated catalog -> German web PDP -> server-authoritative cart/hosted payment -> order and inventory reservation -> controlled fulfilment/tracking -> return/refund -> finance/inventory reconciliation. Later steps remain blocked until their evidence gates.

## Stop rules

Stop or replace the slice if target-customer evidence rejects it; factory/sample repeatability fails; fibre/origin evidence cannot support intended wording; downside contribution margin is non-positive; MOQ/returns exceed approved risk; no responsible importer/operator/fulfilment path is accepted; or critical platform recovery/security criteria fail.
