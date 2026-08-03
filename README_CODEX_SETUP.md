# Running the Fashion Commerce Two-Agent Project in Codex

## What this pack adds

This is a Codex-native version of the two-agent project pack. It adds:

- a root `AGENTS.md` that Codex loads automatically;
- two project-scoped custom agents under `.codex/agents/`;
- an ExecPlan standard under `.agent/PLANS.md`;
- machine-readable Markdown copies of both execution books;
- the extracted PoC under ``;
- controller, continuation and gate-review prompts;
- separate ownership directories for each side and a shared system of record.

## Recommended operating model

Use one main Codex thread as the **controller** and exactly two subagents as accountable delivery leads. The controller is not a third business/technical side; it only delegates, waits, reconciles interfaces, owns shared registers and makes gate recommendations.

Parallelize inspection and bounded ownership tasks. Do not let both agents write the same files simultaneously. Use Codex worktrees when available, or enforce the directory ownership rules in `AGENTS.md`.

## First run in the Codex desktop app or IDE

1. Extract this archive into a clean project directory.
2. Open that directory as the Codex project.
3. Confirm the project includes hidden folders `.codex/` and `.agent/`.
4. Use a permission mode that permits workspace writes and local build/test commands. Keep network and elevated actions approval-controlled.
5. Open `prompts/00_MASTER_ORCHESTRATOR_BOOTSTRAP.md` and paste its full content into the main Codex thread.
6. Let the controller spawn `side_a_business` and `side_b_platform` in parallel.
7. Review the intake artifacts and diffs before accepting material decisions.
8. Use `prompts/01_CONTINUE_GATE_EXECUTION.md` for subsequent execution cycles.
9. Use `prompts/02_GATE_REVIEW_AND_RELEASE_DECISION.md` before advancing any gate.

## First run with Codex CLI

From the extracted project root:

```bash
git init
git add .
git commit -m "Baseline two-agent fashion commerce execution pack"
codex
```

Inside the interactive session, paste the complete content of `prompts/00_MASTER_ORCHESTRATOR_BOOTSTRAP.md`. Use `/agent` to inspect and switch between subagent threads when needed.

## What not to do

- Do not upload only the PDFs and send “build this.”
- Do not ask both agents to edit one shared plan concurrently.
- Do not run the entire A1–A18/B1–B22 roadmap as one unreviewed task.
- Do not treat generated documents as external validation.
- Do not allow Side B to invent product, price, claim or policy truth.
- Do not allow Side A to dictate undocumented schemas or edit technical runtime truth.
- Do not advance a gate because the agent sounds confident.

## Human owner responsibilities

The agents can create, implement, test, analyze and prepare operational dossiers. A human or authorized external party must still provide evidence for physical samples, factory inspections, contracts, registrations, legal/tax/customs conclusions, bank/payment activation, real shipments, customer interviews and app-store approval.

The correct target is not “100% autonomous.” The correct target is **maximum autonomous production with explicit evidence boundaries and no fake completion**.
