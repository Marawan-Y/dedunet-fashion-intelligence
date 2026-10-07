"""Saved items: looks, products and brands a customer chose to keep.

THIS IS PERSONAL DATA. Three consequences run through the whole module.

**It belongs to the customer, not to a merchant.** There is deliberately no
`organization_id` on any table here. A merchant has no business knowing who saved their
products, and a tenant column would make that a query away. Saved rows are reached only
through the authenticated customer who owns them.

**The customer is resolved from the session, never from the request.** No endpoint in this
module accepts a `customer_id`. That is not politeness -- an endpoint that takes an id it
does not verify is an IDOR, and "saved items" is exactly the shape of resource people forget
to check, because it feels harmless until it enumerates someone's taste.

**It is erased with the customer.** The foreign keys cascade on customer delete, AND
`erase_customer` deletes these rows explicitly, because the erasure path pseudonymizes the
customer row rather than deleting it -- so the cascade would never fire. Both are needed;
either alone leaves personal data behind. Addresses are already handled the same way.

UNIQUENESS IS A DATABASE CONSTRAINT, not an application check. Saving twice is the normal
consequence of a double tap or a retried request, and `UNIQUE(customer_id, target_id)` makes
the second one a no-op instead of a duplicate row. Both save and unsave are idempotent: save
returns the existing row, unsave on something not saved succeeds rather than 404-ing, because
the caller's intent -- "this should not be saved" -- is satisfied either way.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, utcnow


class SavedLook(Base):
    __tablename__ = "saved_looks"
    __table_args__ = (
        UniqueConstraint("customer_id", "look_id", name="uq_saved_look_customer_look"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # CASCADE: if the customer row goes, so does this. See the note above about erasure.
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    # CASCADE on the target too. A saved row pointing at a deleted look is not "historical
    # consistency", it is a dangling reference that every read has to defend against.
    # UNPUBLISHING is the case that preserves the row -- that is handled at read time, not
    # here, because a look coming back should bring its saves with it.
    look_id: Mapped[int] = mapped_column(
        ForeignKey("looks.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class FavoriteProduct(Base):
    __tablename__ = "favorite_products"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "product_id", name="uq_favorite_product_customer_product"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class FavoriteBrand(Base):
    __tablename__ = "favorite_brands"
    __table_args__ = (
        UniqueConstraint("customer_id", "brand_id", name="uq_favorite_brand_customer_brand"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


# The three kinds of saveable thing, named once so the API, the tests and the client cannot
# drift apart on spelling.
SAVED_KINDS = ("looks", "products", "brands")
