# Side A G1 M1 Condition-Closure and Business Consistency Validation

| Field | Value |
|---|---|
| Artifact ID / version | EV-A1-002 / 1.0 |
| Owner | Side A Business/Product Lead |
| Sources / dependencies | SOR-G0-011 six controller conditions; A1-DISP-001 v1.0; A1-DISP-002 v1.0; A1-PAYLOAD-001 v0.1.1; A0-EXT-001 v1.1; HO-A-B-003 v1.1; all Side A registers |
| Acceptance criteria | Every Side A CSV parses without ragged rows; only the seven allowed evidence statuses and three allowed dispositions appear; no duplicate artifact, field, evidence or dependency ID exists; every non-URL evidence path resolves on disk; the candidate payload keeps blocked-null, dependency-link and zero-sellable-stock discipline; matrix and payload field sets are identical; no prohibited PoC truth appears in candidate values; no unsupported completion language appears in Side A prose; all ten external-action dossiers contain all eight required elements; and each of the six controller conditions K1-K6 evaluates CLOSED |
| Validation procedure / result | `python evidence/side-a/g1/side_a_m1_validation.py` executed from the repository root; exit code 0; RESULT PASS |
| Evidence path | `evidence/side-a/g1/EV_A1_002_M1_CONDITION_CLOSURE_VALIDATION.md`; validator source retained at `evidence/side-a/g1/side_a_m1_validation.py` |
| Status | SELF-VALIDATED |
| Downstream consumer | Controller M1 reconciliation; Side B B3 schema/validator, B7 catalog, B9 web candidate preview |
| Remaining risk / next action | This validates documents and data only. Side B schema/runtime validation and every human and external evidence item remain pending. Re-run after any receiver response or artifact change |

## Scope and hard limitation

This record proves internal consistency of Side A documents and structured data. It proves **no** external reality. No factory visit, physical sample inspection, laboratory test, customer interview, legal, tax or customs conclusion, registration, contract, payment activation, carrier result or production operation has occurred, and none is claimed. Every such item remains `BLOCKED` on its dependency with an external-action dossier prepared.

## Environment

| Item | Value |
|---|---|
| Working directory | repository root `Fashion_Commerce_Codex_Multi_Agent_Pack` |
| Interpreter | Python 3.14.4 |
| Date | 2026-08-01 |
| Files in Side A ownership scope | 30 under `docs/side-a/`, `evidence/side-a/`, `handoffs/outgoing/side-a/` |
| Prior evidence superseded by | none; EV-A1-001 v1.0 remains valid history and is re-proven, not replaced |

## Checklist

| ID | Control | Method | Result |
|---|---|---|---|
| C1 | Every Side A CSV parses; no ragged rows | `csv.DictReader` over 9 files | PASS |
| C2 | Candidate payload parses as JSON | `json.load` | PASS |
| C3 | Only the seven allowed evidence statuses appear | Set comparison across 8 register/matrix status columns plus all 73 payload entries | PASS |
| C4 | Only the three allowed handoff dispositions appear | Set comparison across both disposition files | PASS |
| C5 | No duplicate artifact, atomic-field, instance-field, evidence, dependency or payload-field ID | `Counter` on six identifier columns | PASS |
| C6 | Every non-URL evidence path exists on disk | `os.path.exists` on deliverable, evidence-index, dependency, payload metadata and payload contract-reference paths | PASS |
| C7 | Blocked-null, dependency-link, metadata, SKU-uniqueness and zero-sellable-stock discipline | Field-level assertions on all 73 payload entries | PASS |
| C8 | Disposition matrix and payload cover exactly the same field set | Symmetric set difference | PASS |
| C9 | No prohibited PoC truth in candidate values | Case-insensitive scan of 12 banned tokens over serialized candidate values | PASS |
| C10 | No unsupported completion language in Side A prose | 13 regex claim patterns over 29 owned files, with fenced code blocks and inline code stripped so validator source text cannot self-trigger | PASS |
| C11 | All ten external-action dossiers contain all eight required elements, and every BLOCKED dependency maps to a dossier | Element-marker audit plus dependency-to-dossier mapping | PASS |
| K1 | Controller condition 1 — Germany and `VS-TEE-001` returned only as DRAFT | Status assertion on six fields plus a check that no row carries full `ACCEPT` | CLOSED |
| K2 | Controller condition 2 — unknown mandatory external fields carry dependency and evidence status, no filler | Assertion over all 52 blocked entries | CLOSED |
| K3 | Controller condition 3 — requested lifecycle vocabulary rejected, canonical lifecycle used, technical state separated | Matrix disposition plus payload `activation_controls` | CLOSED |
| K4a | Controller condition 4 — every nested field enumerated to leaf level, no group placeholder rows | 11 expected leaves present; 3 group names absent | CLOSED |
| K4b | Controller condition 4 — variant instances enumerated one-to-one with the payload, no multi-value rows | Set equality between A1-DISP-002 rows and payload `variants[n]` fields | CLOSED |
| K4c | Controller condition 4 — residual composite fields are single explicit BLOCKED nulls with dependency IDs | Assertion over 10 composite fields | CLOSED |
| K5 | Controller condition 5 — no rejected PoC truth returned as approved, activation flags all false | Value scan plus must-be-null assertion plus four activation flags | CLOSED |
| K6 | Controller condition 6 — complete disposition and minimal explicit payload | Row-count, coverage-gap and required-metadata audit across 74 rows | CLOSED |

