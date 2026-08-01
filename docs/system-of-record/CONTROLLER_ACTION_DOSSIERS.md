# Controller Action Dossiers — Platform-Side Human Decisions

| Control | Value |
|---|---|
| Artifact ID | SOR-G1-002 |
| Version | 1.0 |
| Owner | Controller / integration lead |
| Status | BLOCKED |
| Sources | Side B M1 cycle report; `CONTROLLER_VALIDATION_G1_M1.md`; `MASTER_RISK_REGISTER.csv` R-013..R-017 |
| Acceptance criteria | Every platform-side decision that an agent may not take alone has a dossier with all eight required elements |
| Validation | Eight-element completeness check per dossier |
| Consumer | Named human owners; Side B; gate authority |
| Risk / next action | No named humans exist; CTRL-01 gates the other three |

Side A's ten dossiers in `docs/side-a/work_packages/side_a/EXTERNAL_ACTION_DOSSIERS.md` cover the
business and external world. They do not cover platform-side decisions that require a human risk
owner. These four close that gap. Nothing in this file records a completed action.

## CTRL-01 — Name risk owners for the three open launch blockers

**Responsible:** human executive sponsor, plus a named security owner once appointed. Both unassigned.
**Action required:** assign a named accountable human to each of SB-RISK-003 (stored XSS in the
storefront), SB-RISK-005 (non-transactional inventory) and SB-RISK-011 (secrets shipped inside the
pack), and record an accept/mitigate/fix decision with a date for each.
**Procedure:** review the three risks in `docs/side-b/SIDE_B_LAUNCH_BLOCKER_AUDIT.md`; confirm each
one's exposure condition; assign an owner with authority to block a release; record the decision
and target gate in the shared decision log.
**Questions:** who may block a release; who accepts residual security risk; is any non-localhost
exposure planned before these close; what is the disclosure path if the PoC leaks?
**Acceptance criteria:** three named humans, one per risk; a dated decision each; a written
statement that the PoC stays localhost-only until closure; the register updated.
**Evidence template:** risk ID, owner name and role, decision, date, target gate, approver,
storage URI, limitations.
**Impact if delayed:** R-015 stays `BLOCKED`; G3 cannot be approached; any exposure of the PoC
beyond localhost would be unowned and, for the XSS and secrets risks, actively unsafe.
**Safe fallback:** PoC remains local and non-public; no deployment, no demo on a shared host, no
real data.

## CTRL-02 — Ratify the breaking money wire-format change

**Responsible:** human product/technical authority, unassigned.
**Action required:** ratify or reject DEC-010 — `price_minor_units` integer becomes the
authoritative wire and storage format; `price_eur` is accepted at ingestion only as exact
`Decimal`/string; binary floats are rejected.
**Procedure:** review `docs/side-b/SIDE_B_MONEY_CONTRACT.md` v2.0.0 and the red/green evidence in
`evidence/side-b/g1/SB-EV-G1-006_money_integrity_red_green.md`; confirm no external consumer
depends on the old shape; ratify before any third party integrates.
**Questions:** does any existing or planned consumer read `price_eur`; what currency set must the
minor-unit exponent table cover; who owns rounding and tax-inclusive presentation rules?
**Acceptance criteria:** written ratification or rejection; named approver and date; if ratified, a
recorded statement that the previous decimal wire format is retired.
**Evidence template:** decision ID, approver, date, scope, affected consumers, storage URI.
**Impact if delayed:** the schema cannot be versioned and frozen; B3 contract work and any external
integration stay provisional.
**Safe fallback:** keep the change confined to the local PoC and publish no API contract externally.

## CTRL-03 — Retire or re-run the superseded bootstrap evidence

**Responsible:** controller, with human gate authority to confirm. Gate authority unassigned.
**Action required:** confirm DEC-011 — retire `SB-EV-BOOT-001..005` as superseded rather than
treating them as current evidence.
**Procedure:** these were produced in a different checkout and partly executed bytecode compiled at
`C:\Users\User\Desktop\Platform\...`; mark them superseded in the Side B evidence index without
deleting them; ensure every replacement carries an attribution line.
**Questions:** is the third checkout still in use by anyone; should it be removed to prevent
recurrence; who owns the workspace hygiene rule?
**Acceptance criteria:** the five records marked superseded and retained; each successor evidence
file states the checkout it ran in; no gate decision cites a retired record.
**Evidence template:** evidence ID, supersession reason, successor ID, verifier, date.
**Impact if delayed:** R-013 stays open and a gate decision could cite unattributable evidence.
**Safe fallback:** treat all five as `BLOCKED` and rely only on evidence produced in this checkout.

## CTRL-04 — Establish version control and a reproducible interpreter baseline

**Responsible:** human account/IT owner, unassigned.
**Action required:** create the company source repository, place this pack under version control,
and establish an isolated Python 3.12 environment with a lockfile matching the Dockerfile and CI.
**Procedure:** provision the repository under company ownership with branch protection; import the
pack; pin the interpreter; generate the lockfile; run CI once for real.
**Questions:** who owns the organisation account; what is the branch-protection and review policy;
who holds the CI secrets; is Python 3.12 or 3.14 the target?
**Acceptance criteria:** repository exists under company ownership with a named admin; first CI run
completes with a recorded result; interpreter divergence resolved or accepted in writing.
**Evidence template:** repository URI, owner, admin list, first CI run ID and result, lockfile hash.
**Impact if delayed:** DEP-011 and R-011 stay `BLOCKED`; there is no rollback mechanism other than
supersession; CI remains an unverified claim; the runtime is Python 3.14 while Docker and CI target
3.12.
**Safe fallback:** keep file hashes and the pristine sibling pack as the only baseline, and make no
destructive change.
