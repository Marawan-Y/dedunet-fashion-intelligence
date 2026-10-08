"""The controlled vocabularies a Style DNA profile may reference. ONE source of truth.

WHY THIS FILE IS AUTHORITATIVE AND THE CLIENT IS NOT.

A taxonomy that exists twice is a taxonomy that disagrees. The repository has already paid
for this lesson once: the preview-catalogue rule was written out four times and the fourth
surface to need it would have carried a fifth copy. So the server owns these lists, serves
them from `GET /style-dna/options`, and the consumer renders whatever it is given rather
than shipping its own copy of the words.

The one vocabulary that legitimately pre-exists on the client is STYLE_DIRECTIONS, which is
`STYLE_CATEGORIES` in `apps/consumer/src/features/content.ts` -- editorial copy written
before this phase, already shown to people, and not this phase's to rewrite. Rather than
duplicate it silently, `tests/test_style_taxonomy_drift.py` parses that file and requires the
slugs to match these exactly. The drift guard is the thing that makes the duplication
survivable; without it this module would be the fifth copy.

WHAT A VOCABULARY ENTRY IS, AND IS NOT.

Each entry is a slug, a human label and a short description. The slug is what the database
stores and the API accepts; the label is what a person reads. Nothing here carries a weight,
a score or a vector, because Style DNA in this phase holds what a customer SAID, and a
customer does not say "0.82".

A value absent from these lists is rejected at write time. That is not defensive
programming for its own sake -- an unvalidated preference string is a free-text field with
extra steps, and free text in a personal profile is how a style preference quietly becomes a
biography.
"""

from __future__ import annotations

from typing import Final, TypedDict


class Term(TypedDict):
    slug: str
    label: str
    description: str


# ----------------------------------------------------------------- provenance


#: The ONLY provenance this phase may write. See `style_dna.py` for the column and
#: `style_dna_service.py` for the guard that enforces it.
#:
#: Stored as a string rather than a database enum on purpose. A later phase that introduces
#: inferred signals needs to add values, and a VARCHAR plus an application-level allow-list
#: takes a code change where a PostgreSQL ENUM takes a migration on every table that uses it.
#: The point of the column existing now, with one legal value, is that the distinction
#: between "you told us" and "we guessed" is representable from the start -- so a future
#: inference phase cannot quietly reuse rows that were never explicit.
SOURCE_USER_EXPLICIT: Final = "USER_EXPLICIT"

#: Everything this phase will accept. Exactly one member, deliberately.
ALLOWED_SOURCES: Final[frozenset[str]] = frozenset({SOURCE_USER_EXPLICIT})


# ----------------------------------------------------------------- stances


STANCE_PREFERRED: Final = "PREFERRED"
STANCE_AVOIDED: Final = "AVOIDED"

#: A customer may say "I like this" or "I avoid this". There is no third value, and
#: ABSENCE IS NOT A THIRD VALUE EITHER -- an unset preference is a missing row, not a
#: "neutral" one. Storing neutrality would mean inventing an opinion the customer never
#: expressed, which is the whole failure mode this phase exists to avoid.
STANCES: Final[tuple[str, str]] = (STANCE_PREFERRED, STANCE_AVOIDED)


# ----------------------------------------------------------------- vocabularies


#: Mirrors `STYLE_CATEGORIES` in the consumer's content.ts. Guarded by a drift test.
STYLE_DIRECTIONS: Final[tuple[Term, ...]] = (
    {"slug": "minimal", "label": "Minimal", "description": "Little detail, exact proportion"},
    {"slug": "classic", "label": "Classic", "description": "Shapes that predate the season"},
    {"slug": "smart-casual", "label": "Smart Casual", "description": "Structured, not formal"},
    {"slug": "streetwear", "label": "Streetwear", "description": "Volume and ease"},
    {"slug": "luxury", "label": "Luxury", "description": "Material first"},
    {"slug": "modest", "label": "Modest", "description": "Full coverage, considered line"},
    {"slug": "contemporary", "label": "Contemporary", "description": "Current without being loud"},
    {"slug": "avant-garde", "label": "Avant-Garde", "description": "Proportion as the argument"},
)


#: A bounded, ordinary colour vocabulary. Deliberately NOT a colour-science model: no hex
#: values, no LAB coordinates, no harmony rules. Those would imply the platform can reason
#: about colour, and it cannot. These are the words people use for clothes.
COLOURS: Final[tuple[Term, ...]] = (
    {"slug": "black", "label": "Black", "description": ""},
    {"slug": "white", "label": "White", "description": ""},
    {"slug": "grey", "label": "Grey", "description": ""},
    {"slug": "navy", "label": "Navy", "description": ""},
    {"slug": "blue", "label": "Blue", "description": ""},
    {"slug": "beige", "label": "Beige", "description": ""},
    {"slug": "brown", "label": "Brown", "description": ""},
    {"slug": "cream", "label": "Cream", "description": ""},
    {"slug": "green", "label": "Green", "description": ""},
    {"slug": "olive", "label": "Olive", "description": ""},
    {"slug": "red", "label": "Red", "description": ""},
    {"slug": "burgundy", "label": "Burgundy", "description": ""},
    {"slug": "pink", "label": "Pink", "description": ""},
    {"slug": "purple", "label": "Purple", "description": ""},
    {"slug": "yellow", "label": "Yellow", "description": ""},
    {"slug": "orange", "label": "Orange", "description": ""},
)


