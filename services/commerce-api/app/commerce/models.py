"""ORM models for the commerce domain.

Money invariant
---------------
Every monetary column is ``Integer`` holding MINOR UNITS, per DEC-010. No column
stores a float or a decimal amount. Currency travels with the amount so a value is
never interpreted against the wrong exponent.

Inventory invariant
-------------------
``InventoryItem`` stores ``on_hand`` and ``reserved`` separately. Availability is the
derived difference; it is never stored, so it cannot drift from its inputs.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    FULFILLING = "fulfilling"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, enum.Enum):
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    DECLINED = "declined"
    FAILED = "failed"
    REFUNDED = "refunded"


class ReservationState(str, enum.Enum):
    HELD = "held"
    COMMITTED = "committed"
    RELEASED = "released"


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class ReturnStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"


# --------------------------------------------------------------------------- identity


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="customer")
    # Consent is recorded, not assumed. Absence of a record is treated as refusal.
    marketing_consent: Mapped[bool] = mapped_column(default=False)
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Soft deletion supports the erasure workflow while preserving order history,
    # which must stay immutable for financial reconciliation.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    addresses: Mapped[list["Address"]] = relationship(back_populates="customer")


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    line1: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120))
    postal_code: Mapped[str] = mapped_column(String(20))
    country_code: Mapped[str] = mapped_column(String(2))

    customer: Mapped[Customer] = relationship(back_populates="addresses")


# ---------------------------------------------------------------------------- catalog


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), index=True)
    collection: Mapped[str] = mapped_column(String(80), default="", index=True)
    material: Mapped[str] = mapped_column(String(200), default="")
    care_instructions: Mapped[str] = mapped_column(String(300), default="")
    country_of_origin: Mapped[str] = mapped_column(String(2), default="")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    image_url: Mapped[str] = mapped_column(String(300), default="")
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    variants: Mapped[list["Variant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class Variant(Base):
    __tablename__ = "variants"
    __table_args__ = (
        CheckConstraint("price_minor_units > 0", name="ck_variant_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    size: Mapped[str] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(40))
    price_minor_units: Mapped[int] = mapped_column(Integer)

    product: Mapped[Product] = relationship(back_populates="variants")
    inventory: Mapped["InventoryItem"] = relationship(
        back_populates="variant", uselist=False, cascade="all, delete-orphan"
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("on_hand >= 0", name="ck_inventory_on_hand_non_negative"),
        CheckConstraint("reserved >= 0", name="ck_inventory_reserved_non_negative"),
        # The database itself refuses to hold more stock than exists. This is the last
        # line of defence against overselling if application logic is ever bypassed.
        CheckConstraint("reserved <= on_hand", name="ck_inventory_reserved_within_on_hand"),
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id", ondelete="CASCADE"), primary_key=True
    )
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)

    variant: Mapped[Variant] = relationship(back_populates="inventory")

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


# ------------------------------------------------------------------------------- cart


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lines: Mapped[list["CartLine"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartLine(Base):
    __tablename__ = "cart_lines"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_line_variant"),
        CheckConstraint("quantity > 0", name="ck_cart_line_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"))
    quantity: Mapped[int] = mapped_column(Integer)

    cart: Mapped[Cart] = relationship(back_populates="lines")
    variant: Mapped[Variant] = relationship()


# -------------------------------------------------------------------------- promotion


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(20))  # "percent" | "fixed"
    value: Mapped[int] = mapped_column(Integer)  # basis points, or minor units
    min_subtotal_minor_units: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


# ----------------------------------------------------------------------------- orders


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False), default=OrderStatus.PENDING_PAYMENT
    )
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    subtotal_minor_units: Mapped[int] = mapped_column(Integer, default=0)
    discount_minor_units: Mapped[int] = mapped_column(Integer, default=0)
    shipping_minor_units: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor_units: Mapped[int] = mapped_column(Integer, default=0)
    total_minor_units: Mapped[int] = mapped_column(Integer, default=0)

    promotion_code: Mapped[str] = mapped_column(String(40), default="")
    shipping_country: Mapped[str] = mapped_column(String(2), default="DE")
    # Idempotency key makes checkout safe to retry: a repeated request returns the
    # original order instead of creating a second one and charging twice.
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="order")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="order")


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"))
    # Descriptive fields are COPIED onto the line, not joined at read time. An order is
    # a historical financial record: renaming a product must never alter a past order.
    sku: Mapped[str] = mapped_column(String(80))
    product_name: Mapped[str] = mapped_column(String(200))
    size: Mapped[str] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_minor_units: Mapped[int] = mapped_column(Integer)
    line_total_minor_units: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="lines")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    state: Mapped[ReservationState] = mapped_column(
        Enum(ReservationState, native_enum=False), default=ReservationState.HELD
    )

    order: Mapped[Order] = relationship(back_populates="reservations")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(40), default="sandbox")
    provider_reference: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, native_enum=False))
    amount_minor_units: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    order: Mapped[Order] = relationship(back_populates="payments")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    carrier: Mapped[str] = mapped_column(String(40), default="mock-carrier")
    tracking_number: Mapped[str] = mapped_column(String(80))
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus, native_enum=False), default=ShipmentStatus.PENDING
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    order: Mapped[Order] = relationship(back_populates="shipments")


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[ReturnStatus] = mapped_column(
        Enum(ReturnStatus, native_enum=False), default=ReturnStatus.REQUESTED
    )
    refund_minor_units: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ------------------------------------------------------------- messaging and telemetry


class Notification(Base):
    """Transactional outbox.

    Rows are written inside the business transaction and dispatched separately, so a
    delivery failure can never roll back an order that was genuinely placed.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    channel: Mapped[str] = mapped_column(String(20), default="email")
    template: Mapped[str] = mapped_column(String(60))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text, default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
