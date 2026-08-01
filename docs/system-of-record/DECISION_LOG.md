# Shared Decision Log

| Control | Value |
|---|---|
| Artifact ID | SOR-G0-007 |
| Version | 2.0 |
| Owner | Controller / integration lead |
| Status | SELF-VALIDATED |
| Sources | Side A and Side B decision logs, shared contract and gate criteria |
| Acceptance criteria | Every shared/material decision has options, owner, status, rationale, trigger and next action |
| Validation | Cross-side ownership and reversibility review passed |
| Evidence | `CROSS_AGENT_HANDOFF_STATUS.md`; both agent validation records |
| Consumer | Both sides and human decision owners |
| Risk / next action | Human approvers are unassigned; `DRAFT`/`BLOCKED` decisions are not effective approvals |

| ID | Decision | Options | Recommendation / disposition | Owner / approver | Status | Trigger / next action |
|---|---|---|---|---|---|---|
| DEC-001 | Initial market | Germany / Netherlands / another one-country market | Germany as reversible research and schema hypothesis only | Human executive sponsor | DRAFT | Authorize or replace before G1 exit |
| DEC-002 | First product | Oversized T-shirt / shirt / abaya / another single style | Black oversized crew-neck T-shirt, S/M/L, for first proof | Human product approver | DRAFT | Authorize before tech pack/sample request |
| DEC-003 | Fulfilment model | Controlled EU batch / per-order Egypt dispatch / selected provider model | Controlled EU batch subject to cost/adviser/3PL evidence | Human operations/finance owner | DRAFT | Decide before test import or public promise |
| DEC-004 | Technical shape | Modular monolith / microservices; web first / mobile concurrent | Modular monolith and responsive web first; defer mobile | Side B with controller concurrence | SELF-VALIDATED | Revisit on measured scale, isolation or repeat-use evidence |
| DEC-005 | Candidate lifecycle | Side A `fixture/candidate/sample/approved/sellable/retired` / Side B `draft/approved/active/archived` | Use Side A vocabulary as business lifecycle; Side B may add technical publication state but `active` must never imply `sellable` | Shared, schema controlled by Side B | SELF-VALIDATED | Side B returns mapping and negative tests in G1 |
| DEC-006 | Money representation | Decimal business amount / floating point / integer minor units | Side A owns approved gross amount; Side B stores/calculates integer minor units; no binary float for authoritative commerce | Shared | SELF-VALIDATED | Implement only after price approval; test schema meanwhile |
| DEC-007 | Merchant/importer structure | EU entity importer / Egypt seller with accepted EU roles / merchant-of-record provider | No selection without qualified legal/tax/customs comparison | Human executive/legal/finance owners | BLOCKED | Execute EXT-06 before checkout architecture freezes |
| DEC-008 | Mobile dependency conflict | Force install / align official compatible set / defer | Defer; do not force peer dependencies | Controller / Side B | SELF-VALIDATED | Separate approved mobile cycle if web evidence justifies it |
| DEC-009 | Risk-state vocabulary | Reuse the seven readiness statuses for risks / declare a separate risk-state vocabulary | Declare a separate axis: `OPEN`, `PARTIALLY MITIGATED`, `MITIGATED`, `FIXED`, `ACCEPTED`, `BLOCKED`. Readiness statuses describe artifacts, not risks. Side A aligns to Side B's usage | Controller | SELF-VALIDATED | Side A to migrate `SIDE_A_RISK_REGISTER.csv` `status` to the risk axis next cycle |
| DEC-010 | Money wire-format break | Keep `price_eur` decimal on the wire / move to `price_minor_units` integer | Breaking change accepted: integer minor units are authoritative; `price_eur` accepted at ingestion only as exact `Decimal`/string; binary floats rejected | Side B, controller concurrence; human owner to ratify | SELF-VALIDATED | Ratify before any external consumer integrates the API |
| DEC-011 | Stale-bytecode evidence contamination | Retain `SB-EV-BOOT-001..005` / re-run / retire as superseded | Retire as superseded. They were produced in a different checkout and partly executed foreign bytecode. All future evidence runs with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider` | Controller | SELF-VALIDATED | Side B to mark them superseded without deleting them |
| DEC-012 | Non-transactional inventory test | Write a passing concurrency test / leave the risk open with no test | Leave open with no test. A passing test against a design that cannot meet the requirement would be misleading. SB-RISK-005 stays `OPEN` until the datastore supports transactions | Side B, controller concurrence | SELF-VALIDATED | Revisit at B12 PostgreSQL/ledger work |

## Rejected assertions

The following supplied PoC values are `REJECTED` as business, customer or external truth: “Origin” brand/collection; all sample names/descriptions; `100% cotton`; Egyptian-cotton implications; `Made in Egypt`; prices; positive stock; default shipping/free-shipping thresholds; placeholder imagery; “real product data” wording; stylist output as customer validation; and any implied production/payment/tax/customs/carrier/launch readiness.