#: An EXPLICIT answer to "how do you want colour to work", not something derived from the
#: colours above. A customer who prefers black, white and grey has not thereby told us they
#: want a neutral palette; they have told us three colours. This is the separate question.
COLOUR_APPROACHES: Final[tuple[Term, ...]] = (
    {"slug": "neutrals-only", "label": "Neutrals only", "description": "Keep colour out of it"},
    {"slug": "mostly-neutral", "label": "Mostly neutral", "description": "Neutral base, occasional colour"},
    {"slug": "high-contrast", "label": "High contrast", "description": "Strong differences between pieces"},
    {"slug": "tonal", "label": "Tonal", "description": "One family, varied depth"},
    {"slug": "colour-led", "label": "Colour-led", "description": "Colour is the decision"},
)


#: Garment groupings used for BOTH fit preference and stated size. Coarse on purpose:
#: a customer can answer "tops" reliably and "mid-weight knitwear" only guessingly.
GARMENT_CATEGORIES: Final[tuple[Term, ...]] = (
    {"slug": "tops", "label": "Tops", "description": "T-shirts, shirts, knitwear"},
    {"slug": "bottoms", "label": "Bottoms", "description": "Trousers, shorts, skirts"},
    {"slug": "outerwear", "label": "Outerwear", "description": "Jackets, coats, overshirts"},
    {"slug": "footwear", "label": "Footwear", "description": ""},
)


FITS: Final[tuple[Term, ...]] = (
    {"slug": "slim", "label": "Slim", "description": "Close to the body"},
    {"slug": "regular", "label": "Regular", "description": "The brand's standard cut"},
    {"slug": "relaxed", "label": "Relaxed", "description": "Room without volume"},
    {"slug": "oversized", "label": "Oversized", "description": "Volume as the point"},
)


#: Size SYSTEMS are listed separately from size LABELS and never converted between.
#:
#: There is no cross-brand size conversion in this phase and no table that pretends EU 50
#: equals UK 40 equals M. Those equivalences are approximately true across brands and
#: exactly true within none, and a profile that silently converts them would be confidently
#: wrong in the one place a customer would never think to check. ALPHA is its own system for
#: the same reason: "M" is not a number in disguise.
SIZE_SYSTEMS: Final[tuple[Term, ...]] = (
    {"slug": "ALPHA", "label": "S / M / L", "description": "Letter sizing"},
    {"slug": "EU", "label": "EU", "description": ""},
    {"slug": "UK", "label": "UK", "description": ""},
    {"slug": "US", "label": "US", "description": ""},
    {"slug": "IT", "label": "IT", "description": ""},
    {"slug": "FR", "label": "FR", "description": ""},
)


#: Fibres and materials, as a customer would name them. A preference recorded here says
#: nothing about any product: see the note in `style_dna.py` about claim truthfulness.
MATERIALS: Final[tuple[Term, ...]] = (
    {"slug": "cotton", "label": "Cotton", "description": ""},
    {"slug": "linen", "label": "Linen", "description": ""},
    {"slug": "wool", "label": "Wool", "description": ""},
    {"slug": "cashmere", "label": "Cashmere", "description": ""},
    {"slug": "silk", "label": "Silk", "description": ""},
    {"slug": "leather", "label": "Leather", "description": ""},
    {"slug": "denim", "label": "Denim", "description": ""},
    {"slug": "viscose", "label": "Viscose", "description": ""},
    {"slug": "polyester", "label": "Polyester", "description": ""},
    {"slug": "nylon", "label": "Nylon", "description": ""},
    {"slug": "elastane", "label": "Elastane", "description": ""},
)


CARE_EFFORTS: Final[tuple[Term, ...]] = (
    {"slug": "machine-only", "label": "Machine wash only", "description": "Nothing that needs special handling"},
    {"slug": "some-handwash", "label": "Some hand washing", "description": "Occasional care is fine"},
    {"slug": "any-care", "label": "Any care", "description": "Including dry clean"},
)


SEASONALITIES: Final[tuple[Term, ...]] = (
    {"slug": "warm-climate", "label": "Mostly warm", "description": ""},
    {"slug": "cold-climate", "label": "Mostly cold", "description": ""},
    {"slug": "four-seasons", "label": "Four distinct seasons", "description": ""},
)


