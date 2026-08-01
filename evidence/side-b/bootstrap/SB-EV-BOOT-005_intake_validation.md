# Side B Intake Artifact Validation

- Artifact ID: SB-EV-BOOT-005
- Version: 1.0.1
- Owner: Side B Platform Lead
- Source inputs/dependencies: AGENTS.md definition of done; Shared Contract; `.agent/PLANS.md`; all Side B G0 artifacts
- Acceptance criteria: required artifact paths exist; every Markdown artifact declares the nine definition-of-done controls; CSV headers expose equivalent controls; only allowed readiness statuses are used; cross-references resolve.
- Validation procedure/result: repository-local structural checks and manual cross-reference review; SELF-VALIDATED, with exact structural command appended after artifact creation.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-005_intake_validation.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller G0 reconciliation
- Remaining risks/next action: controller independently reviews content and processes the handoff; any rejection must cite field-level defects.

## Final structural validation

Working directory: repository root. Command: PowerShell existence, CSV parsing/status-enum, ExecPlan section, and Markdown definition-of-done scan over Side B-owned artifacts.

```text
REQUIRED_COUNT=14
MISSING_COUNT=0
DELIVERABLE_ROWS=21
INVALID_STATUS_ROWS=0
DEPENDENCY_ROWS=9
RISK_ROWS=10
FACT_MATRIX_ROWS=8
EXECPLAN_MISSING_SECTIONS=0
MARKDOWN_ARTIFACTS=15
DOD_MISSING_FILES=0
EXIT_CODE: 0
```

Manual review also confirmed that the outgoing handoff contains sender/receiver/date, work-package/artifact IDs, purpose/workflow, files/schema/version, facts/assumptions/questions, acceptance and validation, need-by/impact/fallback, change control/supersession, and pending receiver result.
