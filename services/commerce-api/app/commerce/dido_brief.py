"""The Styling Brief: validation, precedence, contradictions and what to ask next.

This module is the one that decides things. The interpreter proposes; everything here is
deterministic, testable without a model, and the only path by which a value becomes part
of a brief.

FOUR RULES, IN THE ORDER THEY APPLY.

1. **Validate.** A candidate whose value is not in the taxonomy, or whose money is not an
   integer in range, is DROPPED. Not coerced, not rounded, not nearest-matched. A model
   that returns `occasion: "brunch"` changes nothing.

2. **Precedence.** `SESSION_EXPLICIT > STYLE_DNA_EXPLICIT > SYSTEM_DERIVED`. A thing the
   customer said tonight beats a thing they saved in March, and both beat a normalization
   of their words. This is why "no black tonight" works against a profile that prefers
   black **without touching the profile**.

3. **Contradictions are surfaced, never resolved.** When two constraints cannot both hold,
   Dido says so and asks which matters. Picking one silently would be the system deciding
   something about the customer's evening on their behalf, and they would find out by
   looking at a brief that says the opposite of what they meant.

4. **Ask one useful thing.** The next question is chosen from what is *materially* missing.
   Anything already known — from this conversation or from an applied profile — is not
   asked again, which is the difference between a stylist and a form.

WHAT A BRIEF NEVER CONTAINS: a product, a price the customer did not state, an
availability, a size equivalence across brands, or a ranking. Phase 7 ends at the brief.
"""

from __future__ import annotations

import json
from typing import Any, Final

from . import dido_taxonomy as tax

#: Fields whose value is a single taxonomy slug.
_SINGLE_SLUG_FIELDS: Final[dict[str, frozenset[str]]] = {
    "occasion": tax.OCCASION_SLUGS,
    "dress_code": tax.DRESS_CODE_SLUGS,
    "setting": tax.SETTING_SLUGS,
    "temperature": tax.TEMPERATURE_SLUGS,
}

#: Fields whose value is a list of words. Bounded, lowercased, de-duplicated.
_LIST_FIELDS: Final[tuple[str, ...]] = (
    "colour_preferences",
    "colour_avoidances",
    "material_preferences",
    "material_avoidances",
    "brand_preferences",
    "brand_avoidances",
    "fit_preferences",
    "requested_categories",
)

_MONEY_FIELDS: Final[tuple[str, ...]] = ("budget_total", "budget_per_piece")

_BOOL_FIELDS: Final[tuple[str, ...]] = ("budget_skipped",)

#: Every field a brief may hold. An unknown field name is dropped — a brief with a field
#: nobody designed is a brief nobody can review.
ALLOWED_FIELDS: Final[frozenset[str]] = frozenset(
    set(_SINGLE_SLUG_FIELDS) | set(_LIST_FIELDS) | set(_MONEY_FIELDS) | set(_BOOL_FIELDS)
)

MAX_LIST_ITEMS: Final = 20
MAX_ITEM_LENGTH: Final = 40


def empty_brief() -> dict[str, Any]:
    """A brief with nothing in it. The shape is stable so clients need no null checks."""

    return {
        "fields": {},
        "unplaced": [],
        "contradictions": [],
        "currency": "EUR",
    }


def _entry(value: Any, source: str, evidence: str = "") -> dict[str, Any]:
    """A stored field: its value, where it came from, and the words behind it."""

    return {"value": value, "source": source, "evidence": evidence}


# --------------------------------------------------------------------------- validation


