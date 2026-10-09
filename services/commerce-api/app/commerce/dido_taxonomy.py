"""The controlled vocabularies a Styling Brief may hold, and where a value came from.

ONE AUTHORITATIVE TAXONOMY, as Style DNA established. The server validates, so the server
owns the words and serves them; the consumer renders what it is given. `OCCASIONS` already
exists in `apps/consumer/src/features/content.ts` as editorial copy with hints, images and
category hints, so it is NOT duplicated blindly -- the slugs are mirrored here and
`test_dido_taxonomy_drift.py` requires them to match. A duplication with a guard is
survivable; without one it is a trap, and this repository has been bitten by that twice.

WHY DRESS CODE IS A PRODUCT TAXONOMY AND NOT A CLAIM ABOUT THE WORLD.

"Black tie" does not mean the same thing in every country, community or decade, and a
platform that encoded one reading as universal would be confidently wrong at somebody's
wedding. These seven levels are an OPERATIONAL vocabulary: enough to tell a relaxed dinner
from a formal one, presented to the customer as a choice they confirm rather than a cultural
rule the system applies. Nothing here is researched, and nothing here is asserted as
etiquette.

That is also why occasion does not silently become a dress code. A wedding can be anything
from a beach in linen to white tie; mapping one onto the other without asking would be the
system inventing a fact about the customer's evening.
"""

from __future__ import annotations

from typing import Final, TypedDict


class Term(TypedDict):
    slug: str
    label: str
    description: str


# ------------------------------------------------------------------ provenance


#: WHERE A CONSTRAINT CAME FROM. Every meaningful field in a Styling Brief carries one.
#:
#: This is the Style DNA provenance idea extended to a conversation, and it is load-bearing
#: for the same reason: the customer is entitled to know which of the things the system
#: believes about them they actually said. Without it, a value typed tonight and a value
#: read from a profile saved in March are indistinguishable on the review screen.
SOURCE_STYLE_DNA: Final = "STYLE_DNA_EXPLICIT"
SOURCE_SESSION: Final = "SESSION_EXPLICIT"
SOURCE_SYSTEM: Final = "SYSTEM_DERIVED"

#: SYSTEM_DERIVED IS DELIBERATELY NARROW.
#:
#: It means exactly one thing: a controlled taxonomy term was matched from the customer's
#: own words by the documented normalization below -- "job interview" becoming the
#: `interview` occasion. It does NOT mean the model inferred, guessed, or concluded
#: anything. A model guess that cannot be traced to a listed synonym does not enter the
#: brief at all; it becomes a question instead.
ALLOWED_SOURCES: Final[frozenset[str]] = frozenset(
    {SOURCE_STYLE_DNA, SOURCE_SESSION, SOURCE_SYSTEM}
)

#: Precedence, most authoritative first. The merge in `dido_brief.py` depends on this
#: order and nothing else, so the rule is readable in one place rather than inferred from
#: the order of if-statements.
#:
#: Session beats profile because a person telling you something now is better evidence than
#: something they told you in March. SYSTEM_DERIVED ranks LAST on purpose: a normalization
#: of the customer's words must never displace a value the customer stated outright.
SOURCE_PRECEDENCE: Final[tuple[str, ...]] = (
    SOURCE_SESSION,
    SOURCE_STYLE_DNA,
    SOURCE_SYSTEM,
)


def outranks(candidate: str, incumbent: str | None) -> bool:
    """True when `candidate` may overwrite a field currently held by `incumbent`."""

    if incumbent is None:
        return True
    return SOURCE_PRECEDENCE.index(candidate) <= SOURCE_PRECEDENCE.index(incumbent)


# ------------------------------------------------------------------ occasions


#: Mirrors `OCCASIONS` in the consumer's content.ts. Guarded by a drift test.
OCCASIONS: Final[tuple[Term, ...]] = (
    {"slug": "interview", "label": "Interview", "description": "Considered, quiet, credible"},
    {"slug": "work", "label": "Work", "description": "Everyday professional"},
    {"slug": "dinner", "label": "Dinner", "description": "Evening, unfussy"},
    {"slug": "date", "label": "Date", "description": "Personal, not performative"},
    {"slug": "wedding", "label": "Wedding", "description": "Formal, with room to sit"},
    {"slug": "travel", "label": "Travel", "description": "Layers that fold flat"},
    {"slug": "weekend", "label": "Weekend", "description": "Off duty"},
    {"slug": "party", "label": "Party", "description": "Late, warm rooms"},
    {"slug": "everyday", "label": "Everyday", "description": "The default that works"},
    {"slug": "formal", "label": "Formal", "description": "When the code is stated"},
)


