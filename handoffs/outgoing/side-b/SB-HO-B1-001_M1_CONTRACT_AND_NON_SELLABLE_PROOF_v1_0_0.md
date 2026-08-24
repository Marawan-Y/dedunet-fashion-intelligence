# HANDOFF SB-HO-B1-001 — G1 M1: Contract and non-sellable candidate proof

| Envelope field | Value |
|---|---|
| Handoff ID | SB-HO-B1-001 |
| Version | 1.0.0 |
| Sender | `side_b_platform` (Side B Platform Lead) |
| Receiver | Controller / integration lead; Side A for the field conditions it owns |
| Date | 2026-08-01 |
| Work packages | B2, B3, B5, B12, B18, B19, B20 |
| Artifact IDs | SB-AR-B3-002 v1.1.0, SB-AR-B3-003 v2.0.0, SB-AR-B3-004 v2.0.0, SB-AR-B19-001 v1.0.0, SB-AR-G0-007 v2.0.0, SB-AR-G0-009 v2.0.0, SB-AR-G0-010 v2.0.0 |
| Superseded | SB-AR-B3-003 v1.0.0; SB-AR-B3-004 v1.0.0; SB-AR-G0-007 v1.0.0 (all archived, none deleted) |
| Milestone | G1 M1 "Contract and non-sellable candidate proof" |

## 1. Purpose and consuming workflow

Close the controller's M1 conditions on HO-A-B-001, re-establish evidence that is
attributable to **this** working tree, and prove — by construction rather than by
assertion — that a synthetic candidate cannot become sellable or public.

The controller consumes this to decide M1 acceptance. Side A consumes the field
disposition to see exactly which inputs remain blocked and in what format they are needed.

## 2. Payload

### Contracts and registers (`docs/side-b/`)
| File | Version | Status |
|---|---|---|
| `SIDE_B_BPC_FIELD_DISPOSITION.csv` | 2.0.0 | AUTOMATED-TESTED |
| `SIDE_B_BPC_FIELD_DISPOSITION_v1_0_0.csv` | 1.0.0 | archived, unmodified |
| `SIDE_B_MONEY_CONTRACT.md` | 2.0.0 | AUTOMATED-TESTED |
| `SIDE_B_LIFECYCLE_PUBLICATION_CONTRACT.md` | 1.1.0 | AUTOMATED-TESTED |
| `SIDE_B_LAUNCH_BLOCKER_AUDIT.md` | 1.0.0 | SELF-VALIDATED |
| `SIDE_B_RISK_REGISTER.csv` | 2.0.0 | AUTOMATED-TESTED |
| `SIDE_B_RISK_REGISTER_v1_0_0.csv` | 1.0.0 | archived, unmodified |
| `EVIDENCE_INDEX.csv` | 2.0.0 | AUTOMATED-TESTED |
| `DECISION_LOG.md` | 2.0.0 | SELF-VALIDATED |

### Evidence (`evidence/side-b/`)
| File | Status |
|---|---|
| `EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md` | SELF-VALIDATED |
| `g1/SB-EV-G1-002_candidate_green.md` + `_green_pytest_transcript.txt` | AUTOMATED-TESTED |
| `g1/SB-EV-G1-003_guard_mutation_matrix.md` + `_mutation_transcript.txt` | AUTOMATED-TESTED |
| `g1/SB-EV-G1-004_artifact_validation.md` | AUTOMATED-TESTED |
| `g1/SB-EV-G1-005_attributed_baseline_rerun_v2.md` | AUTOMATED-TESTED / BLOCKED (mobile) |
| `g1/SB-EV-G1-006_money_integrity_red_green.md` | AUTOMATED-TESTED |
| `g1/SB-EV-G1-007_launch_blocker_audit.md` | AUTOMATED-TESTED / SELF-VALIDATED |

