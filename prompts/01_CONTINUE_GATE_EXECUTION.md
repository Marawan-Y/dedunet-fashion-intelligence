# Continue Execution — One Gate at a Time

Read `AGENTS.md`, `.agent/PLANS.md`, the current `docs/system-of-record/MASTER_EXECUTION_PLAN.md`, all registers, the latest status reports and all unprocessed handoffs.

Act as the controller. Spawn `side_a_business` and `side_b_platform` only for bounded tasks they own. Wait for both when work is parallel, then reconcile through shared system-of-record files.

Execute the next dependency-ordered milestone for the **current gate only**:

1. Verify the gate's entry conditions and identify non-blocked tasks.
2. Assign exact artifact IDs, target paths, acceptance criteria and evidence requirements.
3. Require agents to inspect relevant upstream artifacts before editing.
4. Require validation, negative-path checks and cross-side reconciliation.
5. Process every handoff as ACCEPT, CONDITIONALLY_ACCEPT or REJECT.
6. Update the Master Execution Plan, deliverable/dependency/risk registers, decision log and gate register.
7. Fix failed checks and repeat until the milestone passes or a genuine external blocker remains.
8. For external blockers, produce complete action dossiers and continue unrelated work.
9. Do not start the next gate until the current gate has a formal controller review.

End with: completed artifacts and evidence, failed criteria, unresolved blockers, decisions needed, current gate recommendation and next executable milestone.
