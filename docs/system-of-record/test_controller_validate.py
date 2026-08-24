"""Targeted tests for the controller integrity validator.

The validator was scoped down on 2026-08-24, from 585 errors to 9, by narrowing WHAT IT
INSPECTS. Every one of the 576 removed was a false positive.

That is a dangerous kind of change: the easy way to make a validator green is to stop it
checking, and the difference between "correctly scoped" and "quietly disabled" is not
visible in an error count. These tests exist to make it visible.

Every scoping rule therefore gets a test **in both directions**:

    the false positive it removed is gone          (the fix worked)
    the real violation it must still catch fails   (the fix did not disable the check)

The second half is the one that matters. A test suite that only asserted the errors went
away would pass just as happily against a validator whose body had been deleted.

Run:
    python -m pytest docs/system-of-record/test_controller_validate.py -q
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / "controller_validate.py"
REPO = HERE.parents[1]


# --------------------------------------------------------------------------- helpers


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the validator against `root` by copying it in.

    The validator derives ROOT from its own location, which is the portability fix this
    change also made. Copying it into a fixture tree is therefore the whole mechanism —
    no environment variable, no monkeypatching, no import-time surgery.
    """

    target = root / "docs" / "system-of-record"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VALIDATOR, target / "controller_validate.py")
    return subprocess.run(
        [sys.executable, str(target / "controller_validate.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return p


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A minimal repository shaped like this one, with nothing wrong in it."""

    write(tmp_path, "docs/registers/clean.csv", """
        artifact_id,artifact_status,artifact_evidence_path
        A-001,AUTOMATED-TESTED,docs/registers/clean.csv
        A-002,SELF-VALIDATED,docs/registers/clean.csv
    """)
    return tmp_path


# ======================================================== the vocabulary still bites
#
# Requirement 5: prove legitimate invalid evidence statuses are still rejected.


@pytest.mark.parametrize("column", ["artifact_status", "readiness_status", "status", "evidence_status"])
def test_an_invalid_evidence_status_is_rejected_in_every_governed_column(tree, column):
    """The check must still fail for a bad value in each column it governs.

    Parametrised over all four rather than testing one, because the scoping change
    replaced a substring match with an explicit set — and a set is exactly the kind of
    thing that loses a member without anyone noticing.
    """

    write(tree, "docs/registers/bad.csv", f"""
        artifact_id,{column}
        A-001,NOT-A-REAL-STATUS
    """)
    result = run_validator(tree)
    assert "BAD STATUS" in result.stdout, result.stdout
    assert "NOT-A-REAL-STATUS" in result.stdout
    assert result.returncode == 1


def test_every_allowed_status_passes(tree):
    """The seven declared statuses must not be reported. Guards over-tightening."""

    rows = "\n".join(
        f"A-{i:03d},{s}"
        for i, s in enumerate(
            ["DRAFT", "SELF-VALIDATED", "AUTOMATED-TESTED", "HUMAN-VERIFIED",
             "EXTERNALLY-VERIFIED", "BLOCKED", "REJECTED"], start=1)
    )
    write(tree, "docs/registers/all.csv", f"artifact_id,artifact_status\n{rows}\n")
    result = run_validator(tree)
    assert "BAD STATUS" not in result.stdout, result.stdout


# ======================================================== SCOPE 3: which columns
#
# The 442-error class. `runtime_status=build-time` is not an invalid evidence status;
# it is not an evidence status at all.


@pytest.mark.parametrize(
    "column,value",
    [
        ("runtime_status", "build-time"),
        ("migration_status", "DONE"),
        ("inventory_status", "prototype_unavailable"),
        ("ownership_status", "ORIGINAL_PROTOTYPE_ASSET"),
    ],
)
def test_domain_status_columns_are_not_judged_by_the_evidence_vocabulary(tree, column, value):
    """The exact four columns and values that produced 442 of the 585 errors."""

    write(tree, "docs/registers/domain.csv", f"""
        artifact_id,{column}
        A-001,{value}
    """)
    result = run_validator(tree)
    assert "BAD STATUS" not in result.stdout, result.stdout


def test_a_new_status_shaped_column_is_not_silently_governed(tree):
    """A column nobody has classified must not be assumed to be an evidence status.

    Requirement 3, stated as behaviour rather than as a comment: "do not assume any field
    ending in _status is an evidence status".
    """

    write(tree, "docs/registers/novel.csv", """
        artifact_id,sync_status
        A-001,PARTIALLY_SYNCED
    """)
    result = run_validator(tree)
    assert "BAD STATUS" not in result.stdout, result.stdout


def test_risk_state_keeps_its_own_vocabulary(tree):
    """`current_status` is the risk axis (DEC-009), not artifact readiness."""

    write(tree, "docs/registers/risk.csv", """
        risk_id,current_status
        R-001,PARTIALLY MITIGATED
        R-002,MITIGATED
    """)
    assert "BAD" not in run_validator(tree).stdout

    write(tree, "docs/registers/risk.csv", """
        risk_id,current_status
        R-001,SOMETHING-ELSE
    """)
    assert "BAD RISK STATE" in run_validator(tree).stdout


# ======================================================== SCOPE 6: two axes
#
# Readiness ("how well is this proven?") and supersession ("is this still the current
# record?") are independent. They shared one column until 2026-08-24, and writing
# SUPERSEDED into it destroyed the readiness four evidence documents had declared.


def test_superseded_is_valid_in_the_supersession_column(tree):
    write(tree, "docs/side-b/EVIDENCE_INDEX.csv", """
        evidence_id,readiness_status,supersession_status,superseded_by
        EV-001,AUTOMATED-TESTED,SUPERSEDED,EV-002
        EV-002,AUTOMATED-TESTED,CURRENT,
    """)
    result = run_validator(tree)
    assert "BAD STATUS" not in result.stdout, result.stdout
    assert "BAD SUPERSESSION" not in result.stdout, result.stdout


def test_superseded_remains_invalid_in_a_readiness_column(tree):
    """The whole point of the split.

    If SUPERSEDED had simply been added to the readiness vocabulary, the overwrite that
    destroyed four readiness values would have become legal again. It must stay illegal
    there, which is a different assertion from "SUPERSEDED is valid somewhere".
    """

    write(tree, "docs/side-b/EVIDENCE_INDEX.csv", """
        evidence_id,readiness_status
        EV-001,SUPERSEDED
    """)
    result = run_validator(tree)
    assert "BAD STATUS" in result.stdout, result.stdout
    assert result.returncode == 1


def test_an_invalid_supersession_value_is_rejected(tree):
    """The lifecycle axis is validated, not merely exempted from the other one."""

    write(tree, "docs/side-b/EVIDENCE_INDEX.csv", """
        evidence_id,readiness_status,supersession_status
        EV-001,AUTOMATED-TESTED,RETIRED
    """)
    result = run_validator(tree)
    assert "BAD SUPERSESSION" in result.stdout, result.stdout
    assert "RETIRED" in result.stdout
    assert result.returncode == 1


def test_a_readiness_value_is_rejected_in_the_supersession_column(tree):
    """Both directions. The two vocabularies must not be interchangeable."""

    write(tree, "docs/side-b/EVIDENCE_INDEX.csv", """
        evidence_id,supersession_status
        EV-001,AUTOMATED-TESTED
    """)
    assert "BAD SUPERSESSION" in run_validator(tree).stdout


def test_the_repository_preserves_recovered_readiness_for_superseded_evidence():
    """The four rows whose readiness was destroyed, restored from their own documents.

    Asserted against the live register rather than a fixture, because the recovery is the
    claim: each value must equal what its evidence document declares, and a future edit
    that re-flattened the two axes would fail here.
    """

    import csv as _csv
    import io as _io

    index = REPO / "docs" / "side-b" / "EVIDENCE_INDEX.csv"
    rows = {r["evidence_id"]: r for r in
            _csv.DictReader(_io.StringIO(index.read_text(encoding="utf-8-sig")))}

    expected = {
        "SB-EV-BOOT-001": "SELF-VALIDATED",
        "SB-EV-BOOT-002": "AUTOMATED-TESTED",
        "SB-EV-BOOT-003": "BLOCKED",
        "SB-EV-BOOT-004": "BLOCKED",
        "SB-EV-BOOT-005": "SELF-VALIDATED",
        "SB-EV-G1-001": "SELF-VALIDATED",
    }
    for evidence_id, readiness in expected.items():
        row = rows[evidence_id]
        assert row["readiness_status"] == readiness, (evidence_id, row)
        assert row["supersession_status"] == "SUPERSEDED", (evidence_id, row)
        assert row["superseded_by"], f"{evidence_id} has no supersession provenance"


def test_recovered_readiness_matches_each_evidence_document():
    """The recovery method itself, re-executed rather than trusted.

    SB-EV-BOOT-003 is the control: its value was never overwritten with SUPERSEDED, so
    document-and-index agreeing there is what shows the method reads the right field
    rather than that the index was written to match.
    """

    import csv as _csv
    import io as _io
    import re as _re

    index = REPO / "docs" / "side-b" / "EVIDENCE_INDEX.csv"
    pattern = _re.compile(r"^\s*-\s*Readiness status:\s*(\S+)\s*$", _re.M | _re.I)

    checked = 0
    for row in _csv.DictReader(_io.StringIO(index.read_text(encoding="utf-8-sig"))):
        doc = REPO / row["path"]
        if not doc.exists() or doc.suffix != ".md":
            continue
        m = pattern.search(doc.read_text(encoding="utf-8", errors="replace"))
        if not m:
            continue
        assert m.group(1).strip() == row["readiness_status"], (
            f"{row['evidence_id']}: index says {row['readiness_status']!r}, "
            f"document says {m.group(1)!r}"
        )
        checked += 1
    assert checked >= 6, f"only {checked} documents declared a readiness status"


# ======================================================== SCOPE 2: whose schema


def test_partner_data_packages_are_not_judged_by_our_vocabulary(tree):
    """`handoffs/incoming/` is immutable partner data with its own schema and validator.

    93 of the 585 errors were here, and none was fixable: the package is checksum-sealed,
    so satisfying the check would have required breaking its own manifest.
    """

    write(tree, "handoffs/incoming/partner/data/assets.csv", """
        asset_id,status
        AS-001,PROTOTYPE_CONCEPT
    """)
    result = run_validator(tree)
    assert "BAD STATUS" not in result.stdout, result.stdout


def test_our_own_registers_are_still_judged(tree):
    """The counterpart. Partner exemption must not leak into our registers."""

    write(tree, "docs/side-b/EVIDENCE_INDEX.csv", """
        evidence_id,status
        EV-001,PROTOTYPE_CONCEPT
    """)
    result = run_validator(tree)
    assert "BAD STATUS" in result.stdout, result.stdout


# ======================================================== SCOPE 1: dependency trees


def test_dependency_trees_are_not_scanned(tree):
    """A third party's README saying "Production-ready." is theirs, not a claim of ours.

    This was one real error in the 585: `apps/mobile/node_modules/expo/README.md`.
    """

    write(tree, "apps/mobile/node_modules/expo/README.md", """
        # Expo
        - **Production-ready.** Used in tens of thousands of apps.
    """)
    result = run_validator(tree)
    assert "UNSUPPORTED CLAIM" not in result.stdout, result.stdout


def test_our_own_documents_are_still_scanned(tree):
    """The counterpart, and the one that proves the exclusion is a filter not a bypass."""

    write(tree, "docs/claims.md", """
        # Status
        This build is production-ready.
    """)
    result = run_validator(tree)
    assert "UNSUPPORTED CLAIM" in result.stdout, result.stdout


def test_a_build_directory_inside_our_tree_is_excluded(tree):
    write(tree, "docs/dist/generated.md", "This build is production-ready.\n")
    assert "UNSUPPORTED CLAIM" not in run_validator(tree).stdout


# ======================================================== SCOPE 5: claim scanning


def test_a_phrase_inside_backticks_is_named_not_claimed(tree):
    """The `EV_A1_002` class: a document explaining a false positive was flagged for it."""

    write(tree, "docs/report.md", """
        ## False positive recorded and resolved

        The scan reported one hit, `payment activated`, which is part of that file's own
        prohibited-phrase regex rather than an assertion.
    """)
    result = run_validator(tree)
    assert "UNSUPPORTED CLAIM" not in result.stdout, result.stdout


def test_a_phrase_inside_a_fenced_block_is_not_a_claim(tree):
    write(tree, "docs/fenced.md", """
        Forbidden phrases:

        ```
        production-ready
        contract signed
        ```
    """)
    assert "UNSUPPORTED CLAIM" not in run_validator(tree).stdout


def test_a_negation_split_across_a_line_break_still_counts(tree):
    """The `CONTROLLER_VALIDATION_G1_M1` class.

    "Nothing here is\\nproduction-ready." put the negation on the previous physical line,
    so the strongest disclaimer in the document was reported as a claim.
    """

    write(tree, "docs/wrapped.md", """
        Every result above is a local proof of concept on synthetic fixtures. Nothing here is
        production-ready.
    """)
    result = run_validator(tree)
    assert "UNSUPPORTED CLAIM" not in result.stdout, result.stdout


def test_an_unhedged_claim_on_one_line_is_still_caught(tree):
    """The counterpart to the two above: widening context must not swallow real claims."""

    write(tree, "docs/plain.md", "The platform is production-ready and ships today.\n")
    assert "UNSUPPORTED CLAIM" in run_validator(tree).stdout


def test_a_negation_inside_code_does_not_excuse_a_claim_outside_it(tree):
    """Negation is read from masked text, so a `not` in a code span cannot launder a claim."""

    write(tree, "docs/laundered.md", """
        Run `grep -v not` first. The platform is production-ready.
    """)
    result = run_validator(tree)
    assert "UNSUPPORTED CLAIM" in result.stdout, result.stdout


# ======================================================== SCOPE 4: path references


def test_historical_path_columns_are_not_required_to_exist(tree):
    """`source_path` records where a file USED to be. Existing would be the surprise."""

    write(tree, "docs/architecture/MAP.csv", """
        source_path,target_path
        platform/poc/old.py,docs/architecture/MAP.csv
    """)
    result = run_validator(tree)
    assert "MISSING PATH" not in result.stdout, result.stdout


def test_prose_containing_a_path_is_not_a_path_reference(tree):
    """A `risk` sentence mentioning a path is a sentence, not a reference."""

    write(tree, "docs/registers/risks.csv", """
        risk_id,risk
        R-001,Secrets committed under platform/poc/.env in an earlier layout
    """)
    result = run_validator(tree)
    assert "MISSING PATH" not in result.stdout, result.stdout


def test_a_live_reference_column_pointing_nowhere_still_fails(tree):
    """The counterpart, and the property the check exists for.

    This is what caught the one real MISSING PATH: a `proving_evidence` cell still
    pointing at the pre-restructure `platform/poc/.github/workflows/ci.yml`.
    """

    write(tree, "docs/registers/live.csv", """
        artifact_id,artifact_evidence_path
        A-001,docs/evidence/does-not-exist.md
    """)
    result = run_validator(tree)
    assert "MISSING PATH" in result.stdout, result.stdout
    assert result.returncode == 1


# ======================================================== portability


def test_the_validator_resolves_its_own_root(tree):
    """It used to hard-code one machine's absolute path.

    Every test above depends on this: they run the validator from a temporary tree and
    would silently validate the real repository instead if ROOT were still fixed.
    """

    source = VALIDATOR.read_text(encoding="utf-8")
    assert "Path(__file__).resolve().parents[2]" in source
    assert "C:\\\\Users" not in source

    write(tree, "docs/registers/bad.csv", "artifact_id,artifact_status\nA-1,NOPE\n")
    result = run_validator(tree)
    assert "NOPE" in result.stdout, "the validator did not inspect the temporary tree"


# ======================================================== the repository itself


def test_the_repository_has_no_false_positive_classes_left():
    """Regression guard on the four classes that made up all 585 baseline errors.

    Asserts by CLASS, not by count. A total would move for legitimate reasons -- a new
    register, a genuine finding fixed -- and would then be edited to match, which is how a
    guard stops guarding.
    """

    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO),
    )

    # ERRORS only. The INFO block legitimately names partner files ("PK unique on
    # 'variant_id': handoffs/incoming/...") because uniqueness IS checked there -- it is
    # the readiness VOCABULARY that does not apply to them. Scanning the whole transcript
    # conflated the two and failed on a line reporting success.
    out = result.stdout.split("--- ERRORS", 1)[-1]

    for banned in ("runtime_status", "migration_status", "inventory_status", "ownership_status"):
        assert banned not in out, f"domain status column {banned} is being judged again"

    assert "node_modules" not in out, "dependency trees are being scanned again"
    assert "handoffs/incoming" not in out, "partner data is being judged by our vocabulary"
    assert "MISSING PATH" not in out, "path checking has regressed onto historical or prose columns"
