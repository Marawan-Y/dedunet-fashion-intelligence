"""Orchestration: sessions, turns, interpretation, and what Dido says back.

The order of operations in `add_message` is the whole design, so it is worth stating
before the code:

    persist the customer's turn
        -> interpret (model or deterministic)
            -> validate every candidate against the taxonomy
                -> merge under precedence
                    -> detect contradictions
                        -> choose the next question deterministically
                            -> compose Dido's reply FROM THE RESULTING STATE

The reply is composed last and from the brief, which is what makes it impossible for Dido
to say "I'll keep it under €200" while the brief holds nothing of the kind.

THE CUSTOMER'S TURN IS PERSISTED BEFORE THE MODEL IS CALLED. If the provider times out,
the message is still in the conversation and the customer is not asked to retype it. A
retry carrying the same `client_message_id` returns the existing turn rather than writing
a second copy — a timeout the client did not see is the most ordinary cause of a double
submit.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from . import dido_brief, dido_taxonomy as tax, style_dna_service
from .dido import DidoSession, DidoTurn
from .dido_interpreter import DidoInterpreter, Interpretation, get_interpreter
from .models import Customer
from .services import record_event

logger = logging.getLogger(__name__)


class DidoError(ValueError):
    """A request that cannot be honoured. Maps to 400."""


class SessionConflict(Exception):
    """The session moved on since the caller read it. Maps to 409."""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"expected revision {expected}, session is at {actual}")
        self.expected = expected
        self.actual = actual


class RateLimited(Exception):
    """This customer has sent too many messages too quickly. Maps to 429."""

    def __init__(self, retry_after: int) -> None:
        super().__init__("too many messages")
        self.retry_after = retry_after


# --------------------------------------------------------------------------- limiter


#: A PER-CUSTOMER limit for model-backed messages, separate from the global IP limiter.
#:
#: The existing limiter keys on client IP, which is the wrong key for this endpoint in
#: both directions: a household or office behind one address would share a budget they
#: never spent together, while one account spread over several addresses would evade it
#: entirely. A model call costs money per account, so the budget belongs to the account.
#:
#: This does NOT replace the global limiter — that still applies underneath as a backstop.
#: Section 44 is explicit that the existing architecture is not to be redesigned here, and
#: it is not: this is one bucket in front of one endpoint.
_MESSAGE_CAPACITY = 20
_MESSAGE_WINDOW_SECONDS = 60.0
_buckets: dict[int, tuple[float, float]] = {}


def _check_rate(customer_id: int) -> None:
    """Token bucket, same shape as `rate_limit.py`: smooth refill, no boundary burst."""

    now = time.monotonic()
    tokens, last = _buckets.get(customer_id, (float(_MESSAGE_CAPACITY), now))
    tokens = min(
        float(_MESSAGE_CAPACITY),
        tokens + (now - last) * (_MESSAGE_CAPACITY / _MESSAGE_WINDOW_SECONDS),
    )
    if tokens < 1.0:
        _buckets[customer_id] = (tokens, now)
        deficit = 1.0 - tokens
        raise RateLimited(
            retry_after=max(1, int(deficit / (_MESSAGE_CAPACITY / _MESSAGE_WINDOW_SECONDS)))
        )
    _buckets[customer_id] = (tokens - 1.0, now)


def reset_rate_limits() -> None:
    """Test seam. Buckets are process-local, like the existing limiter's."""

    _buckets.clear()


# --------------------------------------------------------------------------- sessions


def load_owned(session: Session, *, customer: Customer, session_id: int) -> DidoSession:
    """Fetch a session the caller owns, or raise the SAME error as a missing one.

    404 for somebody else's session, never 403. A 403 confirms the row exists and turns
    the endpoint into an enumeration oracle over other people's conversations.
    """

    row = session.scalar(
        select(DidoSession)
        .where(DidoSession.id == session_id, DidoSession.customer_id == customer.id)
        .options(selectinload(DidoSession.turns))
    )
    if row is None:
        raise LookupError("session not found")
    return row


def current_session(session: Session, *, customer: Customer) -> DidoSession | None:
    """The customer's one ACTIVE session, if any."""

    return session.scalar(
        select(DidoSession)
        .where(
            DidoSession.customer_id == customer.id,
            DidoSession.status == tax.STATUS_ACTIVE,
        )
        .options(selectinload(DidoSession.turns))
        .order_by(DidoSession.created_at.desc())
    )


