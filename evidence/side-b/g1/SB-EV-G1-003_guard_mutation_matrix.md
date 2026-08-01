# G1 M1 Guard Mutation Matrix — proof that each negative test actually guards

- Artifact ID: SB-EV-G1-003
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `platform/poc/scripts/mutation_guard_check.py`; SB-EV-G1-002; controller M1 task C
- Acceptance criteria: for every required negative rule, the guard is temporarily removed from the source, the guarding test is shown to FAIL, and the source is restored; a surviving mutation is reported rather than hidden.
- Validation procedure/result: 19 mutations executed; 19 detected; 0 survived; suite green before and after; exit 0.
- Evidence path: `evidence/side-b/g1/SB-EV-G1-003_guard_mutation_matrix.md` (+ full transcript `SB-EV-G1-003_mutation_transcript.txt`, 85 048 bytes)
- Readiness status: AUTOMATED-TESTED
- Downstream consumer: controller M1 review; SB-AR-B3-004 field disposition
- Remaining risks/next action: mutation coverage proves the tests detect *guard removal*. It does not prove the guards encode correct business rules — that still requires Side A approval of each rule.

## Why this artifact exists

A negative test that passes is not automatically a guard. It can pass because of an unrelated error code, an over-broad assertion, or a fixture accident. The controller required proof by construction: break the guard, watch the test fail, restore.

`platform/poc/scripts/mutation_guard_check.py` automates this. For each mutation it patches exactly one anchor in one source file (refusing to run if the anchor does not match exactly once), runs only the tests that claim to guard that rule, asserts a **non-zero** exit, and restores the file from a temporary backup in a `finally` block. It verifies the suite is green before the first mutation and green again after the last.

## Result

```text
WORKING DIRECTORY: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc
COMMAND: python scripts/mutation_guard_check.py

=== BASELINE (unmutated suite must be green) ===
COMMAND: python -m pytest -q
EXIT_CODE: 0
53 passed, 1 warning in 2.02s

... 19 mutations ...

=== RESTORED (suite must be green again) ===
COMMAND: python -m pytest -q
EXIT_CODE: 0
53 passed, 1 warning in 2.05s

MUTATIONS RUN: 19
DETECTED:      19
SURVIVED:      0
RESULT: every guard removal was detected by its guarding test.
EXIT_CODE: 0
```

## Matrix

| ID | Guard removed | Target | Guarding test(s) | Exit | Result |
|---|---|---|---|---|---|
| M01 | `DUPLICATE_PRODUCT_ID` | `app/candidate_activation.py` | `test_duplicate_product_ids_and_skus_are_rejected` | 1 | DETECTED |
| M02 | `DUPLICATE_SKU` | `app/candidate_activation.py` | `..._are_rejected`, `test_duplicate_sku_across_distinct_products_is_rejected` | 1 | DETECTED |
| M03 | `MISSING_EVIDENCE` | `app/candidate_activation.py` | `test_missing_required_evidence_prevents_sellable_public_activation` | 1 | DETECTED |
| M04 | `EXPIRED_EVIDENCE` | `app/candidate_activation.py` | `test_expired_evidence_prevents_activation` | 1 | DETECTED |
| M05 | `BATCH_NOT_RELEASED` | `app/candidate_activation.py` | `test_unreleased_batch_prevents_activation`, API fail-closed test | 1 | DETECTED |
| M06 | `MISSING_OPERATOR` | `app/candidate_activation.py` | `test_missing_responsible_operator_prevents_activation`, API fail-closed test | 1 | DETECTED |
| M07 | `UNAPPROVED_PRICE` | `app/candidate_activation.py` | `test_unapproved_price_prevents_activation`, API fail-closed test | 1 | DETECTED |
| M08 | `POSITIVE_STOCK_WITHOUT_QC_EVIDENCE` | `app/candidate_activation.py` | `test_positive_stock_requires_qc_location_and_count_evidence` | 1 | DETECTED |
| M09 | `POSITIVE_STOCK_WITHOUT_LOCATION` | `app/candidate_activation.py` | same | 1 | DETECTED |
| M10 | `POSITIVE_STOCK_WITHOUT_COUNT_EVIDENCE` | `app/candidate_activation.py` | same | 1 | DETECTED |
| M11 | `UNSUPPORTED_CLAIM` | `app/candidate_activation.py` | `test_unsupported_claim_prevents_publication`, `test_expired_claim_prevents_publication` | 1 | DETECTED |
| M12 | `PUBLIC_REQUIRES_SELLABLE` | `app/candidate_activation.py` | `test_publication_cannot_bypass_sellable_lifecycle` | 1 | DETECTED |
| M13 | `SYNTHETIC_CANNOT_ACTIVATE` | `app/candidate_activation.py` | `test_synthetic_fixture_cannot_activate`, API fail-closed test | 1 | DETECTED |
| M14 | `PriceRecord.gross_minor_units` strict int | `app/candidate_activation.py` | `test_authoritative_money_rejects_float_minor_units` | 1 | DETECTED |
| M15 | `to_minor_units` float rejection | `app/money.py` | `test_to_minor_units_rejects_binary_float`, `test_product_schema_rejects_binary_float_price` | 1 | DETECTED |
| M16 | catalog `parse_float=Decimal` | `app/catalog.py` | `test_catalog_fixture_never_produces_binary_float` | 1 | DETECTED |
| M17 | `sum_line_totals` integer arithmetic | `app/money.py` | `test_line_total_summation_is_exact_where_a_float_path_drifts` | 1 | DETECTED |
| M18 | `sum_line_totals` integer type check | `app/money.py` | `test_line_total_summation_rejects_float_unit_price` | 1 | DETECTED |
| M19 | `OrderQuote.subtotal_minor_units` strict int | `app/schemas.py` | `test_quote_wire_field_rejects_float_subtotal` | 1 | DETECTED |

Every mutation's full pytest failure output is preserved in the attached transcript.

## Honest record of a surviving mutation, and how it was closed

The first execution of this harness produced **18 detected, 1 survived**:

```text
MUTATION: M17_quote_integer_arithmetic
GUARD: quote subtotal computed in integer minor units
COMMAND: python -m pytest -q tests/test_money_integrity.py::test_quote_totals_are_exact_in_minor_units
EXIT_CODE: 0
EXPECTED: non-zero (guarding test must fail when the guard is removed)
RESULT: SURVIVED — TEST DOES NOT GUARD
1 passed, 1 warning in 2.33s
```

Reintroducing a float round-trip in the quote path (`int(round((minor/100) * qty * 100))`) did **not** break the test, because at the fixture's magnitudes the final rounding absorbs the floating-point error. The test was passing for the wrong reason.

This is not a harness artefact — it is exactly why float money bugs survive review. It was closed by making the invariant structurally testable rather than incidentally true:

1. The line arithmetic was extracted into a pure function `money.sum_line_totals`.
2. A test was added using an adversarial case where the float path is *provably* wrong: EUR 0.70 x 3 is exactly 210 minor units, but `int((70/100) * 3 * 100)` evaluates to **209**.
3. Two further mutations (M18, M19) were added to prove the type contract also blocks a float from reaching the authoritative field and the wire.

Re-run after the change: **19 run, 19 detected, 0 survived, exit 0.**

## Limitation

Mutation testing here is a targeted, hand-authored matrix over named guards, not exhaustive automated mutation coverage of the codebase. Untested code paths remain untested. This is a PoC quality control, not a production assurance claim.
