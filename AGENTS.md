# Fashion Commerce Platform — Codex Operating Instructions

## Purpose
This repository is the system of record for launching a premium Egyptian-manufactured fashion brand into Europe through two accountable workstreams:

- **Side A:** business, product, brand, manufacturing coordination, quality, compliance coordination, logistics, marketing, support and finance operations.
- **Side B:** platform architecture, backend, web, mobile, AI, data, cloud, security, testing, deployment and technical operations.

The main Codex thread is the **controller/orchestrator**. It coordinates but does not replace either accountable side.

## Mandatory source reading
Before proposing or changing anything, read:

1. `docs/source/Shared_Cross_Team_Agent_Interface_Contract.md`
2. The relevant side's system prompt in `docs/source/`
3. The relevant side's full execution book in Markdown in `docs/source/`
4. `.agent/PLANS.md`
5. `README.md` for software work

PDF and DOCX files are retained as human references. Use the Markdown books as the machine-readable source.

## Agent delegation
For project mobilization and gate work, explicitly delegate to exactly these project-scoped agents:

- `side_a_business`
- `side_b_platform`

Use parallel work only for bounded tasks with independent ownership. Wait for both agents before synthesizing cross-team decisions. Do not allow both agents to edit the same shared file concurrently.

## Ownership boundaries
- Side A writes only under `docs/side-a/`, `evidence/side-a/`, and `handoffs/outgoing/side-a/`, plus business-owned data/templates explicitly assigned to it.
- Side B writes only under `docs/side-b/`, `evidence/side-b/`, `handoffs/outgoing/side-b/`, and `platform/`, plus technical files explicitly assigned to it.
- The orchestrator alone writes shared program files under `docs/system-of-record/` after reconciling both agents' findings.
- Source files under `docs/source/` are immutable. Never rewrite them.

## Evidence discipline
Use only these statuses:

`DRAFT`, `SELF-VALIDATED`, `AUTOMATED-TESTED`, `HUMAN-VERIFIED`, `EXTERNALLY-VERIFIED`, `BLOCKED`, `REJECTED`.

Never claim a factory visit, physical inspection, laboratory result, customer validation, legal/tax/customs conclusion, registration, signed agreement, payment activation, real carrier result, app-store approval or real production transaction without attached human/external evidence.

## Planning rule
Any task spanning multiple work packages, more than one component, or more than one execution session requires an ExecPlan following `.agent/PLANS.md`. The plan is a living file and must remain sufficient for another agent to resume from the repository alone.

## Working rules
- Inspect before editing.
- Distinguish confirmed facts, assumptions, decisions, dependencies and blockers.
- Prefer one real product vertical slice, one initial market and web-first MVP before broad scope.
- Use official primary sources for current laws, platform rules, APIs and software behavior.
- Do not ask the user for non-blocking details. Record reversible assumptions and continue safely.
- Stop only for genuine external blockers, destructive ambiguity or decisions with material legal, financial, security or architectural impact.
- Never hide failed tests or unresolved risks.
- Never describe a mock, sandbox, generated asset or PoC as production-ready.

## Definition of done for every artifact
An artifact is not complete unless it has:

1. stable artifact ID and version;
2. named owner;
3. source inputs and dependency IDs;
4. explicit acceptance criteria;
5. validation procedure and result;
6. evidence path;
7. readiness status;
8. downstream handoff or consumer;
9. remaining risks and next action.

## Validation expectations
For software changes, run the narrowest relevant tests plus repository-wide checks affected by the change. Preserve exact commands and outputs in `evidence/side-b/`.

For business artifacts, run structured consistency checks against product, pricing, claim, policy, factory, logistics and platform contracts. Preserve the review checklist and result in `evidence/side-a/`.

## Execution-cycle report
Each agent must end a cycle with:

1. current gate and objective;
2. artifacts created or changed with IDs, versions and statuses;
3. validation performed and exact evidence paths;
4. incoming handoffs accepted, conditionally accepted or rejected;
5. outgoing handoffs and their acceptance criteria;
6. blockers, risks, owners and fallbacks;
7. decisions required with options and recommendation;
8. next executable tasks in priority order;
9. gate readiness based on criteria, not confidence language.
