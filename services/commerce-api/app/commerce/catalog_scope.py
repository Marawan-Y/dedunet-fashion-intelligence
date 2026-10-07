"""Which products a customer may see. ONE definition.

THE RULE: in brand-preview mode the catalogue is the DEDUNET catalogue — exactly the
imported products. The legacy MERET fixture is not deleted, because existing orders
reference it and their line items are financial records; it is simply not shown.

WHY THIS MODULE EXISTS.

The rule was written out three times: in the catalogue listing, in the brand detail endpoint,
and again in the saved-items service. Each copy was correct. The problem is what three copies
of a visibility rule mean — the fourth surface to need it will carry a fourth copy, and the
first one anybody forgets is a surface that quietly shows a customer the legacy catalogue.

It was also, concretely, a broken build. `M60_legacy_hidden_in_preview` anchors a mutation on
the single line that implements this rule and requires it to appear exactly once in its target
file. The second copy made the anchor ambiguous, and the mutation harness refused to run:

    HARNESS ERROR: anchor for M60_legacy_hidden_in_preview matched 2 times
    in app/commerce/api.py (expected exactly 1)

That is the guard registry doing its job. A mutation that cannot identify the line it is
supposed to remove cannot prove anything, so the harness stops rather than reporting a pass
over a line it guessed at.

So the rule lives here, once, and `M60` anchors on it here. Every caller asks this module.
"""

from __future__ import annotations

from sqlalchemy import Select, select

from . import modes
from .models import Product


def visible_products() -> Select:
    """A SELECT over the products a customer may currently see.

    Active only, and in preview mode scoped to products carrying a Side A external identity.
    Callers add their own filters on top.
    """

    stmt = select(Product).where(Product.is_active.is_(True))
    return apply_preview_scope(stmt)


def apply_preview_scope(stmt: Select) -> Select:
    """Narrow an existing product SELECT to what preview mode permits.

    Separate from `visible_products` because callers that already have a statement — the
    brand detail page starts from "products of this brand" — must be able to add the scope
    without rebuilding their query, which is how the second copy of this rule appeared.
    """

    if modes.is_preview_mode():
        stmt = stmt.where(Product.external_product_id.is_not(None))
    return stmt


def is_visible(product: Product) -> bool:
    """The same rule for a product already in hand.

    A deep link reaches a product directly, so the listing filter alone is a filter a URL
    walks around. This is the row-level form of the same decision.
    """

    if not product.is_active:
        return False
    if modes.is_preview_mode() and product.external_product_id is None:
        return False
    return True
