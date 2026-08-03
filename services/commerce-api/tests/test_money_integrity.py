"""Authoritative money integrity tests (SB-AR-B3-003).

Contract under test
-------------------
1. Authoritative monetary values are stored and calculated as INTEGER MINOR UNITS.
2. A binary float is never an accepted authoritative money input and never appears
   on the authoritative path (fixture ingestion, catalog, quote, stylist total).
3. Decimal business amounts convert exactly, or the conversion is rejected. There is
   no silent rounding of excess fractional precision.
4. Any decimal value still emitted on the wire is DERIVED FROM the integer minor
   units for display compatibility and is never the source of arithmetic.

These tests were written before the implementation existed (red stage) and are the
acceptance criteria for removing the float money path from the PoC.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.catalog import CatalogRepository
from app.config import settings
from app.main import app
from app.money import (
    FloatMoneyRejected,
    from_minor_units,
    sum_line_totals,
    to_minor_units,
)
from app.schemas import OrderQuote, Product

client = TestClient(app)

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "products.json"


def _base_product(**overrides: object) -> dict:
    payload = {
        "id": "test-money-001",
        "slug": "test-money-product",
        "name": "Money Test Product",
        "category": "t-shirt",
        "collection": "Test",
        "description": "Synthetic fixture used only by the money integrity tests.",
        "fibre_composition": "100% cotton",
        "made_in": "Egypt",
        "image_url": "https://example.invalid/placeholder.png",
        "variants": [{"sku": "TEST-MONEY-001-S", "size": "S", "color": "Black", "stock": 1}],
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------------------
# 1. Conversion primitives
# --------------------------------------------------------------------------------------


def test_to_minor_units_rejects_binary_float() -> None:
    """A binary float must never be silently accepted as authoritative money."""

    with pytest.raises(FloatMoneyRejected):
        to_minor_units(59.0, "EUR")
    with pytest.raises(FloatMoneyRejected):
        to_minor_units(0.1 + 0.2, "EUR")


def test_to_minor_units_converts_decimal_and_string_exactly() -> None:
    assert to_minor_units(Decimal("59.00"), "EUR") == 5900
    assert to_minor_units("8.90", "EUR") == 890
    assert to_minor_units(Decimal("139"), "EUR") == 13900
    assert to_minor_units(0, "EUR") == 0
    assert to_minor_units(5900, "EUR", already_minor=True) == 5900


def test_to_minor_units_rejects_excess_fractional_precision() -> None:
    """EUR has two minor digits; 59.005 must fail rather than round silently."""

    with pytest.raises(ValueError):
        to_minor_units(Decimal("59.005"), "EUR")
    with pytest.raises(ValueError):
        to_minor_units("0.001", "EUR")


def test_to_minor_units_rejects_unknown_currency() -> None:
    with pytest.raises(ValueError):
        to_minor_units(Decimal("1.00"), "XXZ")


def test_from_minor_units_round_trips_exactly() -> None:
    assert from_minor_units(5900, "EUR") == Decimal("59.00")
    assert from_minor_units(890, "EUR") == Decimal("8.90")
    for minor in (0, 1, 99, 100, 5900, 13900, 999999):
        assert to_minor_units(from_minor_units(minor, "EUR"), "EUR") == minor


# --------------------------------------------------------------------------------------
# 2. Schema boundary
# --------------------------------------------------------------------------------------


def test_product_schema_stores_integer_minor_units() -> None:
    product = Product.model_validate(_base_product(price_minor_units=5900, currency="EUR"))
    assert product.price_minor_units == 5900
    assert isinstance(product.price_minor_units, int)
    assert product.currency == "EUR"


def test_product_schema_rejects_binary_float_price() -> None:
    """`price_eur: 59.0` parsed by plain json is a binary float and must be rejected."""

    with pytest.raises(ValidationError):
        Product.model_validate(_base_product(price_eur=59.0))


def test_product_schema_accepts_exact_decimal_legacy_price() -> None:
    """The legacy decimal key is accepted only as an exact Decimal/string, not a float."""

    product = Product.model_validate(_base_product(price_eur=Decimal("59.00")))
    assert product.price_minor_units == 5900
    product_from_string = Product.model_validate(_base_product(price_eur="139.00"))
    assert product_from_string.price_minor_units == 13900


def test_product_schema_rejects_non_integer_minor_units() -> None:
    with pytest.raises(ValidationError):
        Product.model_validate(_base_product(price_minor_units=5900.0))
    with pytest.raises(ValidationError):
        Product.model_validate(_base_product(price_minor_units=0))


def test_product_display_price_is_derived_not_authoritative() -> None:
    product = Product.model_validate(_base_product(price_minor_units=5900))
    dumped = product.model_dump(mode="json")
    assert dumped["price_minor_units"] == 5900
    assert Decimal(str(dumped["price_display"])) == Decimal("59.00")


# --------------------------------------------------------------------------------------
# 3. Fixture ingestion
# --------------------------------------------------------------------------------------


def test_catalog_fixture_never_produces_binary_float() -> None:
    """Reading the preserved fixture must not create a binary float anywhere."""

    repo = CatalogRepository(FIXTURE)
    raw = repo.read_raw()

    def walk(node: object, path: str) -> None:
        if isinstance(node, float):
            raise AssertionError(f"binary float found at {path}: {node!r}")
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(raw, "products.json")

    for product in repo.list_products(active_only=False):
        assert isinstance(product.price_minor_units, int)


def test_preserved_fixture_prices_convert_exactly() -> None:
    """The original fixture file itself is unchanged and still convertible exactly."""

    raw = json.loads(FIXTURE.read_text(encoding="utf-8"), parse_float=Decimal)
    minor_by_id = {item["id"]: to_minor_units(item["price_eur"], "EUR") for item in raw}
    assert minor_by_id == {
        "prod-nile-tee-001": 5900,
        "prod-desert-abaya-001": 13900,
        "prod-cairo-shirt-001": 8900,
    }


# --------------------------------------------------------------------------------------
# 4. Configuration
# --------------------------------------------------------------------------------------


def test_shipping_configuration_is_integer_minor_units() -> None:
    assert isinstance(settings.default_shipping_minor_units, int)
    assert isinstance(settings.free_shipping_threshold_minor_units, int)
    assert settings.default_shipping_minor_units == 890
    assert settings.free_shipping_threshold_minor_units == 10000


# --------------------------------------------------------------------------------------
# 5. Quote arithmetic
# --------------------------------------------------------------------------------------


def test_quote_totals_are_exact_in_minor_units() -> None:
    """One 59.00 tee: below the 100.00 free-shipping threshold, so 8.90 is charged."""

    response = client.post(
        "/api/v1/orders/quote",
        json={
            "items": [{"sku": "ORG01-TEE-NILE-BLK-M", "quantity": 1}],
            "destination_country": "DE",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["subtotal_minor_units"] == 5900
    assert payload["shipping_minor_units"] == 890
    assert payload["total_minor_units"] == 6790
    assert payload["currency"] == "EUR"
    assert (
        payload["total_minor_units"]
        == payload["subtotal_minor_units"] + payload["shipping_minor_units"]
    )


def test_quote_free_shipping_threshold_uses_integer_comparison() -> None:
    """59.00 + 89.00 = 148.00 crosses the 100.00 threshold exactly in minor units."""

    response = client.post(
        "/api/v1/orders/quote",
        json={
            "items": [
                {"sku": "ORG01-TEE-NILE-BLK-M", "quantity": 1},
                {"sku": "ORG01-SHT-CAI-OFF-M", "quantity": 1},
            ],
            "destination_country": "DE",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["subtotal_minor_units"] == 14800
    assert payload["shipping_minor_units"] == 0
    assert payload["total_minor_units"] == 14800


def test_quote_repeated_small_quantities_do_not_accumulate_error() -> None:
    """18 x 59.00 must be exactly 1062.00; a float accumulation path drifts here."""

    response = client.post(
        "/api/v1/orders/quote",
        json={
            "items": [{"sku": "ORG01-TEE-NILE-BLK-M", "quantity": 18}],
            "destination_country": "DE",
        },
    )
    assert response.status_code == 200
    assert response.json()["subtotal_minor_units"] == 106200


def test_quote_rejects_quantity_above_fixture_stock() -> None:
    """Stock for the tee fixture is 18; 19 must fail closed, not silently clamp."""

    response = client.post(
        "/api/v1/orders/quote",
        json={
            "items": [{"sku": "ORG01-TEE-NILE-BLK-M", "quantity": 19}],
            "destination_country": "DE",
        },
    )
    assert response.status_code == 409


def test_line_total_summation_is_exact_where_a_float_path_drifts() -> None:
    """Adversarial amounts where the naive `major = minor/100` path is provably wrong.

    EUR 0.70 x 3 is exactly 210 minor units. Computed through binary floats,
    ``0.70 * 3 * 100`` evaluates to 209.99999999999997 and truncates to 209.
    """

    adversarial: list[tuple[int, int]] = [(70, 3)]
    assert sum_line_totals(adversarial) == 210

    naive_float_result = int((70 / 100) * 3 * 100)
    assert naive_float_result == 209
    assert naive_float_result != sum_line_totals(adversarial)

    # A broader sweep: integer arithmetic must be exact for every combination.
    for unit_minor in (1, 7, 70, 99, 890, 2999, 5900, 13900, 999_999):
        for quantity in (1, 3, 7, 11, 20):
            assert sum_line_totals([(unit_minor, quantity)]) == unit_minor * quantity


def test_line_total_summation_rejects_float_unit_price() -> None:
    with pytest.raises(FloatMoneyRejected):
        sum_line_totals([(59.0, 1)])


def test_quote_wire_field_rejects_float_subtotal() -> None:
    """The wire contract itself refuses a float, independent of how it was computed."""

    with pytest.raises(ValidationError):
        OrderQuote(
            currency="EUR",
            subtotal_minor_units=5900.0,
            shipping_minor_units=890,
            total_minor_units=6790,
            note="test",
        )


def test_quote_display_values_are_derived_from_minor_units() -> None:
    response = client.post(
        "/api/v1/orders/quote",
        json={
            "items": [{"sku": "ORG01-TEE-NILE-BLK-M", "quantity": 1}],
            "destination_country": "DE",
        },
    )
    payload = response.json()
    assert Decimal(str(payload["subtotal_display"])) == from_minor_units(
        payload["subtotal_minor_units"], "EUR"
    )
    assert Decimal(str(payload["total_display"])) == from_minor_units(
        payload["total_minor_units"], "EUR"
    )


# --------------------------------------------------------------------------------------
# 6. Stylist totals
# --------------------------------------------------------------------------------------


def test_stylist_total_is_integer_minor_units_and_respects_budget() -> None:
    response = client.post(
        "/api/v1/stylist/recommend",
        json={
            "occasion": "summer city dinner",
            "preferred_colors": ["Black", "Off White"],
            "preferred_categories": ["t-shirt", "shirt"],
            "budget_eur": "160.00",
            "style_notes": "eastern streetwear",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["total_minor_units"], int)
    assert payload["total_minor_units"] <= 16000
    assert payload["total_minor_units"] == 5900 + 8900


def test_stylist_rejects_excess_precision_budget() -> None:
    response = client.post(
        "/api/v1/stylist/recommend",
        json={
            "occasion": "test",
            "preferred_colors": [],
            "preferred_categories": [],
            "budget_eur": "160.005",
            "style_notes": "",
        },
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------------------
# 7. No float money remains on the authoritative source path
# --------------------------------------------------------------------------------------


def test_no_float_money_symbols_remain_in_backend_source() -> None:
    """Guards against reintroducing `price_eur: float`-style authoritative fields."""

    app_dir = Path(__file__).resolve().parents[1] / "app"
    banned = (
        "price_eur: float",
        "subtotal: float",
        "shipping: float",
        "total: float",
        "total_eur: float",
        "default_shipping_eur: float",
        "free_shipping_threshold_eur: float",
    )
    offenders: list[str] = []
    for source in sorted(app_dir.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        for needle in banned:
            if needle in text:
                offenders.append(f"{source.name}: {needle}")
    assert offenders == [], f"float money declarations still present: {offenders}"
