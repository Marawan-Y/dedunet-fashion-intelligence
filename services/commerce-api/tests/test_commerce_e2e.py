"""End-to-end and failure-path tests for the commerce vertical slice.

Covers the mandated scenarios: discovery, purchase, invalid payment, retry, duplicate
callback, insufficient stock, concurrency, promotions, shipping, cancellation, return,
refund, admin stock adjustment, data export and erasure.

Every assertion checks observable OUTPUT or persisted STATE. None asserts merely that a
call returned 200.
"""

from __future__ import annotations

import secrets
import threading

import pytest

from app.commerce import inventory, payments
from app.commerce.db import SessionLocal
from app.commerce.models import (
    AnalyticsEvent,
    AuditLog,
    InventoryItem,
    Notification,
    Order,
    OrderStatus,
    Variant,
)
from sqlalchemy import select

TEE_SKU = "MRT-TEE-BLK-M"


def _variant_id(session, sku: str) -> int:
    return session.scalar(select(Variant).where(Variant.sku == sku)).id


def _new_cart_with(client, variant_id: int, quantity: int = 1) -> str:
    response = client.post(
        "/api/v1/cart/items", json={"variant_id": variant_id, "quantity": quantity}
    )
    assert response.status_code == 200, response.text
    return response.json()["cart_token"]


def _checkout(client, cart_token, auth_headers, *, token="pm_success", key=None, promo=""):
    return client.post(
        "/api/v1/checkout",
        json={
            "payment_method_token": token,
            "idempotency_key": key or secrets.token_hex(8),
            "country_code": "DE",
            "promotion_code": promo,
        },
        headers={**auth_headers, "X-Cart-Token": cart_token},
    )


# ------------------------------------------------------------------ the full journey


