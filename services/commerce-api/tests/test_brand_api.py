"""The brand HTTP surface, and the product payload's backwards compatibility.

Two separate obligations are checked here.

THE NEW SURFACE must paginate, filter, 404 correctly and never leak internal ownership.

THE OLD SURFACE must not break. The admin client, the Android preview and the accepted
consumer build all read `/api/v1/catalog/products`, and this phase adds keys to that payload.
`test_product_payload_is_purely_additive` pins the pre-phase key set: adding is allowed,
removing or renaming is not, and a regression there is a broken client rather than a failing
test somebody notices.
"""

from __future__ import annotations

from app.commerce import modes
from app.commerce.brand_registry import DEDUNET_BRAND_SLUG, ensure_canonical_brands
from app.commerce.brands import Brand, BrandOwnership, BrandOwnershipType, MerchantOrganization


# The exact keys `/api/v1/catalog/products/{slug}` returned BEFORE the multi-brand phase.
# Transcribed from the payload at commit be1d1e2. Nothing here may disappear.
PRE_PHASE_PRODUCT_KEYS = {
    "slug", "name", "description", "category", "collection", "material",
    "care_instructions", "country_of_origin", "currency", "image_url",
    "external_product_id", "collection_id", "publication_status", "sellable",
    "inventory_status", "evidence_status", "material_claim_status",
    "origin_claim_status", "intended_origin", "legal_brand_status", "media_status",
    "media", "variants",
}


def test_brands_listing_returns_the_canonical_brands(client):
    response = client.get("/api/v1/brands")
    assert response.status_code == 200
    body = response.json()
    assert {"items", "total", "limit", "offset"} <= set(body)
    slugs = [b["slug"] for b in body["items"]]
    assert DEDUNET_BRAND_SLUG in slugs


def test_brands_listing_clamps_an_unbounded_limit(client):
    """An unbounded ?limit= is a cheap way to make the database do arbitrary work."""

    body = client.get("/api/v1/brands?limit=100000").json()
    assert body["limit"] == 100
    body = client.get("/api/v1/brands?limit=0").json()
    assert body["limit"] == 1


def test_brands_listing_paginates(client, db_session):
    body = client.get("/api/v1/brands?limit=1&offset=0").json()
    assert len(body["items"]) == 1
    assert body["total"] >= 1
    second = client.get("/api/v1/brands?limit=1&offset=1").json()
    if second["items"]:
        assert second["items"][0]["slug"] != body["items"][0]["slug"]


def test_brands_listing_filters_by_name(client):
    body = client.get("/api/v1/brands?q=DEDUNET").json()
    assert body["items"], "the first-party brand should match its own name"
    assert all("dedunet" in b["name"].lower() for b in body["items"])


def test_a_real_brand_sorts_ahead_of_a_development_fixture(client):
    """A fixture must never displace a real brand at the top of the list."""

    items = client.get("/api/v1/brands?limit=100").json()["items"]
    fixtures = [i for i, b in enumerate(items) if b["is_development_fixture"]]
    reals = [i for i, b in enumerate(items) if not b["is_development_fixture"]]
    if fixtures and reals:
        assert max(reals) < min(fixtures)


def test_brand_detail_returns_the_brand_and_its_products(client):
    response = client.get(f"/api/v1/brands/{DEDUNET_BRAND_SLUG}")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == DEDUNET_BRAND_SLUG
    assert body["relationship_label"] == "DEDUNET"
    assert isinstance(body["products"], list)


def test_brand_detail_404s_for_an_unknown_slug(client):
    assert client.get("/api/v1/brands/no-such-brand").status_code == 404


def test_brand_detail_404s_rather_than_403s_for_a_hidden_brand(client, db_session):
    """403 confirms the row exists, which is the enumeration leak."""

    db_session.add(
        Brand(
            slug="hidden-brand",
            name="Hidden",
            ownership_type=BrandOwnershipType.EXTERNAL_CURATED,
            publication_status="archived",
        )
    )
    db_session.commit()
    assert client.get("/api/v1/brands/hidden-brand").status_code == 404


def test_a_brand_with_an_empty_catalogue_is_a_success_not_an_error(client, db_session):
    db_session.add(
        Brand(
            slug="empty-brand",
            name="Empty",
            ownership_type=BrandOwnershipType.EXTERNAL_CURATED,
            publication_status="published",
        )
    )
    db_session.commit()
    body = client.get("/api/v1/brands/empty-brand").json()
    assert body["products"] == []
    assert body["product_count"] == 0