#: Phrases that map to an occasion, used by the DETERMINISTIC normalizer.
#:
#: This table is why `SYSTEM_DERIVED` can be explained to a customer: every derived
#: occasion traces to a listed phrase in their own message, not to a model's judgement.
#: A message containing none of these yields no occasion and Dido asks instead.
OCCASION_SYNONYMS: Final[dict[str, tuple[str, ...]]] = {
    "interview": ("interview", "job interview"),
    "work": ("work", "office", "the office"),
    "dinner": ("dinner", "restaurant"),
    "date": ("date", "date night"),
    "wedding": ("wedding",),
    "travel": ("travel", "flight", "flying", "trip"),
    "weekend": ("weekend",),
    "party": ("party", "birthday"),
    "everyday": ("everyday", "every day", "day to day"),
    "formal": ("gala", "ceremony"),
}


# ------------------------------------------------------------------ dress code


#: An operational formality ladder. See the module docstring: a product vocabulary, not
#: etiquette, and the customer confirms it rather than having it applied to them.
DRESS_CODES: Final[tuple[Term, ...]] = (
    {"slug": "casual", "label": "Casual", "description": "No expectations to meet"},
    {"slug": "smart-casual", "label": "Smart casual", "description": "Considered, not formal"},
    {"slug": "business-casual", "label": "Business casual", "description": "Workplace, no tie"},
    {"slug": "business-formal", "label": "Business formal", "description": "Suit expected"},
    {"slug": "cocktail", "label": "Cocktail", "description": "Evening, short"},
    {"slug": "formal", "label": "Formal", "description": "The invitation says so"},
    {"slug": "black-tie", "label": "Black tie", "description": "Stated on the invitation"},
)

DRESS_CODE_SYNONYMS: Final[dict[str, tuple[str, ...]]] = {
    "casual": ("casual", "relaxed", "informal", "laid back"),
    "smart-casual": ("smart casual", "smart but not", "smart, not", "dressy casual"),
    "business-casual": ("business casual", "office casual"),
    "business-formal": ("business formal", "suit", "corporate"),
    "cocktail": ("cocktail",),
    "formal": ("formal",),
    "black-tie": ("black tie", "black-tie", "tuxedo", "tux"),
}

#: ORDER MATTERS when scanning free text: the longest phrase must win.
#:
#: "business casual" contains "casual", and "black tie" contains "tie" and sits near
#: "formal" in many sentences. Scanning shortest-first would read "business casual" as
#: `casual` -- a real downgrade of what the customer said, and exactly the kind of quiet
#: error that is hard to notice on a review screen. Sorting by descending phrase length
#: makes the most specific match win.
def dress_code_phrases() -> list[tuple[str, str]]:
    pairs = [
        (phrase, slug)
        for slug, phrases in DRESS_CODE_SYNONYMS.items()
        for phrase in phrases
    ]
    return sorted(pairs, key=lambda p: -len(p[0]))


def occasion_phrases() -> list[tuple[str, str]]:
    pairs = [
        (phrase, slug)
        for slug, phrases in OCCASION_SYNONYMS.items()
        for phrase in phrases
    ]
    return sorted(pairs, key=lambda p: -len(p[0]))


# ------------------------------------------------------------------ session context


#: Explicit situational context the customer may supply. NOT fetched from anywhere.
#:
#: There is no weather provider in this phase and none is pretended. "It's cold" is
#: recorded as something the customer said, and the brief labels it that way, because
#: claiming a forecast was checked when it was not is the kind of small lie that makes
#: everything else on the screen suspect.
SETTINGS: Final[tuple[Term, ...]] = (
    {"slug": "indoors", "label": "Indoors", "description": ""},
    {"slug": "outdoors", "label": "Outdoors", "description": ""},
    {"slug": "mixed", "label": "Both", "description": "Some of each"},
)

TEMPERATURE_CONTEXTS: Final[tuple[Term, ...]] = (
    {"slug": "cold", "label": "Cold", "description": "As the customer described it"},
    {"slug": "mild", "label": "Mild", "description": "As the customer described it"},
    {"slug": "warm", "label": "Warm", "description": "As the customer described it"},
)

