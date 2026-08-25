"""Static guards on the browser clients.

These are cheap source-level assertions, not a substitute for a browser security test.
They exist because the specific defect they guard against (SB-RISK-003, stored XSS via
`innerHTML`) was previously shipped, and a regression would silently reintroduce it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

def _repo_root() -> Path:
    """Find the repository root by looking for apps/, not by counting directories.

    A fixed parents[N] breaks the moment the service moves or the tests run from a
    mount where the tree above is absent — which is exactly what happened when this
    suite was first run inside a container against PostgreSQL.
    """

    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "apps").is_dir():
            return candidate
    raise RuntimeError(f"no apps/ directory above {here}; run from a full checkout")


REPO_ROOT = _repo_root()
# Every script the browser clients load, not just the biggest one. Phase 2 split the
# storefront into a design system, a data layer and the routes; scanning only `app.js`
# afterwards would have left the two new files — one of which builds every element on the
# platform — outside the guard that exists because this exact sink shipped once already.
CLIENT_SCRIPTS = [
    REPO_ROOT / "apps" / "web" / "app.js",
    REPO_ROOT / "apps" / "web" / "ds.js",
    REPO_ROOT / "apps" / "web" / "data.js",
    REPO_ROOT / "apps" / "web" / "media-url.js",
    REPO_ROOT / "apps" / "admin" / "admin.js",
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

    for page in [REPO_ROOT / "apps" / "web" / "index.html", REPO_ROOT / "apps" / "admin" / "index.html"]:
        html = page.read_text(encoding="utf-8")
        assert 'name="robots"' in html and "noindex" in html, f"{page.name} lacks a noindex directive"


def test_storefront_discloses_fictional_status() -> None:
    html = (REPO_ROOT / "apps" / "web" / "index.html").read_text(encoding="utf-8").lower()
    assert "fictional" in html, "the storefront must disclose that the brand is fictional"
    assert "sandbox" in html, "the storefront must disclose that payments are sandbox only"

# ---------------------------------------------------------------- the React client
#
# ADR-0004 replaced the consumer web client with a React application. The guard has to
# follow it: SB-RISK-003 was closed by removing every markup sink from the browser
# clients, and a new client with no scan is a client where the sink can come back
# unnoticed. React escapes interpolated values by default, which is a real improvement
# over building DOM by hand — but `dangerouslySetInnerHTML` opts straight back out, and it
# is the sink this must catch.


def _consumer_sources() -> list[Path]:
    """Every TypeScript and TSX source in the consumer client.

    Enumerated rather than listed, unlike the classic clients above: the file set changes
    as features are added, and a hand-maintained list is a guard that silently stops
    covering the file somebody added last week.
    """

    root = REPO_ROOT / "apps" / "consumer" / "src"
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*") if p.suffix in {".ts", ".tsx"})


CONSUMER_SOURCES = _consumer_sources()

# `dangerouslySetInnerHTML` is React's explicit opt-out of escaping. The others are the
# same DOM sinks the classic clients are scanned for, which are still reachable from React.
REACT_FORBIDDEN_SINKS = FORBIDDEN_SINKS + ["dangerouslySetInnerHTML"]


def test_the_consumer_client_has_sources_to_scan() -> None:
    """A scan over an empty list passes for the wrong reason.

    If the client moves or is renamed, the parametrised tests below silently collapse to
    zero cases and report green. This is the assertion that notices.
    """

    assert CONSUMER_SOURCES, "no consumer sources found; the scan below would be vacuous"


@pytest.mark.parametrize("source", CONSUMER_SOURCES, ids=lambda p: p.name)
def test_the_consumer_client_has_no_markup_sink(source: Path) -> None:
    """No source in the React client interprets a string as markup or code."""

    offenders = [
        f"{source.name}:{number}: {code.strip()}"
        for number, code in strip_comments(source.read_text(encoding="utf-8"))
        for sink in REACT_FORBIDDEN_SINKS
        if sink in code
    ]
    assert not offenders, "markup sink in the consumer client:" + chr(10) + chr(10).join(offenders)


@pytest.mark.parametrize("source", CONSUMER_SOURCES, ids=lambda p: p.name)
def test_the_consumer_client_does_not_build_javascript_urls(source: Path) -> None:
    """No source constructs a `javascript:` or inline-HTML data URL.

    React does not escape these: an href is written verbatim, so a value that reaches one
    executes on click. The classic clients are guarded against the DOM sinks; this is the
    equivalent hole in a framework that closed the others for us.
    """

    offenders = [
        f"{source.name}:{number}: {code.strip()}"
        for number, code in strip_comments(source.read_text(encoding="utf-8"))
        if "javascript:" in code.lower() or "data:text/html" in code.lower()
    ]
    assert not offenders, "unsafe URL scheme in the consumer client:" + chr(10) + chr(10).join(offenders)
