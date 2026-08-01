# Independent Gate Review and Release Decision

Perform a controller-level review of the current gate. Do not accept either agent's self-assessment at face value.

1. Read the source books, shared contract, Master Execution Plan, all gate-required artifacts, evidence files, handoff decisions, test logs, risks and accepted exceptions.
2. Ask `side_a_business` to review Side B outputs only for business-contract compatibility, customer promise, product truth and operational usability. It must not rewrite technical ownership.
3. Ask `side_b_platform` to review Side A outputs only for schema completeness, implementability, internal consistency and testability. It must not invent business truth.
4. Wait for both reviews and reconcile contradictions.
5. Re-run or independently verify all automatable checks.
6. Confirm that external-verification claims include actual evidence.
7. Produce `docs/system-of-record/GATE_<N>_REVIEW.md` with every criterion marked PASS, FAIL, CONDITIONAL or NOT_APPLICABLE, including artifact/evidence references.
8. Return exactly one recommendation: GO, CONDITIONAL_GO or NO_GO.
9. CONDITIONAL_GO requires a named risk owner, explicit customer/business impact, compensating control, expiry date and go/no-go authority.
10. A calendar target never overrides a failed gate.
