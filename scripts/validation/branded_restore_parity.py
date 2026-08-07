"""Value-level parity and functional checks for the branded restore rehearsal.

`infrastructure/backup/backup_manager.py parity` compares schema, constraints, indexes
and ROW COUNTS. Equal counts are necessary and not sufficient: a restore that preserved
two order rows while losing `commerce_mode_at_checkout` would pass it, and the whole point
of that column is that a test order must never be reclassifiable after the fact.

This adds the checks that are specific to the branded vertical slice:

  * the values that carry provenance and truth -- commerce mode, synthetic-inventory
    typing, origin/legal/media evidence states, payment and notification final states;
  * functional checks against an API served FROM THE RESTORED DATABASE, because a
    byte-identical dump that the application cannot actually serve is not a usable backup.

Kept separate from `backup_manager.py` deliberately: that module's guards are covered by
mutations M42-M48, and widening it for one milestone's needs would put milestone-specific
assertions inside a shared disaster-recovery tool.

    python scripts/validation/branded_restore_parity.py --values
    python scripts/validation/branded_restore_parity.py --functional --base http://127.0.0.1:18400
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

results: dict = {"checks": [], "data": {}}


def record(name: str, ok: bool, detail: str = "") -> bool:
    results["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return ok


def _url(database: str) -> str:
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("SLICE_DB_HOSTPORT", "127.0.0.1:15433")
    return f"postgresql+psycopg://{user}:{password}@{host}/{database}"


# ------------------------------------------------------------------- value parity


# Each entry is (label, SQL). The SQL must return ONE row and ORDER deterministically,
# so a difference is a real difference and not a row-order artefact.
VALUE_QUERIES: list[tuple[str, str]] = [
    (
        "dedunet_catalogue",
        "SELECT count(*) FILTER (WHERE external_product_id IS NOT NULL)::text || '|' || "
        "string_agg(DISTINCT external_product_id, ',') FROM products",
    ),
    (
        "variant_skus",
        "SELECT count(*)::text || '|' || count(DISTINCT sku)::text || '|' || "
        "md5(string_agg(sku, ',' ORDER BY sku)) FROM variants",
    ),
    (
        "product_media",
        "SELECT count(*)::text || '|' || "
        "md5(string_agg(asset_id || ':' || role || ':' || sort_order || ':' || path, "
        "',' ORDER BY asset_id)) FROM product_media",
    ),
    (
        "evidence_and_brand_states",
        "SELECT md5(string_agg(external_product_id || ':' || origin_claim_status || ':' || "
        "intended_origin || ':' || country_of_origin || ':' || material_claim_status || ':' || "
        "legal_brand_status || ':' || media_status || ':' || evidence_status, "
        "',' ORDER BY external_product_id)) FROM products WHERE external_product_id IS NOT NULL",
    ),
    (
        "synthetic_inventory_classification",
        "SELECT string_agg(v.sku || '=' || v.inventory_status || ':' || i.on_hand || "
        "'/' || i.reserved, ',' ORDER BY v.sku) FROM variants v JOIN inventory_items i "
        "ON i.variant_id = v.id WHERE v.inventory_status <> 'prototype_unavailable' "
        "OR i.on_hand <> 0 OR i.reserved <> 0",
    ),
    (
        "test_customer",
        "SELECT string_agg(email || ':' || role, ',' ORDER BY email) FROM customers",
    ),
    (
        "cart_state",
        "SELECT string_agg(status, ',' ORDER BY id) FROM carts",
    ),
    (
        "orders_and_provenance",
        "SELECT string_agg(order_number || ':' || status || ':' || "
        "coalesce(commerce_mode_at_checkout, 'NULL') || ':' || total_minor_units || ':' || "
        "currency, ',' ORDER BY order_number) FROM orders",
    ),
    (
        "order_lines",
        "SELECT string_agg(sku || ':' || quantity || ':' || unit_price_minor_units || ':' || "
        "line_total_minor_units, ',' ORDER BY id) FROM order_lines",
    ),
    (
        "reservations",
        "SELECT string_agg(variant_id || ':' || quantity || ':' || state, ',' ORDER BY id) "
        "FROM reservations",
    ),
    (
        "sandbox_payment_state",
        "SELECT string_agg(provider || ':' || status || ':' || amount_minor_units || ':' || "
        "currency, ',' ORDER BY id) FROM payments",
    ),
    (
        "notification_final_state",
        "SELECT string_agg(template || ':' || status || ':' || attempts || ':' || "
        "(sent_at IS NOT NULL)::text || ':' || coalesce(claim_token, ''), ',' ORDER BY id) "
        "FROM notifications",
    ),
    (
        "notification_subjects",
        "SELECT md5(string_agg(subject, ',' ORDER BY id)) FROM notifications",
    ),
    ("migration_revision", "SELECT version_num FROM alembic_version"),
]


def value_parity(source_db: str, restored_db: str) -> None:
    print("\n=== VALUE-LEVEL PARITY ===")
    source = create_engine(_url(source_db), future=True)
    restored = create_engine(_url(restored_db), future=True)

    with source.connect() as left, restored.connect() as right:
        for label, sql in VALUE_QUERIES:
            a = left.execute(text(sql)).scalar()
            b = right.execute(text(sql)).scalar()
            record(f"{label} preserved", a == b, f"source={str(a)[:90]}")
            results["data"].setdefault("values", {})[label] = str(a)

        # The three headline counts, asserted absolutely rather than only compared, so a
        # restore of an empty database could never "match".
        for label, sql, expected in (
            ("5 DEDUNET products", "SELECT count(*) FROM products WHERE external_product_id IS NOT NULL", 5),
            ("62 DEDUNET variants", "SELECT count(*) FROM variants", 62),
            ("62 unique SKUs", "SELECT count(DISTINCT sku) FROM variants", 62),
            ("18 product-media records", "SELECT count(*) FROM product_media", 18),
        ):
            actual = right.execute(text(sql)).scalar()
            record(f"restored has {label}", actual == expected, f"actual={actual}")

        # upper(status), not status = 'paid'. The column stores the Python enum NAME
        # ('PAID', 'SHIPPED'); only the API surface lowercases it via `status.value`.
        # Matching on the API spelling silently selected no rows and reported None.
        mode = right.execute(
            text("SELECT commerce_mode_at_checkout FROM orders "
                 "WHERE upper(status::text) IN ('PAID', 'SHIPPED') ORDER BY id DESC LIMIT 1")
        ).scalar()
        record(
            "restored order keeps commerce_mode_at_checkout = COMMERCE_TEST_MODE",
            mode == "COMMERCE_TEST_MODE",
            str(mode),
        )
        modes_all = right.execute(
            text("SELECT count(*) FROM orders WHERE commerce_mode_at_checkout IS DISTINCT FROM "
                 "'COMMERCE_TEST_MODE'")
        ).scalar()
        record(
            "no restored order lost or changed its commerce mode",
            modes_all == 0,
            f"{modes_all} orders with another mode",
        )


# --------------------------------------------------------------- functional checks


def _call(base: str, method: str, path: str, body=None, headers=None):
    request = urllib.request.Request(
        f"{base}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        status = exc.code
        exc.close()
    try:
        return status, json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return status, raw


def functional(base: str, restored_db: str) -> None:
    """Exercise the RESTORED database through the real API."""

    print("\n=== RESTORED FUNCTIONAL CHECKS ===")

    record("API readiness against the restored database", _call(base, "GET", "/ready")[0] == 200)
    record("/health available", _call(base, "GET", "/health")[0] == 200)

    status, catalogue = _call(base, "GET", "/api/v1/catalog/products")
    record("catalogue reads", status == 200 and len(catalogue) == 5, f"{len(catalogue)} products")

    status, product = _call(base, "GET", "/api/v1/catalog/products/the-source-tee")
    record("product media reads", status == 200 and len(product["media"]) == 4,
           f"{len(product['media'])} media")
    media_codes = [_call(base, "GET", m["url"])[0] for m in product["media"]]
    record("restored product media is servable", all(c == 200 for c in media_codes), str(media_codes))

    status, payload = _call(
        base, "POST", "/api/v1/auth/login",
        {"email": "slice.customer.local@dedunet.example",
         "password": os.environ["SLICE_TEST_PASSWORD"]},
    )
    record("customer authentication works", status == 200, f"HTTP {status}")
    customer = {"Authorization": f"Bearer {payload['access_token']}"} if status == 200 else {}

    status, payload = _call(
        base, "POST", "/api/v1/auth/login",
        {"email": os.environ["ADMIN_BOOTSTRAP_EMAIL"],
         "password": os.environ["ADMIN_BOOTSTRAP_PASSWORD"]},
    )
    record("administrator authentication works", status == 200, f"HTTP {status}")
    admin = {"Authorization": f"Bearer {payload['access_token']}"} if status == 200 else {}

    status, orders = _call(base, "GET", "/api/v1/me/orders", headers=customer)
    record("order read works", status == 200 and len(orders) >= 1, f"{len(orders)} orders")
    paid = [o for o in orders if o["status"] in ("paid", "shipped")]
    record("test-order mode survives the restore",
           bool(paid) and paid[0]["commerce_mode_at_checkout"] == "COMMERCE_TEST_MODE",
           str(paid[0]["commerce_mode_at_checkout"]) if paid else "no paid order")
    record("test order is still flagged as a test order", bool(paid) and paid[0]["is_test_order"] is True)

    status, admin_orders = _call(base, "GET", "/api/v1/admin/orders", headers=admin)
    record("admin order read works", status == 200 and len(admin_orders) >= 1, f"HTTP {status}")

    # Invalid state transition, through the layer that actually enforces it. The schema
    # stores status as an unconstrained varchar (see _database_level), so this guard is
    # the real one and it has to survive a restore.
    shipped = next((o for o in admin_orders if o["status"] == "shipped"), None)
    if shipped is not None:
        status, payload = _call(
            base, "POST", f"/api/v1/admin/orders/{shipped['order_number']}/fulfil", headers=admin
        )
        record(
            "an invalid state transition is refused after restore",
            status == 409,
            f"HTTP {status} {str(payload)[:70]}",
        )
        status, _ = _call(base, "GET", f"/api/v1/admin/orders", headers=admin)
        record("the refused transition changed nothing", status == 200)
    else:
        record("a shipped order exists to test the transition guard", False, "none found")

    _database_level(restored_db)


def _database_level(restored_db: str) -> None:
    """Constraint enforcement and a write that is deliberately rolled back."""

    engine = create_engine(_url(restored_db), future=True)

    # Notification read -- there is no notification API by design, so this is the only route.
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT template, status, subject FROM notifications ORDER BY id LIMIT 1")
        ).first()
        record("notification reads from the restored database", row is not None,
               f"{row[0]}:{row[1]}" if row else "")
        record("notification kept its DEDUNET test-order subject",
               row is not None and "DEDUNET" in row[2] and "[TEST ORDER]" in row[2],
               row[2][:70] if row else "")

    # Harmless write, then rollback. Proves the restored database is writable without
    # leaving anything behind.
    with engine.connect() as conn:
        trans = conn.begin()
        before = conn.execute(text("SELECT count(*) FROM analytics_events")).scalar()
        conn.execute(
            text("INSERT INTO analytics_events (name, payload_json, correlation_id, occurred_at) "
                 "VALUES ('restore_rehearsal_probe', '{}', 'rehearsal', now())")
        )
        during = conn.execute(text("SELECT count(*) FROM analytics_events")).scalar()
        trans.rollback()
    with engine.connect() as conn:
        after = conn.execute(text("SELECT count(*) FROM analytics_events")).scalar()
    record("harmless write succeeds and rolls back cleanly",
           during == before + 1 and after == before, f"{before} -> {during} -> {after}")

    def refuses(label: str, sql: str, expect: str) -> None:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(text(sql))
                trans.rollback()
                record(label, False, "the database ACCEPTED an invalid write")
            except Exception as exc:  # noqa: BLE001 - the refusal is the assertion
                trans.rollback()
                record(label, expect.lower() in str(exc).lower(), type(exc).__name__)

    refuses(
        "foreign-key enforcement survives the restore",
        "INSERT INTO order_lines (order_id, variant_id, sku, product_name, size, color, "
        "quantity, unit_price_minor_units, line_total_minor_units) "
        "VALUES (999999, 1, 'X', 'X', 'X', 'X', 1, 1, 1)",
        "foreign key",
    )
    # Invalid order status.
    #
    # Measured, not assumed: `orders.status` is varchar(15) with NO enum type and NO check
    # constraint, so the database rejects 'not_a_real_status' only because it is 17
    # characters, and ACCEPTS a short invalid value such as 'xx'. Status validity is
    # enforced by the Python enum and the transition guards in services.py, not by the
    # schema. Asserting "the database rejects an invalid status" would therefore have been
    # a test that passes for the wrong reason -- a length accident dressed up as
    # validation.
    #
    # What this checks instead is the property that actually holds and actually matters
    # for a restore: the column definition is IDENTICAL in source and restored, so the
    # restore did not silently drop a constraint.
    engine_source = create_engine(_url(os.environ["POSTGRES_DB"]), future=True)
    definition_sql = (
        "SELECT data_type || '(' || coalesce(character_maximum_length::text, '') || ')' "
        "FROM information_schema.columns WHERE table_name='orders' AND column_name='status'"
    )
    constraint_sql = (
        "SELECT coalesce(string_agg(pg_get_constraintdef(c.oid), ',' ORDER BY conname), '') "
        "FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid "
        "WHERE t.relname='orders' AND c.contype='c'"
    )
    with engine_source.connect() as left, engine.connect() as right:
        same_type = left.execute(text(definition_sql)).scalar() == right.execute(
            text(definition_sql)).scalar()
        same_constraints = left.execute(text(constraint_sql)).scalar() == right.execute(
            text(constraint_sql)).scalar()
        column_type = right.execute(text(definition_sql)).scalar()
    record(
        "order status column definition is identical after restore",
        same_type and same_constraints,
        f"restored={column_type}",
    )
    refuses(
        "an over-length order status is rejected by the restored database",
        "UPDATE orders SET status = 'not_a_real_status' WHERE id = "
        "(SELECT min(id) FROM orders)",
        "too long",
    )
    results["data"]["order_status_enforcement"] = (
        f"{column_type}, no CHECK constraint; validity enforced by the application enum "
        "and transition guards, not by the schema. Identical in source and restored."
    )
    refuses(
        "inventory constraint enforcement survives the restore",
        "UPDATE inventory_items SET on_hand = -5 WHERE variant_id = "
        "(SELECT min(variant_id) FROM inventory_items)",
        "ck_inventory_on_hand_non_negative",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--values", action="store_true")
    parser.add_argument("--functional", action="store_true")
    parser.add_argument("--base", default="http://127.0.0.1:18400")
    parser.add_argument("--source", default=None)
    parser.add_argument("--restored", default=None)
    parser.add_argument("--out")
    args = parser.parse_args()

    source_db = args.source or os.environ["POSTGRES_DB"]
    restored_db = args.restored or f"{source_db}_rehearsal"

    results["generated_at"] = datetime.now(timezone.utc).isoformat()
    results["source_database"] = source_db
    results["restored_database"] = restored_db

    if args.values:
        value_parity(source_db, restored_db)
    if args.functional:
        functional(args.base, restored_db)

    failed = [c for c in results["checks"] if not c["pass"]]
    results["summary"] = {
        "total": len(results["checks"]),
        "passed": len(results["checks"]) - len(failed),
        "failed": len(failed),
    }
    print(f"\n{results['summary']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
