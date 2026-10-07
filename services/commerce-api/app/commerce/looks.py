"""A Look: curated editorial content with a durable identity.

WHY THIS TABLE EXISTS, AND WHAT IT DOES NOT CLAIM.

Saved items need something real to point at. Looks were a hardcoded array in the consumer
bundle (`content.ts`), identified only by a slug that existed in one TypeScript file --
nothing the database could reference and nothing a foreign key could protect. Saving a look
against that slug would have been persistence in name only: a row pointing at a string whose
authority was a frontend constant, which silently breaks the moment someone edits the array.

So a Look becomes a real row. That is the whole of the change.

**A `Look` is NOT an outfit engine output.** The foundation acceptance was explicit that a
Look must one day become "a real multi-item outfit object with reasoning, pricing and
modification actions", and that remains a **later phase**. What is here is the four curated
editorial arrangements that already existed, given identity and referential integrity:

  - a `Look` is composed BY A PERSON, not generated;
  - `LookItem.role` is editorial prose, not a computed justification;
  - there is **no total price**, and no column for one. Every DEDUNET product is a prototype,
    so a look total would be a number this platform invented. Its absence is deliberate and
    is the same decision the look detail page already states in words.

Nothing about the recommendation engine, the outfit engine or Style DNA is started here.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class Look(Base):
    """One curated arrangement of catalogue products."""

    __tablename__ = "looks"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    # The occasion slug this look answers. A plain string rather than a foreign key: the
    # occasion taxonomy is still editorial content in the client and giving it a table would
    # be inventing a domain this phase does not need.
    occasion: Mapped[str] = mapped_column(String(80), default="", index=True)
    story: Mapped[str] = mapped_column(Text, default="")
    # A JSON array of short descriptors ("Minimal", "Structured"). Stored as text rather than
    # a related table: they are display labels with no identity, no ordering rules and nothing
    # referencing them, and a join table for three adjectives is a join table nobody wants.
    descriptors_json: Mapped[str] = mapped_column(Text, default="[]")
    publication_status: Mapped[str] = mapped_column(String(30), default="published", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    items: Mapped[list["LookItem"]] = relationship(
        back_populates="look",
        cascade="all, delete-orphan",
        order_by="LookItem.sort_order",
    )

    @property
    def descriptors(self) -> list[str]:
        """Parse defensively. A malformed row must not take down a catalogue page."""

        try:
            value = json.loads(self.descriptors_json or "[]")
        except (ValueError, TypeError):
            return []
        return [str(v) for v in value] if isinstance(value, list) else []


class LookItem(Base):
    """One product's part in a look, with the editorial reason it is there."""

    __tablename__ = "look_items"
    __table_args__ = (
        # A product appears at most once in a look. Twice is a data error, not a style.
        UniqueConstraint("look_id", "product_id", name="uq_look_item_look_product"),
        # And one slot per position, so the rendered order cannot depend on row order.
        UniqueConstraint("look_id", "sort_order", name="uq_look_item_look_sort"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    look_id: Mapped[int] = mapped_column(
        ForeignKey("looks.id", ondelete="CASCADE"), index=True
    )
    # RESTRICT, not CASCADE: silently dropping a garment out of a curated outfit because a
    # product was deleted would leave an editorial arrangement that no longer says what its
    # author meant. Removing the product requires dealing with the look first.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    role: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    look: Mapped[Look] = relationship(back_populates="items")