# ----------------------------------------------------------------- limits


#: Caps on how many preferences one profile may hold per vocabulary.
#:
#: Not an arbitrary number: each cap is the size of its own vocabulary, so a customer can
#: express an opinion about everything and still cannot post an unbounded array. The point
#: is that the bound follows from the taxonomy rather than from a guess, and tightens
#: automatically if a vocabulary shrinks.
MAX_STYLE_DIRECTIONS: Final = len(STYLE_DIRECTIONS)
MAX_COLOURS: Final = len(COLOURS)
MAX_MATERIALS: Final = len(MATERIALS)
MAX_FITS: Final = len(GARMENT_CATEGORIES)
#: Sizes are per (category, system), so the ceiling is the product.
MAX_SIZES: Final = len(GARMENT_CATEGORIES) * len(SIZE_SYSTEMS)
#: Brands are not a fixed vocabulary, so this one IS a judgement: enough to express real
#: taste, far short of enumerating a catalogue into a profile.
MAX_BRANDS: Final = 50

#: A stated size label is a short token like "M", "50" or "10.5". Anything longer is not a
#: size.
MAX_SIZE_LABEL_LENGTH: Final = 12

#: Fit notes are the one free-text field in Style DNA, and they are bounded hard.
#:
#: 280 characters holds "long in the body, short in the arm" and does not hold a biography.
#: An unbounded note in a personal profile invites exactly the sensitive disclosure this
#: phase is required to avoid storing -- health conditions, body anxieties, religion -- and
#: no amount of "please do not" in placeholder text prevents it. A tight bound at least
#: keeps the field obviously a note about clothes.
MAX_FIT_NOTES_LENGTH: Final = 280

#: Budgets are integer minor units. A ceiling exists so a typo cannot store a number that
#: renders as nonsense; EUR 1,000,000.00 is far past any styling budget.
MAX_BUDGET_MINOR_UNITS: Final = 100_000_000

#: Currencies this phase accepts. One, matching the store. Extending it means deciding what
#: a budget in another currency MEANS before storing one.
SUPPORTED_BUDGET_CURRENCIES: Final[frozenset[str]] = frozenset({"EUR"})


# ----------------------------------------------------------------- lookups


def _slugs(terms: tuple[Term, ...]) -> frozenset[str]:
    return frozenset(t["slug"] for t in terms)


STYLE_DIRECTION_SLUGS: Final = _slugs(STYLE_DIRECTIONS)
COLOUR_SLUGS: Final = _slugs(COLOURS)
COLOUR_APPROACH_SLUGS: Final = _slugs(COLOUR_APPROACHES)
GARMENT_CATEGORY_SLUGS: Final = _slugs(GARMENT_CATEGORIES)
FIT_SLUGS: Final = _slugs(FITS)
SIZE_SYSTEM_SLUGS: Final = _slugs(SIZE_SYSTEMS)
MATERIAL_SLUGS: Final = _slugs(MATERIALS)
CARE_EFFORT_SLUGS: Final = _slugs(CARE_EFFORTS)
SEASONALITY_SLUGS: Final = _slugs(SEASONALITIES)


def options_payload() -> dict[str, object]:
    """Everything a client needs to render the editor, in one response.

    Served by `GET /style-dna/options`. The consumer holds no copy of these words, which is
    the point: one place to correct a label, and no possibility of the client offering a
    choice the server will reject.
    """

    return {
        "stances": list(STANCES),
        "style_directions": [dict(t) for t in STYLE_DIRECTIONS],
        "colours": [dict(t) for t in COLOURS],
        "colour_approaches": [dict(t) for t in COLOUR_APPROACHES],
        "garment_categories": [dict(t) for t in GARMENT_CATEGORIES],
        "fits": [dict(t) for t in FITS],
        "size_systems": [dict(t) for t in SIZE_SYSTEMS],
        "materials": [dict(t) for t in MATERIALS],
        "care_efforts": [dict(t) for t in CARE_EFFORTS],
        "seasonalities": [dict(t) for t in SEASONALITIES],
        "limits": {
            "style_directions": MAX_STYLE_DIRECTIONS,
            "colours": MAX_COLOURS,
            "materials": MAX_MATERIALS,
            "fits": MAX_FITS,
            "sizes": MAX_SIZES,
            "brands": MAX_BRANDS,
            "size_label_length": MAX_SIZE_LABEL_LENGTH,
            "fit_notes_length": MAX_FIT_NOTES_LENGTH,
            "budget_minor_units": MAX_BUDGET_MINOR_UNITS,
        },
        "budget_currencies": sorted(SUPPORTED_BUDGET_CURRENCIES),
        # Stated so a client cannot invent a second provenance and a reader of the payload
        # can see what the platform is currently capable of recording.
        "sources": sorted(ALLOWED_SOURCES),
    }
