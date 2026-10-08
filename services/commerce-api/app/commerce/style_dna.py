"""Style DNA: what a customer has DELIBERATELY TOLD DEDUNET about how they dress.

THE DEFINING RULE OF THIS DOMAIN, from which everything else follows:

    Every row here exists because a person chose it. Nothing is inferred, derived,
    scored, embedded or guessed.

That is not a limitation to be lifted quietly later. It is the contract the page makes with
the customer, and the `source` column exists so that a future inference phase has to break
that contract visibly -- with a new value, a migration and its own acceptance -- rather than
by writing inferred rows into tables that already claim to hold explicit ones.

**Saved items are NOT an input.** The repository now holds real Saved data: products,
brands and looks a customer kept. It would be a few lines to turn "saved three black pieces"
into "prefers black", and those few lines would be the moment Style DNA stopped being true.
A save is an act of interest, not a statement of preference -- people save things to decide
against them. Inference needs its own source, confidence, explanation, correction path,
consent and decay, and this phase has none of those, so it does not infer.

**It belongs to the customer.** No `organization_id`, no merchant ownership, no tenancy. A
merchant has no business knowing anyone's sizes, and a tenant column makes that a join away.
The same reasoning as `saved.py`, and for stronger reasons: this data is more intimate.

**It is erased with the customer, by two mechanisms.** The foreign keys cascade on a hard
delete, AND `erase_customer` deletes these rows explicitly, because erasure PSEUDONYMIZES
the customer row rather than removing it -- so the cascade never fires. Saved persistence
learned this the hard way; Style DNA inherits the lesson rather than rediscovering it.

**It is not an identity record.** Fashion preferences stay fashion preferences. Nothing in
this schema stores or infers religion, ethnicity, sexual orientation, health, politics,
gender identity or financial condition. "Modest" is a cut of clothing here and nothing else;
a budget is a number a customer typed, not an estimate of what they can afford. The one
free-text field is capped at 280 characters precisely because an open box in a personal
profile is where sensitive disclosure arrives uninvited.

**A preference is not a product claim.** "I prefer cotton" is a fact about the customer. It
authorizes nothing about any garment: the catalogue's material statements remain
"stated, not verified" until supplier documents and testing say otherwise, and Style DNA
does not launder a customer's preference into evidence about a product.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow
from .style_taxonomy import (
    MAX_BUDGET_MINOR_UNITS,
    MAX_FIT_NOTES_LENGTH,
    MAX_SIZE_LABEL_LENGTH,
    SOURCE_USER_EXPLICIT,
)

#: Width of the provenance column. Generous enough for the inferred-source names a later
#: phase would plausibly want, so introducing them is a code change rather than an ALTER.
_SOURCE_LENGTH = 40


class StyleProfile(Base):
    """One per customer. The root every preference row hangs from.

    ONE PROFILE PER CUSTOMER is a unique constraint, not a convention. Two profiles for one
    person is not a tidiness problem: it is a question with two different answers and no way
    to tell which the customer meant, and the "correct" one would be whichever a query
    happened to order first.
    """

    __tablename__ = "style_profiles"
    __table_args__ = (
        CheckConstraint(
            "budget_per_piece_minor_units IS NULL OR budget_per_piece_minor_units >= 0",
            name="ck_style_profile_piece_budget_non_negative",
        ),
        CheckConstraint(
            "budget_per_look_minor_units IS NULL OR budget_per_look_minor_units >= 0",
            name="ck_style_profile_look_budget_non_negative",
        ),
        CheckConstraint(
            f"budget_per_piece_minor_units IS NULL OR budget_per_piece_minor_units <= {MAX_BUDGET_MINOR_UNITS}",
            name="ck_style_profile_piece_budget_ceiling",
        ),
        CheckConstraint(
            f"budget_per_look_minor_units IS NULL OR budget_per_look_minor_units <= {MAX_BUDGET_MINOR_UNITS}",
            name="ck_style_profile_look_budget_ceiling",
        ),
        # A budget without a currency is a number, not money. The money contract's first
        # rule, expressed where the database can hold the line.
        CheckConstraint(
            "(budget_per_piece_minor_units IS NULL AND budget_per_look_minor_units IS NULL) "
            "OR budget_currency IS NOT NULL",
            name="ck_style_profile_budget_needs_currency",
        ),
        CheckConstraint("revision >= 1", name="ck_style_profile_revision_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    #: UNIQUE: one profile per customer. CASCADE for the hard-delete path; see the module
    #: docstring for why the cascade alone is not enough.
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), unique=True, index=True
    )

    #: The customer's switch. OFF preserves everything and withdraws permission to use it.
    #:
    #: Separate from deletion on purpose, and the separation is the feature: "stop using
    #: this" and "forget this" are different requests, and a control that silently did both
    #: would destroy data a customer expected to keep. Default ON because the customer
    #: creating a profile is the act of opting in -- there is no profile until they make one.
    personalization_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Optimistic concurrency. Incremented on every successful mutation.
    #:
    #: A style profile is edited from a phone and a laptop by the same person, which is
    #: exactly the shape that loses updates: both load revision 4, both PATCH, and the
    #: second silently erases the first. A caller sends the revision it read and gets 409 if
    #: the world moved on. The alternative -- last-write-wins -- is not simpler, it just
    #: moves the loss somewhere nobody sees it.
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    #: Budgets: integer minor units, currency explicit, both nullable because "unset" is a
    #: real state. NEVER a float -- see SIDE_B_MONEY_CONTRACT rule 1.
    budget_per_piece_minor_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_per_look_minor_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    #: Single-select explicit answers. Nullable means the customer has not said.
    colour_approach: Mapped[str | None] = mapped_column(String(40), nullable=True)
    care_effort: Mapped[str | None] = mapped_column(String(40), nullable=True)
    seasonality: Mapped[str | None] = mapped_column(String(40), nullable=True)

    #: The only free text in the domain, hard-capped. See the module docstring.
    fit_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    style_directions: Mapped[list["StyleDirectionPreference"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    colours: Mapped[list["StyleColourPreference"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    fits: Mapped[list["StyleFitPreference"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    sizes: Mapped[list["StyleSize"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    materials: Mapped[list["StyleMaterialPreference"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    brands: Mapped[list["StyleBrandPreference"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )


class _SourcedPreference:
    """Shared columns for every preference row.

    `source` is the load-bearing one. It records WHY this row exists, and in this phase the
    only legal answer is that a person chose it. A check constraint pins that at the
    database, so an inferred row cannot be written by a future code path that forgot -- it
    would have to change the constraint, which is a migration somebody reviews.
    """

    source: Mapped[str] = mapped_column(
        String(_SOURCE_LENGTH), default=SOURCE_USER_EXPLICIT, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


def _explicit_only(table: str) -> CheckConstraint:
    """The database's copy of the explicit-only rule.

    Deliberately redundant with the service-layer guard. The service guard gives a clean
    error message; this one makes the rule true even for a code path that never calls the
    service -- a migration, a fixture, a future bulk import. One of them is about ergonomics
    and the other is about the rule actually holding.
    """

    return CheckConstraint(
        f"source = '{SOURCE_USER_EXPLICIT}'", name=f"ck_{table}_source_user_explicit"
    )


class StyleDirectionPreference(_SourcedPreference, Base):
    """"I dress minimal" / "I avoid avant-garde"."""

    __tablename__ = "style_direction_preferences"
    __table_args__ = (
        # One stance per direction per profile. A customer cannot both prefer and avoid the
        # same thing, and the constraint is on (profile, direction) rather than
        # (profile, direction, stance) precisely so that contradiction is unrepresentable
        # rather than merely discouraged.
        UniqueConstraint("profile_id", "style_slug", name="uq_style_direction_profile_slug"),
        _explicit_only("style_direction_preferences"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("style_profiles.id", ondelete="CASCADE"), index=True
    )
    style_slug: Mapped[str] = mapped_column(String(60))
    stance: Mapped[str] = mapped_column(String(20))

    profile: Mapped[StyleProfile] = relationship(back_populates="style_directions")


class StyleColourPreference(_SourcedPreference, Base):
    __tablename__ = "style_colour_preferences"
    __table_args__ = (
        UniqueConstraint("profile_id", "colour_slug", name="uq_style_colour_profile_slug"),
        _explicit_only("style_colour_preferences"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("style_profiles.id", ondelete="CASCADE"), index=True
    )
    colour_slug: Mapped[str] = mapped_column(String(40))
    stance: Mapped[str] = mapped_column(String(20))

    profile: Mapped[StyleProfile] = relationship(back_populates="colours")


class StyleFitPreference(Base):
    """How a customer wants a garment category to sit. One answer per category."""

    __tablename__ = "style_fit_preferences"
    __table_args__ = (
        UniqueConstraint("profile_id", "garment_category", name="uq_style_fit_profile_category"),
        _explicit_only("style_fit_preferences"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("style_profiles.id", ondelete="CASCADE"), index=True
    )
    garment_category: Mapped[str] = mapped_column(String(40))
    fit_slug: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(
        String(_SOURCE_LENGTH), default=SOURCE_USER_EXPLICIT, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    profile: Mapped[StyleProfile] = relationship(back_populates="fits")


class StyleSize(Base):
    """A size the customer STATED, in the system they stated it in.

    `(category, system, label)` is kept whole and never converted. The uniqueness is on
    (profile, category, system) so a customer can record "tops: ALPHA M" and "tops: EU 50"
    side by side without either claiming to be the other. Nothing in this phase reads one
    system and answers in another; cross-brand and cross-system size recommendation is a
    later problem that needs real garment measurements, not a conversion table.
    """

    __tablename__ = "style_sizes"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "garment_category", "size_system", name="uq_style_size_profile_cat_sys"
        ),
        CheckConstraint(
            f"length(size_label) > 0 AND length(size_label) <= {MAX_SIZE_LABEL_LENGTH}",
            name="ck_style_size_label_length",
        ),
        _explicit_only("style_sizes"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("style_profiles.id", ondelete="CASCADE"), index=True
    )
    garment_category: Mapped[str] = mapped_column(String(40))
    size_system: Mapped[str] = mapped_column(String(20))
    size_label: Mapped[str] = mapped_column(String(MAX_SIZE_LABEL_LENGTH))
    source: Mapped[str] = mapped_column(
        String(_SOURCE_LENGTH), default=SOURCE_USER_EXPLICIT, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    profile: Mapped[StyleProfile] = relationship(back_populates="sizes")


class StyleMaterialPreference(_SourcedPreference, Base):
    __tablename__ = "style_material_preferences"
    __table_args__ = (
        UniqueConstraint("profile_id", "material_slug", name="uq_style_material_profile_slug"),
        _explicit_only("style_material_preferences"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("style_profiles.id", ondelete="CASCADE"), index=True
    )
    material_slug: Mapped[str] = mapped_column(String(40))
    stance: Mapped[str] = mapped_column(String(20))

    profile: Mapped[StyleProfile] = relationship(back_populates="materials")


class StyleBrandPreference(_SourcedPreference, Base):
    """A brand the customer follows or excludes, by FOREIGN KEY.

    Not a name string. The brand domain is real and authoritative, and a stored name would
    drift the moment a brand is renamed, leaving a preference for something that no longer
    exists under that spelling. CASCADE on the brand as well as the profile: a preference
    pointing at a deleted brand is a dangling reference every read has to defend against.

    A preference here is the customer's opinion and NOTHING ELSE. It is not a partnership,
    an endorsement or a commercial relationship, and DEDUNET has none of those with any
    brand.
    """

    __tablename__ = "style_brand_preferences"
    __table_args__ = (
        UniqueConstraint("profile_id", "brand_id", name="uq_style_brand_profile_brand"),
        _explicit_only("style_brand_preferences"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("style_profiles.id", ondelete="CASCADE"), index=True
    )
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    stance: Mapped[str] = mapped_column(String(20))

    profile: Mapped[StyleProfile] = relationship(back_populates="brands")


#: Every table this domain owns, in deletion order (children before the root).
#: Used by the delete path and by `erase_customer`, so neither has to remember the list.
STYLE_DNA_CHILD_MODELS = (
    StyleDirectionPreference,
    StyleColourPreference,
    StyleFitPreference,
    StyleSize,
    StyleMaterialPreference,
    StyleBrandPreference,
)

STYLE_DNA_TABLES = tuple(m.__tablename__ for m in STYLE_DNA_CHILD_MODELS) + (
    StyleProfile.__tablename__,
)
