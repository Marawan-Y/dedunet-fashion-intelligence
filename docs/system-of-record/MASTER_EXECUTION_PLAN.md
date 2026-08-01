# Master Execution Plan — Evidence-Backed One-Product Market Preparation

| Control | Value |
|---|---|
| Artifact ID | SOR-G0-010 |
| Version | 2.0 |
| Owner | Controller / integration lead |
| Gate / status | G0 / DRAFT |
| Sources and dependencies | All binding sources; both G0 intakes; SOR-G0-002 through SOR-G0-009; DEP-001 through DEP-012 |
| Acceptance criteria | All 17 ExecPlan sections; A1-A18 and B1-B22 mapped into dependency-ordered milestones; objective checks/evidence/rollback/decisions/progress present |
| Validation / evidence | Controller structural and cross-side reconciliation; final validation recorded in the progress log |
| Downstream consumers | Side A, Side B, human owners and future controller sessions |
| Remaining risk / next action | G0 governance is externally blocked; execute the non-blocked G1 M1 contract/runtime milestone and update this plan |

## 1. Title, owner, status and gate

Title and controls are above. The plan is `DRAFT` because the first G1 milestone is not yet accepted and human G0 evidence is missing. G0 recommendation is `NO_GO`.

## 2. Purpose and observable outcome

Prepare one evidence-backed product for one European market through an honest web-first commerce and operational proof. Observable completion is a traceable real product, accepted cross-side contracts, tested reversible commerce flow, external approvals/evidence, controlled launch and measured scale/stop decision.

## 3. Context and source documents read

The controller read `AGENTS.md`, `.agent/PLANS.md`, the Shared Interface Contract, both system prompts, both complete Markdown execution books and `platform/poc/README.md`; inventoried and inspected every supplied path. Both accountable agents completed equivalent side-specific reads and produced validated G0 intakes.

## 4. Confirmed facts, assumptions and unresolved questions

`MASTER_FACT_ASSUMPTION_MATRIX.csv` is authoritative. Confirmed: the sample backend tests/validator and Docker image builds pass within documented limits; runtime/mobile do not. Assumptions: Germany, one black oversized T-shirt and controlled EU stock. Unresolved: all named human authority, demand, physical product, factory, claim, economics, operator, policy, provider and operational evidence.

## 5. Scope and explicit non-scope

Scope: A1-A18 and B1-B22 only as sequenced below, with the first approved increment limited to contract/schema/runtime proof for `VS-TEE-001`. Non-scope now: storefront redesign, final branding, catalog expansion, live checkout/provider selection, mobile, broad AI, microservices, Kubernetes, public deployment or production claims.

## 6. Dependencies and required handoffs

`MASTER_DEPENDENCY_REGISTER.csv` controls providers, consumers, gates, evidence and fallbacks. All cross-side inputs use the Shared Interface Contract. Current handoff dispositions are in `CROSS_AGENT_HANDOFF_STATUS.md`; routed copies are in each receiver's incoming directory.

## 7. Artifact list with stable IDs and target paths

Current and next artifacts are in `MASTER_DELIVERABLE_REGISTER.csv`. Each side maintains its own complete delivery register; the controller registers reconciled program artifacts and milestone outputs here.

## 8. Milestones in dependency order

