# Cross-Agent Handoff Status

| Control | Value |
|---|---|
| Artifact ID | SOR-G0-011 |
| Version | 2.0 |
| Owner | Controller / integration lead |
| Status | SELF-VALIDATED |
| Sources | HO-A-B-001 v1.0; SB-HO-B0-001 v1.0.0; HO-A-B-002 v1.0; HO-A-B-003 v1.1; SB-HO-B1-001 v1.0.0; Shared Interface Contract |
| Dependency ID | DEP-008 |
| Acceptance criteria | Each handoff envelope and payload is independently checked; exact disposition, field-level reasons, corrections, evidence, routing and next action are recorded |
| Validation | Controller envelope validator (18 fields) plus payload reconciliation; results in `CONTROLLER_VALIDATION_G1_M1.md` |
| Evidence | `docs/system-of-record/CONTROLLER_VALIDATION_G1_M1.md`; `evidence/side-a/g1/`; `evidence/side-b/g1/` |
| Consumer | Side A, Side B and G1 review |
| Risk / next action | SB-HO-B1-001 has two open corrections; Side B is unavailable until its session limit resets |
| Supersedes | Version 1.0 |

## Summary

| Handoff | Envelope | Controller disposition | Reason |
|---|---|---|---|
| HO-A-B-001 v1.0 | PASS 18/18 | CONDITIONALLY_ACCEPT | Valid 35-field business contract; technical mapping and negative tests were required in response |
| SB-HO-B0-001 v1.0.0 | PASS 18/18 | CONDITIONALLY_ACCEPT | Valid dependency request; many business values legitimately blocked; lifecycle vocabulary conflicted |
| HO-A-B-002 v1.0 | PASS 18/18 | SUPERSEDED by HO-A-B-003 | Closed 5 of 6 conditions; condition 4 left variant values pipe-packed |
| **HO-A-B-003 v1.1** | PASS 18/18 | **ACCEPT** | All 6 controller conditions closed and independently reproduced |
| **SB-HO-B1-001 v1.0.0** | **FAIL 16/18** | **CONDITIONALLY_ACCEPT** | Technical content verified and strong; envelope incomplete and one illegal status value |

## HO-A-B-003 v1.1 — ACCEPT

All six conditions previously sent to Side A are closed. The controller re-ran Side A's validation
harness directly (`python evidence/side-a/g1/side_a_m1_validation.py`, exit 0, `failures=none`) and
performed independent spot-checks rather than relying on the agent's summary.

| # | Condition | Evidence | State |
|---|---|---|---|
| 1 | Germany / VS-TEE-001 as DRAFT hypotheses only | K1: no full ACCEPT, 6 fields DRAFT | CLOSED |
| 2 | Unknown fields carry dependency and evidence status, no filler | K2: 52 blocked entries, all `null` with a dependency ID | CLOSED |
| 3 | Reject `draft\|approved\|active\|archived` lifecycle | K3: canonical vocabulary adopted, technical state cannot imply sellable | CLOSED |
| 4 | Atomic rows; nested fields enumerated | K4b: 9 instance rows, 1:1 with payload, no multivalue cells | CLOSED this cycle |
| 5 | No PoC copy, cotton/origin, price, stock or imagery as approved values | K5: controller traced all 4 matches to a blocked field name and `explicitly_rejected_as_truth` | CLOSED |
| 6 | Complete disposition and minimal explicit payload | K6: 65 atomic + 9 instance rows, no coverage gap | CLOSED |

Side A self-reported the condition-4 residual defect against its own prior work and declined to
edit a G0 evidence file over a false positive in its own scanner. Both behaviours are correct under
the evidence-discipline rules and are recorded as such.

## SB-HO-B1-001 v1.0.0 — CONDITIONALLY_ACCEPT

The technical substance is accepted and was independently reproduced by the controller: 53 tests
pass on a clean interpreter, 19 of 19 guard mutations were detected with the suite restored to
green, sellable assessment fails closed with exit 1, float money is rejected on authoritative
paths, and both data fixtures are byte-identical to the pristine reference pack.

Two defects block full acceptance. Both are contract violations, not preferences. Neither is
repairable by the controller, because `docs/side-b/` and `handoffs/outgoing/side-b/` are Side B's
exclusive write lane.

| # | Defect | Rule breached | State |
|---|---|---|---|
| 1 | `docs/side-b/EVIDENCE_INDEX.csv` carries `SUPERSEDED` in the readiness `status` column, 4 rows | `AGENTS.md` permits exactly seven readiness statuses | OPEN |
| 2 | `SB-HO-B1-001` omits the required `assumptions` and `questions` envelope fields | Shared Interface Contract requires both in every handoff | OPEN |

Correction request was issued to Side B. Side B acknowledged both and began work, archiving
`SB-HO-B1-001_..._v1_0_0.md` at 20:01, then terminated on an account session limit before applying
either fix. **Neither correction is applied.** The archived copy is a partial state, not a
corrected version. Disposition remains CONDITIONALLY_ACCEPT until Side B returns.

## Controller-owned finding — not a Side B defect

Side B's risk register uses `OPEN / FIXED / MITIGATED / PARTIALLY MITIGATED / BLOCKED` in
`current_status`. This was initially flagged by the controller validator and then withdrawn on
review: risk state is a different axis from artifact readiness, and Side B's vocabulary is
semantically correct. Side A instead reuses readiness words (`SELF-VALIDATED`, `BLOCKED`) for risk
state. The real gap is that the program never declared a risk-state vocabulary. Resolved by DEC-009
in `DECISION_LOG.md`; Side A is to align to Side B, not the reverse.

## Change control

Routed copies preserve original handoff IDs and versions. Each side issues new versioned responses
and must not silently edit a sender's source handoff. No schema is frozen. No handoff in this
program has yet been REJECTED.