def validate_candidate(field: str, value: Any) -> Any | None:
    """Return the cleaned value, or None if it may not enter a brief.

    Returning None rather than raising, because one bad field in a message should cost
    that field and not the whole turn — the customer said several things and the ones that
    were understood are still worth keeping.
    """

    if field not in ALLOWED_FIELDS:
        return None

    if field in _SINGLE_SLUG_FIELDS:
        if not isinstance(value, str):
            return None
        slug = value.strip().lower()
        return slug if slug in _SINGLE_SLUG_FIELDS[field] else None

    if field in _MONEY_FIELDS:
        # bool excluded explicitly: isinstance(True, int) is True in Python, and True is
        # not a budget. A float is rejected rather than rounded — see the money contract.
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        if value < 0 or value > tax.MAX_BUDGET_MINOR_UNITS:
            return None
        return value

    if field in _BOOL_FIELDS:
        return value if isinstance(value, bool) else None

    if field in _LIST_FIELDS:
        if not isinstance(value, list):
            return None
        cleaned: list[str] = []
        for item in value[:MAX_LIST_ITEMS]:
            if not isinstance(item, str):
                continue
            token = item.strip().lower()[:MAX_ITEM_LENGTH]
            if token and token not in cleaned:
                cleaned.append(token)
        return cleaned or None

    return None


# --------------------------------------------------------------------------- merging


def apply_candidates(
    brief: dict[str, Any],
    candidates,
    *,
    source: str,
) -> dict[str, Any]:
    """Merge validated candidates into a COPY of the brief, under precedence.

    Never mutates its input: the caller keeps the previous brief so a rejected turn leaves
    the session exactly as it was.
    """

    merged = json.loads(json.dumps(brief))
    fields: dict[str, Any] = merged.setdefault("fields", {})

    for candidate in candidates:
        name = getattr(candidate, "field", None)
        if not isinstance(name, str):
            continue
        cleaned = validate_candidate(name, getattr(candidate, "value", None))
        if cleaned is None:
            continue

        # The candidate's own source wins only if it outranks what is already held.
        candidate_source = getattr(candidate, "source", source) or source
        if candidate_source not in tax.ALLOWED_SOURCES:
            continue
        # A candidate carried in on a customer's message IS session-explicit when the
        # caller says so; the interpreter marks everything SYSTEM_DERIVED because it
        # cannot know the difference, and the service promotes it.
        effective = source if source == tax.SOURCE_SESSION else candidate_source

        existing = fields.get(name)
        if existing and not tax.outranks(effective, existing.get("source")):
            continue

        fields[name] = _entry(cleaned, effective, getattr(candidate, "evidence", ""))

    merged["contradictions"] = detect_contradictions(merged)
    return merged


def apply_style_profile(brief: dict[str, Any], profile_payload: dict[str, Any]) -> dict[str, Any]:
    """Seed a brief from an accepted Style DNA profile.

    ONLY called when personalisation is enabled — the caller enforces that, and a test
    asserts the caller. Everything written here is `STYLE_DNA_EXPLICIT`, so a later
    session instruction outranks it automatically and the review screen can separate
    "from your profile" from "from this conversation" without a second mechanism.

    Note what is NOT copied: sizes are carried as context further down, and nothing is
    converted between size systems. The Style DNA lock holds inside Dido.
    """

    merged = json.loads(json.dumps(brief))
    fields: dict[str, Any] = merged.setdefault("fields", {})

    def seed(name: str, value: Any) -> None:
        if value in (None, [], ""):
            return
        existing = fields.get(name)
        if existing and not tax.outranks(tax.SOURCE_STYLE_DNA, existing.get("source")):
            return
        fields[name] = _entry(value, tax.SOURCE_STYLE_DNA, "your Style DNA")

    stance = lambda rows, want: sorted(  # noqa: E731
        r["slug"] for r in rows if r.get("stance") == want
    )

    seed("colour_preferences", stance(profile_payload.get("colours", []), "PREFERRED"))
    seed("colour_avoidances", stance(profile_payload.get("colours", []), "AVOIDED"))
    seed("material_preferences", stance(profile_payload.get("materials", []), "PREFERRED"))
    seed("material_avoidances", stance(profile_payload.get("materials", []), "AVOIDED"))
    seed("brand_preferences", stance(profile_payload.get("brands", []), "PREFERRED"))
    seed("brand_avoidances", stance(profile_payload.get("brands", []), "AVOIDED"))
    seed(
        "fit_preferences",
        sorted(f"{f['garment_category']}: {f['fit']}" for f in profile_payload.get("fits", [])),
    )

    budget = profile_payload.get("budget") or {}
    if isinstance(budget.get("per_piece_minor_units"), int):
        seed("budget_per_piece", budget["per_piece_minor_units"])
    if isinstance(budget.get("per_look_minor_units"), int):
        seed("budget_total", budget["per_look_minor_units"])
    if budget.get("currency"):
        merged["currency"] = budget["currency"]

    #: Stated sizes travel as CONTEXT, verbatim, never as a conversion.
    #: "customer-stated tops size EU 50" is a fact. "therefore L at brand Y" is not, and
    #: this phase has no evidence that could make it one.
    sizes = profile_payload.get("sizes") or []
    if sizes:
        merged["size_context"] = [
            {
                "garment_category": s["garment_category"],
                "size_system": s["size_system"],
                "size_label": s["size_label"],
                "source": tax.SOURCE_STYLE_DNA,
            }
            for s in sizes
        ]

    merged["contradictions"] = detect_contradictions(merged)
    return merged


