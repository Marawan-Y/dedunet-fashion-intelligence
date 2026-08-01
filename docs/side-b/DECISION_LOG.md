# Side B Decision Log

- Artifact ID: SB-AR-G0-009
- Version: 2.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: Side B Execution Book sections 1-25; Shared Contract; SB-AR-G0-003; SB-AR-B2-001
- Acceptance criteria: reversible technical decisions are recorded with rationale and revisit triggers; Side A/shared truth is not silently decided.
- Validation procedure/result: ownership-boundary and reversibility review completed; SELF-VALIDATED.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-005_intake_validation.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller decision log reconciliation; future B1 ADR log
- Remaining risks/next action: controller/founder decisions listed as pending are not effective until formally recorded in the shared decision log.

| Decision ID | Status | Decision | Owner | Rationale | Revisit trigger |
|---|---|---|---|---|---|
| SB-DEC-001 | SELF-VALIDATED | Constrain technical planning to one product, one selected market, and web-first MVP. | Side B Platform Lead | Binding books prioritize the smallest sellable slice and defer mobile. | Evidence demonstrates a second product/market or mobile repeat-use benefit. |
| SB-DEC-002 | SELF-VALIDATED | Use a modular-monolith architecture baseline; do not select microservices/Kubernetes at G0. | Side B Platform Lead | Small-team scope has no scale/isolation evidence justifying distributed operations. | Measured load, regulatory isolation, team topology, or fault-domain evidence. |
| SB-DEC-003 | SELF-VALIDATED | Treat current JSON, prices, stock, claims, and placeholder images as sample fixtures only. | Side B Platform Lead | No Side A or external evidence supports real-product truth. | Accepted Side A handoff plus human/external evidence IDs. |
| SB-DEC-004 | SELF-VALIDATED | Do not force npm peer resolution during baseline. | Side B Platform Lead | `--force`/`--legacy-peer-deps` would conceal an untouched manifest defect. | Approved B10 dependency alignment change with tests. |
| SB-DEC-P01 | BLOCKED | Select initial country/market and merchant/importer/fulfilment model. | Controller / accountable business owners | Material legal, tax, customer-promise, and architecture impact. | Formal approved Side A/shared decision. |
| SB-DEC-P02 | BLOCKED | Select cloud/identity/payment/carrier providers and budget. | Controller / accountable owners with Side B recommendation | Requires company accounts, legal model, operating process, budget, and official-current verification. | Approved decision record and environment evidence. |
| SB-DEC-G1-001 | AUTOMATED-TESTED | Purge all `__pycache__`/`.pytest_cache` and run every evidence command with `PYTHONDONTWRITEBYTECODE=1` and `pytest -p no:cacheprovider`. | Side B Platform Lead | Bytecode copied from another checkout was being executed here because the copy preserved source mtime and size, silently invalidating result attribution. | A company-owned Git repository and clean-clone CI make cross-tree contamination structurally impossible. |
| SB-DEC-G1-002 | AUTOMATED-TESTED | Prove every negative regression test by removing its guard and asserting the test fails, via a committed harness (`scripts/mutation_guard_check.py`). | Side B Platform Lead | A passing negative test is not automatically a guard; one money test was found to pass for the wrong reason and would have shipped an unproven claim. | Replace with a general mutation-testing tool if coverage needs to grow beyond named guards. |
| SB-DEC-G1-003 | AUTOMATED-TESTED | Remove `price_eur`/`total_eur` from the API and expose authoritative integer minor units plus derived `*_display` values. Breaking wire change; storefront and mobile updated in the same change. | Side B Platform Lead | Keeping a float field would have preserved the defect. The PoC is local and non-public, so the blast radius is zero. | Side A supplies an approved amount, or a consumer outside this repository is discovered. |
| SB-DEC-G1-004 | AUTOMATED-TESTED | A shipped placeholder admin token authorizes nothing in any environment (HTTP 503), not merely outside development. | Side B Platform Lead | The weaker "development is exempt" rule let a default-configured instance destructively rewrite the sample fixture during this cycle. | Work package B5 replaces the token gate with real identity, RBAC, MFA and audit. |
| SB-DEC-G1-005 | SELF-VALIDATED | Do not fix the storefront stored-XSS finding in this cycle; record it as an open launch blocker with a specified remediation. | Side B Platform Lead | The controller scoped task F to audit and record; the fix belongs with B6/B9 front-end work and must not be bundled into an evidence-integrity cycle. | B6/B9 execution, or any decision to expose the storefront beyond localhost — whichever comes first. |
| SB-DEC-G1-006 | SELF-VALIDATED | Do not write a concurrency test for the JSON catalog. | Side B Platform Lead | A passing concurrency test against a design that cannot satisfy the requirement would be misleading evidence. The defect is recorded instead. | PostgreSQL and the inventory ledger land in B12; then write real oversell tests. |
| SB-DEC-G1-007 | SELF-VALIDATED | Preserve superseded evidence unmodified and record supersession in a separate register rather than editing the originals. | Side B Platform Lead | AGENTS.md requires versioning rather than silent overwrite, and the controller required honest recording of the discrepancy. | Controller decides whether to retire the superseded bootstrap records. |
