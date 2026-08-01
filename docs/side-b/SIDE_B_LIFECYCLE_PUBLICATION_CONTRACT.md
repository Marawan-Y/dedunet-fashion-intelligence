# Business Lifecycle and Technical Publication Contract

- Artifact ID: SB-AR-B3-002
- Version: 1.1.0 (supersedes 1.0.0; content unchanged, evidence reference repaired and mutation proof added)
- Owner: Side B Platform Lead; business transitions remain Side A-owned
- Source inputs/dependencies: DEC-005; SOR-G0-009; HO-A-B-001 v1.0; BPC-A-003
- Acceptance criteria: canonical business lifecycle is exact; technical publication is separate; no `active`/`published` state can bypass `sellable`; transitions and failure behavior are explicit and executable.
- Validation procedure/result: implemented in `app/candidate_activation.py`; negative tests cover public-before-sellable and activation blockers; guard removal is detected by mutation M12 and M13; AUTOMATED-TESTED.
- Evidence path: `evidence/side-b/g1/SB-EV-G1-002_candidate_green.md`; `evidence/side-b/g1/SB-EV-G1-003_guard_mutation_matrix.md`

> **v1.0.0 defect corrected:** v1.0.0 cited `SB-EV-G1-002_candidate_green.md` as its evidence path, but that file did not exist — only the RED-stage record SB-EV-G1-001 was present. The green evidence now exists and is attributable to this working tree. No rule in this contract changed.
- Readiness status: AUTOMATED-TESTED
- Downstream consumer: Side A, B3 validator, B7 catalog publication, B9 storefront
- Remaining risks/next action: named approval roles and evidence are absent; no real candidate may transition beyond `candidate` from this artifact alone.

## Canonical business lifecycle

`fixture -> candidate -> sample -> approved -> sellable -> retired`

Side A owns the business meaning and authorized transition. Side B enforces enum values, audit requirements, and activation prerequisites. The lifecycle has no `active` value.

| State | Meaning | Maximum technical publication |
|---|---|---|
| fixture | Synthetic/test-only data | `hidden` or local `preview` with synthetic marking |
| candidate | Proposed product hypothesis | `hidden` or local `preview` |
| sample | Physical sample exists, but not fully approved | `hidden` or controlled `preview` |
| approved | Product approval exists, but commercial/market/stock gates may remain | `hidden` or controlled `preview` |
| sellable | Every required evidence, price, operator, batch/QC, stock, content/rights, policy, market and approval gate passes | `public` may be requested |
| retired | No new sale/public activation | `hidden`; historical records retained |

## Separate technical publication state

`hidden | preview | public`

`preview` is never a synonym for market eligibility. `public` requires the business lifecycle to equal `sellable`, and the activation validator must return zero errors at request time. `active`, `published`, route availability, API presence, or nonzero database stock never substitute for `sellable`.

The supplied candidate is `candidate + preview + synthetic_fixture=true + opening_stock=0`. A simulated `sellable + public` assessment fails closed and does not mutate the source record.

## Transition enforcement

Any future transition must record prior/new state, named authorized approver, timestamp, reason, schema version, source artifact/evidence IDs, and validation result. Direct jumps, expired evidence, synthetic evidence, missing roles, or validator errors are rejected. Retirement does not delete audit/evidence history.
