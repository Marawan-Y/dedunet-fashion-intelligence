# Side A Artifact Catalog and Definition-of-Done Metadata

| Field | Value |
|---|---|
| Artifact ID / version | A0-CATALOG-001 / 1.2 |
| Owner | Side A Business/Product Lead |
| Sources / dependencies | AGENTS.md nine-part definition; A0-PLAN-001; SOR-G0-010; SOR-G0-011; G1 M1 artifacts |
| Acceptance criteria | Every Side A artifact through G1 M1 is listed with stable ID/version, owner, sources/dependencies, criteria, validation/evidence, status, consumer, risk and next action |
| Validation / evidence | PASS / EV-A1-002 |
| Status | SELF-VALIDATED |
| Downstream consumer | Controller and future Side A agents |
| Risk / next action | Flat CSV metadata depends on this catalog and deliverable register; route HO-A-B-003 and maintain both atomically |

Version 1.2 supersedes 1.1. Change: added A1-DISP-002, HO-A-B-003, EV-A1-002 and A1-VAL-001; bumped A0-EXT-001 to 1.1, A1-PAYLOAD-001 to 0.1.1 and A1-CYCLE-001 to 1.1; marked HO-A-B-002 and EV-A1-001 as retained history. No artifact was deleted.

For CSV artifacts, this catalog plus `SIDE_A_DELIVERABLE_REGISTER.csv` supplies file-level definition-of-done metadata without inserting non-tabular rows into machine-readable data.