### Implementation (`platform/poc/`)
New: `backend/app/money.py`, `backend/tests/conftest.py`,
`backend/tests/test_money_integrity.py`, `backend/tests/test_admin_security.py`,
`scripts/mutation_guard_check.py`.
Changed: `backend/app/{schemas,catalog,config,main,ai_stylist}.py`,
`backend/tests/{test_api,test_candidate_activation}.py`,
`scripts/validate_product_data.py`, `storefront/app.js`, `mobile/App.tsx`,
`.github/workflows/ci.yml`, `.env`, `.env.example`, `README.md`.
Unchanged and verified byte-identical: `backend/data/products.json`,
`backend/data/candidate_products.json`.

## 3. Confirmed facts

1. In this checkout, the full suite is **53 passed, exit 0**; both validators exit 0;
   `--assess-sellable` exits non-zero as required; `compileall` exits 0.
2. Docker is available. `docker compose config`, `build`, an isolated `up` on ports
   18100/13100 under a distinct project name, attributed HTTP smoke checks, log capture and
   `down` all succeeded. Container labels prove `working_dir` is this tree. The prior port
   collision was resolved by isolation; no foreign container was stopped or modified.
3. All 19 guard mutations were detected by their guarding tests; 0 survived.
4. A float money path existed across catalog, quote, stylist, config and both clients. It
   was removed after a failing test was written first.
5. `products.json` and `candidate_products.json` are byte-identical to their pre-cycle
   state (sha256 `536f91ab…` and `7f052e4c…`).

## 3a. Assumptions

Stated explicitly on 2026-08-24 for envelope compliance. Each was already operative in
this handoff when it was sent; none is new, and none changes a claim made below.

1. **The candidate record is synthetic and carries no business truth.** Every value in
   `candidate_products.json` is a fixture. `price` is `null` and stays `null` until Side A
   supplies an approved value with evidence.
2. **Side A owns the blocked field inputs.** Side B can prove the gates hold; it cannot
   supply the approved business values that would let a candidate pass them.
3. **Evidence must be attributable to this working tree.** Records naming another checkout
   are treated as superseded rather than corrected — see SB-EV-ATTR-001.
4. **The controller decides M1 acceptance.** This handoff supplies proof, not a decision.
5. **No production provider, market or real product is selected.** The PoC serves
   non-sellable synthetic candidates with every gate failing closed.

## 4. Findings the controller must see

1. **Attribution (as flagged).** SB-EV-BOOT-001..005 and SB-EV-G1-001 record a working
   directory of `C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack`.
   That directory exists and is byte-identical to this one for every file compared.
2. **Root cause found (new).** `__pycache__` copied with the pack caused Python to execute
   bytecode compiled in the other tree — four modules carried `co_filename` values pointing
   there. Because the copy preserved source mtime and size, Python accepted the stale
   `.pyc` as current. The controller-verified `17 passed` baseline was partly executing it.
   Purged; all evidence runs now disable bytecode and pytest caching, as does CI.
3. **Dangling evidence references (new).** `SIDE_B_MONEY_CONTRACT.md` and
   `SIDE_B_LIFECYCLE_PUBLICATION_CONTRACT.md` v1.0.0 both cited
   `evidence/side-b/g1/SB-EV-G1-002_candidate_green.md`, and
   `SIDE_B_BPC_FIELD_DISPOSITION.csv` v1.0.0 cited
   `evidence/side-b/g1/SB-EV-G1-004_artifact_validation.md`. **Neither file existed.** Three
   artifacts were carrying an AUTOMATED-TESTED status against evidence that had never been
   produced. Both files now exist and are attributable.
4. **Unsafe admin default was exploited, not theorised (new).** An intermediate test run
   reached `POST /api/v1/admin/products` with the shipped placeholder token and
   destructively rewrote the preserved fixture. Restored byte-identically; incident recorded
   in full; two permanent controls added.
5. **One mutation initially survived (new).** `test_quote_totals_are_exact_in_minor_units`
   did **not** fail when a float round-trip was reintroduced. It was passing for the wrong
   reason. Closed by extracting the arithmetic and pinning it with EUR 0.70 x 3.
6. **Python divergence confirmed.** ExecPlan and Dockerfile target 3.12; every local run
   used 3.14.4 with no `.venv` and no lockfile. CI extended to a 3.12/3.13/3.14 matrix, but
   **CI has never been executed — there is no runner in this environment.**

