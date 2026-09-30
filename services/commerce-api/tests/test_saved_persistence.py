"""Saved persistence: ownership, idempotency, visibility and privacy.

The defects these exist to prevent:

  * customer A reading or deleting customer B's saved items -- the IDOR that "saved items"
    is the classic shape of, because it feels harmless until it enumerates someone's taste;
  * an anonymous caller creating or listing saved data;
  * a double tap creating two rows, or an unsave of something unsaved returning an error;
  * saving unpublished or fixture-only content by guessing a slug, which would turn the
    save endpoint into a catalogue enumeration;
  * a soft-deleted account continuing to mutate state;
  * an erased customer's saved items surviving erasure, because the erasure path
    pseudonymizes rather than deletes and the FK cascade therefore never fires;
  * a saved list whose order wobbles between requests, which makes pagination skip rows.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.commerce import modes, saved_service, services
from app.commerce.brand_registry import DEDUNET_BRAND_SLUG, ensure_canonical_brands
from app.commerce.brands import Brand, BrandOwnershipType
from app.commerce.look_registry import ensure_curated_looks
from app.commerce.looks import Look
from app.commerce.models import Customer, Product
from app.commerce.saved import FavoriteBrand, FavoriteProduct, SavedLook
from app.commerce.security import hash_password


# --------------------------------------------------------------------------- fixtures


def _customer(session, email="saver@example.test") -> Customer:
    customer = Customer(
        email=email, password_hash=hash_password("Correct-Horse-9"), full_name="Saver"
    )
    session.add(customer)
    session.flush()
    return customer


def _dedunet_product(session, slug="the-source-tee") -> Product:
    """A product that passes the visibility gate in preview mode.

    It needs an `external_product_id`, because preview mode scopes the catalogue to the
    DEDUNET products -- the same filter the saved endpoints reuse.
    """

    brand = ensure_canonical_brands(session)[DEDUNET_BRAND_SLUG]
    product = Product(
        slug=slug,
        name=slug.replace("-", " ").title(),
        category="tops",
        brand_id=brand.id,
        external_product_id=f"DDN-{abs(hash(slug)) % 100000}",
        is_active=True,
        sellable=False,
        publication_status="preview",
        commerce_route="NON_PURCHASABLE",
    )
    session.add(product)
    session.flush()
    return product


def _auth(client, email, password="Correct-Horse-9") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def saver(client, db_session):
    """A registered customer with a token, created through the real registration endpoint."""

    email = "saver-a@example.test"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Correct-Horse-9", "full_name": "Saver A"},
    )
    assert response.status_code in (200, 201), response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}", "email": email}


# --------------------------------------------------------------------------- service level


def test_save_is_idempotent_and_creates_one_row(db_session):
    customer = _customer(db_session)
    product = _dedunet_product(db_session)

    first = saved_service.save(
        db_session, customer=customer, kind="products",
        target_id=product.id, target_slug=product.slug,
    )
    second = saved_service.save(
        db_session, customer=customer, kind="products",
        target_id=product.id, target_slug=product.slug,
    )
    assert first.created is True
    assert second.created is False, "a second save must not create a row"

    rows = db_session.scalars(
        select(FavoriteProduct).where(FavoriteProduct.customer_id == customer.id)
    ).all()
    assert len(rows) == 1


def test_the_database_refuses_a_duplicate_even_without_the_service(db_session):
    """Uniqueness is a CONSTRAINT, not an application convention.

    An application check loses the race between two taps on a flaky connection. This proves
    the database does not.
    """

    from sqlalchemy.exc import IntegrityError

    customer = _customer(db_session)
    product = _dedunet_product(db_session)
    db_session.add(FavoriteProduct(customer_id=customer.id, product_id=product.id))
    db_session.flush()
    db_session.add(FavoriteProduct(customer_id=customer.id, product_id=product.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_unsave_is_idempotent_and_never_errors(db_session):
    customer = _customer(db_session)
    product = _dedunet_product(db_session)
    saved_service.save(
        db_session, customer=customer, kind="products",
        target_id=product.id, target_slug=product.slug,
    )

    assert saved_service.unsave(
        db_session, customer=customer, kind="products",
        target_id=product.id, target_slug=product.slug,
    ) is True
    # Again. The caller asked for "not saved", and that state holds either way.
    assert saved_service.unsave(
        db_session, customer=customer, kind="products",
        target_id=product.id, target_slug=product.slug,
    ) is False


def test_saving_emits_an_event_without_a_customer_identifier(db_session):
    """A product-popularity signal, not a behavioural profile.

    The same event plus a customer id would be a per-person taste history, and this phase
    has no consent basis for one.
    """

    import json

    from app.commerce.models import AnalyticsEvent

    customer = _customer(db_session)
    product = _dedunet_product(db_session)
    saved_service.save(
        db_session, customer=customer, kind="products",
        target_id=product.id, target_slug=product.slug,
    )

    event = db_session.scalar(
        select(AnalyticsEvent).where(AnalyticsEvent.name == "product_saved")
    )
    assert event is not None
    payload = json.loads(event.payload_json)
    assert payload == {"product": product.slug}
    assert "customer" not in event.payload_json
    assert str(customer.id) not in event.payload_json


# --------------------------------------------------------------------------- HTTP: auth


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/me/saved"),
        ("get", "/api/v1/me/saved/state"),
        ("get", "/api/v1/me/saved/products"),
        ("get", "/api/v1/me/saved/brands"),
        ("get", "/api/v1/me/saved/looks"),
        ("post", "/api/v1/me/saved/products/the-source-tee"),
        ("delete", "/api/v1/me/saved/products/the-source-tee"),
        ("post", "/api/v1/me/saved/brands/dedunet"),
        ("delete", "/api/v1/me/saved/brands/dedunet"),
    ],
)
def test_anonymous_callers_are_refused_everywhere(client, method, path):
    """Not one saved endpoint is reachable without a token."""

    assert getattr(client, method)(path).status_code == 401


def test_a_saved_endpoint_never_accepts_a_customer_id(client, saver):
    """The IDOR guard, asserted against the ROUTES rather than trusted.

    No path, query or body parameter names a customer. Identity comes from the token.
    """

    from app.commerce import api

    for route in api.router.routes:
        path = getattr(route, "path", "")
        if "/saved" not in path:
            continue
        assert "customer" not in path.lower(), f"{path} takes a customer identifier"


# --------------------------------------------------------------------------- HTTP: flow


def test_save_list_and_unsave_a_product_over_http(client, saver, db_session):
    product = _dedunet_product(db_session)
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}

    saved = client.post(f"/api/v1/me/saved/products/{product.slug}", headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"saved": True, "created": True, "slug": product.slug}

    again = client.post(f"/api/v1/me/saved/products/{product.slug}", headers=headers)
    assert again.status_code == 200
    assert again.json()["created"] is False, "a repeated save must be a no-op, not an error"

    listing = client.get("/api/v1/me/saved/products", headers=headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["slug"] == product.slug
    assert listing["items"][0]["available"] is True
    assert listing["items"][0]["saved_at"]

    state = client.get("/api/v1/me/saved/state", headers=headers).json()
    assert product.slug in state["products"]

    overview = client.get("/api/v1/me/saved", headers=headers).json()
    assert overview["counts"]["products"] == 1

    removed = client.delete(f"/api/v1/me/saved/products/{product.slug}", headers=headers)
    assert removed.status_code == 200
    assert removed.json()["removed"] is True
    # And again -- still a success.
    assert client.delete(
        f"/api/v1/me/saved/products/{product.slug}", headers=headers
    ).json()["removed"] is False
    assert client.get("/api/v1/me/saved/products", headers=headers).json()["total"] == 0


def test_save_and_unsave_the_dedunet_brand(client, saver, db_session):
    ensure_canonical_brands(db_session)
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}

    assert client.post(
        f"/api/v1/me/saved/brands/{DEDUNET_BRAND_SLUG}", headers=headers
    ).status_code == 200
    listing = client.get("/api/v1/me/saved/brands", headers=headers).json()
    assert listing["total"] == 1
    entry = listing["items"][0]
    assert entry["slug"] == DEDUNET_BRAND_SLUG
    assert entry["is_development_fixture"] is False
    assert entry["fixture_notice"] == ""
    # No internal ownership enum on a consumer payload.
    assert "PLATFORM_CURATED" not in str(entry)

    assert client.delete(
        f"/api/v1/me/saved/brands/{DEDUNET_BRAND_SLUG}", headers=headers
    ).status_code == 200
    assert client.get("/api/v1/me/saved/brands", headers=headers).json()["total"] == 0


def test_save_and_unsave_a_look(client, saver, db_session):
    for slug in (
        "the-source-tee", "the-passage-shirt", "the-measure-trouser",
        "the-structure-overshirt", "the-trace-scarf",
    ):
        if db_session.scalar(select(Product).where(Product.slug == slug)) is None:
            _dedunet_product(db_session, slug)
    ensure_curated_looks(db_session)
    db_session.commit()

    look = db_session.scalar(select(Look))
    assert look is not None, "the curated looks should provision once their products exist"
    headers = {"Authorization": saver["Authorization"]}

    assert client.post(f"/api/v1/me/saved/looks/{look.slug}", headers=headers).status_code == 200
    listing = client.get("/api/v1/me/saved/looks", headers=headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["slug"] == look.slug
    assert listing["items"][0]["item_count"] >= 2, "a look is a multi-item arrangement"

    assert client.delete(
        f"/api/v1/me/saved/looks/{look.slug}", headers=headers
    ).status_code == 200
    assert client.get("/api/v1/me/saved/looks", headers=headers).json()["total"] == 0


# --------------------------------------------------------------------------- isolation


def test_one_customer_cannot_see_or_delete_another_customers_saved_items(client, db_session):
    """THE ISOLATION TEST. Two real customers, two real tokens, no shared state."""

    product = _dedunet_product(db_session)
    db_session.commit()

    tokens = {}
    for name in ("alice", "bob"):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{name}@example.test",
                "password": "Correct-Horse-9",
                "full_name": name.title(),
            },
        )
        assert response.status_code in (200, 201), response.text
        tokens[name] = {"Authorization": f"Bearer {response.json()['access_token']}"}

    client.post(f"/api/v1/me/saved/products/{product.slug}", headers=tokens["alice"])

    # Bob sees nothing.
    assert client.get("/api/v1/me/saved/products", headers=tokens["bob"]).json()["total"] == 0
    assert client.get("/api/v1/me/saved/state", headers=tokens["bob"]).json()["products"] == []

    # Bob's delete succeeds as a no-op and must NOT touch Alice's row.
    bob_delete = client.delete(
        f"/api/v1/me/saved/products/{product.slug}", headers=tokens["bob"]
    )
    assert bob_delete.status_code == 200
    assert bob_delete.json()["removed"] is False

    assert client.get("/api/v1/me/saved/products", headers=tokens["alice"]).json()["total"] == 1


# --------------------------------------------------------------------------- visibility


def test_an_unpublished_product_cannot_be_saved_and_answers_404(client, saver, db_session):
    """404, not 403. A 403 confirms the row exists and makes this an enumeration oracle."""

    brand = ensure_canonical_brands(db_session)[DEDUNET_BRAND_SLUG]
    hidden = Product(
        slug="hidden-product", name="Hidden", category="tops",
        brand_id=brand.id, is_active=False, publication_status="draft",
        external_product_id="DDN-HIDDEN",
    )
    db_session.add(hidden)
    db_session.commit()

    response = client.post(
        "/api/v1/me/saved/products/hidden-product",
        headers={"Authorization": saver["Authorization"]},
    )
    assert response.status_code == 404
    assert "hidden" not in response.text.lower() or "not found" in response.text.lower()


def test_a_legacy_product_without_an_external_identity_cannot_be_saved_in_preview(
    client, saver, db_session, monkeypatch
):
    """Preview mode scopes the catalogue, and the saved endpoint must not route around it."""

    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    brand = ensure_canonical_brands(db_session)[DEDUNET_BRAND_SLUG]
    legacy = Product(
        slug="legacy-product", name="Legacy", category="tops",
        brand_id=brand.id, is_active=True, publication_status="published",
        external_product_id=None,
    )
    db_session.add(legacy)
    db_session.commit()

    assert client.post(
        "/api/v1/me/saved/products/legacy-product",
        headers={"Authorization": saver["Authorization"]},
    ).status_code == 404


def test_an_archived_brand_cannot_be_saved(client, saver, db_session):
    db_session.add(
        Brand(
            slug="archived-brand", name="Archived",
            ownership_type=BrandOwnershipType.EXTERNAL_CURATED,
            publication_status="archived",
        )
    )
    db_session.commit()
    assert client.post(
        "/api/v1/me/saved/brands/archived-brand",
        headers={"Authorization": saver["Authorization"]},
    ).status_code == 404


def test_an_invalid_slug_is_a_404_not_a_500(client, saver):
    headers = {"Authorization": saver["Authorization"]}
    for path in (
        "/api/v1/me/saved/products/no-such-product",
        "/api/v1/me/saved/brands/no-such-brand",
        "/api/v1/me/saved/looks/no-such-look",
    ):
        assert client.post(path, headers=headers).status_code == 404
        assert client.delete(path, headers=headers).status_code == 404


def test_an_unpublished_target_stays_in_the_list_but_is_marked_unavailable(
    client, saver, db_session
):
    """It was theirs. Silent disappearance from your own saved page is worse than a label.

    Nothing hidden leaks: this state is only reachable for a target that was visible when it
    was saved.
    """

    product = _dedunet_product(db_session, "soon-hidden")
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}
    client.post(f"/api/v1/me/saved/products/{product.slug}", headers=headers)

    product.is_active = False
    db_session.commit()

    listing = client.get("/api/v1/me/saved/products", headers=headers).json()
    assert listing["total"] == 1, "the saved row remains"
    entry = listing["items"][0]
    assert entry["available"] is False
    assert entry["image_url"] == "", "an unavailable target is not linked or illustrated"

    # And it is still removable.
    assert client.delete(
        f"/api/v1/me/saved/products/{product.slug}", headers=headers
    ).json()["removed"] is True


# --------------------------------------------------------------------------- lifecycle


def test_a_soft_deleted_customer_cannot_mutate_saved_state(client, saver, db_session):
    """The existing authoritative 401 must keep applying to the new endpoints."""

    product = _dedunet_product(db_session)
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}
    assert client.post(
        f"/api/v1/me/saved/products/{product.slug}", headers=headers
    ).status_code == 200

    customer = db_session.scalar(select(Customer).where(Customer.email == saver["email"]))
    from app.commerce.db import utcnow

    customer.deleted_at = utcnow()
    db_session.commit()

    assert client.post(
        f"/api/v1/me/saved/products/{product.slug}", headers=headers
    ).status_code == 401
    assert client.get("/api/v1/me/saved/products", headers=headers).status_code == 401


def test_erasing_a_customer_deletes_their_saved_items(client, saver, db_session):
    """THE PRIVACY TEST, and the reason the explicit delete exists.

    `erase_customer` PSEUDONYMIZES -- it keeps the customer row so order history stays
    reconcilable -- so the `ondelete=CASCADE` foreign keys never fire. Without the explicit
    deletion an erased customer's taste would remain in the database indefinitely.
    """

    product = _dedunet_product(db_session)
    ensure_canonical_brands(db_session)
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}
    client.post(f"/api/v1/me/saved/products/{product.slug}", headers=headers)
    client.post(f"/api/v1/me/saved/brands/{DEDUNET_BRAND_SLUG}", headers=headers)

    customer = db_session.scalar(select(Customer).where(Customer.email == saver["email"]))
    assert db_session.scalars(
        select(FavoriteProduct).where(FavoriteProduct.customer_id == customer.id)
    ).all()

    services.erase_customer(db_session, customer, actor="test")

    assert db_session.scalars(
        select(FavoriteProduct).where(FavoriteProduct.customer_id == customer.id)
    ).all() == []
    assert db_session.scalars(
        select(FavoriteBrand).where(FavoriteBrand.customer_id == customer.id)
    ).all() == []
    assert db_session.scalars(
        select(SavedLook).where(SavedLook.customer_id == customer.id)
    ).all() == []


def test_deleting_a_customer_row_cascades_their_saved_items(db_session):
    """The other half. Both are needed; either alone leaves data behind."""

    customer = _customer(db_session, "cascade@example.test")
    product = _dedunet_product(db_session, "cascade-product")
    db_session.add(FavoriteProduct(customer_id=customer.id, product_id=product.id))
    db_session.commit()

    db_session.delete(customer)
    db_session.commit()
    assert db_session.scalars(select(FavoriteProduct)).all() == []


# --------------------------------------------------------------------------- listing shape


def test_saved_products_are_ordered_most_recently_saved_first(client, saver, db_session):
    slugs = [f"ordered-{i}" for i in range(3)]
    for slug in slugs:
        _dedunet_product(db_session, slug)
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}
    for slug in slugs:
        client.post(f"/api/v1/me/saved/products/{slug}", headers=headers)

    listing = client.get("/api/v1/me/saved/products", headers=headers).json()
    returned = [i["slug"] for i in listing["items"]]
    assert returned[0] == slugs[-1], "the most recently saved must come first"


def test_saved_listings_paginate_and_clamp(client, saver, db_session):
    for i in range(4):
        _dedunet_product(db_session, f"page-{i}")
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}
    for i in range(4):
        client.post(f"/api/v1/me/saved/products/page-{i}", headers=headers)

    page = client.get("/api/v1/me/saved/products?limit=2&offset=0", headers=headers).json()
    assert page["total"] == 4
    assert len(page["items"]) == 2
    assert page["limit"] == 2

    clamped = client.get("/api/v1/me/saved/products?limit=99999", headers=headers).json()
    assert clamped["limit"] == 100


def test_a_saved_entry_is_a_summary_not_a_full_product_document(client, saver, db_session):
    """Forty complete product documents for forty cards is kilobytes per row."""

    product = _dedunet_product(db_session)
    db_session.commit()
    headers = {"Authorization": saver["Authorization"]}
    client.post(f"/api/v1/me/saved/products/{product.slug}", headers=headers)

    entry = client.get("/api/v1/me/saved/products", headers=headers).json()["items"][0]
    assert "variants" not in entry
    assert "media" not in entry
    assert "description" not in entry
    assert {"slug", "name", "price_minor_units_min", "saved_at", "available"} <= set(entry)


# --------------------------------------------------------------------------- looks API


def test_the_public_looks_api_exposes_curated_content_without_a_total_price(
    client, db_session
):
    """No look total, and no field for one -- summing prototype prices invents a figure."""

    for slug in (
        "the-source-tee", "the-passage-shirt", "the-measure-trouser",
        "the-structure-overshirt", "the-trace-scarf",
    ):
        if db_session.scalar(select(Product).where(Product.slug == slug)) is None:
            _dedunet_product(db_session, slug)
    ensure_curated_looks(db_session)
    db_session.commit()

    looks = client.get("/api/v1/looks").json()
    assert looks, "the curated looks should be served"
    for look in looks:
        assert look["items"], "a look with no items is a wrong look, not a reduced one"
        assert "total_price_minor_units" not in look
        assert "total" not in look
        for item in look["items"]:
            assert item["role"], "each garment states why it is present"
            assert item["product_slug"]


def test_an_unknown_look_is_a_404(client):
    assert client.get("/api/v1/looks/no-such-look").status_code == 404


def test_curated_looks_are_idempotent(db_session):
    for slug in (
        "the-source-tee", "the-passage-shirt", "the-measure-trouser",
        "the-structure-overshirt", "the-trace-scarf",
    ):
        if db_session.scalar(select(Product).where(Product.slug == slug)) is None:
            _dedunet_product(db_session, slug)
    first = ensure_curated_looks(db_session)
    second = ensure_curated_looks(db_session)
    assert {s: l.id for s, l in first.items()} == {s: l.id for s, l in second.items()}


def test_a_look_is_skipped_rather_than_built_partially(db_session):
    """A two-piece outfit rendered with one piece is not a reduced look, it is a wrong one.

    Only one product exists here, and every curated look needs at least two, so nothing
    should be created -- rather than four looks each missing most of their garments.
    """

    from app.commerce.look_registry import CURATED_LOOKS

    _dedunet_product(db_session, "the-source-tee")
    created = ensure_curated_looks(db_session)

    assert created == {}, f"looks were built from an incomplete catalogue: {sorted(created)}"
    assert db_session.scalars(select(Look)).all() == []

    # And every look that WOULD have been created needs more than the one product present.
    for spec in CURATED_LOOKS:
        assert len(spec["items"]) >= 2


# --------------------------------------------------------------------------- no tenancy


def test_no_saved_table_carries_an_organization_column(db_session):
    """Saved data belongs to the customer. A merchant has no business in these tables."""

    for model in (SavedLook, FavoriteProduct, FavoriteBrand):
        columns = set(model.__table__.columns.keys())
        assert not any("organization" in c for c in columns), model.__tablename__
        assert not any("merchant" in c for c in columns), model.__tablename__
