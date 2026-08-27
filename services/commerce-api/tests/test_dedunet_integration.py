"""DEDUNET integration guards.

Covers the Side A package, the normalization, the money conversion, the typed states, the
origin rule, inventory, the commerce modes and the importer's refusals.

Every expected value is asserted EXACTLY. A count that drifts is a failure even when
nothing reports as broken, because a silently smaller catalogue is precisely the defect an
importer would otherwise carry into the database.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SIDE_A = REPO / "handoffs" / "incoming" / "side-a" / "DEDUNET_Platform_Integration_v1"
BRAND = REPO / "packages" / "brand"

sys.path.insert(0, str(REPO / "scripts" / "brand"))

from app.commerce import modes  # noqa: E402
from app.money import FloatMoneyRejected  # noqa: E402


def load_brand(name: str):
    return json.loads((BRAND / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- Side A integrity

def test_side_a_checksums_all_verify():
    manifest = SIDE_A / "CHECKSUMS_SHA256.txt"
    lines = [ln for ln in manifest.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 54, f"expected 54 manifest entries, found {len(lines)}"

    verified = 0
    for line in lines:
        digest, rel = line.split(maxsplit=1)
        target = SIDE_A / rel.strip()
        assert target.is_file(), f"manifest lists a missing file: {rel}"
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest.strip().lower(), rel
        verified += 1
    assert verified == 54


def test_side_a_contains_no_legacy_brand():
    import re

    pattern = re.compile(r"\bMERET\b|\bMERYT\b", re.IGNORECASE)
    offenders = []
    for path in SIDE_A.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if pattern.search(text):
            offenders.append(path.name)
    assert offenders == []


# ------------------------------------------------------------------- exact counts

def test_normalized_counts_are_exact():
    assert len(load_brand("products.json")) == 5
    assert len(load_brand("variants.json")) == 62
    assert len(load_brand("assets.json")) == 31
    assert len(load_brand("product-media.json")) == 18


def test_skus_are_unique():
    skus = [v["sku"] for v in load_brand("variants.json")]
    assert len(skus) == 62
    assert len(set(skus)) == 62


def test_external_product_ids_are_the_expected_stable_set():
    ids = {p["external_product_id"] for p in load_brand("products.json")}
    assert ids == {"DDN-TS01", "DDN-SH01", "DDN-TR01", "DDN-OS01", "DDN-SC01"}


def test_external_variant_ids_are_unique():
    ids = [v["external_variant_id"] for v in load_brand("variants.json")]
    assert len(set(ids)) == len(ids) == 62


def test_no_orphan_variants():
    product_ids = {p["external_product_id"] for p in load_brand("products.json")}
    orphans = [
        v["external_variant_id"]
        for v in load_brand("variants.json")
        if v["external_product_id"] not in product_ids
    ]
    assert orphans == []


def test_every_registered_asset_exists_on_disk():
    missing = [a["asset_id"] for a in load_brand("assets.json") if not (SIDE_A / a["path"]).is_file()]
    assert missing == []


def test_variant_counts_per_product_match_the_source():
    counts: dict[str, int] = {}
    for v in load_brand("variants.json"):
        counts[v["external_product_id"]] = counts.get(v["external_product_id"], 0) + 1
    assert counts == {
        "DDN-TS01": 18,
        "DDN-SH01": 18,
        "DDN-TR01": 12,
        "DDN-OS01": 12,
        "DDN-SC01": 2,
    }
    assert sum(counts.values()) == 62


# ------------------------------------------------------------------------- money

def test_major_to_minor_unit_conversion_is_exact():
    from build_brand_package import price_to_minor_units

    assert price_to_minor_units("72", "EUR", "t") == 7200
    assert price_to_minor_units("72.00", "EUR", "t") == 7200
    assert price_to_minor_units("74", "EUR", "t") == 7400
    assert price_to_minor_units("122", "EUR", "t") == 12200
    assert price_to_minor_units("142", "EUR", "t") == 14200
    assert price_to_minor_units("192", "EUR", "t") == 19200
    assert price_to_minor_units("0.01", "EUR", "t") == 1
    assert price_to_minor_units("72.50", "EUR", "t") == 7250


def test_conversion_rejects_binary_float():
    from build_brand_package import NormalizationError, price_to_minor_units

    # A float is refused, never rounded: 72.00 arriving as 71.99999999999999 must not
    # silently become 7199.
    with pytest.raises(NormalizationError, match="binary float"):
        price_to_minor_units(72.00, "EUR", "t")
    with pytest.raises(NormalizationError, match="binary float"):
        price_to_minor_units(0.1 + 0.2, "EUR", "t")


def test_conversion_rejects_more_than_two_decimals():
    from build_brand_package import NormalizationError, price_to_minor_units

    with pytest.raises(NormalizationError, match="decimal places"):
        price_to_minor_units("72.001", "EUR", "t")


@pytest.mark.parametrize("bad", ["", "abc", "-5", "7,2", None, "1e3"])
def test_conversion_rejects_invalid_values(bad):
    from build_brand_package import NormalizationError, price_to_minor_units

    with pytest.raises(NormalizationError):
        price_to_minor_units(bad, "EUR", "t")


def test_normalized_prices_are_integers_and_positive():
    for v in load_brand("variants.json"):
        price = v["price_minor_units"]
        assert isinstance(price, int) and not isinstance(price, bool)
        assert price > 0
        assert v["currency"] == "EUR"


def test_no_float_survives_into_the_normalized_package():
    # The authoritative runtime price must never be a Side A decimal field.
    raw = (BRAND / "variants.json").read_text(encoding="utf-8")
    for record in json.loads(raw):
        assert isinstance(record["price_minor_units"], int)
        # source_price_eur is retained as a STRING for provenance, never as a number.
        assert isinstance(record["source_price_eur"], str)


# ------------------------------------------------------------- states and origin

def test_every_product_carries_the_typed_states():
    for p in load_brand("products.json"):
        assert p["publication_status"] == "preview"
        assert p["sellable"] is False
        assert p["inventory_status"] == "prototype_unavailable"
        assert p["evidence_status"] == "DRAFT"
        assert p["material_claim_status"] == "UNVERIFIED"
        assert p["origin_claim_status"] == "UNVERIFIED"
        assert p["legal_brand_status"] == "LEGAL_CLEARANCE_PENDING"
        assert p["media_status"] == "PROTOTYPE_CONCEPT"


def test_origin_rule_is_xx_eg_unverified():
    for p in load_brand("products.json"):
        assert p["country_of_origin"] == "XX"
        assert p["intended_origin"] == "EG"
        assert p["origin_claim_status"] == "UNVERIFIED"


def test_normalized_package_makes_no_made_in_claim():
    for name in ("products.json", "collections.json", "content.json"):
        text = (BRAND / name).read_text(encoding="utf-8").lower()
        assert "made in" not in text, f"{name} contains a 'made in' claim"


def test_brand_metadata_preserves_the_naming_risk_and_blocks_the_goddess_claim():
    brand = load_brand("brand.json")
    assert brand["name"] == "DEDUNET"
    assert brand["domain"] == "dedunet.com"
    assert brand["tagline"] == "Worth, worn."
    assert brand["status"]["legal"] == "LEGAL_CLEARANCE_PENDING"
    assert brand["status"]["public_commercial_launch"] == "BLOCKED"
    # Domain ownership is not trademark clearance, and the naming conflict must stay visible.
    assert "DeDeNet" in brand["naming_risk"]["detail"]
    assert "weaving goddess" in brand["naming_risk"]["prohibited_narrative"]


def test_normalized_copy_does_not_assert_the_blocked_weaving_goddess_narrative():
    """The prohibition is on the CLAIM, not on the word.

    An earlier version of this test asserted that "goddess" appeared nowhere. That failed,
    and it failed for the right reason: Side A's copy contains the word precisely in order
    to DISCLAIM the narrative — "DEDUNET does not claim to be an ancient textile-goddess
    name". Banning the word would have forced deleting the very sentence that keeps the
    brand story safe.

    So the guard checks two things: the blocked assertion is absent, and the disclaimer is
    present.
    """

    text = (BRAND / "content.json").read_text(encoding="utf-8").lower()

    # The blocked claim: DEDUNET being an ancient/verified weaving or textile goddess.
    blocked = [
        "ancient egyptian weaving goddess",
        "pharaonic weaving goddess",
        "goddess of weaving",
        "weaving goddess of",
        "was a weaving goddess",
        "is a weaving goddess",
    ]
    for phrase in blocked:
        assert phrase not in text, f"copy asserts the blocked narrative: {phrase!r}"

    # The disclaimer must survive normalization.
    assert "does not claim to be an ancient textile-goddess name" in text
    assert "not mythology cosplay" in text


def test_normalized_copy_keeps_the_attribution_accurate():
    # Side A credits Dedun/Dedwen as a Nubian deity documented in Egyptian sources. That is
    # the approved, evidence-safe narrative and must not be flattened into "Egyptian".
    text = (BRAND / "content.json").read_text(encoding="utf-8").lower()
    assert "nubian deity" in text
    assert "dedun" in text


# --------------------------------------------------------------------- inventory

def test_all_prototype_variants_have_zero_stock_and_are_not_sellable():
    for v in load_brand("variants.json"):
        assert v["stock_quantity"] == 0
        assert v["sellable"] is False
        assert v["inventory_status"] == "prototype_unavailable"


def test_having_a_price_does_not_make_a_prototype_sellable():
    priced = [v for v in load_brand("variants.json") if v["price_minor_units"] > 0]
    assert len(priced) == 62
    assert all(v["sellable"] is False for v in priced)


def test_normalizer_refuses_non_zero_prototype_stock_rather_than_zeroing_it():
    """Exercises the BUILDER, not its committed output.

    Caught by the mutation harness: replacing the refusal with `stock = 0` survived,
    because the other zero-stock test reads `packages/brand/variants.json` — a committed
    artifact the mutation never regenerates. A guard whose test cannot observe it is not a
    guard.

    The distinction matters: silently zeroing would hide a source change that a human must
    review. A prototype catalogue that suddenly ships stock is a decision, not noise.
    """

    import build_brand_package as builder

    row = {
        "variant_id": "DDN-TS01-CAR-XS",
        "product_id": "DDN-TS01",
        "sku": "DDN-SRC-CAR-XS",
        "color": "Carbon",
        "color_code": "CAR",
        "size": "XS",
        "price_eur": "72",
        "currency": "EUR",
        "inventory_status": "prototype_unavailable",
        "stock_quantity": "7",  # <-- must be refused
        "evidence_status": "DRAFT",
    }

    builder.errors.clear()
    result = builder.normalize_variants([row], {"DDN-TS01"})

    assert result == [], "a variant carrying stock must not be normalized at all"
    assert any("stock_quantity must be 0" in e for e in builder.errors), builder.errors
    builder.errors.clear()


def test_normalizer_accepts_zero_stock():
    # The counterpart: prove the refusal above is specific, not a blanket rejection.
    import build_brand_package as builder

    row = {
        "variant_id": "DDN-TS01-CAR-XS",
        "product_id": "DDN-TS01",
        "sku": "DDN-SRC-CAR-XS",
        "color": "Carbon",
        "color_code": "CAR",
        "size": "XS",
        "price_eur": "72",
        "currency": "EUR",
        "inventory_status": "prototype_unavailable",
        "stock_quantity": "0",
        "evidence_status": "DRAFT",
    }

    builder.errors.clear()
    result = builder.normalize_variants([row], {"DDN-TS01"})

    assert len(result) == 1
    assert result[0]["price_minor_units"] == 7200
    assert result[0]["stock_quantity"] == 0
    assert result[0]["sellable"] is False
    assert builder.errors == []
    builder.errors.clear()


def test_normalizer_refuses_an_orphan_variant():
    import build_brand_package as builder

    row = {
        "variant_id": "DDN-XX99-CAR-XS",
        "product_id": "DDN-XX99",  # no such product
        "sku": "DDN-XXX-CAR-XS",
        "color": "Carbon",
        "color_code": "CAR",
        "size": "XS",
        "price_eur": "72",
        "currency": "EUR",
        "inventory_status": "prototype_unavailable",
        "stock_quantity": "0",
        "evidence_status": "DRAFT",
    }

    builder.errors.clear()
    result = builder.normalize_variants([row], {"DDN-TS01"})

    assert result == []
    assert any("orphan variant" in e for e in builder.errors), builder.errors
    builder.errors.clear()


def test_normalizer_refuses_a_duplicate_sku():
    import build_brand_package as builder

    base = {
        "product_id": "DDN-TS01",
        "sku": "DDN-SRC-CAR-XS",
        "color": "Carbon",
        "color_code": "CAR",
        "currency": "EUR",
        "price_eur": "72",
        "inventory_status": "prototype_unavailable",
        "stock_quantity": "0",
        "evidence_status": "DRAFT",
    }
    rows = [
        {**base, "variant_id": "DDN-TS01-CAR-XS", "size": "XS"},
        {**base, "variant_id": "DDN-TS01-CAR-S", "size": "S"},  # same SKU
    ]

    builder.errors.clear()
    result = builder.normalize_variants(rows, {"DDN-TS01"})

    assert len(result) == 1, "the duplicate SKU must not be normalized"
    assert any("duplicate SKU" in e for e in builder.errors), builder.errors
    builder.errors.clear()


# ------------------------------------------------------------------------- media

def test_media_roles_are_valid_and_ordered_deterministically():
    valid = {"front", "back", "detail", "lifestyle", "campaign", "collection"}
    by_product: dict[str, list] = {}
    for m in load_brand("product-media.json"):
        assert m["role"] in valid
        by_product.setdefault(m["external_product_id"], []).append(m)

    for product_id, records in by_product.items():
        orders = [r["sort_order"] for r in records]
        assert orders == sorted(orders), f"{product_id} media is not ordered"
        assert len(set(orders)) == len(orders), f"{product_id} has duplicate sort orders"
        assert orders[0] == 0


def test_media_has_no_duplicate_relationships():
    pairs = [(m["external_product_id"], m["asset_id"]) for m in load_brand("product-media.json")]
    assert len(set(pairs)) == len(pairs)


def test_every_media_file_exists():
    missing = [m["asset_id"] for m in load_brand("product-media.json") if not (SIDE_A / m["path"]).is_file()]
    assert missing == []


def test_media_belongs_to_a_valid_product():
    product_ids = {p["external_product_id"] for p in load_brand("products.json")}
    assert all(m["external_product_id"] in product_ids for m in load_brand("product-media.json"))


def test_concept_media_is_not_presented_as_photography():
    for m in load_brand("product-media.json"):
        assert m["status"] == "PROTOTYPE_CONCEPT"


# ------------------------------------------------------------------ design tokens

def test_normalized_tokens_expose_css_variables():
    tokens = load_brand("tokens.json")
    assert tokens["colors"], "no colour tokens normalized"
    assert tokens["typography"], "no typography tokens normalized"
    css_vars = tokens["css_variables"]
    assert css_vars, "no CSS variables generated"
    assert all(name.startswith("--ddn-") for name in css_vars)

    css = (BRAND / "tokens.css").read_text(encoding="utf-8")
    assert ":root {" in css
    for name in list(css_vars)[:5]:
        assert name in css


# ------------------------------------------------------------------ commerce modes

def test_public_commerce_mode_cannot_be_enabled_by_configuration(monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", "PUBLIC_COMMERCE_MODE")
    with pytest.raises(modes.CommerceModeError, match="cannot be enabled by configuration"):
        modes.current_mode()
    assert modes.public_commerce_enabled() is False


def test_unknown_mode_is_refused(monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", "SOMETHING_ELSE")
    with pytest.raises(modes.CommerceModeError):
        modes.current_mode()


def test_preview_mode_blocks_every_purchase(monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    # Blocks even a product that IS sellable: the mode gate is independent.
    with pytest.raises(modes.PurchaseBlocked, match="brand preview"):
        modes.assert_purchasable(sellable=True, product_name="Anything")


def test_commerce_test_mode_still_blocks_a_non_sellable_product(monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    with pytest.raises(modes.PurchaseBlocked, match="not available for purchase"):
        modes.assert_purchasable(sellable=False, product_name="The Source Tee")
    # ...and allows a genuinely sellable one.
    modes.assert_purchasable(sellable=True, product_name="Legacy")


def test_default_mode_is_commerce_test(monkeypatch):
    monkeypatch.delenv("COMMERCE_MODE", raising=False)
    assert modes.current_mode() == modes.COMMERCE_TEST


# ------------------------------------------------------- database-level behaviour

@pytest.fixture()
def dedunet_product(db_session):
    """A product carrying the DEDUNET prototype states."""
    from app.commerce.models import InventoryItem, Product, ProductMedia, Variant

    product = Product(
        brand_id=_fixture_brand_id(db_session),
        external_product_id="DDN-TS01",
        slug="the-source-tee",
        name="The Source Tee",
        category="T-Shirts",
        currency="EUR",
        country_of_origin="XX",
        intended_origin="EG",
        is_active=True,
        sellable=False,
        publication_status="preview",
        inventory_status="prototype_unavailable",
        evidence_status="DRAFT",
        material_claim_status="UNVERIFIED",
        origin_claim_status="UNVERIFIED",
        legal_brand_status="LEGAL_CLEARANCE_PENDING",
        media_status="PROTOTYPE_CONCEPT",
    )
    db_session.add(product)
    db_session.flush()

    variant = Variant(
        product_id=product.id,
        external_variant_id="DDN-TS01-CAR-XS",
        sku="DDN-SRC-CAR-XS",
        size="XS",
        color="Carbon",
        price_minor_units=7200,
        sellable=False,
        inventory_status="prototype_unavailable",
        evidence_status="DRAFT",
    )
    db_session.add(variant)
    db_session.flush()
    db_session.add(InventoryItem(variant_id=variant.id, on_hand=0, reserved=0))
    db_session.add(
        ProductMedia(
            product_id=product.id,
            asset_id="DDN-TS01-FRONT",
            role="front",
            sort_order=0,
            path="assets/brand-prototype/products/ddn-ts01-front.svg",
            status="PROTOTYPE_CONCEPT",
        )
    )
    # COMMIT, not just flush. The `client` fixture opens its own session per request. On
    # in-memory SQLite every session shares one connection via StaticPool, so a flush is
    # visible; on PostgreSQL each session gets its own connection and uncommitted rows are
    # not. Flushing only passed on SQLite and 404'd on PostgreSQL - the same split the
    # `seeded` fixture already handles by committing.
    db_session.commit()
    return product, variant


def test_prototype_cannot_be_added_to_cart_even_in_commerce_test_mode(
    db_session, dedunet_product, monkeypatch
):
    from app.commerce import services

    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    _, variant = dedunet_product
    cart = services.get_or_create_cart(db_session, token=None, customer_id=None)

    with pytest.raises(services.DomainError, match="not available for purchase"):
        services.add_to_cart(db_session, cart, variant_id=variant.id, quantity=1)

    assert cart.lines == []


def test_external_product_id_is_unique(db_session, dedunet_product):
    from sqlalchemy.exc import IntegrityError

    from app.commerce.models import Product

    db_session.add(
        Product(
            brand_id=_fixture_brand_id(db_session),
            external_product_id="DDN-TS01",
            slug="a-clone",
            name="Clone",
            category="x",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_external_variant_id_is_unique(db_session, dedunet_product):
    from sqlalchemy.exc import IntegrityError

    from app.commerce.models import Variant

    product, _ = dedunet_product
    db_session.add(
        Variant(
            product_id=product.id,
            external_variant_id="DDN-TS01-CAR-XS",
            sku="DIFFERENT-SKU",
            size="S",
            color="Carbon",
            price_minor_units=7200,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_sku_is_rejected(db_session, dedunet_product):
    from sqlalchemy.exc import IntegrityError

    from app.commerce.models import Variant

    product, _ = dedunet_product
    db_session.add(
        Variant(
            product_id=product.id,
            external_variant_id="DDN-TS01-CAR-S",
            sku="DDN-SRC-CAR-XS",  # already taken
            size="S",
            color="Carbon",
            price_minor_units=7200,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_media_relationship_is_rejected(db_session, dedunet_product):
    from sqlalchemy.exc import IntegrityError

    from app.commerce.models import ProductMedia

    product, _ = dedunet_product
    db_session.add(
        ProductMedia(
            product_id=product.id,
            asset_id="DDN-TS01-FRONT",  # same asset on the same product
            role="back",
            sort_order=1,
            path="assets/brand-prototype/products/ddn-ts01-front.svg",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_media_slot_is_rejected(db_session, dedunet_product):
    from sqlalchemy.exc import IntegrityError

    from app.commerce.models import ProductMedia

    product, _ = dedunet_product
    db_session.add(
        ProductMedia(
            product_id=product.id,
            asset_id="DDN-TS01-OTHER",
            role="front",
            sort_order=0,  # slot already occupied
            path="assets/brand-prototype/products/ddn-ts01-back.svg",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_media_role_is_rejected(db_session, dedunet_product):
    from sqlalchemy.exc import IntegrityError

    from app.commerce.models import ProductMedia

    product, _ = dedunet_product
    db_session.add(
        ProductMedia(
            product_id=product.id,
            asset_id="DDN-TS01-WEIRD",
            role="hero_banner",  # not in the allowed set
            sort_order=9,
            path="assets/brand-prototype/products/ddn-ts01-back.svg",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_api_exposes_the_typed_states_and_media(client, db_session, dedunet_product):
    response = client.get("/api/v1/catalog/products/the-source-tee")
    assert response.status_code == 200
    body = response.json()

    assert body["external_product_id"] == "DDN-TS01"
    assert body["sellable"] is False
    assert body["publication_status"] == "preview"
    assert body["evidence_status"] == "DRAFT"
    assert body["origin_claim_status"] == "UNVERIFIED"
    assert body["country_of_origin"] == "XX"
    assert body["intended_origin"] == "EG"
    assert body["legal_brand_status"] == "LEGAL_CLEARANCE_PENDING"
    assert body["media_status"] == "PROTOTYPE_CONCEPT"
    assert body["media"][0]["role"] == "front"
    assert body["variants"][0]["price_minor_units"] == 7200
    assert body["variants"][0]["available"] == 0


def test_api_never_emits_a_made_in_claim(client, db_session, dedunet_product):
    body = client.get("/api/v1/catalog/products/the-source-tee").text.lower()
    assert "made in" not in body


def _fixture_brand_id(session) -> int:
    """A brand for a test-constructed product.

    `Product.brand_id` is NOT NULL since the multi-brand phase: a product with no brand has
    no accountable origin, which is the whole point of the network model. Tests that build a
    bare Product therefore have to say whose it is, and the canonical DEDUNET brand is the
    right answer for a DEDUNET prototype fixture.
    """

    from app.commerce.brand_registry import DEDUNET_BRAND_SLUG, ensure_canonical_brands

    return ensure_canonical_brands(session)[DEDUNET_BRAND_SLUG].id
