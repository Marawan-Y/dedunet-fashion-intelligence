"""Targeted tests for the handoff-envelope validator.

The validator went from 6/20 to 8/8 on 2026-08-24. Two of those documents were genuinely
repaired; the rest of the gap was scope — it had been demanding envelope fields of files
that are not handoff envelopes.

That is the same shape of change as the controller validator's, and carries the same
risk: "correctly scoped" and "quietly disabled" produce identical green output. So every
scoping rule is tested in both directions — the non-envelope is excluded, AND a real
envelope missing a required field still fails.

`REQUIRED` itself is unchanged. All eighteen fields are still demanded.

Run:
    python -m pytest docs/system-of-record/test_handoff_envelope_check.py -q
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / "handoff_envelope_check.py"
REPO = HERE.parents[1]

# A document carrying all eighteen envelope fields.
COMPLETE = """
    # HANDOFF SB-HO-TEST-001 — fixture

    | Envelope field | Value |
    |---|---|
    | Handoff ID | SB-HO-TEST-001 |
    | Version | 1.0.0 |
    | Sender | side_b_platform |
    | Receiver | controller |
    | Work packages | B1 |
    | Artifact IDs | SB-AR-TEST-001 |

    ## Purpose
    Fixture.

    ## Payload
    Files and data: none.

    ## Schema
    Version 1.0.0.

    ## Confirmed facts
    None.

    ## Assumptions
    None.

    ## Questions
    None.

    ## Acceptance criteria
    None.

    ## Validation
    None.

    ## Need-by, impact and fallback
    Need-by: G1. Impact: none. Fallback: none.

    ## Change control
    None.

    ## Disposition
    ACCEPT / REJECT.
"""


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    target = root / "docs" / "system-of-record"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VALIDATOR, target / "handoff_envelope_check.py")
    return subprocess.run(
        [sys.executable, str(target / "handoff_envelope_check.py")],
        capture_output=True, text=True, encoding="utf-8",
    )


def write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return p


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    write(tmp_path, "handoffs/outgoing/side-b/SB-HO-TEST-001_fixture.md", COMPLETE)
    return tmp_path


# ============================================================ the check still bites


def test_a_complete_envelope_passes(tree):
    result = run_validator(tree)
    assert "FAILED: 0" in result.stdout, result.stdout
    assert result.returncode == 0


@pytest.mark.parametrize("field,heading", [
    ("assumptions", "## Assumptions"),
    ("questions", "## Questions"),
    ("fallback", "## Need-by, impact and fallback"),
    ("change control", "## Change control"),
])
def test_an_envelope_missing_a_required_field_still_fails(tree, field, heading):
    """The two fields that actually failed, plus two others.

    Parametrised because the repair added exactly `assumptions` and `questions`; if the
    scoping change had also dropped them from REQUIRED, the documents would pass for the
    wrong reason and this file would be the only thing that noticed.
    """

    doc = tree / "handoffs/outgoing/side-b/SB-HO-TEST-001_fixture.md"
    text = doc.read_text(encoding="utf-8")
    stripped = "\n".join(
        line for line in text.splitlines()
        if field.split()[0].lower() not in line.lower()
    )
    doc.write_text(stripped, encoding="utf-8")

    result = run_validator(tree)
    assert "FAILED: 0" not in result.stdout, result.stdout
    assert field in result.stdout, result.stdout
    assert result.returncode == 1


def test_all_eighteen_fields_are_still_required(tree):
    """Guards the list itself against quiet shrinkage."""

    source = VALIDATOR.read_text(encoding="utf-8")
    body = source.split("REQUIRED = {", 1)[1].split("}", 1)[0]
    assert body.count(":") >= 18, "the required-field list has shrunk"
    for field in ("assumptions", "questions", "confirmed facts", "fallback",
                  "change control", "need-by gate/date", "disposition"):
        assert f'"{field}"' in body, f"{field} was removed from REQUIRED"


# ============================================================ scoping, both directions


def test_package_contents_are_not_treated_as_envelopes(tree):
    """A brand identity document inside a delivered package is not an envelope.

    Eleven such files produced the 6/20 result. The package is sealed by a SHA-256
    manifest, so satisfying the check would have meant breaking its own checksums.
    """

    write(tree, "handoffs/incoming/side-a/PARTNER_PACKAGE_v1/docs/brand/IDENTITY.md",
          "# Brand identity\n\nColours and typography.\n")
    write(tree, "handoffs/incoming/side-a/PARTNER_PACKAGE_v1/README.md",
          "# Package readme\n")
    result = run_validator(tree)
    assert "FAILED: 0" in result.stdout, result.stdout
    assert "Not envelopes" in result.stdout
    assert result.returncode == 0


def test_a_nested_handoffs_directory_is_not_counted_twice(tree):
    """The partner package carries its own `handoffs/` directory.

    `rglob("handoffs/**/*.md")` matched through both anchors, reporting 20 files when 19
    existed — a validator that cannot count its own inputs cannot be trusted with them.
    """

    write(tree, "handoffs/incoming/side-a/PARTNER_PACKAGE_v1/handoffs/outgoing/THEIRS.md",
          "# Their handoff\n")
    result = run_validator(tree)
    assert "CHECKED: 1" in result.stdout, result.stdout


def test_a_real_envelope_at_the_right_depth_is_still_checked(tree):
    """The counterpart. Exclusion must not swallow a document a side actually sent."""

    write(tree, "handoffs/outgoing/side-a/HO-A-B-999_incomplete.md",
          "# Handoff HO-A-B-999\n\nNothing else.\n")
    result = run_validator(tree)
    assert "FAILED: 0" not in result.stdout, result.stdout
    assert "HO-A-B-999" in result.stdout
    assert result.returncode == 1


def test_both_incoming_and_outgoing_are_governed(tree):
    write(tree, "handoffs/incoming/side-b/HO-INCOMING_incomplete.md", "# Incoming\n")
    result = run_validator(tree)
    assert "HO-INCOMING_incomplete" in result.stdout
    assert "FAILED: 0" not in result.stdout


# ============================================================ the repository itself


def test_the_repository_envelopes_all_pass():
    """Asserted as zero failures, not as a fixed count.

    A count would move when a handoff is added and would then be edited to match.
    """

    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO),
    )
    assert "FAILED: 0" in result.stdout, result.stdout
    assert result.returncode == 0