## 5. Controller conditions on HO-A-B-001 — disposition

| # | Condition | Status |
|---|---|---|
| 1 | Business lifecycle `fixture\|candidate\|sample\|approved\|sellable\|retired`; separate technical publication mapping; no ambiguous `active` | **CLOSED** — enum implemented, publication is a separate enum, per-field publication ceiling added to all 35 rows, `active` absent; mutation M12 |
| 2 | Candidate ID/category/SKU/size/colour/currency/locale labelled non-authoritative draft | **CLOSED** — rows 001, 005, 013, 014, 015, 021, 024; record carries `synthetic_fixture: true`; mutation M13 |
| 3 | Integer minor units for authoritative money; EUR 59 research-only | **CLOSED and extended** — enforced system-wide, not only in the candidate record; `price` remains `null`; mutations M14–M19 |
| 4 | Zero is the only permitted sellable quantity until batch/QC/location/count evidence link | **CLOSED** — three distinct guards; mutations M08, M09, M10 |
| 5 | Absent/expired evidence suppresses values and claims, with scope/issuer/approver/expiry validation | **CLOSED** — five evidence error classes plus duplicate detection; mutations M03, M04, M11 |
| 6 | 35-row disposition plus negative tests for the eight named cases | **CLOSED** — 35 unique rows; every case has a passing test and a detected mutation |

## 6. Acceptance criteria for the receiver

Accept M1 only if, from a clean checkout:

```bash
cd platform/poc/backend && PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider   # 53 passed, exit 0
cd ../ && python scripts/validate_product_data.py                                              # exit 0
python scripts/validate_candidate_data.py                                                       # exit 0
python scripts/validate_candidate_data.py --assess-sellable                                     # exit NON-ZERO
python scripts/mutation_guard_check.py                                                          # 19 detected, 0 survived, exit 0
python -m compileall -q backend scripts                                                         # exit 0
sha256sum backend/data/products.json backend/data/candidate_products.json                       # 536f91ab… / 7f052e4c…
```

and if a reviewer confirms the disposition CSV has 35 unique rows with the publication
mapping columns populated.

## 7. Need-by, impact and fallback

Need-by: before any G1 exit decision. Impact if late: the field contract stays unfrozen and
B7/B9/B11 cannot start against a stable schema. Fallback: the PoC continues to serve
non-sellable synthetic candidates with all gates failing closed — no customer-facing risk,
but no progress toward a sellable MVP.

## 8. Change control

Superseded artifacts are archived alongside their replacements with an explicit version
bump. No superseded file was edited or deleted. No file outside `docs/side-b/`,
`evidence/side-b/`, `handoffs/outgoing/side-b/` and `platform/` was written. Side A
artifacts and `docs/source/` were not touched. `docs/system-of-record/` was read only.

**Envelope completion, 2026-08-24.** This document was missing the required `assumptions`
and `questions` envelope fields and failed `handoff_envelope_check.py`. Section 3a was
added and section 9 renamed. **No claim, finding, disposition, acceptance criterion or
evidence reference was altered** — the assumptions restate what sections 1 and 3 already
established, and the questions are verbatim the three section 9 already asked. The version
is deliberately not bumped: a version bump signals a change in what a handoff asserts, and
nothing it asserts has changed. Recorded here rather than applied silently, per the
change-control rule above.

## 9. Questions and receiver response required

ACCEPT / CONDITIONALLY ACCEPT / REJECT, with field-level reasons.

**Open questions for the receiver.** These are the questions this handoff has always
asked; the heading was corrected on 2026-08-24 so the envelope names them as questions.

1. Should SB-EV-BOOT-001..005 be retired or formally re-run?
2. Who is the named human risk owner for SB-RISK-003 (stored XSS), SB-RISK-005
   (non-transactional inventory) and SB-RISK-011 (secrets)? All three remain **OPEN**
   launch blockers that Side B cannot close alone.
3. Is the breaking money wire change (SB-DEC-G1-003) accepted?
