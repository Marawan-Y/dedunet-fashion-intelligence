# Risk Owner Register

| Control | Value |
|---|---|
| Artifact ID | SOR-GOV-001 |
| Version | 2.0 |
| Owner | Technical lead (maintains the register; does not assign owners) |
| **Overall status** | **`ASSIGNMENT_RECORDED — HUMAN ACCEPTANCE PENDING`** |
| Assignment source | Human manager approval, 2026-08-03 |
| Acceptance criteria | Every risk domain names a real, accountable human being |
| Consumer | Gate reviews, release decisions, incident response |

Assignments below were made by the human manager. **The agent must not alter them.** Any change
requires explicit human approval and a new version of this file.

## Status of acceptance — read this before citing the register

The four names were **assigned** by the human manager. The agent holds **no evidence that any
named person has personally acknowledged their assignment.** No signature, reply, ticket or
acknowledgement exists in this repository.

Therefore every acceptance date below is recorded as `PENDING`, not as a date. The agent will not
invent an acceptance it did not observe — an owner who has not accepted cannot be relied on in an
incident, and a fabricated acceptance date would make the register actively dangerous.

To move an entry to `ACCEPTED`, the named person must confirm, and the confirmation must be
recorded here with its real date and where the confirmation is held.

## Accountable owners

| Risk domain | Accountable human | Approval authority | Backup owner | Acceptance |
|---|---|---|---|---|
| Application security and stored XSS | **Marawan Younis** | May block or approve a release on security grounds; may accept residual security risk | **None named** — single point of failure, see below | `PENDING` |
| Inventory and financial integrity | **Ahmed Younis** | May block or approve a release affecting stock, money or reconciliation | **None named** | `PENDING` |
| Secrets and infrastructure | **Marawan Younis** | May approve credential handling, deployment topology and access model | **None named** | `PENDING` |
| Brand claims and naming risk | **Aya Ashraf** | May block publication of any brand, material, origin or sustainability claim | **None named** | `PENDING` |

### Scope of each domain

- **Application security** — browser client safety, injection defences, session and authentication
  handling, security regressions.
- **Inventory and financial integrity** — stock correctness, overselling, money representation,
  order and payment reconciliation, refunds.
- **Secrets and infrastructure** — credential handling, environment configuration, deployment
  topology, backups, access control.
- **Brand claims and naming** — DEDUNET naming exposure, trademark and historical-claim risk,
  material, origin and sustainability wording.

All four are named natural persons. No entry is an agent, a company, a team label or a
placeholder — the register is invalid if any becomes so.

One human may hold more than one domain; Marawan Younis currently holds two. That is permitted
and recorded deliberately rather than disguised by inventing a second name.

**No backup owner is named for any domain.** Every domain is therefore a single point of failure:
if the named owner is unavailable, work in that domain stops, because the escalation rule below
forbids proceeding on an assumed approval. Naming deputies is a cheap, unblocked improvement the
manager may make at any time.

## Responsibilities of an owner

1. Decide whether a residual risk in their domain is accepted, mitigated or blocking.
2. Approve or refuse a release affected by their domain.
3. Approve any compensating control offered in place of a real fix.
4. Be the escalation point when their domain causes an incident.
5. Re-confirm their acceptance whenever the risk materially changes.

An agent may prepare analysis, options and evidence. An agent may **not** accept a residual risk,
close a risk, or approve a release on an owner's behalf.

## Escalation

1. The agent records the risk with evidence and a recommendation.
2. The named owner decides and records the decision.
3. If the owner is unavailable and the work is blocking, the work stops — it does not proceed on
   an assumed approval.
4. Cross-domain conflicts (for example a security fix that changes financial behaviour) require
   both owners to agree, and the disagreement must be recorded, not averaged away.

## Currently open risks awaiting owner decisions

| Risk | Domain | Owner | State |
|---|---|---|---|
| SB-RISK-003 stored XSS | Application security | Marawan Younis | Mitigated in both browser clients; guarded by `test_frontend_security.py` and proven load-bearing by injection. Owner acceptance of residual risk still required |
| SB-RISK-005 inventory integrity | Inventory and financial | Ahmed Younis | Closed for the commerce domain by atomic reservation plus a `reserved <= on_hand` constraint, proven by a 20-thread race. The legacy JSON fixture path remains non-transactional |
| SB-RISK-011 secrets in pack | Secrets and infrastructure | Marawan Younis | `.env` is git-ignored and verified absent from history; the file still exists on disk in the working tree |
| DEDUNET naming exposure | Brand claims | Aya Ashraf | `DeDeNet` conflict disclosed by Side A as high preliminary risk. `LEGAL_CLEARANCE_PENDING`; public commercial launch blocked |
| Domain evidence contained personal data | Secrets and infrastructure | Marawan Younis | **RESOLVED 2026-08-03.** Unredacted letter removed from the working tree and purged from all Git history and object storage; only a generated redacted copy remains. `.gitignore` blocks re-adding it. See `CONFLICT-003` and `GIT_ROOT_NORMALIZATION.md` |

## Not owned by any of the above

Legal, tax, customs and trademark **conclusions** require qualified external professionals. No
person in this register, and no agent, may substitute for that advice.

## Governance follow-up items (manager-required, R0)

| # | Requirement | Gate | Status |
|---|---|---|---|
| GOV-1 | Primary-owner acknowledgment from each of the four named humans | Before hosted staging | OPEN |
| GOV-2 | Backup owner assigned for every risk domain | Before production release | OPEN |
| GOV-3 | Residual-risk approval authority confirmed per domain | Before accepting any exception | OPEN |

None of these blocks local development, R0 or Workstream A. GOV-1 and GOV-3 must both close
before any residual risk can be formally accepted — until then an exception has no valid approver
and cannot be granted, only recorded as outstanding.