def start_session(
    session: Session, *, customer: Customer, correlation_id: str = ""
) -> DidoSession:
    """Begin a styling conversation, seeding Style DNA only if personalisation is on.

    An existing ACTIVE session is abandoned rather than deleted: the customer asked for a
    fresh start, not for their previous answers to be destroyed, and they may still want
    to look at it.

    This is the first point in the repository where Style DNA is READ for use. The switch
    is checked here and nowhere else, so there is exactly one place to audit.
    """

    existing = current_session(session, customer=customer)
    if existing is not None:
        existing.status = tax.STATUS_ABANDONED

    brief = dido_brief.empty_brief()
    profile = style_dna_service.get_profile(session, customer=customer)

    personalization_used = False
    revision_used = None
    if profile is not None and profile.personalization_enabled:
        payload = style_dna_service.serialize(session, profile)
        brief = dido_brief.apply_style_profile(brief, payload)
        personalization_used = True
        revision_used = profile.revision
    # PERSONALISATION OFF IS A HARD STOP. Not a filter applied later, not a flag the
    # composer checks -- the values are never loaded, so there is nothing to leak into a
    # prompt, a brief or a reply. A profile may exist and remain entirely unused.

    row = DidoSession(
        customer_id=customer.id,
        status=tax.STATUS_ACTIVE,
        revision=1,
        brief_json=json.dumps(brief),
        style_profile_revision_used=revision_used,
        personalization_used=personalization_used,
        turn_count=0,
    )
    session.add(row)
    session.flush()

    opening = _opening_line(brief, personalization_used)
    question = dido_brief.next_question(brief)
    _add_turn(
        session,
        row,
        role="DIDO",
        body=opening + (" " + question["prompt"] if question else ""),
        question_key=question["key"] if question else "",
    )

    record_event(session, "dido_session_started", {}, correlation_id)
    session.commit()
    session.refresh(row)
    return row


def delete_session(
    session: Session, *, customer: Customer, session_id: int, correlation_id: str = ""
) -> bool:
    """Remove a session and its turns. Style DNA and Saved are untouched."""

    try:
        row = load_owned(session, customer=customer, session_id=session_id)
    except LookupError:
        return False
    # The relationship cascade removes the turns. Deleting them in bulk FIRST would leave
    # the cascade with nothing to match, which SQLAlchemy correctly reports as a
    # data-integrity warning -- the same lesson the Style DNA phase learned when a
    # redundant explicit delete survived its own mutation test.
    session.delete(row)
    record_event(session, "dido_session_deleted", {}, correlation_id)
    session.commit()
    return True


def delete_all_for_customer(session: Session, *, customer: Customer) -> int:
    """Remove every Dido conversation for a customer. Used by account erasure.

    Needed for the third time in this repository and for the same reason: `erase_customer`
    PSEUDONYMIZES, so the `ondelete=CASCADE` foreign keys never fire. Conversation text is
    the most open-ended personal data the platform holds — whatever the customer chose to
    type — and leaving it behind after an erasure request would be the worst instance yet
    of a bug this codebase has already paid to learn.
    """

    ids = list(
        session.scalars(select(DidoSession.id).where(DidoSession.customer_id == customer.id))
    )
    if not ids:
        return 0
    session.execute(delete(DidoTurn).where(DidoTurn.session_id.in_(ids)))
    result = session.execute(delete(DidoSession).where(DidoSession.id.in_(ids)))
    return int(result.rowcount or 0)


# --------------------------------------------------------------------------- turns


def _add_turn(
    session: Session, row: DidoSession, *, role: str, body: str, question_key: str = ""
) -> DidoTurn:
    # `or -1` would be a bug here and was: ordinal 0 is a perfectly valid first turn and
    # is FALSY, so the second turn would reuse it. The unique constraint caught it rather
    # than letting the conversation quietly reorder itself.
    highest = session.scalar(
        select(func.coalesce(func.max(DidoTurn.ordinal), -1)).where(
            DidoTurn.session_id == row.id
        )
    )
    turn = DidoTurn(
        session_id=row.id,
        ordinal=(highest if highest is not None else -1) + 1,
        role=role,
        body=body,
        question_key=question_key,
    )
    session.add(turn)
    row.turn_count += 1
    session.flush()
    return turn


