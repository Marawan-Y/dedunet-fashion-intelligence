"""DEDUNET integration-closure guards.

Asset serving, legacy-catalogue isolation, synthetic test inventory, order provenance and
notification identity.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BRAND = REPO / "packages" / "brand"

from app.commerce import modes, synthetic_inventory  # noqa: E402
from app.commerce.models import InventoryItem, Product, ProductMedia, Variant  # noqa: E402


# ------------------------------------------------------------------- asset serving

def test_every_product_media_url_resolves(client):
    import json

    media = json.loads((BRAND / "product-media.json").read_text(encoding="utf-8"))
    assert len(media) == 18

    for record in media:
        response = client.get(record["url"])
        assert response.status_code == 200, record["url"]
        assert response.headers["content-type"].startswith("image/svg+xml")
        # Prototype SVGs are active content; a browser must not re-interpret the type.
        assert response.headers["x-content-type-options"] == "nosniff"


def test_every_brand_asset_resolves(client):
    import json

    assets = json.loads((BRAND / "assets.json").read_text(encoding="utf-8"))
    assert len(assets) == 31
    assert all(client.get(a["url"]).status_code == 200 for a in assets)


@pytest.mark.parametrize(
    "path",
    [
        "../../../../etc/passwd",
        "..%2f..%2fbrand.json",
        "../brand.json",
        ".env",
        "assets/../../../.git/config",
        "assets/brand-prototype/logos",          # a directory, not a listing
        "",                                       # the root itself
        "assets/brand-prototype/logos/nope.svg",  # missing
    ],
)
def test_unsafe_or_missing_media_paths_are_refused(client, path):
    assert client.get(f"/api/v1/media/{path}").status_code in (404, 405)


def test_media_route_never_serves_a_non_image(client):
    # tokens.css lives in packages/brand but is not under assets/ and is not an allowed type.
    for path in ("../tokens.css", "../products.json", "../NORMALIZATION_REPORT.json"):
        assert client.get(f"/api/v1/media/{path}").status_code == 404


def test_committed_svgs_pass_the_safety_validator():
    sys.path.insert(0, str(REPO / "scripts" / "brand"))
    from build_brand_package import validate_svg

    svgs = sorted((BRAND / "assets").rglob("*.svg"))
    assert len(svgs) == 30, f"expected 30 committed SVGs, found {len(svgs)}"

    unsafe = {p.name: problems for p in svgs if (problems := validate_svg(p))}
    assert unsafe == {}


def test_safety_validator_rejects_active_content(tmp_path):
    """The validator must actually reject; a validator that passes everything is not one."""

    sys.path.insert(0, str(REPO / "scripts" / "brand"))
    from build_brand_package import validate_svg

    cases = {
        "script": '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        "handler": '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)"/></svg>',
        "foreign": '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
        "external": '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/x.png"/></svg>',
        "jsurl": '<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"/></svg>',
    }
    for name, body in cases.items():
        target = tmp_path / f"{name}.svg"
        target.write_text(body, encoding="utf-8")
        assert validate_svg(target), f"{name} was accepted but must be rejected"


# --------------------------------------------------------- legacy-catalogue isolation

@pytest.fixture()
def dedunet_catalogue(db_session):
    """Five DEDUNET products alongside the legacy MERET seed."""

    for index in range(5):
        product = Product(
            external_product_id=f"DDN-X{index}",
            slug=f"ddn-product-{index}",
            name=f"DEDUNET Product {index}",
            category="tops",
            currency="EUR",
            country_of_origin="XX",
            intended_origin="EG",
            is_active=True,
            sellable=False,
            publication_status="preview",
            inventory_status="prototype_unavailable",
            origin_claim_status="UNVERIFIED",
        )
        db_session.add(product)
        db_session.flush()
        variant = Variant(
            product_id=product.id,
            external_variant_id=f"DDN-X{index}-M",
            sku=f"DDN-X{index}-M",
            size="M",
            color="Ink",
            price_minor_units=7200,
            sellable=False,
            inventory_status="prototype_unavailable",
        )
        db_session.add(variant)
        db_session.flush()
        db_session.add(InventoryItem(variant_id=variant.id, on_hand=0, reserved=0))
    db_session.commit()
    return db_session


def test_preview_mode_shows_only_dedunet_products(client, dedunet_catalogue, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    body = client.get("/api/v1/catalog/products").json()

    assert len(body) == 5
    assert all(p["external_product_id"] is not None for p in body)
    # The legacy fixture must not leak into the DEDUNET catalogue.
    assert not any(p["slug"] == "oversized-crew-tee-black" for p in body)


def test_commerce_test_mode_still_shows_the_legacy_demo_catalogue(
    client, dedunet_catalogue, monkeypatch
):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    slugs = {p["slug"] for p in client.get("/api/v1/catalog/products").json()}
    assert "oversized-crew-tee-black" in slugs
    assert "ddn-product-0" in slugs


def test_legacy_product_is_not_reachable_by_direct_url_in_preview(
    client, dedunet_catalogue, monkeypatch
):
    # A filter the deep link walks around is not a filter.
    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    assert client.get("/api/v1/catalog/products/oversized-crew-tee-black").status_code == 404
    assert client.get("/api/v1/catalog/products/ddn-product-0").status_code == 200


# ----------------------------------------------------------- synthetic test inventory

def test_synthetic_inventory_refuses_preview_mode(db_session, dedunet_catalogue, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    with pytest.raises(synthetic_inventory.TestInventoryRefused, match="only permitted"):
        synthetic_inventory.load_test_inventory(db_session, confirmed=True)


def test_synthetic_inventory_refuses_public_mode(db_session, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", "PUBLIC_COMMERCE_MODE")
    with pytest.raises(modes.CommerceModeError):
        synthetic_inventory.load_test_inventory(db_session, confirmed=True)


def test_synthetic_inventory_refuses_without_confirmation(db_session, dedunet_catalogue, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    with pytest.raises(synthetic_inventory.TestInventoryRefused, match="confirm-test-only"):
        synthetic_inventory.load_test_inventory(db_session, confirmed=False)


def test_synthetic_inventory_loads_and_is_typed(db_session, dedunet_catalogue, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    result = synthetic_inventory.load_test_inventory(db_session, confirmed=True, quantity=10)

    assert result.variants_touched == 5
    assert result.units_loaded == 50

    variant = db_session.query(Variant).filter_by(external_variant_id="DDN-X0-M").one()
    # Typed, not implied. Nothing infers "test data" from a quantity or a naming convention.
    assert variant.inventory_status == synthetic_inventory.SYNTHETIC_STATUS
    assert variant.sellable is True


def test_synthetic_inventory_is_idempotent(db_session, dedunet_catalogue, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    synthetic_inventory.load_test_inventory(db_session, confirmed=True, quantity=10)
    synthetic_inventory.load_test_inventory(db_session, confirmed=True, quantity=10)

    variant = db_session.query(Variant).filter_by(external_variant_id="DDN-X0-M").one()
    item = db_session.query(InventoryItem).filter_by(variant_id=variant.id).one()
    # Set, never accumulate: a second run must not double the stock.
    assert item.on_hand == 10


def test_cleanup_restores_the_prototype_default(db_session, dedunet_catalogue, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    synthetic_inventory.load_test_inventory(db_session, confirmed=True, quantity=10)
    synthetic_inventory.clear_test_inventory(db_session, confirmed=True)

    variant = db_session.query(Variant).filter_by(external_variant_id="DDN-X0-M").one()
    item = db_session.query(InventoryItem).filter_by(variant_id=variant.id).one()
    assert item.on_hand == 0
    assert variant.sellable is False
    assert variant.inventory_status == synthetic_inventory.PROTOTYPE_STATUS


def test_synthetic_inventory_never_touches_evidence_or_origin(
    db_session, dedunet_catalogue, monkeypatch
):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    synthetic_inventory.load_test_inventory(db_session, confirmed=True)

    product = db_session.query(Product).filter_by(external_product_id="DDN-X0").one()
    assert product.origin_claim_status == "UNVERIFIED"
    assert product.country_of_origin == "XX"
    assert product.intended_origin == "EG"


def test_synthetic_stock_is_still_unbuyable_in_preview_without_cleanup(
    db_session, dedunet_catalogue, monkeypatch
):
    """The whole point of computing effective sellability at request time.

    Switching to preview must block checkout IMMEDIATELY, with no database cleanup and no
    window in which rows carrying synthetic stock are still purchasable.
    """

    from app.commerce import services

    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    synthetic_inventory.load_test_inventory(db_session, confirmed=True, quantity=10)
    variant = db_session.query(Variant).filter_by(external_variant_id="DDN-X0-M").one()

    cart = services.get_or_create_cart(db_session, token=None, customer_id=None)
    services.add_to_cart(db_session, cart, variant_id=variant.id, quantity=1)
    assert len(cart.lines) == 1

    # Flip the mode. Nothing in the database changes.
    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    cart2 = services.get_or_create_cart(db_session, token=None, customer_id=None)
    with pytest.raises(services.DomainError, match="brand preview"):
        services.add_to_cart(db_session, cart2, variant_id=variant.id, quantity=1)


def test_unknown_sku_is_refused_rather_than_loading_nothing(
    db_session, dedunet_catalogue, monkeypatch
):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    with pytest.raises(synthetic_inventory.TestInventoryRefused, match="unknown DEDUNET SKUs"):
        synthetic_inventory.load_test_inventory(
            db_session, confirmed=True, skus=["DDN-X0-M", "NO-SUCH-SKU"]
        )


# ------------------------------------------------------------------ order provenance

def test_new_order_records_the_commerce_mode(client, seeded, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)

    token = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@dedunet.example", "password": "demo-password-123"},
    ).json()["access_token"]

    cart = client.get("/api/v1/cart").json()
    variant_id = client.get("/api/v1/catalog/products").json()[0]["variants"][0]["id"]
    client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant_id, "quantity": 1},
        headers={"X-Cart-Token": cart["cart_token"]},
    )

    body = client.post(
        "/api/v1/checkout",
        json={"payment_method_token": "pm_success", "idempotency_key": "closure-test-key-1"},
        headers={"X-Cart-Token": cart["cart_token"], "Authorization": f"Bearer {token}"},
    ).json()

    assert body["order"]["commerce_mode_at_checkout"] == "COMMERCE_TEST_MODE"
    assert body["order"]["is_test_order"] is True


def test_order_model_defaults_to_legacy_unclassified(db_session, seeded):
    """Orders predating modes must not be backfilled as public commerce."""

    from app.commerce.models import Order, OrderStatus

    order = Order(
        order_number="FC-LEGACY1",
        customer_id=db_session.query(Product).first().id,
        status=OrderStatus.PAID,
        currency="EUR",
        subtotal_minor_units=100,
        discount_minor_units=0,
        shipping_minor_units=0,
        tax_minor_units=0,
        total_minor_units=100,
        idempotency_key="legacy-key-1",
    )
    db_session.add(order)
    db_session.flush()
    assert order.commerce_mode_at_checkout == "LEGACY_UNCLASSIFIED"
    assert order.commerce_mode_at_checkout != "PUBLIC_COMMERCE_MODE"


# --------------------------------------------------------------- notification identity

def test_order_notifications_carry_the_dedunet_identity(client, seeded, monkeypatch):
    from app.commerce.models import Notification

    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@dedunet.example", "password": "demo-password-123"},
    ).json()["access_token"]

    cart = client.get("/api/v1/cart").json()
    variant_id = client.get("/api/v1/catalog/products").json()[0]["variants"][0]["id"]
    client.post(
        "/api/v1/cart/items",
        json={"variant_id": variant_id, "quantity": 1},
        headers={"X-Cart-Token": cart["cart_token"]},
    )
    client.post(
        "/api/v1/checkout",
        json={"payment_method_token": "pm_success", "idempotency_key": "closure-notify-key-1"},
        headers={"X-Cart-Token": cart["cart_token"], "Authorization": f"Bearer {token}"},
    )

    note = seeded.query(Notification).order_by(Notification.id.desc()).first()
    assert note is not None
    assert "DEDUNET" in note.subject
    # A test order that reads like a real confirmation is the one notification defect a
    # customer cannot detect for themselves.
    assert "[TEST ORDER]" in note.subject
    assert "MERET" not in note.subject.upper()


# ------------------------------------------------------------ brand-package drift

def test_brand_package_has_no_drift():
    result = subprocess.run(
        [sys.executable, "-B", "scripts/brand/build_brand_package.py", "--verify-no-drift"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "BRAND_PACKAGE_NO_DRIFT" in result.stdout


# ------------------------------------------------------------ active legacy brand scan

def test_no_active_customer_facing_legacy_brand():
    """Active client surfaces must not display the legacy brand.

    Scoped to what a customer or operator actually sees. Historical evidence, test fixtures
    and the storage-key migration are deliberately excluded and classified in
    docs/side-b/DEDUNET_REBRAND_MIGRATION_REGISTER.md.
    """

    import re

    surfaces = [
        REPO / "apps" / "web" / "index.html",
        REPO / "apps" / "web" / "app.js",
        REPO / "apps" / "web" / "styles.css",
        REPO / "apps" / "admin" / "index.html",
        REPO / "apps" / "admin" / "admin.js",
        REPO / "apps" / "admin" / "styles.css",
    ]
    assert all(p.is_file() for p in surfaces), "a scanned surface is missing"

    pattern = re.compile(r"\bMERET\b|\bMERYT\b", re.IGNORECASE)
    offenders = []
    for path in surfaces:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not pattern.search(line):
                continue
            # The one permitted class: the one-time storage-key migration, which must name
            # the old keys in order to move them.
            if "meret_cart" in line or "meret_token" in line or "meret_role" in line:
                continue
            if "meret_admin_token" in line or "legacy brand prefix" in line:
                continue
            offenders.append(f"{path.name}:{number}: {line.strip()[:70]}")

    assert offenders == []
