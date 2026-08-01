# Side B First Two-Week Backlog

- Artifact ID: SB-AR-G0-012
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: SB-AR-G0-001; SB-AR-B2-001; SB-AR-G0-006/007; SB-AR-B3-001
- Acceptance criteria: ten working days are dependency ordered, tied to artifact IDs, objectively testable, limited to G0/G1, and identify blocked versus non-blocked work.
- Validation procedure/result: cross-checked against ExecPlan milestones and ownership; SELF-VALIDATED.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-005_intake_validation.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller Master ExecPlan and Side B next cycle
- Remaining risks/next action: controller selects tasks only after G0 reconciliation; do not treat day labels as calendar commitments.

| Priority/day | Task | Artifact/WP | Dependency | Acceptance evidence | State |
|---|---|---|---|---|---|
| P0/D1 | Process controller disposition and accepted Side A response field by field | SB-HO-B0-001 / B3 | Controller/Side A | ACCEPT/CONDITIONALLY_ACCEPT/REJECT record | requested |
| P0/D1-2 | Initialize company Git/access/review baseline and reproducible Python 3.12 setup | B2-D01/B2-D02/B2-D04 | SB-DEP-001 | clean-clone setup/test evidence | blocked on ownership; design non-blocked |
| P0/D2 | Add regression tests for unsafe admin default, XSS data path contract, duplicate IDs/slugs/SKUs, zero-stock stylist, quote boundaries | B20-D02 | none | failing-before/fixed-after exact test logs | pending |
| P0/D3 | Parameterize local ports or establish isolated runtime lane; run attributed Compose smoke/log/down | B2-D01 | SB-DEP-008 | this checkout labels + HTTP/log evidence | requested |
| P0/D3-4 | Expand CI to compile, validator, tests, dependency/security checks with pinned workflow behavior | B2-D03/B20-D02 | Git baseline | CI config plus local-equivalent logs | pending |
| P1/D4 | Decide mobile defer versus compatible official Expo alignment; never force peer deps | B10-D01 | SB-DEP-009; controller scope | decision + install/type/export evidence or explicit deferral | pending |
| P0/D5 | Draft B1 engineering handbook, ADRs, NFRs, technology radar for modular monolith | B1-D01..D04 | volume/risk tolerance useful, not blocking draft | checklist/self-review | pending |
| P0/D6 | Version one-product schema/evidence/lifecycle contract without inventing values | B3-D01..D03 | SB-HO-B0-001 response | schema tests and example rejection report | blocked on final fields; framework non-blocked |
| P0/D7 | Build import validator contract tests and publish-gating rules | B3-D04/B7-D02 | accepted product contract | positive/negative fixtures, no unverified claim publication | blocked on accepted fixture |
| P1/D8 | Draft API error/idempotency/version policy for catalog/read-only preview | B4-D01/B4-D03 | domain draft | OpenAPI validation/contract tests | pending |
| P0/D9 | Threat-model product admin/publish, storefront XSS, secrets, data flows, and supply evidence | B19-D01/B19-D03 | operator roles/privacy inputs partly requested | threat model checklist; owners/actions | pending |
| P0/D10 | G1 alignment review and next-cycle report; no gate advance without controller decision | G1 report | all above | criterion-level report and evidence index | pending |

Mobile, live payment, carrier, tax calculation, cloud deployment, public launch, broad catalog, and generative AI are explicit non-scope for this two-week backlog unless a new controller-approved plan changes scope.