# --------------------------------------------------------------------------- contradictions


#: Dress codes at which trainers-and-a-t-shirt is not an option. Narrow on purpose: this
#: table exists to catch the obvious impossibility, not to referee taste.
_STRICT_DRESS_CODES: Final[frozenset[str]] = frozenset({"black-tie", "formal", "business-formal"})
_CASUAL_MARKERS: Final[tuple[str, ...]] = ("trainers", "sneakers", "t-shirt", "tshirt", "shorts", "hoodie")


def detect_contradictions(brief: dict[str, Any]) -> list[dict[str, str]]:
    """Find constraints that cannot both hold. Report them; never pick a winner.

    Each entry carries the two sides and a question, so the UI shows the conflict in the
    customer's own terms and lets them choose. Deciding for them is the failure mode: a
    brief that silently dropped "no black" would read as agreement.
    """

    fields = brief.get("fields", {})
    found: list[dict[str, str]] = []

    def value(name: str):
        entry = fields.get(name)
        return entry.get("value") if entry else None

    # ---- the same term both wanted and refused
    for kind, pref_field, avoid_field in (
        ("colour", "colour_preferences", "colour_avoidances"),
        ("material", "material_preferences", "material_avoidances"),
        ("brand", "brand_preferences", "brand_avoidances"),
    ):
        both = sorted(set(value(pref_field) or []) & set(value(avoid_field) or []))
        if both:
            found.append(
                {
                    "kind": f"{kind}_conflict",
                    "detail": f"{', '.join(both)} is listed as both preferred and avoided",
                    "question": f"Should I keep {both[0]} in, or leave it out for this one?",
                }
            )

    # ---- a strict dress code against explicitly casual requests
    dress_code = value("dress_code")
    requested = " ".join(value("requested_categories") or []) + " " + " ".join(
        brief.get("unplaced", [])
    )
    if dress_code in _STRICT_DRESS_CODES:
        hits = [m for m in _CASUAL_MARKERS if m in requested.lower()]
        if hits:
            found.append(
                {
                    "kind": "formality_conflict",
                    "detail": f"{dress_code.replace('-', ' ')} does not usually allow {hits[0]}",
                    "question": f"Which matters more here — the dress code, or the {hits[0]}?",
                }
            )

    # ---- a per-piece budget above the whole-look budget
    per_piece = value("budget_per_piece")
    total = value("budget_total")
    if isinstance(per_piece, int) and isinstance(total, int) and per_piece > total:
        found.append(
            {
                "kind": "budget_conflict",
                "detail": "the per-piece budget is higher than the budget for the whole look",
                "question": "Is that per-piece figure right, or should the total be higher?",
            }
        )

    return found


# --------------------------------------------------------------------------- question policy


