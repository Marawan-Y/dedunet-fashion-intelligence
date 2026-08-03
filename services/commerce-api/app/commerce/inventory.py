"""Stock reservation.

Overselling is prevented by a single CONDITIONAL UPDATE:

    UPDATE inventory_items
       SET reserved = reserved + :qty
     WHERE variant_id = :id
       AND on_hand - reserved >= :qty

The predicate and the mutation are evaluated in one atomic statement by the database,
so two concurrent checkouts for the last unit cannot both observe availability and both
succeed. ``rowcount`` tells us which one won: exactly one gets 1, the loser gets 0.

This is deliberately NOT a read-then-write in Python. A ``SELECT`` followed by an
``UPDATE`` has a window between the two in which another transaction can commit, and
that window is exactly where overselling happens. The check constraint
``reserved <= on_hand`` in the schema is the backstop if this module is ever bypassed.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import InventoryItem, Reservation, ReservationState


class InsufficientStock(Exception):
    """Raised when the requested quantity exceeds availability."""

    def __init__(self, variant_id: int, requested: int, available: int) -> None:
        self.variant_id = variant_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"variant {variant_id}: requested {requested}, available {available}"
        )


@dataclass(frozen=True)
class StockLine:
    variant_id: int
    quantity: int


def available_quantity(session: Session, variant_id: int) -> int:
    item = session.get(InventoryItem, variant_id)
    return 0 if item is None else item.available


def try_reserve(session: Session, variant_id: int, quantity: int) -> bool:
    """Atomically reserve stock. Returns True if the reservation succeeded."""

    if quantity <= 0:
        raise ValueError("quantity must be positive")

    result = session.execute(
        text(
            "UPDATE inventory_items "
            "SET reserved = reserved + :qty "
            "WHERE variant_id = :vid AND on_hand - reserved >= :qty"
        ),
        {"qty": quantity, "vid": variant_id},
    )
    return result.rowcount == 1


def reserve_for_order(
    session: Session, order_id: int, lines: list[StockLine]
) -> list[Reservation]:
    """Reserve every line or none of them.

    Partial reservation is never acceptable: it would leave stock held for an order
    that cannot be fulfilled. Any failure releases everything already taken in this
    call before raising.
    """

    taken: list[StockLine] = []
    reservations: list[Reservation] = []

    for line in lines:
        if try_reserve(session, line.variant_id, line.quantity):
            taken.append(line)
            reservations.append(
                Reservation(
                    order_id=order_id,
                    variant_id=line.variant_id,
                    quantity=line.quantity,
                    state=ReservationState.HELD,
                )
            )
            continue

        # Roll back the ones already taken in this call, then report the failure.
        for done in taken:
            release(session, done.variant_id, done.quantity)
        raise InsufficientStock(
            line.variant_id, line.quantity, available_quantity(session, line.variant_id)
        )

    session.add_all(reservations)
    return reservations


def release(session: Session, variant_id: int, quantity: int) -> None:
    """Return reserved stock to availability without changing on-hand."""

    session.execute(
        text(
            "UPDATE inventory_items "
            "SET reserved = CASE WHEN reserved - :qty < 0 THEN 0 ELSE reserved - :qty END "
            "WHERE variant_id = :vid"
        ),
        {"qty": quantity, "vid": variant_id},
    )


def commit_reservation(session: Session, reservation: Reservation) -> None:
    """Convert a held reservation into a despatch: stock leaves the building.

    Both counters drop together so availability is unchanged by this transition; the
    goods move from 'promised' to 'gone'.
    """

    session.execute(
        text(
            "UPDATE inventory_items "
            "SET on_hand = on_hand - :qty, reserved = reserved - :qty "
            "WHERE variant_id = :vid AND reserved >= :qty AND on_hand >= :qty"
        ),
        {"qty": reservation.quantity, "vid": reservation.variant_id},
    )
    reservation.state = ReservationState.COMMITTED


def release_reservation(session: Session, reservation: Reservation) -> None:
    if reservation.state is ReservationState.HELD:
        release(session, reservation.variant_id, reservation.quantity)
        reservation.state = ReservationState.RELEASED


def restock(session: Session, variant_id: int, quantity: int, *, actor: str = "system") -> None:
    """Add units back to on-hand, used by returns and admin adjustments."""

    item = session.get(InventoryItem, variant_id)
    if item is None:
        item = InventoryItem(variant_id=variant_id, on_hand=0, reserved=0)
        session.add(item)
        session.flush()
    item.on_hand += quantity