SETTING_SYNONYMS: Final[dict[str, tuple[str, ...]]] = {
    "outdoors": ("outdoors", "outdoor", "outside", "garden", "beach"),
    "indoors": ("indoors", "indoor", "inside"),
}

TEMPERATURE_SYNONYMS: Final[dict[str, tuple[str, ...]]] = {
    "cold": ("cold", "freezing", "chilly"),
    "warm": ("warm", "hot"),
    "mild": ("mild",),
}


# ------------------------------------------------------------------ limits


#: One message cannot be an essay. A bound here is a cost control and a prompt-injection
#: surface reduction at once: a shorter message is a smaller place to hide instructions.
MAX_MESSAGE_LENGTH: Final = 1000

#: How many prior turns are sent to the interpreter. The structured brief carries the
#: accumulated state, so the transcript does not have to -- resending a lifetime of
#: conversation would grow cost without adding information the brief does not already hold.
MAX_CONTEXT_TURNS: Final = 8

#: A styling conversation that has not converged in this many turns is not going to.
#:
#: Comfortably ABOVE the per-minute message budget on purpose. At 40 this cap and the
#: 20-messages-per-minute limiter landed at almost the same point, so a burst hit whichever
#: happened to come first and the customer got "this conversation has gone on long enough"
#: when the real answer was "slow down". Two limits that fire at the same boundary are one
#: limit with two confusing messages.
MAX_TURNS_PER_SESSION: Final = 120

#: Model call budget. Bounded because an unbounded one is a bill.
INTERPRETER_TIMEOUT_SECONDS: Final = 12.0
INTERPRETER_MAX_RETRIES: Final = 1

#: Session budgets are money and follow the money contract: integer minor units only.
MAX_BUDGET_MINOR_UNITS: Final = 100_000_000
SUPPORTED_CURRENCIES: Final[frozenset[str]] = frozenset({"EUR"})

#: Free-text constraints the normalizer could not place. Kept verbatim and SHOWN to the
#: customer as unplaced, rather than quietly dropped -- a constraint the system did not
#: understand is a fact about the system, and hiding it would let the brief look more
#: complete than it is.
MAX_FREE_TEXT_CONSTRAINTS: Final = 10
MAX_FREE_TEXT_LENGTH: Final = 200


# ------------------------------------------------------------------ lookups


def _slugs(terms: tuple[Term, ...]) -> frozenset[str]:
    return frozenset(t["slug"] for t in terms)


OCCASION_SLUGS: Final = _slugs(OCCASIONS)
DRESS_CODE_SLUGS: Final = _slugs(DRESS_CODES)
SETTING_SLUGS: Final = _slugs(SETTINGS)
TEMPERATURE_SLUGS: Final = _slugs(TEMPERATURE_CONTEXTS)


#: Session statuses. `abandoned` exists so a customer can walk away without the row
#: pretending to be live, and so "resume current session" has an unambiguous answer.
STATUS_ACTIVE: Final = "ACTIVE"
STATUS_BRIEF_READY: Final = "BRIEF_READY"
STATUS_ABANDONED: Final = "ABANDONED"
STATUSES: Final[tuple[str, ...]] = (STATUS_ACTIVE, STATUS_BRIEF_READY, STATUS_ABANDONED)


def options_payload() -> dict[str, object]:
    """Everything the Dido client needs to render choices, in one response.

    Public, like the Style DNA options endpoint and for the same reason: these are the
    platform's words rather than anybody's data. It is also what lets the deterministic
    fallback offer real choices when the interpreter is unavailable -- the client already
    has the vocabulary and does not need the model to produce it.
    """

    return {
        "occasions": [dict(t) for t in OCCASIONS],
        "dress_codes": [dict(t) for t in DRESS_CODES],
        "settings": [dict(t) for t in SETTINGS],
        "temperatures": [dict(t) for t in TEMPERATURE_CONTEXTS],
        "sources": sorted(ALLOWED_SOURCES),
        "currencies": sorted(SUPPORTED_CURRENCIES),
        "limits": {
            "message_length": MAX_MESSAGE_LENGTH,
            "turns_per_session": MAX_TURNS_PER_SESSION,
            "free_text_constraints": MAX_FREE_TEXT_CONSTRAINTS,
        },
    }
