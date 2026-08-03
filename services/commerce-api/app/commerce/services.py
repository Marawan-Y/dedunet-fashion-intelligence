"""Domain services: carts, checkout, fulfilment, returns and customer data rights.

Checkout ordering
-----------------
Stock is reserved BEFORE payment is authorized, and released if authorization fails.
The alternative — charge first, then reserve — can take a customer's money for goods
that are already sold out, which is both a refund liability and a support incident.
Holding stock briefly for a payment that then declines is the cheaper failure.

Idempotency
-----------
Checkout is keyed. A repeated request with the same key returns the ORIGINAL order and
does not re-charge. The key is enforced by a unique database constraint, so two
concurrent requests race at the database rather than in application logic.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import os

from . import inventory, notifications, payments, pricing
from .models import (
    AnalyticsEvent,
    AuditLog,
    Cart,
    CartLine,
    Customer,
    InventoryItem,
    Notification,
    Order,
    OrderLine,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    Promotion,
    ReservationState,
    ReturnRequest,
    ReturnStatus,
    Shipment,
    ShipmentStatus,
    Variant,
    as_utc,
    utcnow,
)
from .security import hash_password, verify_password


class DomainError(Exception):
    """Business-rule violation that should surface as a 4xx, not a 500."""


class NotFound(DomainError):
    pass


# ------------------------------------------------------------------ telemetry helpers


def record_event(
    session: Session, name: str, payload: dict, correlation_id: str = ""
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        name=name,
        correlation_id=correlation_id,
        payload_json=json.dumps(payload, sort_keys=True, default=str),
    )
    session.add(event)
    return event


def record_audit(
    session: Session,
    *,
    actor: str,
    action: str,
    entity: str,
    entity_id: str,
    detail: str = "",
    correlation_id: str = "",
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        detail=detail,
        correlation_id=correlation_id,
    )
    session.add(entry)
    return entry


def queue_notification(
    session: Session, customer_id: int, template: str, subject: str, body: str
) -> Notification:
    note = Notification(
        customer_id=customer_id, template=template, subject=subject, body=body
    )
    session.add(note)
    return note


# ------------------------------------------------------------- notification dispatch

# Conservative default. No authoritative specification fixes this value, so it is
# configurable and documented rather than invented silently. Five attempts across worker
# cycles is enough to ride out a short provider outage without hammering a broken one.
DEFAULT_MAX_ATTEMPTS = int(os.getenv("NOTIFICATION_MAX_ATTEMPTS", "5"))
DEFAULT_BATCH_SIZE = int(os.getenv("NOTIFICATION_BATCH_SIZE", "50"))

# Terminal states. A row in one of these is never claimed again.
TERMINAL_STATUSES = frozenset({"sent", "failed", "suppressed"})


def dispatch_pending_notifications(
    session: Session,
    *,
    limit: int | None = None,
    max_attempts: int | None = None,
) -> dict[str, int]:
    """Dispatch queued notifications. Returns per-outcome counts.

    Transaction boundaries
    ----------------------
    ONE transaction per notification. A poison row must not roll back the deliveries that
    already succeeded in the same batch.

    Attempt accounting
    ------------------
    ``attempts`` is incremented and COMMITTED before the sender is invoked. A crash
    mid-send therefore burns an attempt instead of leaving the row eligible forever. The
    cost is the honest one: delivery is AT LEAST ONCE. If the provider accepts the message
    and the process dies before ``sent_at`` commits, a later cycle re-sends it. The
    outgoing message carries ``X-Notification-Key`` so a duplicate can be traced to the row
    that produced it.

    Claiming
    --------
    ``FOR UPDATE SKIP LOCKED`` on PostgreSQL, so two workers never claim the same row.
    SQLAlchemy silently omits it on SQLite, which has no such syntax and no concurrent
    writers to protect against, so the same code is correct on both.

    Rows are NEVER deleted, on any path.
    """

    limit = DEFAULT_BATCH_SIZE if limit is None else limit
    max_attempts = DEFAULT_MAX_ATTEMPTS if max_attempts is None else max_attempts
    counts = {"sent": 0, "failed": 0, "retried": 0, "suppressed": 0, "claimed": 0}

    # Claim ATOMICALLY, in one statement, and commit before doing any work.
    #
    # An earlier version held the batch with SELECT ... FOR UPDATE SKIP LOCKED and then
    # committed inside the loop. That commit released the locks on every row still
    # waiting in the batch, so a second worker immediately claimed them: a 4-worker race
    # over 10 rows produced 19 sends. Row locks last only until the transaction ends,
    # which makes them useless for a loop that must commit per row.
    #
    # Moving each row to an intermediate 'sending' state makes the claim DURABLE: it
    # survives the commit, and the eligibility filter (status == 'queued') excludes it
    # from every other worker permanently, not just for the life of a transaction.
    eligible = (
        select(Notification.id)
        .where(Notification.status == "queued", Notification.attempts < max_attempts)
        .order_by(Notification.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    claimed_ids = list(
        session.scalars(
            update(Notification)
            .where(Notification.id.in_(eligible))
            .values(status="sending", attempts=Notification.attempts + 1)
            .returning(Notification.id)
            .execution_options(synchronize_session=False)
        ).all()
    )
    session.commit()          # attempts persisted BEFORE any external call

    pending = (
        list(session.scalars(select(Notification).where(Notification.id.in_(claimed_ids))).all())
        if claimed_ids
        else []
    )
    counts["claimed"] = len(pending)

    for note in pending:

        customer = session.get(Customer, note.customer_id)
        if customer is None or customer.deleted_at is not None:
            # Erasure must not be undone by a queued email. Terminal, never retried,
            # and the sender is never invoked.
            note.status = "suppressed"
            note.last_error = "recipient erased or missing; delivery suppressed"
            session.commit()
            counts["suppressed"] += 1
            continue

        try:
            sender = notifications.get_sender()
            result = sender.send(
                recipient=customer.email,
                subject=note.subject,
                body=note.body,
                idempotency_key=f"notification-{note.id}",
            )
        except notifications.NotificationRejected as exc:
            note.status = "failed"
            note.last_error = f"terminal: {exc}"
            session.commit()
            counts["failed"] += 1
            continue
        except notifications.NotificationError as exc:
            # Retryable. Stays queued until the attempt ceiling, then becomes terminal so
            # a permanently broken provider cannot produce an infinite retry loop.
            note.last_error = f"retryable: {exc}"
            # Back to 'queued' so a later cycle can retry it; a row left in 'sending'
            # would be invisible to every future claim and silently stuck forever.
            note.status = "queued"
            if note.attempts >= max_attempts:
                note.status = "failed"
                note.last_error = (
                    f"retryable failure persisted after {note.attempts} attempts: {exc}"
                )
                counts["failed"] += 1
            else:
                counts["retried"] += 1
            session.commit()
            continue

        note.status = "sent"
        note.sent_at = utcnow()
        note.provider_reference = result.provider_reference
        note.last_error = ""
        session.commit()
        counts["sent"] += 1

    return counts


# ---------------------------------------------------------------------------- identity


def register_customer(
    session: Session, *, email: str, password: str, full_name: str, marketing_consent: bool = False
) -> Customer:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise DomainError("a valid email address is required")

    existing = session.scalar(select(Customer).where(Customer.email == email))
    if existing is not None:
        raise DomainError("an account with that email already exists")

    from .models import utcnow

    customer = Customer(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        marketing_consent=bool(marketing_consent),
        consent_recorded_at=utcnow() if marketing_consent else None,
    )
    session.add(customer)
    session.flush()
    return customer


def authenticate(session: Session, *, email: str, password: str) -> Customer:
    customer = session.scalar(
        select(Customer).where(Customer.email == (email or "").strip().lower())
    )
    # Verify against a dummy hash when the account is missing so that a non-existent
    # account and a wrong password take similar time and cannot be distinguished.
    if customer is None or customer.deleted_at is not None:
        verify_password(password, "pbkdf2_sha256$1$AA==$AA==")
        raise DomainError("invalid credentials")
    if not verify_password(password, customer.password_hash):
        raise DomainError("invalid credentials")
    return customer


# -------------------------------------------------------------------------------- cart


def get_or_create_cart(session: Session, *, token: str | None, customer_id: int | None) -> Cart:
    if token:
        cart = session.scalar(select(Cart).where(Cart.token == token))
        if cart is not None:
            if customer_id and cart.customer_id is None:
                cart.customer_id = customer_id
            return cart
    cart = Cart(token=secrets.token_urlsafe(24), customer_id=customer_id)
    session.add(cart)
    session.flush()
    return cart


def add_to_cart(session: Session, cart: Cart, *, variant_id: int, quantity: int) -> CartLine:
    if quantity <= 0:
        raise DomainError("quantity must be positive")

    variant = session.get(Variant, variant_id)
    if variant is None:
        raise NotFound(f"variant {variant_id} does not exist")
    if not variant.product.is_active:
        raise DomainError("this product is not available for sale")

    existing = session.scalar(
        select(CartLine).where(CartLine.cart_id == cart.id, CartLine.variant_id == variant_id)
    )
    desired = (existing.quantity if existing else 0) + quantity

    # Availability is advisory at cart time and authoritative at checkout. Checking here
    # gives the customer an honest signal instead of a failure at the payment step.
    if inventory.available_quantity(session, variant_id) < desired:
        raise DomainError("not enough stock available for that quantity")

    if existing is not None:
        existing.quantity = desired
        return existing

    line = CartLine(cart_id=cart.id, variant_id=variant_id, quantity=quantity)
    session.add(line)
    session.flush()
    return line


def remove_from_cart(session: Session, cart: Cart, *, variant_id: int) -> None:
    line = session.scalar(
        select(CartLine).where(CartLine.cart_id == cart.id, CartLine.variant_id == variant_id)
    )
    if line is None:
        raise NotFound("that item is not in the cart")
    session.delete(line)


def _promotion_dict(session: Session, code: str) -> dict | None:
    if not code:
        return None
    promo = session.scalar(
        select(Promotion).where(Promotion.code == code.upper(), Promotion.is_active.is_(True))
    )
    if promo is None:
        return None
    return {
        "code": promo.code,
        "kind": promo.kind,
        "value": promo.value,
        "min_subtotal_minor_units": promo.min_subtotal_minor_units,
    }


def quote_cart(
    session: Session, cart: Cart, *, country_code: str = "DE", promotion_code: str = ""
) -> pricing.PriceBreakdown:
    if not cart.lines:
        raise DomainError("the cart is empty")
    items = [(line.variant.price_minor_units, line.quantity) for line in cart.lines]
    return pricing.price_basket(
        items,
        currency="EUR",
        country_code=country_code,
        promotion=_promotion_dict(session, promotion_code),
    )


# ---------------------------------------------------------------------------- checkout


@dataclass
class CheckoutResult:
    order: Order
    replayed: bool


def checkout(
    session: Session,
    cart: Cart,
    *,
    customer: Customer,
    payment_method_token: str,
    idempotency_key: str,
    country_code: str = "DE",
    promotion_code: str = "",
    correlation_id: str = "",
) -> CheckoutResult:
    if not idempotency_key:
        raise DomainError("an idempotency key is required")

    existing = session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
    if existing is not None:
        return CheckoutResult(order=existing, replayed=True)

    if not cart.lines:
        raise DomainError("the cart is empty")

    breakdown = quote_cart(session, cart, country_code=country_code, promotion_code=promotion_code)

    order = Order(
        order_number=f"FC-{secrets.token_hex(4).upper()}",
        customer_id=customer.id,
        status=OrderStatus.PENDING_PAYMENT,
        currency=breakdown.currency,
        subtotal_minor_units=breakdown.subtotal_minor_units,
        discount_minor_units=breakdown.discount_minor_units,
        shipping_minor_units=breakdown.shipping_minor_units,
        tax_minor_units=breakdown.tax_minor_units,
        total_minor_units=breakdown.total_minor_units,
        promotion_code=breakdown.promotion_code,
        shipping_country=country_code,
        idempotency_key=idempotency_key,
    )
    session.add(order)
    try:
        session.flush()
    except IntegrityError:
        # Another concurrent request with the same key won the race. Return its order.
        session.rollback()
        winner = session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if winner is None:
            raise
        return CheckoutResult(order=winner, replayed=True)

    for line in cart.lines:
        variant = line.variant
        session.add(
            OrderLine(
                order_id=order.id,
                variant_id=variant.id,
                sku=variant.sku,
                product_name=variant.product.name,
                size=variant.size,
                color=variant.color,
                quantity=line.quantity,
                unit_price_minor_units=variant.price_minor_units,
                line_total_minor_units=variant.price_minor_units * line.quantity,
            )
        )

    stock_lines = [
        inventory.StockLine(variant_id=line.variant_id, quantity=line.quantity)
        for line in cart.lines
    ]
    reservations = inventory.reserve_for_order(session, order.id, stock_lines)
    session.flush()

    gateway = payments.get_gateway()
    try:
        auth = gateway.authorize(
            amount_minor_units=order.total_minor_units,
            currency=order.currency,
            payment_method_token=payment_method_token,
            idempotency_key=idempotency_key,
        )
    except (payments.PaymentDeclined, payments.PaymentError):
        # Payment failed: give the stock back immediately rather than holding goods
        # hostage to an order that will never be paid.
        for reservation in reservations:
            inventory.release_reservation(session, reservation)
        session.add(
            Payment(
                order_id=order.id,
                provider=gateway.name,
                provider_reference="",
                status=PaymentStatus.DECLINED,
                amount_minor_units=order.total_minor_units,
                currency=order.currency,
            )
        )
        order.status = OrderStatus.CANCELLED
        record_event(
            session, "checkout_failed", {"order": order.order_number}, correlation_id
        )
        session.commit()
        raise

    session.add(
        Payment(
            order_id=order.id,
            provider=gateway.name,
            provider_reference=auth.provider_reference,
            status=PaymentStatus.AUTHORIZED,
            amount_minor_units=auth.amount_minor_units,
            currency=auth.currency,
        )
    )
    order.status = OrderStatus.PAID
    cart.status = "converted"

    queue_notification(
        session,
        customer.id,
        template="order_confirmation",
        subject=f"Your order {order.order_number}",
        body=(
            f"Thank you for your order {order.order_number}. "
            f"Total {order.total_minor_units} minor units {order.currency}."
        ),
    )
    record_event(
        session,
        "order_placed",
        {
            "order_number": order.order_number,
            "total_minor_units": order.total_minor_units,
            "line_count": len(cart.lines),
        },
        correlation_id,
    )
    session.commit()
    return CheckoutResult(order=order, replayed=False)


# -------------------------------------------------------------------------- fulfilment


def fulfil_order(
    session: Session, order: Order, *, actor: str, correlation_id: str = ""
) -> Shipment:
    if order.status not in {OrderStatus.PAID, OrderStatus.FULFILLING}:
        raise DomainError(f"order in status {order.status.value} cannot be fulfilled")

    for reservation in order.reservations:
        if reservation.state is ReservationState.HELD:
            inventory.commit_reservation(session, reservation)

    shipment = Shipment(
        order_id=order.id,
        carrier="mock-carrier",
        tracking_number=f"TRK{secrets.token_hex(5).upper()}",
        status=ShipmentStatus.IN_TRANSIT,
    )
    session.add(shipment)
    order.status = OrderStatus.SHIPPED

    queue_notification(
        session,
        order.customer_id,
        template="order_shipped",
        subject=f"Your order {order.order_number} has shipped",
        body=f"Tracking number {shipment.tracking_number}.",
    )
    record_audit(
        session,
        actor=actor,
        action="order.fulfil",
        entity="order",
        entity_id=order.order_number,
        detail=f"shipment {shipment.tracking_number}",
        correlation_id=correlation_id,
    )
    record_event(
        session, "order_shipped", {"order_number": order.order_number}, correlation_id
    )
    session.commit()
    return shipment


def cancel_order(session: Session, order: Order, *, actor: str) -> Order:
    if order.status in {OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.REFUNDED}:
        raise DomainError(f"order in status {order.status.value} cannot be cancelled")

    for reservation in order.reservations:
        inventory.release_reservation(session, reservation)

    order.status = OrderStatus.CANCELLED
    record_audit(
        session, actor=actor, action="order.cancel", entity="order", entity_id=order.order_number
    )
    session.commit()
    return order


# ----------------------------------------------------------------- returns and refunds


def request_return(session: Session, order: Order, *, reason: str) -> ReturnRequest:
    if order.status not in {OrderStatus.SHIPPED, OrderStatus.DELIVERED}:
        raise DomainError("only shipped or delivered orders can be returned")

    request = ReturnRequest(order_id=order.id, reason=reason.strip()[:300])
    session.add(request)
    session.commit()
    return request


def approve_return(
    session: Session, request: ReturnRequest, *, actor: str, restock_items: bool = True
) -> ReturnRequest:
    if request.status is not ReturnStatus.REQUESTED:
        raise DomainError(f"return already {request.status.value}")

    order = session.get(Order, request.order_id)
    if order is None:
        raise NotFound("order not found")

    payment = next(
        (p for p in order.payments if p.status is PaymentStatus.AUTHORIZED), None
    )
    if payment is None:
        raise DomainError("no authorized payment to refund")

    gateway = payments.get_gateway()
    refund = gateway.refund(
        provider_reference=payment.provider_reference,
        amount_minor_units=order.total_minor_units,
        idempotency_key=f"refund-{order.order_number}",
    )

    payment.status = PaymentStatus.REFUNDED
    request.status = ReturnStatus.REFUNDED
    request.refund_minor_units = refund.amount_minor_units
    order.status = OrderStatus.REFUNDED

    if restock_items:
        for line in order.lines:
            inventory.restock(session, line.variant_id, line.quantity, actor=actor)

    queue_notification(
        session,
        order.customer_id,
        template="refund_issued",
        subject=f"Refund for {order.order_number}",
        body=f"We have refunded {refund.amount_minor_units} minor units.",
    )
    record_audit(
        session,
        actor=actor,
        action="return.approve",
        entity="return",
        entity_id=str(request.id),
        detail=f"refunded {refund.amount_minor_units}",
    )
    session.commit()
    return request


# --------------------------------------------------------------- customer data rights


def export_customer_data(session: Session, customer: Customer) -> dict:
    """Structured export of everything held about one customer."""

    orders = session.scalars(select(Order).where(Order.customer_id == customer.id)).all()
    return {
        "customer": {
            "email": customer.email,
            "full_name": customer.full_name,
            "created_at": as_utc(customer.created_at).isoformat() if customer.created_at else None,
            "marketing_consent": customer.marketing_consent,
        },
        "addresses": [
            {
                "line1": a.line1,
                "city": a.city,
                "postal_code": a.postal_code,
                "country_code": a.country_code,
            }
            for a in customer.addresses
        ],
        "orders": [
            {
                "order_number": o.order_number,
                "status": o.status.value,
                "total_minor_units": o.total_minor_units,
                "currency": o.currency,
                "placed_at": as_utc(o.placed_at).isoformat() if o.placed_at else None,
                "lines": [
                    {
                        "sku": line.sku,
                        "product_name": line.product_name,
                        "quantity": line.quantity,
                        "unit_price_minor_units": line.unit_price_minor_units,
                    }
                    for line in o.lines
                ],
            }
            for o in orders
        ],
    }


def erase_customer(session: Session, customer: Customer, *, actor: str) -> Customer:
    """Pseudonymize a customer while preserving financial records.

    Order rows are retained because they are accounting records, but every direct
    identifier is removed and the login is disabled. Deleting the orders outright would
    destroy the financial history the business is required to be able to reconcile.
    """

    from .models import utcnow

    customer.email = f"erased-{customer.id}@invalid.example"
    customer.full_name = "erased"
    customer.password_hash = hash_password(secrets.token_urlsafe(32))
    customer.marketing_consent = False
    customer.deleted_at = utcnow()

    for address in customer.addresses:
        session.delete(address)

    record_audit(
        session,
        actor=actor,
        action="customer.erase",
        entity="customer",
        entity_id=str(customer.id),
        detail="identifiers removed; order history retained for reconciliation",
    )
    session.commit()
    return customer


# ------------------------------------------------------------------- admin operations


def create_product(
    session: Session,
    *,
    actor: str,
    slug: str,
    name: str,
    category: str,
    variants: list[dict],
    description: str = "",
    material: str = "",
    care_instructions: str = "",
    country_of_origin: str = "",
    collection: str = "",
    image_url: str = "",
    is_active: bool = False,
) -> Product:
    if session.scalar(select(Product).where(Product.slug == slug)) is not None:
        raise DomainError(f"product slug {slug!r} already exists")
    if not variants:
        raise DomainError("a product requires at least one variant")

    product = Product(
        slug=slug,
        name=name,
        description=description,
        category=category,
        collection=collection,
        material=material,
        care_instructions=care_instructions,
        country_of_origin=country_of_origin,
        image_url=image_url,
        is_active=is_active,
    )
    session.add(product)
    session.flush()

    for spec in variants:
        variant = Variant(
            product_id=product.id,
            sku=spec["sku"],
            size=spec["size"],
            color=spec["color"],
            price_minor_units=int(spec["price_minor_units"]),
        )
        session.add(variant)
        session.flush()
        session.add(
            InventoryItem(variant_id=variant.id, on_hand=int(spec.get("on_hand", 0)), reserved=0)
        )

    record_audit(
        session,
        actor=actor,
        action="product.create",
        entity="product",
        entity_id=slug,
        detail=f"{len(variants)} variants",
    )
    session.commit()
    return product


def adjust_stock(
    session: Session, *, actor: str, variant_id: int, delta: int, reason: str
) -> InventoryItem:
    item = session.get(InventoryItem, variant_id)
    if item is None:
        raise NotFound(f"no inventory record for variant {variant_id}")

    new_on_hand = item.on_hand + delta
    if new_on_hand < 0:
        raise DomainError("stock adjustment would make on-hand negative")
    if new_on_hand < item.reserved:
        raise DomainError(
            f"adjustment would leave {item.reserved} reserved units above {new_on_hand} on hand"
        )

    item.on_hand = new_on_hand
    record_audit(
        session,
        actor=actor,
        action="inventory.adjust",
        entity="variant",
        entity_id=str(variant_id),
        detail=f"delta {delta}: {reason}",
    )
    session.commit()
    return item