| Milestone | Gate | Work-package mapping | Objective / exit evidence | State |
|---|---|---|---|---|
| M0 Repository intake and technical baseline | G0 | A1 governance intake; B1/B2/B20 baseline | Full inventory, two intakes, exact PoC evidence, registers and handoffs | completed knowledge work |
| M0.1 Governance authority | G0 | A1; B1/B2 access/account policy | Founder/IP/company baseline, named authorities/accounts and spend limits | BLOCKED on DEP-001/011 |
| M1 Contract and non-sellable candidate proof | first G1 milestone | A2/A4/A5/A7/A8/A10/A11/A12/A13/A17 input fields; B2/B3/B4/B7/B19/B20 | 35-field dispositions, canonical lifecycle/evidence gates, negative tests, isolated attributable runtime | content MET and independently reproduced; acceptance held on 2 open Side B corrections |
| M2 Market/product thesis | G1 | A2/A4/A8/A14; B9/B16 | Traceable research/high-intent evidence, competitor/price map, authorized single-product thesis, instrumented non-transactional test | BLOCKED on DEP-002/005 |
| M3 Real product and makeability truth | G2 | A5/A6/A7/A8/A9/A10/A17; B3/B7/B13/B20 | Approved sample/tech pack/BOM/measurements, factory/material/claim/QC/cost evidence, validated complete record | BLOCKED on DEP-003/004/005 |
| M4 Importable sellable staging MVP | G3 | A10/A11/A12/A13/A15/A16/A17; B5/B6/B7/B8/B9/B11/B12/B14/B15/B19/B20 | Accepted operator/compliance/policy/content/rights; authoritative checkout/order/inventory/return flows and recovery tests | BLOCKED on DEP-005/006/007/010 |
| M5 Operational beta | G4 | A11/A12/A15/A16/A18; B11/B12/B14/B15/B16/B18/B19/B20/B21/B22 | Real test import/package/shipment/return/refund/reconciliation, UAT, privacy/security, restore/incident rehearsal | BLOCKED |
| M6 Controlled market launch | G5 | A14/A18 plus launch-critical A work; B9/B11-B16/B18-B22 | Released stock, verified production accounts/registrations, monitoring/support/finance and named go/no-go | BLOCKED |
| M7 Scale/stop | G6 | A14/A17/A18; B8/B10/B16/B17/B18-B22 | Real demand/returns/margin/quality/reliability evidence; mobile/AI only if value gate passes | BLOCKED |

Every A1-A18 and B1-B22 package is represented. A3 brand and B6 design begin only after A2 positioning; B10 mobile is deferred to M7; B17 AI is deferred to M7; no later milestone starts merely because a date arrives.

## 9. Detailed implementation or production steps

For M1, Side A returns field-level dispositions to SB-HO-B0-001 and a provisional candidate payload containing only evidence-backed values or explicit blocked dependencies. Side B returns a 35-row technical mapping to HO-A-B-001, implements or specifies lifecycle/evidence validation, adds negative tests before fixes, isolates Compose ports and records attributable smoke/log/down evidence. Both update owned registers/evidence/handoffs. The controller rechecks conditions and updates shared files.

For later milestones, execute the mapped work packages only when their dependencies enter an acceptable evidence status. Physical, legal/provider and real operational actions use the Side A external-action dossiers and are never inferred from prepared documents.

## 10. Acceptance criteria

M1 accepts only when both handoff conditions close, lifecycle and money representations reconcile, unsupported fields cannot activate, negative tests pass, and runtime evidence belongs to this checkout. Later gates use `GATE_REGISTER.md`. No artifact is complete without the nine repository definition-of-done controls.

## 11. Validation commands, review procedures and expected evidence

Minimum M1 technical checks: Python compile, backend tests, product validator, contract/negative tests, Compose config/build, isolated `up`, attributed health/catalog/storefront checks, logs and `down`. Side A runs CSV/status/ID/evidence-path and contract consistency checks. Exact commands, outputs, exit codes and limitations go under `evidence/side-b/g1/` and `evidence/side-a/g1/`.

Controller validation parses all CSVs, checks allowed statuses/duplicate IDs/path existence/ExecPlan sections/handoff fields, rehashes immutable sources and scans for unsupported completion language.

## 12. Security, privacy, compliance and operational impact

No real customer data is required for M1. The PoC remains local. Unsafe admin defaults, stored XSS, float money, non-transactional inventory, identity, secrets, privacy, monitoring and recovery are launch blockers tracked in `MASTER_RISK_REGISTER.csv`. No legal/compliance conclusion is created by this plan.

## 13. Migration, rollback and recovery plan

Documentation changes are versioned and superseded, never silently overwritten. M1 schema work must preserve the original sample fixture or provide reversible migration plus validation. Local Compose uses isolated project/ports and removes only its own resources. JSON-to-PostgreSQL migration later requires checksummed export, dry-run import, backups, reconciliation and rehearsed restore/forward-fix. No destructive Git operation is authorized.

## 14. Risks, mitigations and decision points

