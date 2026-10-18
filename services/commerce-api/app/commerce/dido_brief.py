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
from .dido_taxonomy import SOURCE_SESSION, SOURCE_STYLE_DNA, SOURCE_SYSTEM

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

    merged = resolve_precedence_conflicts(merged)
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

    merged = resolve_precedence_conflicts(merged)
    merged["contradictions"] = detect_contradictions(merged)
    return merged


# --------------------------------------------------------------------------- contradictions


#: Dress codes at which trainers-and-a-t-shirt is not an option. Narrow on purpose: this
#: table exists to catch the obvious impossibility, not to referee taste.
_STRICT_DRESS_CODES: Final[frozenset[str]] = frozenset({"black-tie", "formal", "business-formal"})
_CASUAL_MARKERS: Final[tuple[str, ...]] = ("trainers", "sneakers", "t-shirt", "tshirt", "shorts", "hoodie")


#: The (preferred, avoided) field pairs where the same term appearing on both sides is a
#: conflict rather than a coincidence.
_OPPOSED_FIELDS: Final[tuple[tuple[str, str, str], ...]] = (
    ("colour", "colour_preferences", "colour_avoidances"),
    ("material", "material_preferences", "material_avoidances"),
    ("brand", "brand_preferences", "brand_avoidances"),
)


def resolve_precedence_conflicts(brief: dict[str, Any]) -> dict[str, Any]:
    """Let the higher-precedence side win, BEFORE anything is called a contradiction.

    THIS IS THE PRECEDENCE RULE DOING ITS JOB, NOT A CONTRADICTION.

    A profile that likes black and a session instruction to avoid black are not two
    constraints in deadlock. They are a general preference and a specific override, and the
    locked order -- SESSION_EXPLICIT > STYLE_DNA_EXPLICIT > SYSTEM_DERIVED -- already says
    which wins. Asking "should I keep black in, or leave it out?" makes the customer repeat
    an instruction they have already given, and implies the system did not understand it.

    So the lower-precedence side loses the overlapping term here, and only a conflict
    between constraints of the SAME effective precedence survives to
    `detect_contradictions`. That is the case where there genuinely is no rule to apply and
    asking is the only honest move.

    The removal is recorded in `overrides` so the brief can SAY what happened. Silently
    dropping a value the customer can see on their profile would be its own small
    deception -- the point is that the profile is untouched and this session differs, which
    only helps if it is stated.

    Never mutates its input.
    """

    merged = json.loads(json.dumps(brief))
    fields: dict[str, Any] = merged.setdefault("fields", {})
    overrides: list[dict[str, str]] = []

    for kind, pref_field, avoid_field in _OPPOSED_FIELDS:
        pref = fields.get(pref_field)
        avoid = fields.get(avoid_field)
        if not pref or not avoid:
            continue

        shared = sorted(set(pref.get("value") or []) & set(avoid.get("value") or []))
        if not shared:
            continue

        pref_rank = tax.SOURCE_PRECEDENCE.index(pref.get("source", tax.SOURCE_SYSTEM))
        avoid_rank = tax.SOURCE_PRECEDENCE.index(avoid.get("source", tax.SOURCE_SYSTEM))
        if pref_rank == avoid_rank:
            # Same precedence: there is no rule that resolves this, so leave it for
            # `detect_contradictions` to surface and for the customer to settle.
            continue

        winner, loser = (
            (avoid_field, pref_field) if avoid_rank < pref_rank else (pref_field, avoid_field)
        )
        loser_entry = fields[loser]
        remaining = [v for v in loser_entry["value"] if v not in shared]

        overrides.append(
            {
                "kind": kind,
                "terms": ", ".join(shared),
                "applied": "avoided" if winner == avoid_field else "preferred",
                "winner_source": fields[winner]["source"],
                "loser_source": loser_entry["source"],
            }
        )

        if remaining:
            loser_entry["value"] = remaining
        else:
            # The whole lower-precedence field was overridden; drop it rather than leave
            # an empty list, which would render as a heading with nothing under it.
            fields.pop(loser, None)

    if overrides:
        merged["overrides"] = overrides
    return merged


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

    # ---- the same term both wanted and refused, AT THE SAME PRECEDENCE
    #
    # Anything resolvable by precedence has already been settled by
    # `resolve_precedence_conflicts`, so what reaches here is a real deadlock: the customer
    # said both things with equal authority, and there is no rule that picks between them.
    for kind, pref_field, avoid_field in _OPPOSED_FIELDS:
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
        # What this session does differently from the stored profile, and why. Shown so
        # the customer can see the profile is intact rather than having to trust it.
        "overrides": brief.get("overrides", []),
        "size_context": brief.get("size_context", []),
        "currency": brief.get("currency", "EUR"),
        "still_unset": missing,
        "ready": is_ready(brief),
    }


