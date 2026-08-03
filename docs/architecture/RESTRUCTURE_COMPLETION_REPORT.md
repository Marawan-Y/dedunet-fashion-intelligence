# Restructure Completion Report — Milestone R0

| Control | Value |
|---|---|
| Artifact ID | ARCH-R0-006 |
| Version | 1.0 |
| Date | 2026-08-03 |
| Owner | Technical lead |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| **Gate status** | **`RESTRUCTURE_VERIFIED`** |

## Decision

All fifteen gate criteria pass with exact-value comparison against the pre-restructure baseline.
The 83-test suite, the 19/19 mutation harness and both fixture checksums are identical before and
after. The restructure is behaviour-preserving.

`RESTRUCTURE_VERIFIED` — Workstream A is authorised to begin in a separate commit with its own
evidence package.

## What changed

67 tracked files moved via `git mv`, so rename history is preserved and no duplicate active
source tree can exist. `platform/` is gone.

| From | To | Files |
|---|---|---|
| `platform/poc/backend/` | `services/commerce-api/` | 36 |
| `platform/poc/docs/` | `docs/operations/` | 8 |
| `platform/poc/storefront/` | `apps/web/` | 5 |
| `platform/poc/mobile/` | `apps/mobile/` | 4 |
| `platform/poc/scripts/` | `scripts/validation/` | 3 |
| `platform/poc/admin/` | `apps/admin/` | 3 |
| `platform/poc/docs/api/openapi.json` | `packages/contracts/openapi/` | 1 |
| `platform/poc/.github/workflows/` | `.github/workflows/` | 1 |
| Root-level config, README, limitations | repository root and `docs/` | 6 |

References updated: `conftest.py`, `manage.py`, `test_frontend_security.py`,
`mutation_guard_check.py`, both validators, `docker-compose.yml`, `apps/web/Dockerfile`,
`.dockerignore`, `.github/workflows/ci.yml`, `apps/admin/index.html`, `Makefile`, `README.md`,
`AGENTS.md`, `README_CODEX_SETUP.md`, the Codex agent definition and the Side B start prompt.

## Functional corrections, isolated and explained

§13 requires any correction needed to make the moved repository run to be separated and justified.
There were four; none changes business behaviour.

1. **`apps/admin` given its own stylesheet.** It previously loaded `../storefront/styles.css`,
   crossing an application boundary the target architecture forbids. The copied content is
   byte-identical, so rendered output is unchanged.
2. **Validator path resolution.** Both validators hard-coded `ROOT/"backend"` and crashed after
   the move.
3. **`manage.py` contract resolution made lazy.** It computed the path at import time and raised
   `IndexError` inside the container, where no repository root exists above `/app`.
4. **Documented local URLs corrected.** `/apps/web/` and `/apps/admin/` when served from the
   repository root; nginx still maps `/storefront/` and `/admin/` in the container.

## The near-miss worth recording

Check 5 (`--assess-sellable` must fail closed) **appeared to pass while actually broken**. The
validator was crashing on import, which also exits 1 — indistinguishable from failing closed if
only the status code is checked.

It was caught by asserting the *reason* (`ACTIVATION_BLOCKED`) rather than the exit code alone.
The lesson generalises: a fail-closed check verified only by its exit code cannot distinguish
"correctly refused" from "crashed before deciding", and the second is a fail-open risk wearing the
first one's clothes. Future gates on fail-closed behaviour should assert the reason.

## Scope discipline

Nothing from the excluded list entered this milestone. No PostgreSQL, notifications, rate
limiting, staging, DEDUNET schema, product import, mobile feature, payment or business-rule
change. The MERET→DEDUNET rebrand remains untouched and deferred to M7 under
`CONFLICT-008`; 12 live source files still carry MERET strings, deliberately.

## Deviations from the approved target tree

Four directories were not created, each deferred until it has real content rather than committed
as empty scaffolding: root `data/` (M7), `packages/{brand,shared-types,shared-utils}` (M7 and when
a second consumer exists), root `tests/` (M6/M8), `infrastructure/` (M3/M5). Rationale in
`TARGET_REPOSITORY_ARCHITECTURE.md`.

One further deviation: `services/commerce-api/data/` retains the two JSON fixtures rather than
moving them to a root `data/`. They are that service's own checksum-guarded test fixtures, and
moving them during a behaviour-preserving commit would have risked the checksum gate for no gain.

## Known limitations carried forward

- **CI has never executed.** Paths updated and reviewed by hand; no runner exists. Not claimed as
  passing.
- **Mobile remains BLOCKED.** Relocated only; the peer conflict is Workstream F.
- **One empty `platform/poc` directory could not be deleted** — a stale OS handle holds it. It is
  empty, untracked and invisible to Git. It will disappear on the next reboot or can be removed
  manually. Recorded rather than hidden.
- **Risk owners remain `ASSIGNMENT_RECORDED — HUMAN ACCEPTANCE PENDING`.**

## Governance follow-up (required by the manager decision)

| # | Requirement | Gate |
|---|---|---|
| GOV-1 | Primary-owner acknowledgment from all four named humans | **Before hosted staging** |
| GOV-2 | Backup owner assigned for every risk domain | **Before production release** |
| GOV-3 | Residual-risk approval authority confirmed per domain | **Before accepting any exception** |

None blocks Workstream A. All three are tracked in `docs/system-of-record/RISK_OWNER_REGISTER.md`.

## Next

Workstream A — PostgreSQL runtime foundation — in a separate commit with its own evidence
package, per M1 of the approved execution order.