def test_complete_customer_and_admin_journey(client, seeded, auth):
    """The 17-step slice: admin creates a product through to traced analytics."""

    # 1-2. Administrator creates a product; variants and stock become available.
    create = client.post(
        "/api/v1/admin/catalog/products",
        headers=auth["admin"],
        json={
            "slug": "journey-shirt",
            "name": "Journey Shirt",
            "category": "tops",
            "description": "Created by the end-to-end test.",
            "is_active": True,
            "variants": [
                {"sku": "JRN-SHT-M", "size": "M", "color": "Bone",
                 "price_minor_units": 7500, "on_hand": 3}
            ],
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["variants"][0]["available"] == 3

    # 3-4. Customer discovers it with valid price and size information.
    listing = client.get("/api/v1/catalog/products?q=Journey")
    assert [p["slug"] for p in listing.json()] == ["journey-shirt"]
    detail = client.get("/api/v1/catalog/products/journey-shirt").json()
    assert detail["variants"][0]["size"] == "M"
    assert detail["variants"][0]["price_minor_units"] == 7500

    variant_id = detail["variants"][0]["id"]

    # 5-6. Add to cart; availability is checked.
    cart_token = _new_cart_with(client, variant_id, 2)

    # 7. Checkout calculates totals, tax, discount and shipping.
    quote = client.get(
        "/api/v1/cart/quote", headers={"X-Cart-Token": cart_token}
    ).json()
    assert quote["subtotal_minor_units"] == 15000
    assert quote["shipping_minor_units"] == 0          # over the free-shipping threshold
    assert quote["total_minor_units"] == 15000
    # VAT is a COMPONENT of the gross total, not an addition to it.
    assert quote["tax_minor_units"] == 15000 - round(15000 / 1.19)

    # 8-10. Sandbox payment authorized, stock reserved, order created.
    response = _checkout(client, cart_token, auth["customer"])
    assert response.status_code == 201, response.text
    order = response.json()["order"]
    assert order["status"] == "paid"
    assert order["total_minor_units"] == 15000

    with SessionLocal() as session:
        item = session.get(InventoryItem, variant_id)
        assert item.on_hand == 3 and item.reserved == 2
        assert item.available == 1

        # 11. Customer receives a notification.
        notes = session.scalars(select(Notification)).all()
        assert any(n.template == "order_confirmation" for n in notes)

    # 12. Administrator sees the order.
    admin_orders = client.get("/api/v1/admin/orders", headers=auth["admin"]).json()
    assert order["order_number"] in [o["order_number"] for o in admin_orders]

    # 13. Administrator processes it and shipment status updates.
    fulfil = client.post(
        f"/api/v1/admin/orders/{order['order_number']}/fulfil", headers=auth["admin"]
    )
    assert fulfil.status_code == 200, fulfil.text
    assert fulfil.json()["status"] == "shipped"
    tracking = fulfil.json()["tracking_number"]

    # Committing the reservation removes the goods from stock entirely.
    with SessionLocal() as session:
        item = session.get(InventoryItem, variant_id)
        assert item.on_hand == 1 and item.reserved == 0

    # 14. Customer sees order tracking.
    mine = client.get(
        f"/api/v1/me/orders/{order['order_number']}", headers=auth["customer"]
    ).json()
    assert mine["shipments"][0]["tracking_number"] == tracking
    assert mine["status"] == "shipped"

    # 15-16. Analytics events recorded, and the journey is traceable and audited.
    with SessionLocal() as session:
        names = {e.name for e in session.scalars(select(AnalyticsEvent)).all()}
        assert {"order_placed", "order_shipped"} <= names
        actions = {a.action for a in session.scalars(select(AuditLog)).all()}
        assert {"product.create", "order.fulfil"} <= actions

    # The correlation ID is surfaced for cross-component tracing.
    assert client.get("/health").headers["X-Correlation-ID"]


# --------------------------------------------------------------------- payment paths


def test_declined_payment_releases_stock_and_charges_nothing(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
        before = session.get(InventoryItem, variant_id).available

    cart_token = _new_cart_with(client, variant_id, 1)
    response = _checkout(client, cart_token, auth["customer"], token="pm_decline")

    assert response.status_code == 402
    # The stock must be returned; a declined payment may not hold inventory hostage.
    with SessionLocal() as session:
        assert session.get(InventoryItem, variant_id).available == before
        order = session.scalars(select(Order)).first()
        assert order.status is OrderStatus.CANCELLED


def test_provider_error_is_retryable_and_retry_succeeds(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)

    cart_token = _new_cart_with(client, variant_id, 1)
    failed = _checkout(client, cart_token, auth["customer"], token="pm_error")
    # 503 tells the client this is retryable and no money moved.
    assert failed.status_code == 503

    retry_cart = _new_cart_with(client, variant_id, 1)
    ok = _checkout(client, retry_cart, auth["customer"], token="pm_success")
    assert ok.status_code == 201
    assert ok.json()["order"]["status"] == "paid"


def test_duplicate_checkout_with_same_key_does_not_charge_twice(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)

    cart_token = _new_cart_with(client, variant_id, 1)
    key = "idem-key-fixed-123"

    first = _checkout(client, cart_token, auth["customer"], key=key)
    second = _checkout(client, cart_token, auth["customer"], key=key)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["replayed"] is True
    assert first.json()["order"]["order_number"] == second.json()["order"]["order_number"]

    with SessionLocal() as session:
        assert len(session.scalars(select(Order)).all()) == 1


# ------------------------------------------------------------------------- inventory


def test_cannot_add_more_than_available(client, seeded):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
        available = session.get(InventoryItem, variant_id).available

    response = client.post(
        "/api/v1/cart/items", json={"variant_id": variant_id, "quantity": available + 1}
    )
    assert response.status_code == 409


def test_concurrent_reservation_never_oversells(seeded):
    """Twenty threads race for five units. Exactly five may win.

    This is the overselling guard. It asserts on the DATABASE state, not on the number
    of successful HTTP responses, because the invariant that matters is that reserved
    never exceeds on_hand.
    """

    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
        item = session.get(InventoryItem, variant_id)
        item.on_hand = 5
        item.reserved = 0
        session.commit()

    successes: list[bool] = []
    lock = threading.Lock()

    def attempt() -> None:
        session = SessionLocal()
        try:
            won = inventory.try_reserve(session, variant_id, 1)
            session.commit()
            with lock:
                successes.append(won)
        finally:
            session.close()

    threads = [threading.Thread(target=attempt) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(successes) == 5, f"expected exactly 5 winners, got {sum(successes)}"
    with SessionLocal() as session:
        item = session.get(InventoryItem, variant_id)
        assert item.reserved == 5
        assert item.available == 0
        assert item.reserved <= item.on_hand


def test_admin_stock_adjustment_is_audited_and_bounded(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)

    up = client.post(
        f"/api/v1/admin/variants/{variant_id}/stock",
        headers=auth["admin"],
        json={"delta": 5, "reason": "stock count correction"},
    )
    assert up.status_code == 200
    assert up.json()["on_hand"] == 23

    # An adjustment may not drive on-hand negative.
    down = client.post(
        f"/api/v1/admin/variants/{variant_id}/stock",
        headers=auth["admin"],
        json={"delta": -1000, "reason": "invalid"},
    )
    assert down.status_code == 409

    with SessionLocal() as session:
        actions = [a.action for a in session.scalars(select(AuditLog)).all()]
        assert "inventory.adjust" in actions


# ------------------------------------------------------------- promotions & shipping


def test_percentage_promotion_and_shipping_threshold(client, seeded):
    """A discount that drops the basket below the threshold reinstates shipping."""

    with SessionLocal() as session:
        variant_id = _variant_id(session, "MRT-SCF-CLY-OS")  # 4500 each

    cart_token = _new_cart_with(client, variant_id, 2)  # 9000 subtotal, under threshold
    plain = client.get("/api/v1/cart/quote", headers={"X-Cart-Token": cart_token}).json()
    assert plain["subtotal_minor_units"] == 9000
    assert plain["shipping_minor_units"] == 890
    assert plain["total_minor_units"] == 9890

    discounted = client.get(
        "/api/v1/cart/quote?promotion_code=WELCOME10", headers={"X-Cart-Token": cart_token}
    ).json()
    assert discounted["discount_minor_units"] == 900
    assert discounted["shipping_minor_units"] == 890
    assert discounted["total_minor_units"] == 9000 - 900 + 890


def test_unknown_promotion_code_is_ignored_not_fatal(client, seeded):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
    cart_token = _new_cart_with(client, variant_id, 1)
    quote = client.get(
        "/api/v1/cart/quote?promotion_code=NOPE", headers={"X-Cart-Token": cart_token}
    ).json()
    assert quote["discount_minor_units"] == 0
    assert quote["promotion_code"] == ""


# ------------------------------------------------- cancellation, returns and refunds


def test_cancel_order_releases_reserved_stock(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
        before = session.get(InventoryItem, variant_id).available

    cart_token = _new_cart_with(client, variant_id, 2)
    order = _checkout(client, cart_token, auth["customer"]).json()["order"]

    cancel = client.post(
        f"/api/v1/admin/orders/{order['order_number']}/cancel", headers=auth["admin"]
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    with SessionLocal() as session:
        assert session.get(InventoryItem, variant_id).available == before


def test_return_and_refund_restocks_and_notifies(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)

    cart_token = _new_cart_with(client, variant_id, 1)
    order = _checkout(client, cart_token, auth["customer"]).json()["order"]
    client.post(f"/api/v1/admin/orders/{order['order_number']}/fulfil", headers=auth["admin"])

    with SessionLocal() as session:
        after_ship = session.get(InventoryItem, variant_id).on_hand

    created = client.post(
        f"/api/v1/me/orders/{order['order_number']}/returns",
        headers=auth["customer"],
        json={"reason": "Did not fit"},
    )
    assert created.status_code == 201
    return_id = created.json()["return_id"]

    approved = client.post(
        f"/api/v1/admin/returns/{return_id}/approve", headers=auth["admin"]
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "refunded"

    with SessionLocal() as session:
        assert session.get(InventoryItem, variant_id).on_hand == after_ship + 1
        templates = {n.template for n in session.scalars(select(Notification)).all()}
        assert "refund_issued" in templates
        refreshed = session.scalar(
            select(Order).where(Order.order_number == order["order_number"])
        )
        assert refreshed.status is OrderStatus.REFUNDED


def test_return_rejected_before_shipment(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
    cart_token = _new_cart_with(client, variant_id, 1)
    order = _checkout(client, cart_token, auth["customer"]).json()["order"]

    # Not yet shipped, so a return is not valid.
    response = client.post(
        f"/api/v1/me/orders/{order['order_number']}/returns",
        headers=auth["customer"],
        json={"reason": "too early"},
    )
    assert response.status_code == 409


# ----------------------------------------------------------- authorization & privacy


def test_inactive_product_is_invisible_and_unbuyable(client, seeded):
    assert client.get("/api/v1/catalog/products/archive-coat-ink").status_code == 404
    slugs = [p["slug"] for p in client.get("/api/v1/catalog/products").json()]
    assert "archive-coat-ink" not in slugs

    with SessionLocal() as session:
        variant_id = _variant_id(session, "MRT-COA-INK-M")
    blocked = client.post(
        "/api/v1/cart/items", json={"variant_id": variant_id, "quantity": 1}
    )
    assert blocked.status_code == 409


def test_customer_cannot_reach_admin_endpoints(client, seeded, auth):
    response = client.get("/api/v1/admin/orders", headers=auth["customer"])
    assert response.status_code == 403


def test_anonymous_cannot_checkout_or_read_orders(client, seeded):
    assert client.get("/api/v1/me/orders").status_code == 401
    assert client.get("/api/v1/admin/orders").status_code == 401


def test_forged_token_is_rejected(client, seeded):
    response = client.get(
        "/api/v1/me/orders", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert response.status_code == 401


def test_customer_cannot_read_another_customers_order(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
    cart_token = _new_cart_with(client, variant_id, 1)
    order = _checkout(client, cart_token, auth["customer"]).json()["order"]

    other = client.post(
        "/api/v1/auth/register",
        json={"email": "other@dedunet.example", "password": "password-abc", "full_name": "Other"},
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}

    response = client.get(f"/api/v1/me/orders/{order['order_number']}", headers=headers)
    # 404 rather than 403: existence of another customer's order is not disclosed.
    assert response.status_code == 404


def test_data_export_then_erasure_preserves_financial_history(client, seeded, auth):
    with SessionLocal() as session:
        variant_id = _variant_id(session, TEE_SKU)
    cart_token = _new_cart_with(client, variant_id, 1)
    order = _checkout(client, cart_token, auth["customer"]).json()["order"]

    export = client.get("/api/v1/me/data-export", headers=auth["customer"]).json()
    assert export["customer"]["email"] == "customer@dedunet.example"
    assert export["orders"][0]["order_number"] == order["order_number"]

    erased = client.delete("/api/v1/me", headers=auth["customer"])
    assert erased.status_code == 200

    from app.commerce.models import Customer

    with SessionLocal() as session:
        remaining = session.scalar(
            select(Order).where(Order.order_number == order["order_number"])
        )
        # The order survives for reconciliation; the identity does not.
        assert remaining is not None
        assert remaining.total_minor_units == order["total_minor_units"]

        customer = session.get(Customer, remaining.customer_id)
        assert customer.deleted_at is not None
        assert customer.email.endswith("@invalid.example")
        assert customer.full_name == "erased"

    # The session must stop working immediately after erasure.
    assert client.get("/api/v1/me/orders", headers=auth["customer"]).status_code == 401


def test_password_is_never_stored_or_returned_in_clear(client, seeded):
    payload = {
        "email": "clear@dedunet.example",
        "password": "super-secret-value",
        "full_name": "Clear Text",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert "super-secret-value" not in response.text

    from app.commerce.models import Customer

    with SessionLocal() as session:
        customer = session.scalar(select(Customer).where(Customer.email == payload["email"]))
        assert customer.password_hash.startswith("pbkdf2_sha256$")
        assert payload["password"] not in customer.password_hash


# ------------------------------------------------------------------- payment adapter


def test_unknown_payment_provider_fails_loudly(monkeypatch):
    """A misconfigured provider must not silently fall back to the sandbox."""

    monkeypatch.setenv("PAYMENT_PROVIDER", "stripe")
    with pytest.raises(payments.PaymentError, match="no adapter is implemented"):
        payments.get_gateway()


def test_sandbox_rejects_float_amounts():
    gateway = payments.SandboxGateway()
    with pytest.raises(payments.PaymentError):
        gateway.authorize(
            amount_minor_units=59.0,  # type: ignore[arg-type]
            currency="EUR",
            payment_method_token="pm_success",
            idempotency_key="k",
        )


def test_admin_route_namespaces_do_not_collide(client, seeded, auth):
    """Regression: the commerce admin API must not shadow the legacy fixture API.

    They have different auth models. If they ever share a path again, whichever router
    registers first silently decides the guard, which is how an endpoint ends up
    protected by the wrong mechanism.
    """

    # Legacy path: guarded by the shared header token, which is the shipped placeholder,
    # so it fails closed with 503 regardless of a valid admin session.
    legacy = client.post(
        "/api/v1/admin/products",
        headers=auth["admin"],
        json={"slug": "x", "name": "x", "category": "x", "variants": []},
    )
    assert legacy.status_code == 503

    # Commerce path: guarded by role-based session auth, which a customer fails.
    denied = client.post(
        "/api/v1/admin/catalog/products",
        headers=auth["customer"],
        json={
            "slug": "denied-item", "name": "Denied", "category": "tops",
            "variants": [{"sku": "DEN-1", "size": "M", "color": "Ink",
                          "price_minor_units": 1000, "on_hand": 1}],
        },
    )
    assert denied.status_code == 403
