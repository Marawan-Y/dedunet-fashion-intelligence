"""The guard that makes one duplicated vocabulary survivable.

`STYLE_CATEGORIES` lives in `apps/consumer/src/features/content.ts` as editorial copy that
predates Style DNA and has already been shown to people. `style_taxonomy.STYLE_DIRECTIONS`
is the server's authoritative copy, because the server validates writes and the client must
not be able to offer a choice the server rejects.

That is two copies of one list, which is the condition this repository has already been
bitten by. The difference between a duplication that is survivable and one that is a trap
is whether something fails when they disagree. This is that something.

Every other Style DNA vocabulary exists ONLY on the server and is fetched by the client
from `/style-dna/options`, so no equivalent guard is needed for them -- and that is the
pattern to follow when adding one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.commerce import style_taxonomy as tax

CONTENT_TS = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "consumer"
    / "src"
    / "features"
    / "content.ts"
)

_ENTRY = re.compile(
    r"\{\s*slug:\s*\"(?P<slug>[a-z0-9-]+)\"\s*,\s*"
    r"name:\s*\"(?P<name>[^\"]+)\"\s*,\s*"
    r"description:\s*\"(?P<description>[^\"]*)\"\s*,?\s*\}"
)


def _parse_style_categories() -> list[dict[str, str]]:
    source = CONTENT_TS.read_text(encoding="utf-8")
    start = source.index("export const STYLE_CATEGORIES")
    end = source.index("];", start)
    return [m.groupdict() for m in _ENTRY.finditer(source[start:end])]


@pytest.mark.skipif(not CONTENT_TS.exists(), reason="consumer sources not present")
def test_style_directions_match_the_consumer_content_file():
    """Slugs, labels, descriptions AND ORDER must agree.

    Order matters because both lists are rendered to people and a reordering between
    surfaces is a visible inconsistency, not a cosmetic one.
    """

    parsed = _parse_style_categories()
    assert parsed, "could not parse STYLE_CATEGORIES out of content.ts"

    client_side = [(e["slug"], e["name"], e["description"]) for e in parsed]
    server_side = [(t["slug"], t["label"], t["description"]) for t in tax.STYLE_DIRECTIONS]

    assert client_side == server_side, (
        "STYLE_CATEGORIES in apps/consumer/src/features/content.ts has drifted from "
        "style_taxonomy.STYLE_DIRECTIONS. The server is authoritative for what a profile "
        "may store; update both, or move the client to the options endpoint."
    )


def test_every_vocabulary_has_unique_slugs():
    for name in (
        "STYLE_DIRECTIONS",
        "COLOURS",
        "COLOUR_APPROACHES",
        "GARMENT_CATEGORIES",
        "FITS",
        "SIZE_SYSTEMS",
        "MATERIALS",
        "CARE_EFFORTS",
        "SEASONALITIES",
    ):
        terms = getattr(tax, name)
        slugs = [t["slug"] for t in terms]
        assert len(slugs) == len(set(slugs)), f"{name} has duplicate slugs"
        assert all(t["label"] for t in terms), f"{name} has an entry with no label"


def test_limits_follow_the_vocabularies_rather_than_being_guessed():
    """A cap that tracks its vocabulary tightens automatically when the vocabulary shrinks."""

    assert tax.MAX_STYLE_DIRECTIONS == len(tax.STYLE_DIRECTIONS)
    assert tax.MAX_COLOURS == len(tax.COLOURS)
    assert tax.MAX_MATERIALS == len(tax.MATERIALS)
    assert tax.MAX_FITS == len(tax.GARMENT_CATEGORIES)
    assert tax.MAX_SIZES == len(tax.GARMENT_CATEGORIES) * len(tax.SIZE_SYSTEMS)


def test_no_vocabulary_term_implies_a_sensitive_characteristic():
    """Fashion preferences stay fashion preferences.

    A deliberately blunt check: none of these words may appear in a Style DNA vocabulary,
    because a taxonomy that can record them is a taxonomy that will. "Modest" is a cut of
    clothing and is listed as a style direction; it is not in this list, and that
    distinction is the point -- the term describes a garment line, not a believer.
    """

    forbidden = {
        "religion", "religious", "muslim", "christian", "jewish", "hindu", "faith",
        "ethnicity", "race", "gender", "sexuality", "orientation", "pregnant",
        "pregnancy", "disability", "disabled", "medical", "health", "political",
        "income", "salary", "wealth", "affluent", "poor", "body-shape", "bodyshape",
        "bmi", "weight",
    }
    for name in (
        "STYLE_DIRECTIONS", "COLOURS", "COLOUR_APPROACHES", "GARMENT_CATEGORIES",
        "FITS", "SIZE_SYSTEMS", "MATERIALS", "CARE_EFFORTS", "SEASONALITIES",
    ):
        for term in getattr(tax, name):
            words = set(re.split(r"[\s/-]+", f"{term['slug']} {term['label']} {term['description']}".lower()))
            leaked = words & forbidden
            assert not leaked, f"{name}/{term['slug']} references {leaked}"
