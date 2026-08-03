# Risk Owner Register

| Control | Value |
|---|---|
| Artifact ID | SOR-GOV-001 |
| Version | 1.0 |
| Owner | Technical lead (maintains the register; does not assign owners) |
| Status | HUMAN-VERIFIED |
| Source | Human manager approval, 2026-08-03 |
| Acceptance criteria | Every risk domain names a real, accountable human being |
| Consumer | Gate reviews, release decisions, incident response |

Assignments below were made by the human manager. **The agent must not alter them.** Any change
requires explicit human approval and a new version of this file.

## Accountable owners

| Risk domain | Accountable human | Scope |
|---|---|---|
| Application security and stored XSS | **Marawan Younis** | Browser client safety, injection defences, session and authentication handling, security regressions |
| Inventory and financial integrity | **Ahmed Younis** | Stock correctness, overselling, money representation, order and payment reconciliation, refunds |
| Secrets and infrastructure | **Marawan Younis** | Credential handling, environment configuration, deployment topology, backups, access control |
| Brand claims and naming risk | **Aya Ashraf** | DEDUNET naming exposure, trademark and historical-claim risk, material, origin and sustainability wording |

All four are named natural persons. No entry is an agent, a company, a team label or a
placeholder — the register is invalid if any becomes so.

One human may hold more than one domain; Marawan Younis currently holds two. That is permitted
and recorded deliberately rather than disguised by inventing a second name.

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
| Domain evidence contains personal data | Secrets and infrastructure | Marawan Younis | Registrant home address, phone and email are committed in the ownership letter. See `CONFLICT-003` |

## Not owned by any of the above

Legal, tax, customs and trademark **conclusions** require qualified external professionals. No
person in this register, and no agent, may substitute for that advice.
