"""The wire format for timestamps must not depend on which database is behind it.

SQLite has no timestamp type. It ignores ``DateTime(timezone=True)`` and hands back a
NAIVE datetime. PostgreSQL stores TIMESTAMPTZ and hands back an AWARE one. Without
normalisation the same order serialises as ``...T10:00:00`` on one engine and
``...T10:00:00+00:00`` on the other, and any client doing arithmetic on the parsed value
silently gets a different answer.

These tests fail on SQLite if ``as_utc`` is removed, so they are load-bearing on the
engine the suite runs on by default — not only on the one it rarely runs on.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.commerce.db import SessionLocal
from app.commerce.models import Customer, Order, as_utc

COMMERCE_DIR = Path(__file__).resolve().parents[1] / "app" / "commerce"

# Columns whose values come back from the database and therefore carry the naive/aware
# divergence. Ordering comparisons on these must go through as_utc().
STORED_DATETIME_ATTRS = {
    "created_at", "placed_at", "sent_at", "occurred_at", "at",
    "deleted_at", "consent_recorded_at", "updated_at", "valid_from", "valid_to",
}


def _checkout(client, auth, seeded):
    from app.commerce.models import Variant
    import secrets

    with SessionLocal() as session:
        variant_id = session.scalar(
            select(Variant).where(Variant.sku == "MRT-TEE-BLK-M")
        ).id
    cart = client.post(
        "/api/v1/cart/items", json={"variant_id": variant_id, "quantity": 1}
    ).json()
    response = client.post(
        "/api/v1/checkout",
        json={
            "payment_method_token": "pm_success",
            "idempotency_key": secrets.token_hex(8),
            "country_code": "DE",
            "promotion_code": "",
        },
        headers={**auth["customer"], "X-Cart-Token": cart["cart_token"]},
    )
    assert response.status_code == 201, response.text
    return response.json()["order"]


def test_placed_at_is_serialized_with_an_explicit_utc_offset(client, seeded, auth):
    """Fails on SQLite without as_utc, and keeps passing on PostgreSQL.

    The order is re-fetched rather than read from the checkout response. That matters:
    the checkout response serialises the in-memory object whose ``placed_at`` is still
    the aware value ``utcnow()`` produced, so it carries an offset even without
    normalisation. Only a value READ BACK from the database exhibits the divergence.
    An earlier version of this test asserted on the checkout response and survived
    deleting as_utc entirely — it proved nothing.
    """

    created = _checkout(client, auth, seeded)
    order = client.get(
        f"/api/v1/me/orders/{created['order_number']}", headers=auth["customer"]
    ).json()
    placed_at = order["placed_at"]

    assert placed_at is not None
    assert placed_at.endswith("+00:00"), (
        f"timestamp {placed_at!r} carries no UTC offset; a client cannot tell what "
        "zone it is in, and the value differs by engine"
    )
    parsed = datetime.fromisoformat(placed_at)
    assert parsed.tzinfo is not None
    # Sanity: the order was placed just now, not at an epoch or a local-time offset.
    assert abs(datetime.now(timezone.utc) - parsed) < timedelta(minutes=5)


def test_data_export_timestamps_carry_offsets(client, seeded, auth):
    _checkout(client, auth, seeded)
    export = client.get("/api/v1/me/data-export", headers=auth["customer"]).json()

    assert export["customer"]["created_at"].endswith("+00:00")
    assert export["orders"][0]["placed_at"].endswith("+00:00")


def test_as_utc_normalises_naive_and_preserves_aware() -> None:
    naive = datetime(2026, 8, 3, 12, 0, 0)
    assert as_utc(naive) == datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)

    aware = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)
    assert as_utc(aware) == aware

    # A non-UTC aware value is converted, not merely relabelled.
    plus_two = datetime(2026, 8, 3, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert as_utc(plus_two) == datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)

    assert as_utc(None) is None


def test_no_stored_timestamp_is_ordered_without_normalisation() -> None:
    """Structural guard against reintroducing the divergence.

    An ordering comparison against a column read from the database is exactly what breaks
    when the engine changes. ``is None`` / ``is not None`` checks stay legal because they
    are unaffected by tzinfo.
    """

    offenders: list[str] = []
    for path in sorted(COMMERCE_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            if not any(isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)) for op in node.ops):
                continue
            for side in [node.left, *node.comparators]:
                if isinstance(side, ast.Attribute) and side.attr in STORED_DATETIME_ATTRS:
                    offenders.append(f"{path.name}:{side.lineno} orders on .{side.attr}")

    assert not offenders, (
        "stored timestamps ordered without as_utc(); this works on one engine and "
        "raises TypeError on the other:\n  " + "\n  ".join(offenders)
    )


def test_erasure_preserves_financial_records(client, seeded, auth):
    """Pseudonymisation must not delete orders, on either engine.

    PostgreSQL enforces foreign keys unconditionally, while SQLite only does so because
    of a PRAGMA set per connection. If erasure ever became a hard delete, PostgreSQL
    would refuse it outright — and the accounting history it protects would be at risk on
    SQLite, which is the engine the suite runs on by default.
    """

    order = _checkout(client, auth, seeded)

    assert client.delete("/api/v1/me", headers=auth["customer"]).status_code == 200

    with SessionLocal() as session:
        retained = session.scalar(
            select(Order).where(Order.order_number == order["order_number"])
        )
        assert retained is not None, "order was deleted by erasure"
        assert retained.total_minor_units == order["total_minor_units"]
        assert len(retained.lines) == len(order["lines"])

        customer = session.get(Customer, retained.customer_id)
        assert customer is not None, "customer row was hard-deleted"
        assert customer.deleted_at is not None
        assert customer.email.endswith("@invalid.example")
        assert customer.full_name == "erased"
        assert customer.addresses == []

    # The session must stop working immediately.
    assert client.get("/api/v1/me/orders", headers=auth["customer"]).status_code == 401
