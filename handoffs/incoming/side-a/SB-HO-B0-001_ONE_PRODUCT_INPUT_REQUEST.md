# Formal Handoff — One-Product Input and G0 Dependency Request

- Artifact ID / HANDOFF-ID: SB-HO-B0-001
- Version: 1.0.0
- Owner/sender: Side B Platform Lead
- Receiver: Controller and Side A Business/Product/Ops/Brand/Finance owners
- Date: 2026-08-01
- Source inputs/dependencies: SB-AR-B3-001; SB-AR-G0-003/006/007/011; Shared Contract
- Acceptance criteria: receiver records ACCEPT, CONDITIONALLY_ACCEPT, or REJECT for the envelope and each required field group, with reasons/evidence/dependency IDs.
- Validation procedure/result: checked against every Shared Contract handoff field and field-level schema; SELF-VALIDATED.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-005_intake_validation.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller handoff processing; Side A response; B3/B7/B9
- Remaining risks/next action: receiver disposition is pending; no requested business value is accepted until controller processing.

## Work package and artifact IDs

Work packages: G0/B1/B2/B3/B7/B9 with future dependencies on B5/B11-B16/B19. Payload schema: SB-AR-B3-001 v0.1.0 at `docs/side-b/contracts/ONE_PRODUCT_VERTICAL_SLICE_INPUT_CONTRACT_V0_1.md`.

## Purpose and consuming workflow

Request the minimum owned truth required to turn the sample PoC into a production-oriented but still non-sellable one-product, one-market, web-first vertical slice. Side B will consume accepted fields to version schemas, validate an import, gate unverified claims, create a catalog preview, and define later commerce/operations interfaces.

## Confirmed facts

The repository currently contains sample product/price/stock/claim/media data only. Backend tests and validator pass locally after setup; Docker images build; mobile install and this checkout’s Compose runtime are not proven. No real product or external operational evidence is present.

## Assumptions

One physical apparel product, all of its sellable variants, one explicitly selected market, web-first. Germany may appear only as a synthetic test fixture and is not presumed as the launch market. No production provider is selected.

## Exact requests/questions

1. Return each SB-AR-B3-001 field group with owner, version, approval status, and evidence ID.
2. Name technical/account/source-control owners and the approved G0 spending limit.
3. Identify the selected initial country, legal seller/merchant, importer/responsible-operator plan, invoice identity, and qualified review evidence/status.
4. Identify the one real product/style and variant set; confirm whether any public Egyptian-cotton/origin claims are approved and evidence-backed.
5. Provide price/currency/tax-class/net-gross decision, operational fulfilment/returns/delivery policy, approved media/rights/alt text, and named operator roles.

## Acceptance criteria and validation procedure

Receiver must respond per field group using exactly one disposition:

- `ACCEPT`: complete, internally consistent, owned, versioned, and evidence-linked.
- `CONDITIONALLY_ACCEPT`: usable only for draft/schema work; list missing fields, owner, dependency ID, impact, and due gate.
- `REJECT`: invalid/contradictory/unsupported; cite field-level reason and replacement action.

Side B validation will check identifier uniqueness, types/enums/units, 100% composition total, evidence links, claim publish status, price minor units/validity, variant traceability, one-market constraint, and cross-field lifecycle rules. Human/external evidence remains subject to its stated verifier.

## Need-by, impact, and fallback

Need-by: G1 architecture/data alignment; no calendar date overrides acceptance. Late impact: production schema, final UI, checkout, inventory, fulfilment, analytics, and security decisions cannot be frozen without material rework. Safe fallback: continue only B1/B2 framework, security/test design, and sample-data local work; keep public exposure and checkout disabled.

## Change control

This is initial v1.0.0 and supersedes nothing. Changes require a new version, change summary, impacted fields/consumers, migration/testing impact, owner approval, and explicit receiver disposition. Neither side silently rewrites the other’s source truth.

## Receiver result

Controller: `CONDITIONALLY_ACCEPT`, 2026-08-01. Conditions and field-level corrections are authoritative in `docs/system-of-record/CROSS_AGENT_HANDOFF_STATUS.md`. Side A response remains required.
