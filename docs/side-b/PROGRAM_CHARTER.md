# Side B G0 Program Charter

- Artifact ID: SB-AR-G0-002
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: AGENTS.md; Shared Contract v1; Side B System Prompt; Side B Execution Book v1.0; `.agent/PLANS.md`; `platform/poc/README.md`
- Acceptance criteria: defines accountable scope, evidence boundary, current gate, technical objective, vertical-slice constraint, and write ownership.
- Validation procedure/result: line-by-line consistency review against the named sources; SELF-VALIDATED.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-005_intake_validation.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller, Side A, all Side B work packages
- Remaining risks/next action: controller must reconcile the program-wide owner names, spend limit, target market, and Side A intake before G0 can pass program-wide.

## Charter

Side B owns platform architecture, schema/API/software state, security engineering, builds, deployment preparation, tests, and runtime truth. Side B does not own product claims, prices, market/policy truth, merchant/importer identity, physical stock, quality evidence, or legal conclusions.

Current gate is G0 Mobilized. This cycle's observable outcome is a complete technical intake: unchanged PoC baseline, initialized Side B registers, a resumable ExecPlan, objective G0 assessment, two-week backlog, and a field-level dependency request for one product in one explicitly selected market through a web-first slice.

The PoC remains a local sample-data demonstration. It is not a production store and is not authorized for public exposure or real customer, payment, carrier, identity, tax, or order processing.

Side B writes only under `docs/side-b/`, `evidence/side-b/`, `handoffs/outgoing/side-b/`, and `platform/`. Shared system-of-record reconciliation and incoming handoff disposition remain controller-owned.

## Working principles

1. One product, one market, web-first; mobile and broad AI are deferred until evidence supports them.
2. Modular monolith and managed services are the planning baseline; no microservices or Kubernetes without measured triggers.
3. Server-authoritative money, stock, order, and integration state; deterministic/manual fallbacks remain available.
4. No production claim without environment and external-provider evidence.
5. Failed checks and external dependencies remain visible in registers and handoffs.