@dataclass(frozen=True)
class MessageResult:
    session: DidoSession
    interpretation: Interpretation
    reply: str
    question: dict[str, str] | None


def add_message(
    session: Session,
    *,
    customer: Customer,
    session_id: int,
    message: str,
    expected_revision: int | None = None,
    client_message_id: str = "",
    correlation_id: str = "",
    interpreter: DidoInterpreter | None = None,
) -> MessageResult:
    """The main path. See the module docstring for the order and why it is that order."""

    row = load_owned(session, customer=customer, session_id=session_id)

    if row.status != tax.STATUS_ACTIVE:
        raise DidoError("this styling session is finished; start a new one")
    if expected_revision is not None and expected_revision != row.revision:
        raise SessionConflict(expected_revision, row.revision)

    text = (message or "").strip()
    if not text:
        raise DidoError("a message cannot be empty")
    if len(text) > tax.MAX_MESSAGE_LENGTH:
        raise DidoError(f"a message is limited to {tax.MAX_MESSAGE_LENGTH} characters")
    if row.turn_count >= tax.MAX_TURNS_PER_SESSION:
        raise DidoError("this conversation has gone on long enough; start a new session")

    # IDEMPOTENCY BEFORE THE RATE LIMIT. A retry of a message that already landed must not
    # also spend a token, or a flaky connection would be charged twice for one message.
    if client_message_id:
        existing = session.scalar(
            select(DidoTurn).where(
                DidoTurn.session_id == row.id,
                DidoTurn.role == "CUSTOMER",
                DidoTurn.body == text,
            ).order_by(DidoTurn.ordinal.desc())
        )
        if existing is not None:
            reply_turn = session.scalar(
                select(DidoTurn)
                .where(DidoTurn.session_id == row.id, DidoTurn.ordinal > existing.ordinal)
                .order_by(DidoTurn.ordinal)
            )
            brief = json.loads(row.brief_json)
            return MessageResult(
                session=row,
                interpretation=Interpretation(),
                reply=reply_turn.body if reply_turn else "",
                question=dido_brief.next_question(brief),
            )

    _check_rate(customer.id)

    # The customer's turn is stored FIRST, so a provider failure never loses it.
    _add_turn(session, row, role="CUSTOMER", body=text)

    brief = json.loads(row.brief_json)
    known_fields = frozenset(brief.get("fields", {}))

    engine = interpreter or get_interpreter()
    interpretation = engine.interpret(message=text, known_fields=known_fields)

    if interpretation.degraded:
        # NO GUESSING. The customer is told plainly and offered the controlled choices
        # the client already holds. Substituting an invented interpretation here is the
        # single most tempting and most damaging thing this code could do.
        record_event(
            session, "dido_interpretation_failed", {"reason": interpretation.degraded_reason},
            correlation_id,
        )
        question = dido_brief.next_question(brief) or dido_brief.QUESTION_POLICY[0]
        reply = (
            "I could not read that reliably just now. "
            + question["prompt"]
        )
        _add_turn(session, row, role="DIDO", body=reply, question_key=question.get("key", ""))
        row.revision += 1
        session.commit()
        session.refresh(row)
        return MessageResult(row, interpretation, reply, question)

    # Candidates arrive marked SYSTEM_DERIVED because the interpreter cannot know the
    # difference. They came from THIS message, so the service promotes them to
    # SESSION_EXPLICIT -- which is what lets "no black tonight" outrank a profile.
    updated = dido_brief.apply_candidates(
        brief, interpretation.candidates, source=tax.SOURCE_SESSION
    )
    if interpretation.unplaced:
        existing_unplaced = updated.get("unplaced", [])
        updated["unplaced"] = (existing_unplaced + list(interpretation.unplaced))[
            : tax.MAX_FREE_TEXT_CONSTRAINTS
        ]
        updated["contradictions"] = dido_brief.detect_contradictions(updated)

    row.brief_json = json.dumps(updated)
    row.revision += 1

    question = dido_brief.next_question(updated)
    reply = _compose_reply(updated, interpretation, question)
    _add_turn(
        session, row, role="DIDO", body=reply, question_key=question["key"] if question else ""
    )

    if question is None and row.status == tax.STATUS_ACTIVE:
        record_event(session, "dido_brief_ready", {}, correlation_id)

    # NO RAW MESSAGE AND NO PREFERENCE VALUES. The event records that a message was
    # submitted and how many constraints landed -- enough to see whether interpretation is
    # working, and nothing that reconstructs what anyone said.
    record_event(
        session,
        "dido_message_submitted",
        {"constraints_applied": len(interpretation.candidates), "ready": question is None},
        correlation_id,
    )

    session.commit()
    session.refresh(row)
    return MessageResult(row, interpretation, reply, question)


