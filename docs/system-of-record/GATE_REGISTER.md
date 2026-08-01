# Gate Register

| Control | Value |
|---|---|
| Artifact ID | SOR-G0-008 |
| Version | 2.0 |
| Owner | Controller / integration lead |
| Status | SELF-VALIDATED |
| Sources | Both execution books; both G0 assessments; both M1 cycle reports; controller independent validation |
| Acceptance criteria | Current and later gates have objective evidence criteria, result, failed criteria and next action; one recommendation is recorded |
| Validation | Controller criterion-level reconciliation with independently executed evidence |
| Evidence | `CONTROLLER_VALIDATION_G1_M1.md`; `evidence/side-a/g1/`; `evidence/side-b/g1/` |
| Consumer | Controller, both sides, human go/no-go authority |
| Risk / next action | No named go/no-go authority exists; G0 remains BLOCKED |
| Supersedes | Version 1.0 |

## Current decision: G0

Recommendation: `NO_GO`. Readiness status: `BLOCKED`. Unchanged from version 1.0 — the three
failed criteria are all governance criteria that only a human can satisfy, and no human evidence
has been supplied.

| G0 criterion | Result | Evidence / failure | Action |
|---|---|---|---|
| Mandatory sources and full repository inspected | PASS | SOR-G0-001; both intake plans; 7/7 source hashes stable | Maintain source hashes |
| Two accountable agents available and intakes completed | PASS (with adaptation) | Both sides delivered validated cycles; see note below | None |
| Side workspaces, registers, plans, evidence and handoffs exist | PASS | 19 registers parse, PKs unique; 3 ExecPlans at 17/17 sections | Process open corrections |
| All identifiable PoC checks attempted and failures preserved | PASS | Controller re-ran every check; mobile and CI failures preserved, not hidden | Address only approved next work |
| Unsupported external/business claims rejected | PASS | `DECISION_LOG.md` rejected assertions; payload carries `explicitly_rejected_as_truth` | Keep fixture gating |
| One-product / one-market / web-first hypothesis defined | PASS | SOR-G0-009 | Human authorization still pending |
| Founder/IP/company operating baseline | **FAIL** | No signed or human evidence exists | Execute EXT-01 |
| Named accountable humans and account owners | **FAIL** | Owners remain UNASSIGNED | Human sponsor assigns names and authority |
| Spending and approval limits | **FAIL** | No authority matrix | Human sponsor approves thresholds |

### Note on the two-agent criterion

`side_a_business` and `side_b_platform` are defined in `.codex/agents/*.toml` as **Codex CLI**
agents. They are not registered subagent types in the environment that executed this cycle. Both
were run as general-purpose agents carrying their `developer_instructions` verbatim, with the
ownership lanes enforced in-prompt. Lane compliance was then verified by file mtime: every
`docs/system-of-record/` file predates both agent spawns, and neither agent wrote outside its lane.
The criterion is met in substance. It is recorded here rather than silently passed, because the
mechanism differs from the one `AGENTS.md` specifies.

## First G1 milestone: M1 — contract and non-sellable candidate proof

Result: **MET on both sides' technical content; acceptance held open on two Side B corrections.**

| M1 criterion | Result | Evidence |
|---|---|---|
| Both handoff condition sets closed | PARTIAL | Side A 6/6 closed and accepted; Side B content verified, envelope incomplete |
| Lifecycle and money representations reconcile | PASS | Canonical business lifecycle adopted; technical publication state separate; `active` cannot imply sellable |
| Unsupported fields cannot activate | PASS | `--assess-sellable` exits 1 with `UNAPPROVED_PRICE`, `ACTIVATION_BLOCKED` |
| Negative tests pass and are load-bearing | PASS | 53 tests pass; 19/19 guard mutations detected, 0 survived |
| Runtime evidence belongs to this checkout | PASS | Stale foreign bytecode purged; runs pinned with `PYTHONDONTWRITEBYTECODE=1` |
| Money is integer minor units | PASS | `gross_minor_units: int (strict)`; binary floats rejected |
| Fixtures preserved | PASS | `products.json` sha256 `536f91ab…` identical to pristine reference pack |

### M1 failed / open criteria

1. `docs/side-b/EVIDENCE_INDEX.csv` uses `SUPERSEDED`, which is not one of the seven permitted
   readiness statuses. **OPEN.**
2. `SB-HO-B1-001` omits the required `assumptions` and `questions` envelope fields. **OPEN.**

Both were issued to Side B as field-level corrections. Side B acknowledged them and terminated on
an account session limit before applying either. They are not repairable by the controller: that
directory is Side B's exclusive write lane.

## Later gates

| Gate | Objective | Exit evidence | Current status |
|---|---|---|---|
| G1 | Market/product thesis and architecture/data contract aligned | Research and high-intent evidence; authorized one-product hypothesis; accepted field contract; evidence-gated validation | BLOCKED |
| G2 | One makeable product truth proven | Approved sample, tech pack, BOM, measurements; factory, material, claim, QC and cost evidence | BLOCKED |
| G3 | Sellable reversible web MVP proven in staging | Reviewed market/operator/tax/compliance/policy; content rights; server-authoritative checkout and critical tests | BLOCKED |
| G4 | Operational beta proven | Real test import, package, shipment, return, refund, reconciliation; UAT, security, recovery | BLOCKED |
| G5 | Controlled launch approved | Verified accounts and registrations; released batch; production monitoring, support, finance; named go/no-go | BLOCKED |
| G6 | Scale or stop decision | Real demand, returns, contribution margin, quality and reliability evidence | BLOCKED |

G1 cannot exit regardless of M1, because no approved market, merchant model, product, price, batch,
operator or policy exists, and three launch blockers remain OPEN: stored XSS (SB-RISK-003),
non-transactional inventory (SB-RISK-005) and shipped secrets (SB-RISK-011). CI has never executed;
mobile is untested. No calendar date overrides any of this.
