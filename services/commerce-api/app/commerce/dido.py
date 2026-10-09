"""Dido session domain: a styling conversation and the brief it produces.

CUSTOMER-OWNED, like Saved and Style DNA, and for a sharper reason than either. A
conversation holds whatever a person chose to type — where they are going, who with, what
they are worried about wearing. There is no `organization_id`, no merchant access and no
admin browser over these rows in this phase.

THREE TABLES, AND THE DIVISION IS DELIBERATE.

`dido_sessions` holds the AUTHORITATIVE STRUCTURED BRIEF. `dido_turns` holds the
conversation. The brief is not derived from the turns at read time — it is accumulated as
each turn is processed and stored on the session, so the thing the customer reviews and
the thing the system holds are the same object. A brief recomputed from a transcript would
be a second implementation of the merge rules, and the two would eventually disagree.

**The brief is the authority; the prose is not.** Anything Dido says is composed from the
stored brief, so it cannot promise a budget the brief does not hold.

WHY THE BRIEF IS A JSON COLUMN HERE WHEN STYLE DNA REFUSED ONE.

Style DNA is a durable record queried by other features, so it earned normalized tables
with uniqueness guarantees. A styling brief is a single session's working state, read and
written whole, never joined against, and its shape is expected to change as later phases
learn what a recommendation actually needs. Normalizing it now would buy constraints
nothing queries and freeze a shape nothing has used yet. The validation that normalization
would have provided is applied in `dido_brief.py` before anything is stored, and the
provenance of every field travels inside the document rather than beside it.

RETENTION IS BOUNDED. A styling conversation is working state, not an archive, and this
phase does not build a lifelong chat history. A customer has one active session, can start
a new one, and can delete any of them.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow
from .dido_taxonomy import STATUS_ACTIVE, STATUSES


class DidoSession(Base):
    """One styling conversation, and the brief it is building."""

    __tablename__ = "dido_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('" + "','".join(STATUSES) + "')", name="ck_dido_session_status"
        ),
        CheckConstraint("revision >= 1", name="ck_dido_session_revision_positive"),
        CheckConstraint("turn_count >= 0", name="ck_dido_session_turn_count"),
        # The hot query is "this customer's active session". Partial indexes are not
        # portable to SQLite, so the status rides in a composite index instead.
        Index("ix_dido_sessions_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=STATUS_ACTIVE, nullable=False)

    #: Optimistic concurrency, same contract as the Style DNA profile. Two devices in one
    #: conversation is a real shape -- a phone in hand and a laptop open -- and the loser
    #: of a silent overwrite is a customer who watches their answer disappear.
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    #: THE AUTHORITATIVE BRIEF. Validated before it is written; see `dido_brief.py`.
    brief_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    #: The Style DNA revision this session was initialised from, or NULL when
    #: personalisation was off or no profile existed.
    #:
    #: A SNAPSHOT, not a live link. If the profile changes mid-conversation the session
    #: keeps what it started with and Dido can OFFER to refresh -- silently rewriting a
    #: conversation underneath someone is how a brief comes to say something they never
    #: agreed to.
    style_profile_revision_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    #: Whether Style DNA was actually applied. Stored rather than recomputed, because the
    #: switch can be flipped after the session starts and the honest answer is what was
    #: true when the brief was built.
    personalization_used: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )

    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    turns: Mapped[list["DidoTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DidoTurn.ordinal",
    )


class DidoTurn(Base):
    """One message in the conversation, from the customer or from Dido.

    `ordinal` rather than a timestamp for ordering. Two turns written in the same
    transaction share a timestamp, and a conversation whose order wobbles between reads is
    not a conversation. `UNIQUE(session_id, ordinal)` makes the sequence a guarantee
    rather than a convention.
    """

    __tablename__ = "dido_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_dido_turn_session_ordinal"),
        CheckConstraint("role IN ('CUSTOMER','DIDO')", name="ck_dido_turn_role"),
        CheckConstraint("ordinal >= 0", name="ck_dido_turn_ordinal"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("dido_sessions.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)

    #: The message text. PERSONAL DATA: never written to application logs, never placed in
    #: an analytics payload, never included in evidence, and removed on account erasure.
    body: Mapped[str] = mapped_column(Text, nullable=False)

    #: For a Dido turn, the deterministic reason this question was asked -- a policy key,
    #: not generated prose. It is what lets "why did you ask that?" be answered without
    #: calling a model to invent a justification for a decision the model did not make.
    question_key: Mapped[str] = mapped_column(String(60), default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    session: Mapped[DidoSession] = relationship(back_populates="turns")


#: Deletion order, children first. Used by the delete path and by `erase_customer`, so
#: neither has to remember the list.
DIDO_CHILD_MODELS = (DidoTurn,)
DIDO_TABLES = ("dido_turns", "dido_sessions")
