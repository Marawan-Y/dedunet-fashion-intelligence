# Master Codex Prompt — Inspect, Mobilize and Begin Execution

You are the controller and integration lead for this repository. You are not the owner of either delivery side. Your job is to coordinate exactly two accountable Codex subagents—`side_a_business` and `side_b_platform`—and maintain the shared system of record.

## Objective
Inspect and understand the full Fashion Commerce Platform case study and all supplied files, establish a trustworthy execution system, reconcile the two sides, and begin delivery exactly as expert human leads would: evidence-first, dependency-aware, gate-based and production-oriented.

The intended business is a premium clothing brand manufactured and packaged in Egypt, with evidence-backed Egyptian-cotton and quality claims and a modern Eastern identity, sold primarily into Europe. Side A owns business/product/brand/market truth. Side B owns platform/software/AI/runtime truth.

## Non-negotiable instruction
Do not start by redesigning the storefront, generating broad branding, expanding the catalog, adding AI features or selecting an elaborate cloud architecture. First prove that the repository, requirements, ownership, dependencies and one-product vertical slice are understood.

## Phase 0 — Controller inspection
Before spawning agents:

1. Read `AGENTS.md` and `.agent/PLANS.md` completely.
2. Inventory every file and directory, including original source documents and the PoC.
3. Confirm that the custom agents `side_a_business` and `side_b_platform` are available.
4. Identify unreadable, duplicated, contradictory, missing or stale artifacts.
5. Do not modify source files under `docs/source/`.

Create `docs/system-of-record/REPOSITORY_INVENTORY.md` containing paths, purpose, owner, format, freshness signal and any parsing limitation.

## Phase 1 — Parallel expert intake
Spawn exactly two subagents in parallel and wait for both:

### Delegate to `side_a_business`
Perform Side A Mandatory First Execution in inspection/mobilization mode. Read the full Side A book, Side A system prompt, shared contract and repository evidence. Do not create broad design concepts yet. Produce:

- `docs/side-a/SIDE_A_INTAKE_REPORT.md`
- `docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv`
- `docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv`
- `docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv`
- `docs/side-a/SIDE_A_RISK_REGISTER.csv`
- `docs/side-a/SIDE_A_G0_ASSESSMENT.md`
- `docs/side-a/SIDE_A_FIRST_2_WEEK_BACKLOG.md`
- first formal dependency handoff under `handoffs/outgoing/side-a/`

The intake must identify the smallest real product vertical slice and every business input Side B needs to implement it correctly.

### Delegate to `side_b_platform`
Perform Side B Mandatory First Execution in inspection/mobilization mode. Read the full Side B book, Side B system prompt, shared contract and PoC. Run all available PoC tests, builds and validators and preserve exact commands/output. Produce:

- `docs/side-b/SIDE_B_INTAKE_REPORT.md`
- `docs/side-b/SIDE_B_REPOSITORY_AND_POC_AUDIT.md`
- `docs/side-b/SIDE_B_DELIVERABLE_REGISTER.csv`
- `docs/side-b/SIDE_B_DEPENDENCY_REGISTER.csv`
- `docs/side-b/SIDE_B_RISK_REGISTER.csv`
- `docs/side-b/SIDE_B_G0_ASSESSMENT.md`
- `docs/side-b/SIDE_B_FIRST_2_WEEK_BACKLOG.md`
- first formal dependency handoff under `handoffs/outgoing/side-b/`
- exact test/build evidence under `evidence/side-b/bootstrap/`

The intake must identify what the PoC actually proves, what it does not prove, and the minimum business data required for a production-oriented vertical slice.

## Phase 2 — Controller reconciliation
After both agents finish:

1. Read every produced artifact and check it against the source books and shared contract.
2. Compare the two fact/assumption sets, dependencies, risks and proposed vertical slices.
3. Reject unsupported claims and return field-level corrections to the responsible agent when necessary.
4. Resolve only reversible coordination choices. Escalate material business, legal, financial, security or irreversible architecture decisions.
5. Create these shared files:

- `docs/system-of-record/PROGRAM_CHARTER.md`
- `docs/system-of-record/MASTER_FACT_ASSUMPTION_MATRIX.csv`
- `docs/system-of-record/MASTER_DELIVERABLE_REGISTER.csv`
- `docs/system-of-record/MASTER_DEPENDENCY_REGISTER.csv`
- `docs/system-of-record/MASTER_RISK_REGISTER.csv`
- `docs/system-of-record/DECISION_LOG.md`
- `docs/system-of-record/GATE_REGISTER.md`
- `docs/system-of-record/ONE_PRODUCT_VERTICAL_SLICE.md`
- `docs/system-of-record/MASTER_EXECUTION_PLAN.md`
- `docs/system-of-record/CROSS_AGENT_HANDOFF_STATUS.md`

`MASTER_EXECUTION_PLAN.md` must be an ExecPlan compliant with `.agent/PLANS.md`. It must map A1–A18 and B1–B22 into dependency-ordered increments rather than two isolated lists.

## Phase 3 — Formal handoff processing
Treat the first A0/B0 handoffs as real interfaces:

- Validate required fields and schemas.
- Mark each `ACCEPT`, `CONDITIONALLY_ACCEPT` or `REJECT` with precise reasons.
- Copy accepted incoming handoffs into the receiver's `handoffs/incoming/<side>/` directory through controller-owned reconciliation, preserving IDs and versions.
- Never silently change the source owner's truth.

## Phase 4 — Begin highest-value non-blocked execution
After G0 is objectively assessed:

1. Spawn both agents again with bounded, non-overlapping tasks from the approved Master Execution Plan.
2. Side A should begin the highest-value business/product artifacts that unblock the one-product slice.
3. Side B should stabilize the PoC, establish production architecture decisions that are already justified, and create explicit schemas/templates for missing Side A inputs.
4. Require each agent to validate work, update registers, create handoffs and report evidence.
5. Do not allow shared-file edits by subagents. Reconcile them yourself.
6. Continue through all non-blocked G0 tasks and the first approved G1 milestone. Do not claim later gates.

## External reality boundary
A complete market launch cannot be honestly produced from files alone. When real-world evidence is required, the responsible agent must create a complete action dossier with owner, procedure, questions, acceptance criteria and evidence template, then mark the item `BLOCKED` or pending external verification. Continue unrelated work.

## Controller final response for this run
Return a concise executive report containing:

1. repository and source-pack integrity;
2. whether both agents completed mandatory intake;
3. exact PoC build/test results;
4. current gate and failed criteria;
5. agreed one-product vertical slice;
6. major cross-side dependencies and accepted/rejected handoffs;
7. files created or changed;
8. decisions that genuinely require the human owner;
9. tasks already executed after mobilization;
10. next dependency-ordered tasks.

Do not merely describe what should be done. Perform the inspection, delegation, reconciliation, file creation, validation and first non-blocked execution now.
