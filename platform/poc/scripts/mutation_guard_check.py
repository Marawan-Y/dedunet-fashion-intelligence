"""Guard mutation harness for the candidate-activation negative regression suite.

Purpose
-------
A negative test is only meaningful if it fails when the guard it claims to protect
is removed. This harness temporarily removes one guard at a time from the source
under test, runs the specific test that must detect that removal, and asserts the
test FAILS. The original source is always restored, including on error.

This is a local developer/CI verification tool. It is not a production control and
proves nothing about production systems.

Usage
-----
    python scripts/mutation_guard_check.py            # run every mutation
    python scripts/mutation_guard_check.py --list     # list mutation IDs
    python scripts/mutation_guard_check.py --only ID  # run one mutation

Exit codes
----------
    0  every mutation was detected by its guarding test (suite is meaningful)
    1  at least one mutation survived (a guarding test does not actually guard)
    2  harness error (patch anchor not found, restore failure, ...)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


@dataclass(frozen=True)
class Mutation:
    """One guard removal and the test(s) that must detect it."""

    mutation_id: str
    guard: str
    target: Path
    original: str
    mutated: str
    tests: tuple[str, ...]
    notes: str = ""
    covers: tuple[str, ...] = field(default_factory=tuple)


CANDIDATE_ACTIVATION = BACKEND / "app" / "candidate_activation.py"
SCHEMAS = BACKEND / "app" / "schemas.py"
MONEY = BACKEND / "app" / "money.py"

TEST_CANDIDATE = "tests/test_candidate_activation.py"
TEST_API = "tests/test_api.py"
TEST_MONEY = "tests/test_money_integrity.py"


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        mutation_id="M01_duplicate_product_id",
        guard="DUPLICATE_PRODUCT_ID",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    product_counts = Counter(item.product_id for item in candidates)\n'
            '    for product_id, count in product_counts.items():\n'
            '        if count > 1:\n'
            '            errors.append(_error("DUPLICATE_PRODUCT_ID", "product_id", f"duplicate product ID: {product_id}"))\n'
        ),
        mutated="    # MUTATED: duplicate product ID guard removed\n",
        tests=(f"{TEST_CANDIDATE}::test_duplicate_product_ids_and_skus_are_rejected",),
        covers=("duplicate product IDs",),
    ),
    Mutation(
        mutation_id="M02_duplicate_sku",
        guard="DUPLICATE_SKU",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    skus = [variant.sku for candidate in candidates for variant in candidate.variants]\n'
            '    for sku, count in Counter(skus).items():\n'
            '        if count > 1:\n'
            '            errors.append(_error("DUPLICATE_SKU", "variants.sku", f"duplicate SKU: {sku}"))\n'
        ),
        mutated="    # MUTATED: duplicate SKU guard removed\n",
        tests=(
            f"{TEST_CANDIDATE}::test_duplicate_product_ids_and_skus_are_rejected",
            f"{TEST_CANDIDATE}::test_duplicate_sku_across_distinct_products_is_rejected",
        ),
        covers=("duplicate SKUs",),
    ),
    Mutation(
        mutation_id="M03_missing_evidence",
        guard="MISSING_EVIDENCE",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    if not evidence_id or evidence_id not in evidence_by_id:\n'
            '        return [_error("MISSING_EVIDENCE", field, f"current {required_scope} evidence is required")]\n'
        ),
        mutated=(
            '    if not evidence_id or evidence_id not in evidence_by_id:\n'
            '        return []  # MUTATED: missing-evidence guard removed\n'
        ),
        tests=(
            f"{TEST_CANDIDATE}::test_missing_required_evidence_prevents_sellable_public_activation",
        ),
        covers=("missing evidence",),
    ),
    Mutation(
        mutation_id="M04_expired_evidence",
        guard="EXPIRED_EVIDENCE",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    if evidence.expires_at is not None and evidence.expires_at <= now:\n'
            '        errors.append(_error("EXPIRED_EVIDENCE", field, f"evidence {evidence_id} is expired"))\n'
        ),
        mutated="    # MUTATED: expired-evidence guard removed\n",
        tests=(f"{TEST_CANDIDATE}::test_expired_evidence_prevents_activation",),
        covers=("expired evidence",),
    ),
    Mutation(
        mutation_id="M05_unreleased_batch",
        guard="BATCH_NOT_RELEASED",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    if candidate.batch is None or candidate.batch.qc_release_status != "released":\n'
            '        errors.append(_error("BATCH_NOT_RELEASED", "batch.qc_release_status", "only a released batch can activate"))\n'
        ),
        mutated="    # MUTATED: unreleased-batch guard removed\n",
        tests=(
            f"{TEST_CANDIDATE}::test_unreleased_batch_prevents_activation",
            f"{TEST_API}::test_candidate_activation_endpoint_fails_closed",
        ),
        covers=("unreleased batch",),
    ),
    Mutation(
        mutation_id="M06_missing_operator",
        guard="MISSING_OPERATOR",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    if not candidate.importer_responsible_operator_id:\n'
            '        errors.append(_error("MISSING_OPERATOR", "importer_responsible_operator_id", "a verified responsible operator is required"))\n'
        ),
        mutated="    # MUTATED: missing-operator guard removed\n",
        tests=(
            f"{TEST_CANDIDATE}::test_missing_responsible_operator_prevents_activation",
            f"{TEST_API}::test_candidate_activation_endpoint_fails_closed",
        ),
        covers=("missing operator",),
    ),
    Mutation(
        mutation_id="M07_unapproved_price",
        guard="UNAPPROVED_PRICE",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    if candidate.price is None or not candidate.price.approved:\n'
            '        errors.append(_error("UNAPPROVED_PRICE", "price", "an approved price is required"))\n'
        ),
        mutated=(
            '    if candidate.price is None or not candidate.price.approved:\n'
            '        pass  # MUTATED: unapproved-price guard removed\n'
        ),
        tests=(
            f"{TEST_CANDIDATE}::test_unapproved_price_prevents_activation",
            f"{TEST_API}::test_candidate_activation_endpoint_fails_closed",
        ),
        covers=("unapproved price",),
    ),
    Mutation(
        mutation_id="M08_positive_stock_qc_evidence",
        guard="POSITIVE_STOCK_WITHOUT_QC_EVIDENCE",
        target=CANDIDATE_ACTIVATION,
        original=(
            '        if candidate.batch is None or not candidate.batch.qc_evidence_id:\n'
            '            errors.append(_error("POSITIVE_STOCK_WITHOUT_QC_EVIDENCE", "batch.qc_evidence_id", "positive stock requires QC evidence"))\n'
            '        else:\n'
        ),
        mutated=(
            '        if False:  # MUTATED: positive-stock QC-evidence guard removed\n'
            '            pass\n'
            '        elif candidate.batch is not None and candidate.batch.qc_evidence_id:\n'
        ),
        tests=(
            f"{TEST_CANDIDATE}::test_positive_stock_requires_qc_location_and_count_evidence",
        ),
        covers=("unauthorized positive stock (QC evidence)",),
    ),
    Mutation(
        mutation_id="M09_positive_stock_location",
        guard="POSITIVE_STOCK_WITHOUT_LOCATION",
        target=CANDIDATE_ACTIVATION,
        original=(
            '        if not candidate.warehouse_location_id:\n'
            '            errors.append(_error("POSITIVE_STOCK_WITHOUT_LOCATION", "warehouse_location_id", "positive stock requires an accepted location"))\n'
        ),
        mutated="        # MUTATED: positive-stock location guard removed\n",
        tests=(
            f"{TEST_CANDIDATE}::test_positive_stock_requires_qc_location_and_count_evidence",
        ),
        covers=("unauthorized positive stock (location)",),
    ),
    Mutation(
        mutation_id="M10_positive_stock_count_evidence",
        guard="POSITIVE_STOCK_WITHOUT_COUNT_EVIDENCE",
        target=CANDIDATE_ACTIVATION,
        original=(
            '            if not variant.count_evidence_id:\n'
            '                errors.append(_error("POSITIVE_STOCK_WITHOUT_COUNT_EVIDENCE", f"variants[{variant.sku}].count_evidence_id", "positive stock requires count evidence"))\n'
            '            else:\n'
        ),
        mutated=(
            '            if False:  # MUTATED: positive-stock count-evidence guard removed\n'
            '                pass\n'
            '            elif variant.count_evidence_id:\n'
        ),
        tests=(
            f"{TEST_CANDIDATE}::test_positive_stock_requires_qc_location_and_count_evidence",
        ),
        covers=("unauthorized positive stock (count evidence)",),
    ),
    Mutation(
        mutation_id="M11_unsupported_claim",
        guard="UNSUPPORTED_CLAIM",
        target=CANDIDATE_ACTIVATION,
        original=(
            '        if claim.expires_at <= now or claim_errors:\n'
            '            errors.append(_error("UNSUPPORTED_CLAIM", f"approved_claims[{index}]", "claim lacks current scoped approval evidence"))\n'
        ),
        mutated="        # MUTATED: unsupported-claim publication guard removed\n",
        tests=(
            f"{TEST_CANDIDATE}::test_unsupported_claim_prevents_publication",
            f"{TEST_CANDIDATE}::test_expired_claim_prevents_publication",
        ),
        covers=("unsupported claim publication",),
    ),
    Mutation(
        mutation_id="M12_public_requires_sellable",
        guard="PUBLIC_REQUIRES_SELLABLE",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    if candidate.publication_status is PublicationStatus.PUBLIC and candidate.lifecycle_status is not BusinessLifecycle.SELLABLE:\n'
            '        errors.append(_error("PUBLIC_REQUIRES_SELLABLE", "publication_status", "public publication requires business lifecycle sellable"))\n'
        ),
        mutated="    # MUTATED: public-requires-sellable guard removed\n",
        tests=(f"{TEST_CANDIDATE}::test_publication_cannot_bypass_sellable_lifecycle",),
        covers=("technical publication cannot bypass business lifecycle",),
    ),
    Mutation(
        mutation_id="M13_synthetic_cannot_activate",
        guard="SYNTHETIC_CANNOT_ACTIVATE",
        target=CANDIDATE_ACTIVATION,
        original=(
            '    if candidate.synthetic_fixture:\n'
            '        errors.append(_error("SYNTHETIC_CANNOT_ACTIVATE", "synthetic_fixture", "synthetic fixtures cannot become sellable or public"))\n'
        ),
        mutated="    # MUTATED: synthetic-fixture activation guard removed\n",
        tests=(
            f"{TEST_CANDIDATE}::test_synthetic_fixture_cannot_activate",
            f"{TEST_API}::test_candidate_activation_endpoint_fails_closed",
        ),
        covers=("synthetic fixture cannot be sold or published",),
    ),
    Mutation(
        mutation_id="M14_candidate_price_float_rejection",
        guard="PriceRecord.gross_minor_units strict integer",
        target=CANDIDATE_ACTIVATION,
        original="    gross_minor_units: int = Field(strict=True, gt=0)\n",
        mutated="    gross_minor_units: int = Field(gt=0)  # MUTATED: strict integer removed\n",
        tests=(
            f"{TEST_CANDIDATE}::test_authoritative_money_rejects_float_minor_units",
        ),
        covers=("authoritative money is integer minor units (candidate record)",),
    ),
    Mutation(
        mutation_id="M15_catalog_price_float_rejection",
        guard="money.to_minor_units rejects binary float",
        target=MONEY,
        original=(
            "    if isinstance(value, float):\n"
            "        raise FloatMoneyRejected(\n"
            '            "binary float is not an accepted authoritative money input; "\n'
            '            "supply an integer minor-unit value, a Decimal, or a decimal string"\n'
            "        )\n"
        ),
        mutated=(
            "    if isinstance(value, float):\n"
            "        value = Decimal(str(value))  # MUTATED: float rejection removed\n"
        ),
        tests=(
            f"{TEST_MONEY}::test_to_minor_units_rejects_binary_float",
            f"{TEST_MONEY}::test_product_schema_rejects_binary_float_price",
        ),
        covers=("no float money path at the ingestion boundary",),
    ),
    Mutation(
        mutation_id="M16_catalog_decimal_parsing",
        guard="catalog JSON parsed with parse_float=Decimal",
        target=BACKEND / "app" / "catalog.py",
        original="            data = json.load(handle, parse_float=Decimal)\n",
        mutated="            data = json.load(handle)  # MUTATED: exact decimal parsing removed\n",
        tests=(f"{TEST_MONEY}::test_catalog_fixture_never_produces_binary_float",),
        covers=("catalog fixture money never becomes a binary float",),
    ),
    Mutation(
        mutation_id="M17_line_total_integer_arithmetic",
        guard="sum_line_totals uses integer arithmetic",
        target=MONEY,
        original="        total += unit_minor_units * quantity\n",
        mutated=(
            "        total = int((unit_minor_units / 100) * quantity * 100) + total"
            "  # MUTATED: float round-trip reintroduced\n"
        ),
        tests=(
            f"{TEST_MONEY}::test_line_total_summation_is_exact_where_a_float_path_drifts",
        ),
        covers=("quote/line arithmetic is integer-only and exact",),
        notes=(
            "Reintroduces the classic major-unit float round-trip. Detected by the "
            "EUR 0.70 x 3 adversarial case, which truncates to 209 instead of 210."
        ),
    ),
    Mutation(
        mutation_id="M18_line_total_float_type_rejection",
        guard="sum_line_totals rejects a non-integer unit price",
        target=MONEY,
        original=(
            "        if isinstance(unit_minor_units, bool) or not isinstance(unit_minor_units, int):\n"
            "            raise FloatMoneyRejected(\n"
            '                f"unit price must be integer minor units, got "\n'
            '                f"{type(unit_minor_units).__name__}"\n'
            "            )\n"
        ),
        mutated="        # MUTATED: line-item integer type guard removed\n",
        tests=(f"{TEST_MONEY}::test_line_total_summation_rejects_float_unit_price",),
        covers=("no float unit price can enter the authoritative total",),
    ),
    Mutation(
        mutation_id="M19_quote_wire_type_is_strict_int",
        guard="OrderQuote.subtotal_minor_units strict integer",
        target=SCHEMAS,
        original="    subtotal_minor_units: int = Field(strict=True, ge=0)\n",
        mutated="    subtotal_minor_units: int = Field(ge=0)  # MUTATED: strict integer removed\n",
        tests=(f"{TEST_MONEY}::test_quote_wire_field_rejects_float_subtotal",),
        covers=("a float can never be serialized onto the authoritative quote wire",),
    ),
)


def _run_pytest(node_ids: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *node_ids],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )


def _apply(mutation: Mutation) -> None:
    source = mutation.target.read_text(encoding="utf-8")
    occurrences = source.count(mutation.original)
    if occurrences != 1:
        raise SystemExit(
            f"HARNESS ERROR: anchor for {mutation.mutation_id} matched {occurrences} times "
            f"in {mutation.target} (expected exactly 1)"
        )
    mutation.target.write_text(
        source.replace(mutation.original, mutation.mutated), encoding="utf-8"
    )


def run_mutation(mutation: Mutation) -> tuple[bool, str]:
    """Return (detected, transcript). `detected` means the guarding test failed."""

    with tempfile.TemporaryDirectory() as tmp:
        backup = Path(tmp) / mutation.target.name
        shutil.copy2(mutation.target, backup)
        try:
            _apply(mutation)
            result = _run_pytest(mutation.tests)
        finally:
            shutil.copy2(backup, mutation.target)

    detected = result.returncode != 0
    transcript = (
        f"MUTATION: {mutation.mutation_id}\n"
        f"GUARD: {mutation.guard}\n"
        f"TARGET: {mutation.target.relative_to(ROOT).as_posix()}\n"
        f"COVERS: {'; '.join(mutation.covers)}\n"
        f"COMMAND: python -m pytest -q {' '.join(mutation.tests)}\n"
        f"EXIT_CODE: {result.returncode}\n"
        f"EXPECTED: non-zero (guarding test must fail when the guard is removed)\n"
        f"RESULT: {'DETECTED' if detected else 'SURVIVED — TEST DOES NOT GUARD'}\n"
        f"--- stdout ---\n{result.stdout.strip()}\n"
    )
    if result.stderr.strip():
        transcript += f"--- stderr ---\n{result.stderr.strip()}\n"
    return detected, transcript


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list mutation IDs and exit")
    parser.add_argument("--only", help="run a single mutation by ID")
    args = parser.parse_args()

    if args.list:
        for mutation in MUTATIONS:
            print(f"{mutation.mutation_id}\t{mutation.guard}")
        return 0

    selected = [m for m in MUTATIONS if not args.only or m.mutation_id == args.only]
    if not selected:
        print(f"No mutation matches {args.only!r}")
        return 2

    baseline = _run_pytest(())
    print("=== BASELINE (unmutated suite must be green) ===")
    print(f"COMMAND: python -m pytest -q")
    print(f"EXIT_CODE: {baseline.returncode}")
    print(baseline.stdout.strip())
    if baseline.returncode != 0:
        print("HARNESS ERROR: baseline suite is not green; fix that before mutating.")
        return 2

    survived: list[str] = []
    for mutation in selected:
        detected, transcript = run_mutation(mutation)
        print("=" * 78)
        print(transcript)
        if not detected:
            survived.append(mutation.mutation_id)

    restored = _run_pytest(())
    print("=" * 78)
    print("=== RESTORED (suite must be green again) ===")
    print(f"COMMAND: python -m pytest -q")
    print(f"EXIT_CODE: {restored.returncode}")
    print(restored.stdout.strip())
    if restored.returncode != 0:
        print("HARNESS ERROR: source was not restored cleanly.")
        return 2

    print("=" * 78)
    print(f"MUTATIONS RUN: {len(selected)}")
    print(f"DETECTED:      {len(selected) - len(survived)}")
    print(f"SURVIVED:      {len(survived)}")
    if survived:
        print("SURVIVING MUTATIONS (these guards are not actually tested):")
        for mutation_id in survived:
            print(f"  - {mutation_id}")
        return 1
    print("RESULT: every guard removal was detected by its guarding test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