`MASTER_RISK_REGISTER.csv` and `DECISION_LOG.md` are authoritative. Critical decisions requiring humans are market authorization, product authorization, governance/spend, merchant/importer model and later provider/budget selection. Reversible technical decisions are modular monolith, web-first, evidence-gated lifecycle and minor-unit money.

## 15. Progress log with timestamps

- 2026-08-01: controller completed mandatory reads, full baseline inventory and source integrity checks.
- 2026-08-01: exactly two accountable agents completed parallel G0 intakes; 21 governed artifacts per side created.
- 2026-08-01: backend tests 4/4 and product validator passed after setup; Docker images built; runtime port collision and mobile peer conflict preserved.
- 2026-08-01: controller reconciled facts/risks/contracts, rejected unsupported PoC truth and set G0 `NO_GO` / `BLOCKED`.
- 2026-08-01: initial handoffs conditionally accepted and first M1 tasks prepared for delegation.
- 2026-08-01T18:12+02:00: both accountable agents re-engaged in parallel on M1 with disjoint write lanes. `side_a_business` and `side_b_platform` are Codex CLI definitions and are not registered subagent types in the executing environment; both were run carrying their `developer_instructions` verbatim. Lane compliance later verified by mtime.
- 2026-08-01T19:00+02:00: controller integrity pass — 7/7 immutable source hashes stable, 19/19 registers parse with unique primary keys, 3/3 ExecPlans at 17/17 sections, 5/5 then 6/8 handoff envelopes valid. Two controller-validator false positives (foreign-key columns read as primary keys; `evidence/gate` prose read as a path) were corrected in the harness rather than reported as defects.
- 2026-08-01T19:40+02:00: Side A closed all six HO-A-B-001 conditions and issued HO-A-B-003 v1.1. Controller re-ran Side A's harness directly (exit 0) and traced every `cotton`/`Egypt`/`origin` occurrence to a blocked field name or to `explicitly_rejected_as_truth`. Disposition ACCEPT.
- 2026-08-01T20:00+02:00: Side B delivered the M1 platform increment. Controller independently reproduced 53 passing tests on a clean interpreter, 19/19 detected guard mutations with 0 survivors, fail-closed sellable assessment at exit 1, integer-minor-unit money with binary floats rejected, and byte-identical fixtures.
- 2026-08-01T20:00+02:00: **the controller's own earlier `17 passed` baseline was found contaminated.** `__pycache__` shipped inside the pack carried bytecode compiled at `C:\Users\User\Desktop\Platform\...`; preserved mtime and size caused Python to accept the stale `.pyc`. Side B found and reported this against its own interest. The baseline is superseded by the attributed re-run; DEC-011 pins all future evidence runs.
- 2026-08-01T20:05+02:00: two field-level corrections issued to Side B (illegal `SUPERSEDED` readiness status; handoff missing `assumptions` and `questions`). Side B acknowledged both, archived a copy at 20:01, then terminated on an account session limit before applying either. Both remain OPEN and are not repairable by the controller, which may not write into a side lane.
- 2026-08-01T20:10+02:00: controller recorded DEC-009 through DEC-012 and risks R-013 through R-017, and updated the gate register. G0 remains `NO_GO`/`BLOCKED` on the same three governance criteria; M1 content is met with two open corrections.

## 16. Decision log

See `DECISION_LOG.md`. No `DRAFT` or `BLOCKED` human decision is an approval.

## 17. Completion summary and residual work

G0 knowledge-work mobilization and the controller system of record are complete. G0 exit remains
blocked externally by governance/authority evidence — the same three criteria as at version 1.0,
because only a human can satisfy them.

M1, the first non-blocked G1 milestone, is **substantively complete and independently verified**:
the cross-side field contract is reconciled, the candidate cannot activate without evidence, the
negative guards are proven load-bearing by mutation, money is integer minor units, and runtime
evidence is attributable to this checkout. Two Side B corrections remain OPEN (an illegal readiness
status and an incomplete handoff envelope); both are inside Side B's exclusive write lane and are
waiting on that agent's availability, not on any external party.

Residual work after M1 closes is customer and price evidence (M2), then physical product and
economics proof (M3). All later commerce and launch work remains blocked. Three launch blockers —
stored XSS, non-transactional inventory and shipped secrets — are OPEN with no named risk owner and
must not be closed by an agent acting alone.