| Artifact ID / version | Path | Owner | Inputs / dependencies | Acceptance criteria | Validation / evidence | Status | Consumer | Remaining risk / next action |
|---|---|---|---|---|---|---|---|---|
| A0-PLAN-001 / 1.0 | docs/side-a/SIDE_A_EXECPLAN_G0.md | Side A Business/Product Lead | Binding sources; repository | 17 required sections and resumable | PASS / EV-A0-002 | SELF-VALIDATED | Controller | Human governance missing; execute EXT-01 |
| A0-CHARTER-001 / 1.0 | docs/side-a/PROGRAM_CHARTER.md | Side A Business/Product Lead | A0-PLAN-001; DEP-A-001 | Mission/ownership/evidence/scope/gate explicit | PASS / EV-A0-002 | SELF-VALIDATED | All Side A work | Assign named authorities |
| A0-INTAKE-001 / 1.0 | docs/side-a/SIDE_A_INTAKE_REPORT.md | Side A Business/Product Lead | Full repository; EV-A0-001 | Facts/gaps/contradictions/rejections complete | PASS / EV-A0-002 | SELF-VALIDATED | Controller/Side B | External evidence absent; execute dossiers |
| A0-FACT-REG-001 / 1.1 | docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv | Side A Business/Product Lead | A0-INTAKE-001; SOR-G0-007/009 | Classified/sourced/owned/actionable records | PASS / EV-A1-001 | SELF-VALIDATED | Controller | Update after receiver mapping or evidence |
| A0-ASM-REG-001 / 1.0 | docs/side-a/ASSUMPTION_REGISTER.csv | Side A Business/Product Lead | A0-VS-001 | Reversibility/test/trigger/fallback set | PASS / EV-A0-002 | SELF-VALIDATED | Controller | Human disposition pending |
| A0-DEC-REG-001 / 1.1 | docs/side-a/DECISION_LOG.md | Side A Business/Product Lead | Intake; SOR-G0-007; dependencies | Options/recommendation/approver/trigger set | PASS / EV-A1-001 | SELF-VALIDATED | Controller/humans | Lifecycle mapping and human approvers pending |
| A0-DEP-REG-001 / 1.1 | docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv | Side A Business/Product Lead | Intake; dossiers; M1 handoffs | Provider/consumer/gate/criteria/impact/fallback set | PASS / EV-A1-001 | SELF-VALIDATED | Controller | Process DEP-A-009; preserve external blockers |
| A0-RISK-REG-001 / 1.1 | docs/side-a/SIDE_A_RISK_REGISTER.csv | Side A Business/Product Lead | Intake; M1 contract reconciliation | Risk control/escalation fields complete | PASS / EV-A1-001 | SELF-VALIDATED | Controller | Verify R-A-009 in receiver response |
| A0-EVID-REG-001 / 1.1 | docs/side-a/EVIDENCE_INDEX.csv | Side A Business/Product Lead | EV-A0-001 through EV-A1-001 | Evidence scope/status/limitations explicit | PASS / EV-A1-001 | SELF-VALIDATED | Controller | Add receiver evidence append-only |
| A0-DELIV-REG-001 / 1.1 | docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv | Side A Business/Product Lead | All cycle artifacts | Required register columns and all artifacts present | PASS / EV-A1-001 | SELF-VALIDATED | Controller | Maintain atomically |
| A0-VS-001 / 1.0 | docs/side-a/SIDE_A_VERTICAL_SLICE_RECOMMENDATION.md | Side A Product Lead | Intake; DEP-A-002 to 009 | One product/market/web proof with stop rules | PASS / EV-A0-002 | SELF-VALIDATED | Side B/controller | Candidate not real; authorize/test |
| A0-BPC-001 / 1.0 | docs/side-a/SIDE_A_BUSINESS_PLATFORM_CONTRACT.csv | Side A Business/Product Lead | B3 fields; A0-VS-001 | Field owner/truth/evidence/missing behavior/AC set | PASS / EV-A0-002 | SELF-VALIDATED | Side B | Receiver decision pending |
| A0-GATE-001 / 1.0 | docs/side-a/SIDE_A_G0_ASSESSMENT.md | Side A Business/Product Lead | All G0 artifacts | Strict criteria and recommendation set | PASS / EV-A0-002 | SELF-VALIDATED | Controller | NO-GO until governance passes |
| A0-ROADMAP-001 / 1.0 | docs/side-a/SIDE_A_GATE_ROADMAP.md | Side A Business/Product Lead | A1-A18; dependency register | Evidence-ordered gate map | PASS / EV-A0-002 | SELF-VALIDATED | Controller | Reconcile into master plan |
| A0-BACKLOG-001 / 1.0 | docs/side-a/SIDE_A_FIRST_2_WEEK_BACKLOG.md | Side A Business/Product Lead | G0 assessment | Task/output/owner/evidence/stop rule set | PASS / EV-A0-002 | SELF-VALIDATED | Side A/controller | Assign and execute P0 tasks |
| A0-EXT-001 / 1.1 | docs/side-a/work_packages/side_a/EXTERNAL_ACTION_DOSSIERS.md | Side A Business/Product Lead | All ten BLOCKED dependencies; SOR-G0-005 | Ten dossiers each carrying all eight required elements | Eight-element audit PASS / EV-A1-002 (C11) | BLOCKED | Human/specialist owners | Assign named parties and execute EXT-01 first |
| HO-A-B-001 / 1.0 | handoffs/outgoing/side-a/HO-A-B-001_G0_VERTICAL_SLICE_INPUTS_v1.md | Side A Business/Product Lead | A0-VS-001; A0-BPC-001 | Complete envelope and field-level decision request | PASS envelope / EV-A0-002 | DRAFT | Controller/Side B | Receiver disposition pending |
| EV-A0-001 / 1.0 | evidence/side-a/bootstrap/SIDE_A_REPOSITORY_INVENTORY.txt | Side A Business/Product Lead | Repository inspection | Scope/absence/limitations recorded | Self-review | SELF-VALIDATED | Controller | Independently compare |
| EV-A0-002 / 1.0 | evidence/side-a/bootstrap/SIDE_A_G0_CONSISTENCY_REVIEW.md | Side A Business/Product Lead | All G0 artifacts | Commands/checklist/results retained | Self-review | SELF-VALIDATED | Controller | Re-run after change |
| A0-CATALOG-001 / 1.1 | docs/side-a/ARTIFACT_CATALOG.md | Side A Business/Product Lead | All artifacts through G1 M1 | Every artifact has nine-part metadata and stable path | PASS / EV-A1-001 | SELF-VALIDATED | Controller | Maintain atomically with deliverable register |
| A0-CYCLE-001 / 1.0 | docs/side-a/STATUS_REPORT_G0_v1.md | Side A Business/Product Lead | All G0 outputs | Nine mandated G0 cycle sections | PASS / EV-A0-002 | SELF-VALIDATED | Controller | Immutable archived cycle history |
| A1-DISP-001 / 1.0 | docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv | Side A Business/Product Lead | SB-AR-B3-001; SOR-G0-011 | All 65 atomic fields have disposition/owner/state/dependency/reason/impact/action | PASS / EV-A1-001 | SELF-VALIDATED | Controller/Side B | Receiver returns 65 schema mappings |
| A1-DISP-002 / 1.0 | docs/side-a/SB_HO_B0_001_VARIANT_INSTANCE_DISPOSITIONS.csv | Side A Product/Ops Lead | SB-AR-B3-001; A1-DISP-001; SOR-G0-011 condition 4 | Nine instance rows match payload `variants[n]` one to one with no multi-value cell | PASS / EV-A1-002 (K4b) | SELF-VALIDATED | Controller/Side B | Receiver returns per-instance mapping and error keys |
| A1-PAYLOAD-001 / 0.1.1 | docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json | Side A Product Lead | SOR-G0-009; A1-DISP-001; A1-DISP-002 | Only DRAFT hypotheses valued; unsupported fields BLOCKED/null with dependency IDs; zero sellable cap | PASS structure / EV-A1-002 | DRAFT | Side B | Metadata-only bump from 0.1.0; candidate only; schema validation pending |
| HO-A-B-002 / 1.0 | handoffs/outgoing/side-a/HO-A-B-002_SB_B0_INPUT_RESPONSE_v1.md | Side A Business/Product Lead | SB-HO-B0-001; A1-DISP-001; A1-PAYLOAD-001 | Full response envelope and receiver criteria | PASS envelope / EV-A1-001 | DRAFT | Controller/Side B | Superseded by HO-A-B-003 v1.1; retained as history, do not delete |
| HO-A-B-003 / 1.1 | handoffs/outgoing/side-a/HO-A-B-003_SB_B0_INPUT_RESPONSE_v1_1.md | Side A Business/Product Lead | HO-A-B-002; SOR-G0-011; A1-DISP-001/002; A1-PAYLOAD-001 | Envelope complete and each of the six controller conditions proven closed with a named artifact and check | PASS envelope and closure / EV-A1-002 | DRAFT | Controller/Side B | Receiver disposition pending |
| EV-A1-001 / 1.0 | evidence/side-a/g1/EV_A1_001_M1_CONSISTENCY_VALIDATION.md | Side A Business/Product Lead | All Side A M1 artifacts/registers | Exact parse/status/lifecycle/null/stock/prohibited-value checks | Self-review | SELF-VALIDATED | Controller | Retained as history; re-proven by EV-A1-002 |
| EV-A1-002 / 1.0 | evidence/side-a/g1/EV_A1_002_M1_CONDITION_CLOSURE_VALIDATION.md | Side A Business/Product Lead | All Side A M1 artifacts, registers and dossiers; SOR-G0-011 | Command and output preserved; C1-C11 and K1-K6 all pass | Executed script, exit 0 | SELF-VALIDATED | Controller | Re-run after receiver response or artifact change |
| A1-VAL-001 / 1.0 | evidence/side-a/g1/side_a_m1_validation.py | Side A Business/Product Lead | Side A registers, dispositions, payload, dossiers | Runs from repository root, exits 0 on PASS and non-zero on any failed control | Executed, exit 0 / EV-A1-002 | AUTOMATED-TESTED | Controller | Extend with receiver-mapping checks |
| A1-CYCLE-001 / 1.1 | docs/side-a/STATUS_REPORT.md | Side A Business/Product Lead | All Side A M1 artifacts | Nine mandatory current cycle sections | PASS / EV-A1-002 | SELF-VALIDATED | Controller | Reconcile and route HO-A-B-003 |
