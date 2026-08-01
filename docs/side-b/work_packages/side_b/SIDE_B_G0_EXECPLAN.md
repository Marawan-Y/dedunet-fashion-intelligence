# Side B G0 Intake and One-Product Technical Alignment ExecPlan

- Artifact ID: SB-AR-G0-001
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: AGENTS.md; `.agent/PLANS.md`; Shared Contract; Side B System Prompt; complete Side B Execution Book; PoC README/repository
- Acceptance criteria: contains all 17 required ExecPlan sections, ordered milestones, exact validation/evidence, recovery, progress, decisions, and residual work sufficient for a fresh agent to resume.
- Validation procedure/result: section-presence and source-consistency review; SELF-VALIDATED.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-005_intake_validation.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller Master ExecPlan; next Side B cycle
- Remaining risks/next action: controller reconciles Side A dependencies and authorizes the first G1 B2/B3 increment.

## 1. Title, owner, status and gate

Title as above. Owner: Side B Platform Lead. Status: SELF-VALIDATED. Current gate: G0 Mobilized; program advancement recommendation is NO-GO pending stated criteria.

## 2. Purpose and observable outcome

Establish a truthful, reproducible technical baseline and exact business-platform input boundary for a one-product, one-market, web-first slice. Observable outcome: baseline evidence, complete Side B G0 artifacts/registers, formal handoff, and dependency-ordered backlog exist and validate.

## 3. Context and source documents read

Read completely: `AGENTS.md`, `.agent/PLANS.md`, `docs/source/Shared_Cross_Team_Agent_Interface_Contract.md`, `docs/source/Side_B_Platform_Software_AI_Apps_Agent_System_Prompt.md`, all 2,689 lines of `docs/source/Side_B_Execution_Book.md`, and `platform/poc/README.md`. Inspected every repository text/config/code/data file; inventoried PDF/DOCX references without treating them as machine sources.

## 4. Confirmed facts, assumptions and unresolved questions

Facts and classifications: SB-AR-G0-004. Assumptions: SB-AR-G0-008. Unresolved: owner/account/spend baseline; initial market; product; merchant/importer/tax; price; fulfilment; policy; brand/content/rights; cloud/provider budget; mobile compatibility.

## 5. Scope and explicit non-scope

Scope: intake, unchanged baseline, G0 registers, risk/privacy/security/runtime review, field contract, roadmap/backlog, formal handoff. Non-scope: broad repair, public deployment, final architecture/provider selection, checkout, real data, mobile production, Kubernetes/microservices, generative AI.

## 6. Dependencies and required handoffs

SB-AR-G0-006 and SB-HO-B0-001 are authoritative for this plan. Controller must record receiver disposition before fields become accepted inputs.

## 7. Artifact list with stable IDs and target paths

The complete list and paths are in SB-AR-G0-005. Core artifacts are SB-AR-G0-001..013, SB-AR-B2-001, SB-AR-B3-001, SB-EV-BOOT-001..005, and SB-HO-B0-001.

## 8. Milestones in dependency order

1. M0 binding read/inventory — completed.
2. M1 untouched baseline attempts — completed, including failures.
3. M2 post-setup local backend/image verification — completed; runtime/mobile residuals open.
4. M3 G0 workspace/registers/intake/risk assessment — completed.
5. M4 one-product field contract and outgoing handoff — completed, receiver disposition pending.
6. M5 controller reconciliation/program G0 decision — pending, controller-owned.
7. M6 approved G1 B2 reproducibility/security increment — pending.
8. M7 accepted one-product B3 schema/contract increment — pending Side A input.

## 9. Detailed implementation or production steps

For M6: establish Git/company ownership; Python 3.12 isolated setup and lock strategy; safe local config validation; compatible mobile dependency decision or explicit continued deferral; expand CI to validator/compile/security basics; parameterize local ports; add tests before fixes for identified defects. For M7: accept one Side A payload; map fields without invention; version schema; validate uniqueness/evidence links/lifecycle; create preview with claims visibly gated. These are implementation steps, not completed production claims.

## 10. Acceptance criteria

M6 accepts when a clean clone can set up, test, validate, build, run, smoke, and stop without tribal knowledge, mobile is either coherently validated or formally deferred, and unsafe defaults fail closed outside local. M7 accepts when one evidence-linked product/variant imports with no unresolved mandatory fields, every sellable SKU is unique, unverified claims cannot publish, and contract tests pass.