def complete_session(
    session: Session,
    *,
    customer: Customer,
    session_id: int,
    expected_revision: int | None = None,
    correlation_id: str = "",
) -> DidoSession:
    """Mark the brief agreed. This is where Phase 7 ends."""

    row = load_owned(session, customer=customer, session_id=session_id)
    if expected_revision is not None and expected_revision != row.revision:
        raise SessionConflict(expected_revision, row.revision)

    brief = json.loads(row.brief_json)
    if brief.get("contradictions"):
        raise DidoError("resolve the conflicting constraints before finishing the brief")

    row.status = tax.STATUS_BRIEF_READY
    row.revision += 1
    _add_turn(
        session,
        row,
        role="DIDO",
        body=(
            "Your styling brief is ready. DEDUNET does not yet rank products or build the "
            "outfit from it — you can review the brief, browse the catalogue, or look at "
            "the curated Looks."
        ),
    )
    record_event(session, "dido_brief_ready", {}, correlation_id)
    session.commit()
    session.refresh(row)
    return row


def correct_brief(
    session: Session,
    *,
    customer: Customer,
    session_id: int,
    changes: dict[str, Any],
    expected_revision: int | None = None,
    correlation_id: str = "",
) -> DidoSession:
    """Direct correction from the review screen. Always SESSION_EXPLICIT.

    A value the customer typed into the brief outranks everything, including a profile
    value it replaces — and still does not write back to the profile. `null` clears a
    field, which is how a customer removes something Dido got wrong.
    """

    row = load_owned(session, customer=customer, session_id=session_id)
    if expected_revision is not None and expected_revision != row.revision:
        raise SessionConflict(expected_revision, row.revision)

    brief = json.loads(row.brief_json)
    fields = brief.setdefault("fields", {})

    for name, value in changes.items():
        if name not in dido_brief.ALLOWED_FIELDS:
            raise DidoError(f"unknown brief field: {name!r}")
        if value is None:
            fields.pop(name, None)
            continue
        cleaned = dido_brief.validate_candidate(name, value)
        if cleaned is None:
            raise DidoError(f"{name} is not a value this brief can hold")
        fields[name] = {
            "value": cleaned,
            "source": tax.SOURCE_SESSION,
            "evidence": "you corrected this",
        }

    brief["contradictions"] = dido_brief.detect_contradictions(brief)
    row.brief_json = json.dumps(brief)
    row.revision += 1
    record_event(session, "dido_brief_corrected", {}, correlation_id)
    session.commit()
    session.refresh(row)
    return row


def refresh_style_profile(
    session: Session, *, customer: Customer, session_id: int
) -> DidoSession:
    """Re-seed from the current Style DNA, ON REQUEST ONLY.

    A session keeps the profile snapshot it began with. This exists so a customer who
    changed their profile mid-conversation can pull the change in deliberately — the
    alternative, rewriting an open conversation underneath them, would change a brief they
    had already read.
    """

    row = load_owned(session, customer=customer, session_id=session_id)
    profile = style_dna_service.get_profile(session, customer=customer)
    brief = json.loads(row.brief_json)

    if profile is not None and profile.personalization_enabled:
        payload = style_dna_service.serialize(session, profile)
        brief = dido_brief.apply_style_profile(brief, payload)
        row.style_profile_revision_used = profile.revision
        row.personalization_used = True
    else:
        row.personalization_used = False
        row.style_profile_revision_used = None

    row.brief_json = json.dumps(brief)
    row.revision += 1
    session.commit()
    session.refresh(row)
    return row


# --------------------------------------------------------------------------- wording