def test_no_consumer_brand_payload_exposes_ownership_internals(client, db_session):
    """The security metadata a consumer must never receive."""

    brand = Brand(
        slug="merchant-brand", name="Merchant Brand",
        ownership_type=BrandOwnershipType.MERCHANT_OWNED, publication_status="published",
    )
    db_session.add(brand)
    db_session.flush()
    org = MerchantOrganization(slug="tenant-org", name="Tenant Org", status="active")
    db_session.add(org)
    db_session.flush()
    db_session.add(BrandOwnership(brand_id=brand.id, merchant_organization_id=org.id))
    db_session.commit()

    for path in ("/api/v1/brands", "/api/v1/brands/merchant-brand"):
        text = client.get(path).text
        assert "MERCHANT_OWNED" not in text
        assert "tenant-org" not in text
        assert "merchant_organization" not in text


# --------------------------------------------------------------------------- compatibility


def test_product_payload_is_purely_additive(client, db_session):
    """The accepted clients must keep working. Adding keys is allowed; losing them is not."""

    products = client.get("/api/v1/catalog/products").json()
    assert products, "no catalogue to check compatibility against"
    detail = client.get(f"/api/v1/catalog/products/{products[0]['slug']}").json()

    missing = PRE_PHASE_PRODUCT_KEYS - set(detail)
    assert not missing, f"the product payload lost pre-phase keys: {sorted(missing)}"

    # And the additions this phase promised are present.
    assert {"brand", "commerce_route", "commerce_action", "availability"} <= set(detail)


def test_product_variants_keep_their_authoritative_price_shape(client):
    products = client.get("/api/v1/catalog/products").json()
    for product in products:
        for variant in product["variants"]:
            assert isinstance(variant["price_minor_units"], int)
            assert "price" not in variant or isinstance(variant.get("price"), (int, type(None)))


def test_every_product_carries_a_brand_attribution(client):
    for product in client.get("/api/v1/catalog/products").json():
        assert product["brand"] is not None
        assert product["brand"]["slug"]
        assert product["brand"]["relationship_label"]


def test_the_commerce_action_is_present_and_refuses_in_preview(client, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    for product in client.get("/api/v1/catalog/products").json():
        action = product["commerce_action"]
        assert action["kind"] == "NOT_AVAILABLE"
        assert action["enabled"] is False
        assert action["url"] == ""


def test_availability_is_a_confidence_and_never_asserted_as_fact(client):
    for product in client.get("/api/v1/catalog/products").json():
        availability = product["availability"]
        assert availability["confidence"] in {
            "UNKNOWN", "REPORTED_AVAILABLE", "REPORTED_UNAVAILABLE", "VERIFIED_AVAILABLE",
        }
        # Nothing in this catalogue is verified, so nothing may claim to be a fact.
        assert availability["is_fact"] is False


# --------------------------------------------------------------------------- admin


def test_admin_brand_listing_requires_authentication(client):
    assert client.get("/api/v1/admin/brands").status_code == 401


def test_admin_brand_listing_shows_what_a_consumer_is_not_shown(client, db_session, auth):
    """Operators need the raw ownership type and the merchant behind it; consumers do not."""

    body = client.get("/api/v1/admin/brands", headers=auth["admin"]).json()
    slugs = {row["slug"] for row in body["items"]}
    assert DEDUNET_BRAND_SLUG in slugs
    dedunet = next(r for r in body["items"] if r["slug"] == DEDUNET_BRAND_SLUG)
    assert dedunet["ownership_type"] == "PLATFORM_CURATED"
    assert dedunet["merchant_organization"] is None
    assert "product_count" in dedunet
    assert "commerce_routes" in dedunet


def test_a_brand_card_count_matches_the_products_its_page_lists(client):
    """A count that disagrees with the list under it is a defect a customer sees first.

    The legacy fixture row is active but has no external identity, so preview mode hides it
    on the detail page. Before this was fixed the listing advertised "1 piece" for a brand
    whose page showed none.
    """

    listing = client.get("/api/v1/brands?limit=100").json()
    for summary in listing["items"]:
        detail = client.get(f"/api/v1/brands/{summary['slug']}").json()
        assert summary["product_count"] == len(detail["products"]), summary["slug"]
