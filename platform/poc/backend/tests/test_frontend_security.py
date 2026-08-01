"""Static guards on the browser clients.

These are cheap source-level assertions, not a substitute for a browser security test.
They exist because the specific defect they guard against (SB-RISK-003, stored XSS via
`innerHTML`) was previously shipped, and a regression would silently reintroduce it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[2]
CLIENT_SCRIPTS = [
    POC_ROOT / "storefront" / "app.js",
    POC_ROOT / "admin" / "admin.js",
]

# Sinks that interpret a string as markup or code. Assigning attacker-controlled data
# to any of these executes it in the customer's browser.
FORBIDDEN_SINKS = [
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    "eval(",
    "new Function(",
]


def strip_comments(source: str) -> list[tuple[int, str]]:
    """Return ``(line_number, code)`` with comments blanked out.

    Both ``/* */`` blocks and ``//`` tails are removed. These files document the very
    sinks they must not use, so scanning raw text would flag the safety notes as
    violations. Line numbering is preserved so offenders report a usable location.
    """

    # Blank block comments while keeping newlines, so line numbers do not shift.
    without_blocks = re.sub(
        r"/\*.*?\*/",
        lambda match: re.sub(r"[^\n]", " ", match.group(0)),
        source,
        flags=re.DOTALL,
    )
    return [
        (number, line.split("//", 1)[0])
        for number, line in enumerate(without_blocks.splitlines(), start=1)
    ]


@pytest.mark.parametrize("script", CLIENT_SCRIPTS, ids=lambda p: p.name)
def test_client_scripts_use_no_markup_sinks(script: Path) -> None:
    assert script.exists(), f"{script} is missing"

    offenders = []
    for line_number, code in strip_comments(script.read_text(encoding="utf-8")):
        for sink in FORBIDDEN_SINKS:
            if sink in code:
                offenders.append(f"{script.name}:{line_number} uses {sink}")

    assert not offenders, (
        "Markup/code sinks reintroduced (SB-RISK-003 stored XSS):\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("script", CLIENT_SCRIPTS, ids=lambda p: p.name)
def test_client_scripts_do_not_divide_money(script: Path) -> None:
    """Money must be formatted from integer minor units, never by dividing by 100.

    Division introduces a binary float onto a money path, which is exactly what
    contract SB-AR-B3-003 and DEC-010 forbid.
    """

    offenders = [
        f"{script.name}:{n}"
        for n, code in strip_comments(script.read_text(encoding="utf-8"))
        if "/ 100" in code or "/100" in code
    ]
    assert not offenders, "Money divided by 100 (float on a money path): " + ", ".join(offenders)


def test_storefront_is_marked_noindex() -> None:
    """A fictional demonstration store must never be indexed by a search engine."""

    for page in [POC_ROOT / "storefront" / "index.html", POC_ROOT / "admin" / "index.html"]:
        html = page.read_text(encoding="utf-8")
        assert 'name="robots"' in html and "noindex" in html, f"{page.name} lacks a noindex directive"


def test_storefront_discloses_fictional_status() -> None:
    html = (POC_ROOT / "storefront" / "index.html").read_text(encoding="utf-8").lower()
    assert "fictional" in html, "the storefront must disclose that the brand is fictional"
    assert "sandbox" in html, "the storefront must disclose that payments are sandbox only"