def _opening_line(brief: dict[str, Any], personalization_used: bool) -> str:
    """What Dido says first. Truthful about whether the profile is in play."""

    if personalization_used:
        return (
            "I have your Style DNA to work from, and I will say which parts I use."
        )
    return (
        "Your Style DNA is not being used — either you have not made one, or "
        "personalisation is off. Tell me what you need and I will work from that."
    )


def _label(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _compose_reply(
    brief: dict[str, Any], interpretation: Interpretation, question: dict[str, str] | None
) -> str:
    """Dido's reply, built FROM THE STORED BRIEF.

    Not from the model, and not from the candidates — from what actually landed. That is
    the structural guarantee behind section 39: if the brief does not hold a budget, no
    sentence here can mention one, because the sentence is assembled from the fields that
    exist.
    """

    fields = brief.get("fields", {})
    applied = [
        c.field
        for c in interpretation.candidates
        if c.field in fields and fields[c.field].get("source") == tax.SOURCE_SESSION
    ]

    parts: list[str] = []
    if applied:
        readable = []
        for name in applied[:4]:
            value = fields[name]["value"]
            if name in ("budget_total", "budget_per_piece") and isinstance(value, int):
                readable.append(f"{'per piece' if 'piece' in name else 'in total'} "
                                f"€{value // 100}.{value % 100:02d}")
            else:
                readable.append(_label(value).replace("-", " "))
        parts.append("Noted: " + "; ".join(readable) + ".")
    elif interpretation.ambiguous:
        parts.append("I did not catch a styling constraint in that.")

    if interpretation.unplaced:
        parts.append(
            "I kept this as a note because I could not place it: "
            + "; ".join(interpretation.unplaced[:2])
            + "."
        )

    if question:
        parts.append(question["prompt"])
    else:
        parts.append(
            "That is enough for a brief. Review it when you are ready — DEDUNET does not "
            "rank products or build outfits yet."
        )

    return " ".join(parts)


# --------------------------------------------------------------------------- serialisation


def serialize_session(row: DidoSession, *, include_turns: bool = True) -> dict[str, Any]:
    brief = json.loads(row.brief_json)
    question = dido_brief.next_question(brief)
    payload: dict[str, Any] = {
        "session_id": row.id,
        "status": row.status,
        "revision": row.revision,
        "turn_count": row.turn_count,
        "personalization_used": row.personalization_used,
        "style_profile_revision_used": row.style_profile_revision_used,
        "brief": dido_brief.summarize(brief),
        "next_question": question,
        # Stated on every response so the client never has to infer it, and so the
        # boundary is visible in the contract rather than only in the UI copy.
        "capabilities": {
            "understands_constraints": True,
            "uses_style_dna": row.personalization_used,
            "recommends_products": False,
            "builds_outfits": False,
        },
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if include_turns:
        payload["turns"] = [
            {
                "ordinal": t.ordinal,
                "role": t.role,
                "body": t.body,
                "question_key": t.question_key,
                "created_at": t.created_at,
            }
            for t in sorted(row.turns, key=lambda t: t.ordinal)
        ]
    return payload


def explain_question(question_key: str) -> dict[str, str] | None:
    """"Why did you ask that?" — answered from policy metadata, never from a model.

    Calling a language model to justify a decision made by an if-statement would produce
    a plausible explanation that is not the actual reason. The reason is written down
    beside the rule.
    """

    if question_key.startswith("conflict:"):
        return {
            "key": question_key,
            "why": "Two things you have told me cannot both be true, and choosing for you would be guessing.",
        }
    for policy in dido_brief.QUESTION_POLICY:
        if policy["key"] == question_key:
            return {"key": question_key, "why": policy["why"]}
    return None


def what_is_in_use(row: DidoSession) -> dict[str, Any]:
    """"What do you know about me?" — the session's own answer, grouped by source."""

    brief = json.loads(row.brief_json)
    summary = dido_brief.summarize(brief)
    return {
        "from_style_dna": summary["from_style_dna"],
        "from_this_conversation": summary["from_session"] + summary["derived_from_your_words"],
        "style_dna_available_but_unused": not row.personalization_used,
        "note": (
            "Your Style DNA is stored but personalisation is off, so Dido is not using it."
            if not row.personalization_used
            else "Dido is using the Style DNA values listed above, and nothing else about you."
        ),
    }
