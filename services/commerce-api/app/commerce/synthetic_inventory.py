"""Synthetic inventory for COMMERCE_TEST_MODE.

Loads explicitly-marked, non-real stock onto selected DEDUNET SKUs so a sandbox purchase
journey can be exercised, WITHOUT changing what the prototype data means.

The default DEDUNET truth is untouched:

    stock_quantity = 0
    sellable       = false
    inventory_status = prototype_unavailable

Two properties matter more than anything else here:

1. **Synthetic stock is typed, not implied.** `inventory_status` becomes
   `synthetic_test_stock`. Nothing infers "this is test data" from a quantity, a comment or
   a naming convention — a future reader, an admin screen and a backup all see the same
   explicit state.

2. **Effective sellability is computed, never stored alone.** A row carrying synthetic stock
   is still unpurchasable in `BRAND_PREVIEW_MODE`, because the mode is consulted at request
   time. Switching preview on blocks checkout immediately, with no database cleanup and no
   window in which stale rows are still buyable.

Evidence, origin, material and legal states are never touched by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import modes
from .models import InventoryItem, Product, Variant

# The typed marker. Anything carrying this is test data by definition.
SYNTHETIC_STATUS = "synthetic_test_stock"
PROTOTYPE_STATUS = "prototype_unavailable"

DEFAULT_QUANTITY = 25


class TestInventoryRefused(RuntimeError):
    """The operation is not permitted in the current mode, or was not confirmed."""


@dataclass
class InventoryResult:
    mode: str
    variants_touched: int = 0
    units_loaded: int = 0
    skus: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "variants_touched": self.variants_touched,
            "units_loaded": self.units_loaded,
            "skus": sorted(self.skus),
        }


def _assert_allowed(confirmed: bool) -> str:
    """Refuse unless the mode permits it AND the operator said so explicitly.

    Two independent conditions. The mode check stops synthetic stock existing where it
    would be a lie; the confirmation flag stops it appearing because a script ran by
    accident. Neither substitutes for the other.
    """

    # `current_mode()` itself raises for PUBLIC_COMMERCE_MODE, so public is refused here
    # by construction rather than by a branch someone could later delete.
    mode = modes.current_mode()

    if mode != modes.COMMERCE_TEST:
        raise TestInventoryRefused(
            f"synthetic test inventory is only permitted in {modes.COMMERCE_TEST}; "
            f"the current mode is {mode}. Loading fake stock into a brand preview would "
            f"make a prototype look purchasable."
        )
    if not confirmed:
        raise TestInventoryRefused(
            "refusing to load synthetic inventory without explicit confirmation; "
            "pass --confirm-test-only"
        )
    return mode


def load_test_inventory(
    session: Session,
    *,
    confirmed: bool,
    skus: list[str] | None = None,
    quantity: int = DEFAULT_QUANTITY,
) -> InventoryResult:
    """Load synthetic stock onto DEDUNET variants. Idempotent."""

    mode = _assert_allowed(confirmed)

    if quantity <= 0:
        raise TestInventoryRefused("quantity must be positive")

    stmt = select(Variant).join(Product).where(Product.external_product_id.is_not(None))
    if skus:
        stmt = stmt.where(Variant.sku.in_(skus))

    variants = list(session.scalars(stmt).all())
    if skus:
        found = {v.sku for v in variants}
        missing = sorted(set(skus) - found)
        if missing:
            # A typo must not silently load nothing and report success.
            raise TestInventoryRefused(f"unknown DEDUNET SKUs: {missing}")

    result = InventoryResult(mode=mode)
    for variant in variants:
        inventory = session.scalar(
            select(InventoryItem).where(InventoryItem.variant_id == variant.id)
        )
        if inventory is None:
            inventory = InventoryItem(variant_id=variant.id, on_hand=0, reserved=0)
            session.add(inventory)
            session.flush()

        # Idempotent: set, never accumulate. Re-running must not multiply the stock.
        inventory.on_hand = quantity
        variant.inventory_status = SYNTHETIC_STATUS
        variant.sellable = True
        variant.product.inventory_status = SYNTHETIC_STATUS
        variant.product.sellable = True

        result.variants_touched += 1
        result.units_loaded += quantity
        result.skus.append(variant.sku)

    session.flush()
    return result


def clear_test_inventory(session: Session, *, confirmed: bool) -> InventoryResult:
    """Restore the prototype default: zero stock, not sellable."""

    mode = _assert_allowed(confirmed)

    variants = list(
        session.scalars(
            select(Variant)
            .join(Product)
            .where(
                Product.external_product_id.is_not(None),
                Variant.inventory_status == SYNTHETIC_STATUS,
            )
        ).all()
    )

    result = InventoryResult(mode=mode)
    for variant in variants:
        inventory = session.scalar(
            select(InventoryItem).where(InventoryItem.variant_id == variant.id)
        )
        if inventory is not None:
            inventory.on_hand = 0
            inventory.reserved = 0
        variant.inventory_status = PROTOTYPE_STATUS
        variant.sellable = False
        variant.product.inventory_status = PROTOTYPE_STATUS
        variant.product.sellable = False
        result.variants_touched += 1
        result.skus.append(variant.sku)

    session.flush()
    return result