## 11. Validation commands, review procedures and expected evidence

Baseline commands are preserved in SB-EV-BOOT-001..004. Future minimum commands: Python dependency install in isolated 3.12 environment; `python -m compileall -q backend scripts`; `python -m pytest -q`; `python scripts/validate_product_data.py`; `docker compose config`; `docker compose build`; isolated `docker compose up --build --detach`; attributed HTTP smoke; logs; `docker compose down`; approved Expo install/alignment/TypeScript/export if mobile is retained. Store full output/exit codes under `evidence/side-b/`.

## 12. Security, privacy, compliance and operational impact

Risks are SB-AR-G0-007. No real personal data. Claims require evidence links and publish gating. Admin defaults, XSS, money/stock integrity, logging, secrets, recovery, accessibility, consent, and provider controls must be designed/tested before public or transactional use. Legal/tax/customs conclusions stay external.

## 13. Migration, rollback and recovery plan

G0 is documentation/evidence plus an ignored local `.env`; rollback is removal/supersession of owned artifacts through versioned change control, not destructive Git operations. Future JSON-to-PostgreSQL work requires export/checksum, dry-run import, dual verification, immutable backup, explicit cutover, and forward-fix/restore rehearsal before adoption. Current PoC remains recoverable from the source pack.

## 14. Risks, mitigations and decision points

SB-AR-G0-007 contains risks/controls. Decision points are SB-DEC-P01 market/merchant model and SB-DEC-P02 providers/budget. Recommendation: decide market/merchant before checkout/infrastructure; retain web-first/modular baseline meanwhile.

## 15. Progress log with timestamps

- 2026-08-01T15:00+02:00: mandatory reading and full inventory began.
- 2026-08-01T15:20+02:00: untouched backend/validator/Docker/mobile attempts captured.
- 2026-08-01T15:27+02:00: backend post-install checks passed; mobile dependency conflict confirmed.
- 2026-08-01T17:25+02:00: Docker images built; Compose runtime port collision attributed to another checkout.
- 2026-08-01T17:30+02:00: G0 artifacts/registers/handoff production and validation began.
- 2026-08-01T19:05+02:00: G1 M1 cycle began in `C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack`. Attribution discrepancy confirmed against `Desktop\Platform\...`; root cause identified as stale cross-checkout bytecode; caches purged.
- 2026-08-01T19:15+02:00: M1 acceptance criterion partially superseded — the ExecPlan targets an isolated Python 3.12 environment, but all local execution used Python 3.14.4 user-site. CI extended to a 3.12/3.13/3.14 matrix; the isolated-environment and lockfile requirement remains OPEN (SB-RISK-010).
- 2026-08-01T19:20+02:00: guard mutation harness added; first run found one surviving mutation (a money test passing for the wrong reason); closed by extracting `sum_line_totals` and pinning it with an adversarial case.
- 2026-08-01T19:40+02:00: float money path found across catalog/quote/stylist/config/clients; RED test written first, then removed. Breaking wire change recorded as SB-DEC-G1-003.
- 2026-08-01T19:55+02:00: admin unsafe-default exploited by an intermediate test run, which rewrote the preserved fixture. Restored byte-identically; fail-closed guard and `conftest.py` fixture protection added.
- 2026-08-01T20:10+02:00: isolated Docker runtime proven under project `sb-g1-m1-final` on ports 18100/13100 with container-label attribution; teardown clean; M3 residual "isolated runtime proof" is now CLOSED, mobile remains BLOCKED.
- 2026-08-01T20:30+02:00: M7 partially advanced — the one-product B3 schema/contract mapping (SB-AR-B3-004 v2.0.0) is complete and tested, but remains blocked on accepted Side A business values.

## 16. Decision log

See SB-AR-G0-009. No Side A/shared source truth was altered.

## 17. Completion summary and residual work

The bounded Side B intake/baseline/G0 artifact cycle is complete after structural validation. Residuals: controller review/handoff processing, named program owners/spend/account evidence, isolated runtime proof, mobile disposition, and accepted one-product business inputs. Program G0 remains BLOCKED/NO-GO.