# --------------------------------------------------------------------------- questions
#
# THE CUSTOMER MAY ASK, NOT ONLY TELL.
#
# The first version of this phase treated every message as constraint extraction, so
# "what budget do I have for this?" produced "I did not catch a styling constraint in
# that." The data was all there -- the brief holds it and /in-use returns it -- but it was
# reachable only by a button, which is not where somebody mid-conversation looks.
#
# A question is answered from the STORED BRIEF, deterministically, and never from a model.
# That is not a shortcut: the honest answer to "what are you using about me?" is a readout
# of state, and asking a language model to describe state it cannot see is how a system
# comes to confidently misreport itself.

#: Interrogative openers. A message must either end in "?" or start with one of these to
#: count as a question, so "I want to avoid wool" stays a constraint while
#: "what did I tell you to avoid?" does not.
_INTERROGATIVE: Final[tuple[str, ...]] = (
    "what", "which", "who", "when", "where", "why", "how",
    "do you", "are you", "can you", "could you", "did i", "have i",
    "tell me", "remind me", "show me", "list",
)

QUERY_STYLE_DNA: Final = "style_dna_in_use"
QUERY_BUDGET: Final = "budget_in_use"
QUERY_AVOIDANCES: Final = "avoidances_in_use"
QUERY_EVERYTHING: Final = "everything_in_use"

#: Subject matter, checked only once the message is known to be a question. Ordered: the
#: specific subjects are tried before the catch-all, so "what budget do I have?" is
#: answered with the budget rather than with everything.
_QUERY_SUBJECTS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    (QUERY_BUDGET, ("budget", "spend", "spending", "price range", "how much")),
    (QUERY_AVOIDANCES, ("avoid", "not want", "exclude", "stay away", "rule out", "ruled out")),
    (QUERY_STYLE_DNA, ("style dna", "style profile", "my profile", "profile")),
    (QUERY_EVERYTHING, ("know about me", "about me", "using", "have so far", "so far", "my brief")),
)


def detect_query(message: str) -> str | None:
    """Is this a question about the session, and about what? Otherwise None.

    Deliberately conservative. A false positive silently discards a real constraint, which
    is worse than a false negative: a missed question produces an unhelpful reply, while a
    missed constraint produces a brief that is quietly wrong and looks complete.
    """

    text = (message or "").strip().lower()
    if not text:
        return None

    if not (text.endswith("?") or text.startswith(_INTERROGATIVE)):
        return None

    for intent, phrases in _QUERY_SUBJECTS:
        if any(phrase in text for phrase in phrases):
            return intent
    return None


def _money_words(value: object, currency: str) -> str:
    """Integer minor units to words by SLICING DIGITS. Never division."""

    if not isinstance(value, int) or isinstance(value, bool):
        return str(value)
    symbol = "EUR " if currency != "EUR" else "€"
    digits = str(abs(value)).rjust(3, "0")
    return f"{symbol}{digits[:-2]}.{digits[-2:]}"


_READABLE_LABELS: Final[dict[str, str]] = {
    "occasion": "occasion",
    "dress_code": "dress level",
    "setting": "setting",
    "temperature": "weather, as you described it",
    "colour_preferences": "colours you want",
    "colour_avoidances": "colours to avoid",
    "material_preferences": "materials you want",
    "material_avoidances": "materials to avoid",
    "brand_preferences": "brands you follow",
    "brand_avoidances": "brands to exclude",
    "fit_preferences": "fit",
    "requested_categories": "pieces you mentioned",
    "budget_total": "budget for the whole look",
    "budget_per_piece": "budget per piece",
    "budget_skipped": "budget",
}


def _readable(field: str, value: object, currency: str) -> str:
    label = _READABLE_LABELS.get(field, field.replace("_", " "))
    if field in ("budget_total", "budget_per_piece"):
        return f"{label}: {_money_words(value, currency)}"
    if isinstance(value, list):
        return f"{label}: {', '.join(str(v).replace('-', ' ') for v in value)}"
    return f"{label}: {str(value).replace('-', ' ')}"