## Exact command

```
cd C:/Users/User/Desktop/Claude/Fashion_Commerce_Codex_Multi_Agent_Pack
python evidence/side-a/g1/side_a_m1_validation.py; echo "EXIT=$?"
```

## Exact output

```text
C1 PARSE SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv       rows=65   cols=13  ragged=none
C1 PARSE SB_HO_B0_001_VARIANT_INSTANCE_DISPOSITIONS.csv   rows=9    cols=14  ragged=none
C1 PARSE SIDE_A_DELIVERABLE_REGISTER.csv                  rows=30   cols=13  ragged=none
C1 PARSE SIDE_A_DEPENDENCY_REGISTER.csv                   rows=12   cols=12  ragged=none
C1 PARSE SIDE_A_RISK_REGISTER.csv                         rows=9    cols=12  ragged=none
C1 PARSE EVIDENCE_INDEX.csv                               rows=8    cols=12  ragged=none
C1 PARSE ASSUMPTION_REGISTER.csv                          rows=5    cols=11  ragged=none
C1 PARSE SIDE_A_FACT_ASSUMPTION_MATRIX.csv                rows=17   cols=10  ragged=none
C1 PARSE SIDE_A_BUSINESS_PLATFORM_CONTRACT.csv            rows=35   cols=14  ragged=none
C2 JSON  parse=OK version=0.1.1 candidate=21 blocked=52
C3 STATUS_VOCAB invalid=none
C4 DISPOSITION atomic=65 {'CONDITIONALLY_ACCEPT': 64, 'REJECT': 1} | instance=9 {'CONDITIONALLY_ACCEPT': 9} | invalid=none
C5 DUPLICATE deliverable.artifact_id          none
C5 DUPLICATE matrix.atomic_field              none
C5 DUPLICATE instance.atomic_instance_field   none
C5 DUPLICATE evidence.evidence_id             none
C5 DUPLICATE dependency.dependency_id         none
C5 DUPLICATE payload.field                    none
C6 EVIDENCE_PATHS_ON_DISK checked_and_missing=none
C7 PAYLOAD blocked_nonnull=none non_draft_candidate=none non_blocked_unknown=none blocked_without_dependency=none missing_metadata=none
C7 PAYLOAD candidate_skus=3 unique=3 sellable_stock_cap=[0] price.gross_minor_units=[None] inventory.opening_stock=[None]
C8 COVERAGE matrix_fields=65 payload_fields=65 matrix_only=none payload_only=none
C9 PROHIBITED_POC_TRUTH_IN_CANDIDATE_VALUES hits=none
C10 UNSUPPORTED_COMPLETION_LANGUAGE files_scanned=30 prose_hits=none
C11 DOSSIERS found=10 required_elements=8
C11 EXT-01  missing_elements=none
C11 EXT-02  missing_elements=none
C11 EXT-03  missing_elements=none
C11 EXT-04  missing_elements=none
C11 EXT-05  missing_elements=none
C11 EXT-06  missing_elements=none
C11 EXT-07  missing_elements=none
C11 EXT-08  missing_elements=none
C11 EXT-09  missing_elements=none
C11 EXT-10  missing_elements=none
C11 BLOCKED_DEPENDENCIES=10 DOSSIERS=10 unmapped=none

K1 CONDITION_1 draft_only_violations=none any_full_ACCEPT=none -> CLOSED
K2 CONDITION_2 blocked_entries=52 violations=none -> CLOSED
K3 CONDITION_3 disposition=REJECT canonical=fixture|candidate|sample|approved|sellable|retired technical_implies_sellable=False -> CLOSED
K4a CONDITION_4_nested leaves_expected=11 missing_or_placeholder=none -> CLOSED
K4b CONDITION_4_instances rows=9 payload_instances=9 rows_only=none payload_only=none multivalue_rows=none -> CLOSED
K4c CONDITION_4_composites checked=10 not_explicit_blocked_null=none -> CLOSED
K5 CONDITION_5 poc_value_hits=none must_be_null_but_set=none activation_flags_all_false=True -> CLOSED
K6 CONDITION_6 atomic_rows=65 instance_rows=9 coverage_gap=none rows_missing_required_metadata=none candidate=21 blocked=52 -> CLOSED

OWNED_FILES docs/side-a+evidence/side-a+handoffs/outgoing/side-a = 30
RESULT: PASS  failures=none
EXIT=0
```