#: What to ask, in order, and why. The "why" is stored so "why did you ask that?" is
#: answered from policy metadata rather than by asking a model to justify a decision it
#: did not make.
QUESTION_POLICY: Final[tuple[dict[str, str], ...]] = (
    {
        "key": "occasion",
        "field": "occasion",
        "prompt": "Where are you going?",
        "why": "The occasion decides almost everything else, so it is the one thing worth asking first.",
    },
    {
        "key": "dress_code",
        "field": "dress_code",
        "prompt": "How formal does it need to be?",
        "why": "An occasion can run from relaxed to black tie, and guessing which would put you in the wrong thing.",
    },
    {
        "key": "budget",
        "field": "budget_total",
        "prompt": "What are you working with?",
        "why": "So a later recommendation does not suggest a look outside the amount you want to spend.",
    },
)


def known(brief: dict[str, Any], field: str) -> bool:
    return field in brief.get("fields", {})


def next_question(brief: dict[str, Any]) -> dict[str, str] | None:
    """The one thing worth asking, or None when the brief is ready.

    A CONTRADICTION OUTRANKS EVERY OTHER QUESTION. Collecting more constraints on top of
    two that already conflict produces a longer brief that is still wrong.

    Then the policy, in order, skipping anything already known from any source. This is
    what stops Dido asking for a budget it just read out of the profile, and what makes
    "interview tomorrow, business casual, around €200" produce one question rather than
    three.
    """

    contradictions = brief.get("contradictions") or []
    if contradictions:
        first = contradictions[0]
        return {
            "key": f"conflict:{first['kind']}",
            "prompt": first["question"],
            "why": "Two things you have told me cannot both be true, and choosing for you would be guessing.",
            "kind": "conflict",
            "detail": first["detail"],
        }

    budget_skipped = bool(
        (brief.get("fields", {}).get("budget_skipped") or {}).get("value")
    )

    for policy in QUESTION_POLICY:
        if policy["key"] == "budget":
            # "Rather not say" is an answer. Asking again would be ignoring it.
            if budget_skipped or known(brief, "budget_total") or known(brief, "budget_per_piece"):
                continue
        elif known(brief, policy["field"]):
            continue
        return {**policy, "kind": "question"}

    return None


def is_ready(brief: dict[str, Any]) -> bool:
    """A brief is ready when nothing material is missing and nothing conflicts."""

    return next_question(brief) is None


# --------------------------------------------------------------------------- presentation


def summarize(brief: dict[str, Any]) -> dict[str, Any]:
    """Group the brief by WHERE each constraint came from, for the review screen.

    The grouping is the point. "Avoid wool" means something different depending on whether
    the customer said it tonight or saved it in March, and a flat list would hide that —
    along with the fact that a profile value can be overridden without touching the
    profile.
    """

    fields = brief.get("fields", {})
    groups: dict[str, list[dict[str, Any]]] = {
        tax.SOURCE_SESSION: [],
        tax.SOURCE_STYLE_DNA: [],
        tax.SOURCE_SYSTEM: [],
    }
    for name, entry in sorted(fields.items()):
        groups.setdefault(entry.get("source", tax.SOURCE_SYSTEM), []).append(
            {"field": name, "value": entry.get("value"), "evidence": entry.get("evidence", "")}
        )

    missing = [
        policy["field"]
        for policy in QUESTION_POLICY
        if not known(brief, policy["field"])
        and not (policy["key"] == "budget" and known(brief, "budget_per_piece"))
    ]

    return {
        "from_session": groups[tax.SOURCE_SESSION],
        "from_style_dna": groups[tax.SOURCE_STYLE_DNA],
        "derived_from_your_words": groups[tax.SOURCE_SYSTEM],
        "unplaced": brief.get("unplaced", []),
        "contradictions": brief.get("contradictions", []),
        "size_context": brief.get("size_context", []),
        "currency": brief.get("currency", "EUR"),
        "still_unset": missing,
        "ready": is_ready(brief),
    }