def answer_query(brief: dict[str, Any], intent: str, *, personalization_used: bool) -> str:
    """Answer a question from stored state, in sentences a person can read.

    THE GROUPING IS THE ANSWER. "Avoid wool" means something different depending on
    whether it came from a profile saved in March or from this conversation, and a flat
    list would hide the one thing the customer is actually asking about.
    """

    fields = brief.get("fields", {})
    currency = brief.get("currency", "EUR")
    unplaced = brief.get("unplaced", [])

    def group(source: str) -> list[tuple[str, Any]]:
        return sorted(
            (name, entry["value"])
            for name, entry in fields.items()
            if entry.get("source") == source
        )

    from_profile = group(SOURCE_STYLE_DNA)
    from_session = group(SOURCE_SESSION) + group(SOURCE_SYSTEM)

    if intent == QUERY_STYLE_DNA:
        if not personalization_used:
            return (
                "I am not using your Style DNA for this session. Either you have not made "
                "one, or personalisation is switched off in My Style. Everything in this "
                "brief came from what you have told me here."
            )
        if not from_profile:
            return (
                "Personalisation is on, but nothing from your Style DNA has gone into this "
                "brief yet."
            )
        profile_line = "; ".join(_readable(f, v, currency) for f, v in from_profile)
        if from_session:
            session_line = "; ".join(_readable(f, v, currency) for f, v in from_session)
            tail = f" From this conversation, separately: {session_line}."
        else:
            tail = " You have not added anything to it in this conversation yet."
        return f"From your Style DNA I am using: {profile_line}.{tail}"

    if intent == QUERY_BUDGET:
        if (fields.get("budget_skipped") or {}).get("value"):
            return "You said you would rather not give a budget, so I am not working to one."
        total = fields.get("budget_total")
        per_piece = fields.get("budget_per_piece")
        if not total and not per_piece:
            return "You have not given me a budget for this session yet."
        parts = []
        for entry, label in ((total, "for the whole look"), (per_piece, "per piece")):
            if entry:
                origin = (
                    "from your Style DNA"
                    if entry.get("source") == SOURCE_STYLE_DNA
                    else "from this conversation"
                )
                parts.append(
                    f"{_money_words(entry['value'], currency)} {label} ({origin})"
                )
        return "Your budget for this session is " + " and ".join(parts) + "."

    if intent == QUERY_AVOIDANCES:
        avoid = [
            (name, entry)
            for name, entry in sorted(fields.items())
            if name.endswith("_avoidances")
        ]
        if not avoid and not unplaced:
            return "You have not told me anything to avoid for this session."
        said_here = [
            _readable(name, entry["value"], currency)
            for name, entry in avoid
            if entry.get("source") != SOURCE_STYLE_DNA
        ]
        from_dna = [
            _readable(name, entry["value"], currency)
            for name, entry in avoid
            if entry.get("source") == SOURCE_STYLE_DNA
        ]
        parts = []
        if said_here:
            parts.append("For this session you told me to avoid " + "; ".join(said_here) + ".")
        if unplaced:
            # Kept verbatim and flagged as NOT a working constraint. Implying otherwise
            # would be worse than having dropped it: the customer would believe it was
            # being honoured.
            quoted = "; ".join(f'"{note}"' for note in unplaced)
            parts.append(
                f"You also said {quoted} — I kept that, but I have not turned it into a "
                "constraint I can act on."
            )
        if from_dna:
            parts.append("From your Style DNA: " + "; ".join(from_dna) + ".")
        return " ".join(parts)

    parts = []
    if from_profile:
        parts.append(
            "From your Style DNA: "
            + "; ".join(_readable(f, v, currency) for f, v in from_profile)
            + "."
        )
    elif personalization_used:
        parts.append("Nothing from your Style DNA applies to this brief yet.")
    else:
        parts.append("I am not using your Style DNA — personalisation is off.")
    if from_session:
        parts.append(
            "From this conversation: "
            + "; ".join(_readable(f, v, currency) for f, v in from_session)
            + "."
        )
    else:
        parts.append("You have not told me anything in this conversation yet.")
    if unplaced:
        quoted = "; ".join(f'"{note}"' for note in unplaced)
        parts.append(f"Noted but not understood: {quoted}.")
    return " ".join(parts)