## Defects found and corrected in this cycle

| # | Defect | Detected by | Correction | Version change |
|---|---|---|---|---|
| 1 | All ten external-action dossiers were missing two of the eight mandatory elements: an explicit `Action required` statement and an explicit `Impact if delayed` statement. The action was implicit inside the procedure text and the delay impact existed only in the dependency register | C11 element audit, first run | Added both elements to every dossier, plus a dependency-to-dossier coverage map and a supersession note. No existing procedure, question, acceptance criterion, evidence field or fallback was removed or weakened | A0-EXT-001 1.0 → 1.1 |
| 2 | Controller condition 4 was only partially met. Nested fields were correctly enumerated to leaf level, but the three variant rows in A1-DISP-001 each packed three instance values into one pipe-joined cell, so a validator could not report a field-specific error for a single variant | K4b instance check, first run | Added A1-DISP-002, a nine-row instance-level disposition file matching the payload `variants[n]` fields one to one. A1-DISP-001 was left byte-for-byte unchanged so the 65-field contract Side B is already validating against is not disturbed | new artifact A1-DISP-002 1.0; HO-A-B-002 1.0 → HO-A-B-003 1.1 |
| 3 | Candidate payload metadata pointed at the superseded response handoff and did not reference the instance-level file or this evidence record | C6 path check and manual review | Metadata-only update. No business value, status, dependency or null was added, changed or removed; every field entry retains `effective_version` 0.1.0 | A1-PAYLOAD-001 0.1.0 → 0.1.1 |

## False positive recorded and resolved

The first run of the completion-language scan reported one hit, `payment activated`, in `evidence/side-a/bootstrap/SIDE_A_G0_CONSISTENCY_REVIEW.md` line 54. Manual inspection showed the string is part of that file's own prohibited-phrase regex inside a fenced code block, not a Side A claim. The scanner was corrected to strip fenced code blocks and inline code before matching. The G0 evidence file was not modified.

## Conclusion

Side A M1 inputs are `SELF-VALIDATED`. All six controller conditions on SB-HO-B0-001 evaluate CLOSED. A1-PAYLOAD-001 and HO-A-B-003 remain `DRAFT` until controller and Side B processing. A0-EXT-001 remains `BLOCKED` because no external party is assigned and no external evidence exists. G0 remains `BLOCKED` / `NO_GO` on DEP-001 and DEP-011.
