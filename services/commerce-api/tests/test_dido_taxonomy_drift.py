"""The guard that keeps the one duplicated Dido vocabulary survivable.

`OCCASIONS` lives in `apps/consumer/src/features/content.ts` as editorial copy with hints,
images and category hints, and it predates this phase. `dido_taxonomy.OCCASIONS` is the
server's authoritative copy, because the server validates writes and must not accept an
occasion the client never offers — or reject one it does.

That is two copies of one list, which this repository has been bitten by before. The
difference between a survivable duplication and a trap is whether anything fails when they
disagree. This is that something, and it is the same pattern Style DNA established.

Every other Dido vocabulary — dress codes, settings, temperatures — exists ONLY on the
server and is fetched from `/dido/options`, so no equivalent guard is needed. That is the
pattern to follow when adding one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.commerce import dido_taxonomy as tax

CONTENT_TS = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "consumer"
    / "src"
    / "features"
    / "content.ts"
)

_ENTRY = re.compile(
    r"\{\s*slug:\s*\"(?P<slug>[a-z0-9-]+)\"\s*,\s*name:\s*\"(?P<name>[^\"]+)\"\s*,\s*"
    r"hint:\s*\"(?P<hint>[^\"]*)\""
)


def _parse_occasions() -> list[dict[str, str]]:
    source = CONTENT_TS.read_text(encoding="utf-8")
    start = source.index("export const OCCASIONS")
    end = source.index("];", start)
    return [m.groupdict() for m in _ENTRY.finditer(source[start:end])]


@pytest.mark.skipif(not CONTENT_TS.exists(), reason="consumer sources not present")
def test_occasions_match_the_consumer_content_file():
    """Slugs, labels, hints AND ORDER must agree.

    Order matters because both lists are shown to people, and a reordering between
    surfaces is a visible inconsistency rather than a cosmetic one.
    """

    parsed = _parse_occasions()
    assert parsed, "could not parse OCCASIONS out of content.ts"

    client_side = [(e["slug"], e["name"], e["hint"]) for e in parsed]
    server_side = [(t["slug"], t["label"], t["description"]) for t in tax.OCCASIONS]

    assert client_side == server_side, (
        "OCCASIONS in apps/consumer/src/features/content.ts has drifted from "
        "dido_taxonomy.OCCASIONS. The server is authoritative for what a brief may hold; "
        "update both, or move the client to the /dido/options endpoint."
    )


def test_every_synonym_maps_to_a_real_term():
    """A synonym pointing at a slug that does not exist would silently never match."""

    for slug in tax.OCCASION_SYNONYMS:
        assert slug in tax.OCCASION_SLUGS, f"occasion synonym for unknown slug {slug!r}"
    for slug in tax.DRESS_CODE_SYNONYMS:
        assert slug in tax.DRESS_CODE_SLUGS, f"dress code synonym for unknown slug {slug!r}"
    for slug in tax.SETTING_SYNONYMS:
        assert slug in tax.SETTING_SLUGS
    for slug in tax.TEMPERATURE_SYNONYMS:
        assert slug in tax.TEMPERATURE_SLUGS


def test_longer_phrases_are_scanned_first():
    """"business casual" must not be read as "casual".

    The scan order is the whole defence here: shortest-first would quietly downgrade what
    the customer said, and a downgraded dress code is hard to spot on a review screen.
    """

    phrases = [p for p, _ in tax.dress_code_phrases()]
    assert phrases == sorted(phrases, key=len, reverse=True)
    assert phrases.index("business casual") < phrases.index("casual")
    assert phrases.index("black tie") < phrases.index("formal")


def test_precedence_is_a_total_order_over_the_allowed_sources():
    assert set(tax.SOURCE_PRECEDENCE) == tax.ALLOWED_SOURCES
    assert len(tax.SOURCE_PRECEDENCE) == len(set(tax.SOURCE_PRECEDENCE))
    # SYSTEM_DERIVED ranks last: a normalization of someone's words must never displace
    # something they stated outright.
    assert tax.SOURCE_PRECEDENCE[-1] == tax.SOURCE_SYSTEM


def test_the_turn_cap_sits_above_the_message_rate_budget():
    """Two limits that fire at the same boundary are one limit with two error messages."""

    from app.commerce import dido_service

    messages_per_window = dido_service._MESSAGE_CAPACITY
    # Each exchange is two turns. The cap must allow a full burst and then some.
    assert tax.MAX_TURNS_PER_SESSION > messages_per_window * 2


def test_no_dido_vocabulary_term_implies_a_sensitive_characteristic():
    """Fashion stays fashion. The Style DNA guard, applied to the conversation taxonomy."""

    forbidden = {
        "religion", "religious", "muslim", "christian", "jewish", "hindu", "faith",
        "ethnicity", "race", "gender", "sexuality", "orientation", "pregnant",
        "pregnancy", "disability", "disabled", "medical", "health", "political",
        "income", "salary", "wealth", "affluent", "poor", "bmi", "weight",
    }
    for name in ("OCCASIONS", "DRESS_CODES", "SETTINGS", "TEMPERATURE_CONTEXTS"):
        for term in getattr(tax, name):
            words = set(
                re.split(r"[\s/,-]+", f"{term['slug']} {term['label']} {term['description']}".lower())
            )
            leaked = words & forbidden
            assert not leaked, f"{name}/{term['slug']} references {leaked}"
