# Controller Independent Validation — G1 M1

| Control | Value |
|---|---|
| Artifact ID | SOR-G1-001 |
| Version | 1.0 |
| Owner | Controller / integration lead |
| Status | AUTOMATED-TESTED |
| Sources | Side A M1 cycle report; Side B M1 cycle report; direct execution in this checkout |
| Acceptance criteria | Every agent claim material to an M1 gate decision is independently reproduced by the controller, or recorded as unreproduced |
| Validation | Commands below executed by the controller, not by the reporting agent |
| Evidence | This file; `evidence/side-a/g1/`; `evidence/side-b/g1/` |
| Consumer | Gate register; both agents; human go/no-go authority |
| Risk / next action | Two Side B corrections outstanding; risk-state vocabulary divergence resolved by DEC-009 |

## Why this file exists

An agent's own report is a claim, not evidence. `AGENTS.md` makes the controller the only party
that may write shared system-of-record files, so the controller must reproduce the claims it
records. Everything below was run by the controller in this checkout,
`C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack`.

## Repository integrity

| Check | Command | Result |
|---|---|---|
| Immutable sources unchanged | `sha256sum docs/source/*.md AGENTS.md .agent/PLANS.md` | 7/7 byte-identical before and after both agent cycles |
| Cross-pack source drift | `sha256sum` vs `Fashion_Commerce_Two_Agent_Execution_Pack` | Contract and both system prompts IDENTICAL |
| Product fixture | `sha256sum backend/data/products.json` | `536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d` — identical to the pristine reference pack |
| Ownership boundary | `ls --time-style=full-iso docs/system-of-record/` | Every file mtime precedes the agent spawn time; neither agent wrote to the shared lane |
| Registers | controller validator | 19/19 parse, primary keys unique |
| ExecPlan structure | controller validator | 3/3 files carry all 17 `.agent/PLANS.md` sections |
| Handoff envelopes | controller validator | 6/7 pass; `SB-HO-B1-001` fails on two fields |

Repository is **not** a Git repository. There is no version control, so supersession is the only
rollback mechanism available and the pristine sibling pack is the only clean baseline.

## Executed validation — Side B platform claims

Working directory `platform/poc/backend` unless stated. Bytecode reuse disabled.

| Command | Output | Exit |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider` | `53 passed, 1 warning in 1.61s` | 0 |
| `python -B scripts/validate_product_data.py` | `Validated 3 products and 9 unique SKUs` | 0 |
| `python -B scripts/validate_candidate_data.py` | `current_state_valid: true`, `sellable_public_eligible: false`, `errors: []` | 0 |
| `python -B scripts/validate_candidate_data.py --assess-sellable` | blocking errors incl. `UNAPPROVED_PRICE`, `ACTIVATION_BLOCKED` | 1 — fail-closed, as required |
| `python -B scripts/mutation_guard_check.py` | `MUTATIONS RUN: 19 / DETECTED: 19 / SURVIVED: 0`, suite restored to `53 passed` | 0 |
| `python -m compileall -q backend scripts` | silent | 0 |
| `docker --version` / `docker compose version` | 29.6.1 / v5.3.0 | 0 |

The mutation run was observed mid-flight: a guard removal produced
`FAILED tests/test_money_integrity.py::test_quote_wire_field_rejects_float_subtotal`, then the
suite returned to green after restoration. The guards are therefore load-bearing, not decorative.

Money representation independently inspected: `PriceRecord.gross_minor_units` is
`int (strict=True, gt=0)`; `app/money.py` rejects binary floats on authoritative money paths;
the legacy `price_eur` key is accepted at ingestion only as exact `Decimal`/string.

## Executed validation — Side A business claims

| Command | Output | Exit |
|---|---|---|
| `python evidence/side-a/g1/side_a_m1_validation.py` | `RESULT: PASS failures=none`; K1–K6 all `CLOSED` | 0 |

Controller spot-checks beyond the agent's own harness:

- Candidate payload parses as JSON; 22 `DRAFT` / 52 `BLOCKED` entries.
- Every `cotton` / `Egypt` / `origin` occurrence traced: one is the blocked field name
  `material.country_of_origin`; three are inside `explicitly_rejected_as_truth`. No such value is
  asserted as truth anywhere in the payload.
- External-action dossiers: 10 sections, each carrying all eight required elements.
- `SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv` (A1-DISP-001) is byte-for-byte unchanged, so the
  65-field contract Side B validated against was not moved underneath it.

## Claims corrected during validation

1. **Controller's own earlier baseline was contaminated.** The `17 passed` figure recorded earlier
   in this cycle was produced while `__pycache__` directories shipped inside the pack, containing
   bytecode compiled at `C:\Users\User\Desktop\Platform\...`. Because the copy preserved mtime and
   size, Python accepted the stale `.pyc`. That baseline is **superseded** by the attributed
   53-test re-run. Side B found and reported this against its own interest.
2. **A third checkout exists** at `C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack`,
   byte-identical to this one. It explains the foreign paths in `SB-EV-BOOT-001..005` and the
   earlier Docker port collision. Prior bootstrap evidence is of uncertain attribution.
3. **Two controller-validator findings were my own false positives**, corrected rather than
   reported: `request_artifact_id` / `register_id` are foreign keys and register tags, not primary
   keys; and `evidence/gate` in prose is an or-phrase, not a path.

## Outstanding corrections issued to Side B

| # | Defect | Rule breached | State |
|---|---|---|---|
| 1 | `docs/side-b/EVIDENCE_INDEX.csv` uses `SUPERSEDED` in the readiness `status` column (4 rows) | `AGENTS.md` permits exactly seven readiness statuses | ISSUED |
| 2 | `SB-HO-B1-001` omits `assumptions` and `questions` | Shared Interface Contract requires both in every handoff | ISSUED |

## Explicitly NOT claimed

No factory visit, physical inspection, laboratory test, customer interview, legal, tax or customs
conclusion, registration, contract, payment activation, carrier result, app-store approval or real
production operation occurred. No evidence of any of these exists in this repository. Every result
above is a local, non-public proof of concept running on synthetic fixtures. Nothing here is
production-ready.
