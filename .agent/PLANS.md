# Codex ExecPlans for the Fashion Commerce Platform

An **ExecPlan** is a living, executable specification for a substantial workstream. It must allow a fresh agent with only the repository to understand the goal, resume progress and verify the result.

## When required
Create or update an ExecPlan when work:

- crosses more than one work package or repository component;
- requires coordination between Side A and Side B;
- spans more than one execution session;
- changes architecture, customer promises, compliance assumptions, money flow, inventory truth or launch gates;
- has a meaningful rollback or migration requirement.

## Required sections

1. **Title, owner, status and gate**
2. **Purpose and observable outcome**
3. **Context and source documents read**
4. **Confirmed facts, assumptions and unresolved questions**
5. **Scope and explicit non-scope**
6. **Dependencies and required handoffs**
7. **Artifact list with stable IDs and target paths**
8. **Milestones in dependency order**
9. **Detailed implementation or production steps**
10. **Acceptance criteria**
11. **Validation commands, review procedures and expected evidence**
12. **Security, privacy, compliance and operational impact**
13. **Migration, rollback and recovery plan**
14. **Risks, mitigations and decision points**
15. **Progress log with timestamps**
16. **Decision log**
17. **Completion summary and residual work**

## Execution behavior

- Read the entire relevant plan before acting.
- Update progress and decisions as work proceeds, not only at the end.
- Keep milestones independently verifiable.
- Do not mark a milestone complete because files exist; execute its acceptance checks.
- Continue to the next non-blocked milestone without asking for permission.
- When blocked externally, finish all preparatory work, document the exact evidence needed, and proceed on unrelated work.
- Commit or checkpoint at coherent milestones when Git access is available.
