"""Style DNA: explicit provenance, ownership, validation, concurrency and deletion.

The defects these exist to prevent:

  * a preference row appearing that no customer chose -- the failure that would make the
    whole domain a lie, and the reason `source` has a database CHECK rather than a comment;
  * Saved activity silently becoming a style preference;
  * customer A reading, editing or deleting customer B's profile, or an anonymous caller
    doing any of it -- this is someone's measurements, not a wishlist;
  * two devices editing one profile and the second silently erasing the first;
  * "delete my Style DNA" also deleting Saved items, orders or the account;
  * an erased customer's sizes, budgets and fit notes surviving erasure, because the
    erasure path pseudonymizes and the FK cascade therefore never fires;
  * float money reaching an authoritative column;
  * a development fixture being offered as a brand someone could follow;
  * an unbounded free-text field turning a style profile into a biography.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.commerce import style_dna_service, style_taxonomy as tax
from app.commerce.brand_registry import (
    DEDUNET_BRAND_SLUG,
    LEGACY_FIXTURE_BRAND_SLUG,
    ensure_canonical_brands,
)
from app.commerce.models import Customer
from app.commerce.saved import FavoriteProduct
from app.commerce.security import hash_password
from app.commerce.style_dna import (
    STYLE_DNA_CHILD_MODELS,
    StyleBrandPreference,
    StyleColourPreference,
    StyleDirectionPreference,
    StyleProfile,
    StyleSize,
)


# --------------------------------------------------------------------------- helpers


def _customer(session, email="style@example.test") -> Customer:
    customer = Customer(
        email=email, password_hash=hash_password("Correct-Horse-9"), full_name="Style"
    )
    session.add(customer)
    session.flush()
    return customer


def _register(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Correct-Horse-9", "full_name": "Style Tester"},
    )
    assert response.status_code in (200, 201), response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def owner(client):
    return _register(client, "style-owner@example.test")


@pytest.fixture()
def other(client):
    return _register(client, "style-other@example.test")


# --------------------------------------------------------------------------- empty state


def test_empty_profile_is_200_not_404(client, owner):
    """Absence is a normal state, not an error.

    A 404 would be indistinguishable from a wrong URL, and a client forced to read absence
    out of an error status cannot tell "no profile yet" from "session expired" -- which
    need opposite responses.
    """

    response = client.get("/api/v1/me/style-dna", headers=owner)
    assert response.status_code == 200
    body = response.json()
    assert body["exists"] is False
    assert body["revision"] == 0
    assert body["style_directions"] == []
    assert body["budget"]["per_piece_minor_units"] is None
    assert body["sections_with_preferences"] == 0
    assert body["section_count"] == 5


def test_empty_profile_creates_no_row(client, owner, db_session):
    client.get("/api/v1/me/style-dna", headers=owner)
    assert db_session.scalars(select(StyleProfile)).all() == []


# --------------------------------------------------------------------------- provenance


def test_every_written_preference_is_user_explicit(client, owner, db_session):
    """THE defining rule of this domain, checked on real rows."""

    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "style_directions": [{"slug": "minimal", "stance": "PREFERRED"}],
            "colours": [{"slug": "black", "stance": "PREFERRED"}],
            "materials": [{"slug": "wool", "stance": "AVOIDED"}],
            "fits": [{"garment_category": "tops", "fit": "relaxed"}],
            "sizes": [
                {"garment_category": "tops", "size_system": "ALPHA", "size_label": "M"}
            ],
        },
    )
    for model in STYLE_DNA_CHILD_MODELS:
        for row in db_session.scalars(select(model)).all():
            assert row.source == tax.SOURCE_USER_EXPLICIT, model.__tablename__


def test_only_one_source_is_allowed_this_phase(client, owner):
    """The options endpoint must not advertise a provenance the platform cannot produce."""

    body = client.get("/api/v1/style-dna/options").json()
    assert body["sources"] == ["USER_EXPLICIT"]
    assert tax.ALLOWED_SOURCES == frozenset({"USER_EXPLICIT"})


def test_inferred_source_is_refused_by_the_database(db_session):
    """The CHECK constraint, not the service, is what makes the rule hold.

    A future code path that writes an inferred row without going through the service must
    still fail. This writes directly through the ORM to prove the guard is in the schema.

    SQLite enforces CHECK constraints natively, so this is a real assertion here and not
    merely a PostgreSQL-only guarantee.
    """

    from sqlalchemy.exc import IntegrityError

    customer = _customer(db_session, "inferred@example.test")
    profile = StyleProfile(customer_id=customer.id)
    db_session.add(profile)
    db_session.flush()

    db_session.add(
        StyleDirectionPreference(
            profile_id=profile.id,
            style_slug="minimal",
            stance="PREFERRED",
            source="INFERRED_FROM_SAVED",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# --------------------------------------------------------------------------- Saved boundary


def test_saving_items_does_not_create_or_change_style_dna(client, owner, db_session):
    """The boundary this phase exists to hold.

    Saving is an act of interest, not a statement of preference -- people save things to
    decide against them. If this test ever fails, inference has arrived without its
    source, confidence, explanation, correction path, consent or decay.
    """

    brands = ensure_canonical_brands(db_session)
    db_session.commit()

    client.post(f"/api/v1/me/saved/brands/{DEDUNET_BRAND_SLUG}", headers=owner)

    assert db_session.scalars(select(StyleProfile)).all() == []
    assert client.get("/api/v1/me/style-dna", headers=owner).json()["exists"] is False
    assert brands[DEDUNET_BRAND_SLUG].slug == DEDUNET_BRAND_SLUG


def test_deleting_style_dna_leaves_saved_items_alone(client, owner, db_session):
    """"Forget how I dress" is a narrow request and must stay narrow."""

    ensure_canonical_brands(db_session)
    db_session.commit()
    client.post(f"/api/v1/me/saved/brands/{DEDUNET_BRAND_SLUG}", headers=owner)
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "navy", "stance": "PREFERRED"}]},
    )

    saved_before = client.get("/api/v1/me/saved/brands", headers=owner).json()

    assert client.delete("/api/v1/me/style-dna", headers=owner).status_code == 200

    assert client.get("/api/v1/me/style-dna", headers=owner).json()["exists"] is False
    assert client.get("/api/v1/me/saved/brands", headers=owner).json() == saved_before
    # And the account itself survives.
    assert client.get("/api/v1/me/saved", headers=owner).status_code == 200


# --------------------------------------------------------------------------- create / update


def test_create_then_read_round_trips_every_section(client, owner, db_session):
    ensure_canonical_brands(db_session)
    db_session.commit()

    response = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "style_directions": [
                {"slug": "minimal", "stance": "PREFERRED"},
                {"slug": "streetwear", "stance": "AVOIDED"},
            ],
            "colours": [{"slug": "black", "stance": "PREFERRED"}],
            "colour_approach": "mostly-neutral",
            "fits": [{"garment_category": "tops", "fit": "relaxed"}],
            "sizes": [
                {"garment_category": "tops", "size_system": "ALPHA", "size_label": "M"},
                {"garment_category": "bottoms", "size_system": "EU", "size_label": "50"},
            ],
            "materials": [{"slug": "cotton", "stance": "PREFERRED"}],
            "care_effort": "machine-only",
            "seasonality": "four-seasons",
            "fit_notes": "long in the body",
            "brands": [{"slug": DEDUNET_BRAND_SLUG, "stance": "PREFERRED"}],
            "budget": {
                "per_piece_minor_units": 20000,
                "per_look_minor_units": 60000,
                "currency": "EUR",
            },
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["exists"] is True
    assert body["revision"] == 1
    assert body["personalization_enabled"] is True
    assert {d["slug"]: d["stance"] for d in body["style_directions"]} == {
        "minimal": "PREFERRED",
        "streetwear": "AVOIDED",
    }
    assert body["colour_approach"] == "mostly-neutral"
    assert body["budget"] == {
        "per_piece_minor_units": 20000,
        "per_look_minor_units": 60000,
        "currency": "EUR",
    }
    assert body["brands"][0]["slug"] == DEDUNET_BRAND_SLUG
    assert body["sections_with_preferences"] == 5

    # And the same thing comes back on a fresh read.
    assert client.get("/api/v1/me/style-dna", headers=owner).json() == body


def test_absent_field_is_left_alone_and_empty_list_clears(client, owner):
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "colours": [{"slug": "black", "stance": "PREFERRED"}],
            "materials": [{"slug": "linen", "stance": "PREFERRED"}],
        },
    )
    # Mentioning only colours must not disturb materials.
    body = client.patch(
        "/api/v1/me/style-dna", headers=owner, json={"colours": []}
    ).json()
    assert body["colours"] == []
    assert [m["slug"] for m in body["materials"]] == ["linen"]


def test_replacing_a_collection_leaves_exactly_one_row_per_value(client, owner, db_session):
    for _ in range(3):
        client.patch(
            "/api/v1/me/style-dna",
            headers=owner,
            json={"colours": [{"slug": "navy", "stance": "PREFERRED"}]},
        )
    rows = db_session.scalars(select(StyleColourPreference)).all()
    assert len(rows) == 1


def test_sections_with_preferences_is_a_count_not_a_score(client, owner):
    body = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "black", "stance": "PREFERRED"}]},
    ).json()
    assert body["sections_with_preferences"] == 1
    assert body["section_count"] == 5
    # No invented confidence anywhere in the payload.
    assert "score" not in body and "strength" not in body and "confidence" not in body


# --------------------------------------------------------------------------- validation


@pytest.mark.parametrize(
    "patch",
    [
        {"style_directions": [{"slug": "not-a-style", "stance": "PREFERRED"}]},
        {"colours": [{"slug": "chartreuse", "stance": "PREFERRED"}]},
        {"materials": [{"slug": "unobtanium", "stance": "AVOIDED"}]},
        {"fits": [{"garment_category": "hats", "fit": "relaxed"}]},
        {"fits": [{"garment_category": "tops", "fit": "skintight"}]},
        {"sizes": [{"garment_category": "tops", "size_system": "ZZ", "size_label": "M"}]},
        {"colour_approach": "vibes"},
        {"care_effort": "whatever"},
        {"seasonality": "monsoon"},
    ],
)
def test_unknown_taxonomy_values_are_refused(client, owner, patch):
    response = client.patch("/api/v1/me/style-dna", headers=owner, json=patch)
    assert response.status_code == 400, response.text


def test_contradictory_stances_in_one_patch_are_refused(client, owner):
    response = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "colours": [
                {"slug": "black", "stance": "PREFERRED"},
                {"slug": "black", "stance": "AVOIDED"},
            ]
        },
    )
    assert response.status_code == 400
    assert "twice" in response.json()["detail"]


def test_unique_constraint_backs_the_application_check(db_session):
    """The constraint is the guarantee; the 400 above is only the error message."""

    from sqlalchemy.exc import IntegrityError

    customer = _customer(db_session, "dupe@example.test")
    profile = StyleProfile(customer_id=customer.id)
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        StyleColourPreference(profile_id=profile.id, colour_slug="black", stance="PREFERRED")
    )
    db_session.flush()
    db_session.add(
        StyleColourPreference(profile_id=profile.id, colour_slug="black", stance="AVOIDED")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


@pytest.mark.parametrize(
    "budget",
    [
        {"per_piece_minor_units": 199.99, "currency": "EUR"},
        {"per_piece_minor_units": -1, "currency": "EUR"},
        {"per_piece_minor_units": True, "currency": "EUR"},
        {"per_piece_minor_units": "20000", "currency": "EUR"},
        {"per_piece_minor_units": 20000, "currency": "USD"},
        {"per_piece_minor_units": 10**12, "currency": "EUR"},
    ],
)
def test_budget_rejects_float_negative_bool_string_currency_and_overflow(client, owner, budget):
    """Float money is rejected, never coerced.

    `int(199.99 * 100)` is 19998 on this hardware. A money value that is quietly one cent
    wrong is worse than a rejected request, because it is invisible until reconciliation.
    """

    response = client.patch("/api/v1/me/style-dna", headers=owner, json={"budget": budget})
    assert response.status_code == 400, response.text


def test_budget_without_currency_is_refused(client, owner):
    response = client.patch(
        "/api/v1/me/style-dna", headers=owner, json={"budget": {"per_piece_minor_units": 5000}}
    )
    assert response.status_code == 400
    assert "currency" in response.json()["detail"]


def test_budget_is_stored_as_integer_minor_units(client, owner, db_session):
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"budget": {"per_piece_minor_units": 7200, "currency": "EUR"}},
    )
    profile = db_session.scalars(select(StyleProfile)).one()
    assert profile.budget_per_piece_minor_units == 7200
    assert isinstance(profile.budget_per_piece_minor_units, int)
    assert profile.budget_currency == "EUR"


def test_fit_notes_are_bounded(client, owner):
    response = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"fit_notes": "x" * (tax.MAX_FIT_NOTES_LENGTH + 1)},
    )
    assert response.status_code == 400


def test_oversized_collections_are_refused(client, owner):
    response = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "black", "stance": "PREFERRED"}] * (tax.MAX_COLOURS + 1)},
    )
    assert response.status_code == 400


def test_size_label_is_short(client, owner):
    response = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "sizes": [
                {
                    "garment_category": "tops",
                    "size_system": "ALPHA",
                    "size_label": "M" * (tax.MAX_SIZE_LABEL_LENGTH + 1),
                }
            ]
        },
    )
    assert response.status_code == 400


def test_unknown_field_is_refused(client, owner):
    """`extra: forbid`. A typo'd field should fail loudly, not be silently discarded."""

    response = client.patch(
        "/api/v1/me/style-dna", headers=owner, json={"body_shape": "pear"}
    )
    assert response.status_code == 422


def test_two_size_systems_for_one_category_coexist_and_are_not_converted(client, owner):
    body = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "sizes": [
                {"garment_category": "tops", "size_system": "ALPHA", "size_label": "M"},
                {"garment_category": "tops", "size_system": "EU", "size_label": "50"},
            ]
        },
    ).json()
    assert len(body["sizes"]) == 2
    labels = {s["size_system"]: s["size_label"] for s in body["sizes"]}
    assert labels == {"ALPHA": "M", "EU": "50"}


# --------------------------------------------------------------------------- brands


def test_brand_preference_uses_a_foreign_key(client, owner, db_session):
    brands = ensure_canonical_brands(db_session)
    db_session.commit()
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"brands": [{"slug": DEDUNET_BRAND_SLUG, "stance": "PREFERRED"}]},
    )
    row = db_session.scalars(select(StyleBrandPreference)).one()
    assert row.brand_id == brands[DEDUNET_BRAND_SLUG].id


def test_development_fixture_cannot_be_a_brand_preference(client, owner, db_session):
    """A scaffold must not be offered as a fashion house."""

    ensure_canonical_brands(db_session)
    db_session.commit()
    response = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"brands": [{"slug": LEGACY_FIXTURE_BRAND_SLUG, "stance": "PREFERRED"}]},
    )
    assert response.status_code == 400
    assert "fixture" in response.json()["detail"]


def test_unknown_brand_is_refused(client, owner):
    response = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"brands": [{"slug": "a-brand-that-does-not-exist", "stance": "PREFERRED"}]},
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------- concurrency


def test_stale_revision_is_409_and_does_not_overwrite(client, owner):
    """Two devices, one profile. The second edit must not silently erase the first."""

    first = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "black", "stance": "PREFERRED"}]},
    ).json()
    assert first["revision"] == 1

    # Device A saves.
    second = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"expected_revision": 1, "colours": [{"slug": "navy", "stance": "PREFERRED"}]},
    ).json()
    assert second["revision"] == 2

    # Device B is still holding revision 1.
    conflict = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"expected_revision": 1, "colours": [{"slug": "red", "stance": "PREFERRED"}]},
    )
    assert conflict.status_code == 409
    detail = conflict.json()["detail"]
    assert detail["current_revision"] == 2

    # And device A's edit survived untouched.
    assert [c["slug"] for c in client.get("/api/v1/me/style-dna", headers=owner).json()["colours"]] == ["navy"]


def test_revision_increments_on_every_update(client, owner):
    client.patch("/api/v1/me/style-dna", headers=owner, json={"care_effort": "any-care"})
    for expected in (2, 3, 4):
        body = client.patch(
            "/api/v1/me/style-dna", headers=owner, json={"seasonality": "four-seasons"}
        ).json()
        assert body["revision"] == expected


def test_expected_revision_zero_means_no_profile_yet(client, owner):
    created = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"expected_revision": 0, "care_effort": "any-care"},
    )
    assert created.status_code == 200
    # Sending 0 again, when a profile now exists, is a conflict.
    again = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"expected_revision": 0, "care_effort": "any-care"},
    )
    assert again.status_code == 409


def test_a_rejected_patch_changes_nothing(client, owner):
    """Validation is whole-patch. A half-applied update is a profile nobody asked for."""

    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "black", "stance": "PREFERRED"}]},
    )
    before = client.get("/api/v1/me/style-dna", headers=owner).json()

    rejected = client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "colours": [{"slug": "navy", "stance": "PREFERRED"}],
            "materials": [{"slug": "unobtanium", "stance": "PREFERRED"}],
        },
    )
    assert rejected.status_code == 400
    assert client.get("/api/v1/me/style-dna", headers=owner).json() == before


# --------------------------------------------------------------------------- personalization


def test_disable_preserves_every_value(client, owner):
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "colours": [{"slug": "black", "stance": "PREFERRED"}],
            "budget": {"per_piece_minor_units": 15000, "currency": "EUR"},
        },
    )
    disabled = client.patch(
        "/api/v1/me/style-dna", headers=owner, json={"personalization_enabled": False}
    ).json()

    assert disabled["personalization_enabled"] is False
    assert [c["slug"] for c in disabled["colours"]] == ["black"]
    assert disabled["budget"]["per_piece_minor_units"] == 15000


def test_disable_then_re_enable_is_lossless(client, owner):
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "olive", "stance": "PREFERRED"}]},
    )
    client.patch("/api/v1/me/style-dna", headers=owner, json={"personalization_enabled": False})
    re_enabled = client.patch(
        "/api/v1/me/style-dna", headers=owner, json={"personalization_enabled": True}
    ).json()
    assert re_enabled["personalization_enabled"] is True
    assert [c["slug"] for c in re_enabled["colours"]] == ["olive"]


def test_disable_is_not_delete(client, owner, db_session):
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "grey", "stance": "PREFERRED"}]},
    )
    client.patch("/api/v1/me/style-dna", headers=owner, json={"personalization_enabled": False})
    assert db_session.scalars(select(StyleProfile)).all() != []


# --------------------------------------------------------------------------- delete


def test_delete_removes_profile_and_every_child_row(client, owner, db_session):
    ensure_canonical_brands(db_session)
    db_session.commit()
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "style_directions": [{"slug": "classic", "stance": "PREFERRED"}],
            "colours": [{"slug": "cream", "stance": "PREFERRED"}],
            "materials": [{"slug": "linen", "stance": "PREFERRED"}],
            "fits": [{"garment_category": "tops", "fit": "regular"}],
            "sizes": [{"garment_category": "tops", "size_system": "ALPHA", "size_label": "L"}],
            "brands": [{"slug": DEDUNET_BRAND_SLUG, "stance": "PREFERRED"}],
        },
    )
    assert client.delete("/api/v1/me/style-dna", headers=owner).json()["deleted"] is True

    assert db_session.scalars(select(StyleProfile)).all() == []
    for model in STYLE_DNA_CHILD_MODELS:
        assert db_session.scalars(select(model)).all() == [], model.__tablename__


def test_delete_is_idempotent(client, owner):
    assert client.delete("/api/v1/me/style-dna", headers=owner).json()["deleted"] is False
    assert client.delete("/api/v1/me/style-dna", headers=owner).status_code == 200


def test_delete_returns_the_empty_representation(client, owner):
    client.patch("/api/v1/me/style-dna", headers=owner, json={"care_effort": "any-care"})
    body = client.delete("/api/v1/me/style-dna", headers=owner).json()
    assert body["profile"]["exists"] is False
    assert body["profile"]["revision"] == 0


# --------------------------------------------------------------------------- authorization


@pytest.mark.parametrize("method,kwargs", [("get", {}), ("patch", {"json": {}}), ("delete", {})])
def test_anonymous_is_refused_on_every_route(client, method, kwargs):
    response = getattr(client, method)("/api/v1/me/style-dna", **kwargs)
    assert response.status_code == 401


def test_customer_a_cannot_see_or_touch_customer_b(client, owner, other):
    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={"colours": [{"slug": "burgundy", "stance": "PREFERRED"}]},
    )

    # B sees their own empty profile, never A's.
    assert client.get("/api/v1/me/style-dna", headers=other).json()["exists"] is False

    # B writing creates B's profile and leaves A's alone.
    client.patch(
        "/api/v1/me/style-dna",
        headers=other,
        json={"colours": [{"slug": "white", "stance": "PREFERRED"}]},
    )
    assert [c["slug"] for c in client.get("/api/v1/me/style-dna", headers=owner).json()["colours"]] == ["burgundy"]

    # B deleting removes only B's.
    client.delete("/api/v1/me/style-dna", headers=other)
    assert client.get("/api/v1/me/style-dna", headers=owner).json()["exists"] is True


def test_no_route_accepts_a_customer_id(client):
    """Walked from the route table, not eyeballed.

    Style DNA is exactly the resource where an unverified id gets overlooked, and the
    consequence here is someone's measurements rather than a wishlist.
    """

    from app.main import app

    for route in app.routes:
        path = getattr(route, "path", "")
        if "style-dna" not in path:
            continue
        assert "customer_id" not in path, path
        assert "{customer" not in path, path


def test_soft_deleted_customer_cannot_use_the_profile(client, owner, db_session):
    customer = db_session.scalars(
        select(Customer).where(Customer.email == "style-owner@example.test")
    ).one()
    client.patch("/api/v1/me/style-dna", headers=owner, json={"care_effort": "any-care"})

    from app.commerce.models import utcnow

    customer.deleted_at = utcnow()
    db_session.commit()

    assert client.get("/api/v1/me/style-dna", headers=owner).status_code == 401
    assert client.patch("/api/v1/me/style-dna", headers=owner, json={}).status_code == 401
    assert client.delete("/api/v1/me/style-dna", headers=owner).status_code == 401


# --------------------------------------------------------------------------- erasure


def test_hard_delete_of_the_customer_cascades(db_session):
    from app.commerce.brand_registry import ensure_canonical_brands as _brands

    _brands(db_session)
    customer = _customer(db_session, "cascade@example.test")
    profile = StyleProfile(customer_id=customer.id)
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        StyleSize(
            profile_id=profile.id,
            garment_category="tops",
            size_system="ALPHA",
            size_label="M",
        )
    )
    db_session.commit()

    db_session.delete(customer)
    db_session.commit()

    assert db_session.scalars(select(StyleProfile)).all() == []
    assert db_session.scalars(select(StyleSize)).all() == []


def test_erase_customer_removes_style_dna(client, owner, db_session):
    """The lesson Saved persistence paid for, inherited rather than rediscovered.

    `erase_customer` PSEUDONYMIZES -- the customer row survives so order history stays
    reconcilable -- so the FK cascade never fires. Without the explicit deletion the most
    intimate data in the system would outlive the erasure request meant to remove it.
    """

    from app.commerce import services

    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "sizes": [{"garment_category": "tops", "size_system": "ALPHA", "size_label": "M"}],
            "budget": {"per_piece_minor_units": 20000, "currency": "EUR"},
            "fit_notes": "long in the body",
        },
    )
    customer = db_session.scalars(
        select(Customer).where(Customer.email == "style-owner@example.test")
    ).one()
    assert db_session.scalars(select(StyleProfile)).all() != []

    services.erase_customer(db_session, customer, actor="test")

    # The customer row survives, pseudonymized...
    assert db_session.get(Customer, customer.id) is not None
    # ...and no style data survives with it.
    assert db_session.scalars(select(StyleProfile)).all() == []
    for model in STYLE_DNA_CHILD_MODELS:
        assert db_session.scalars(select(model)).all() == [], model.__tablename__


def test_erase_customer_removes_both_saved_and_style_dna(client, owner, db_session):
    from app.commerce import services

    ensure_canonical_brands(db_session)
    db_session.commit()
    client.post(f"/api/v1/me/saved/brands/{DEDUNET_BRAND_SLUG}", headers=owner)
    client.patch("/api/v1/me/style-dna", headers=owner, json={"care_effort": "any-care"})

    customer = db_session.scalars(
        select(Customer).where(Customer.email == "style-owner@example.test")
    ).one()
    services.erase_customer(db_session, customer, actor="test")

    assert db_session.scalars(select(StyleProfile)).all() == []
    assert db_session.scalars(select(FavoriteProduct)).all() == []


# --------------------------------------------------------------------------- privacy of events


def test_events_carry_no_profile_content(client, owner, db_session):
    """An analytics table holding sizes and budgets is a copy of the most personal data in
    the system, sitting outside every control built to protect the original -- outside the
    delete endpoint, outside erasure, and outside what the customer can inspect.
    """

    from app.commerce.models import AnalyticsEvent

    client.patch(
        "/api/v1/me/style-dna",
        headers=owner,
        json={
            "sizes": [{"garment_category": "tops", "size_system": "EU", "size_label": "52"}],
            "budget": {"per_piece_minor_units": 33300, "currency": "EUR"},
            "fit_notes": "a distinctive note",
            "colours": [{"slug": "burgundy", "stance": "AVOIDED"}],
        },
    )
    events = db_session.scalars(
        select(AnalyticsEvent).where(AnalyticsEvent.name.like("style_profile%"))
    ).all()
    assert events, "the update should emit an event"
    for event in events:
        blob = event.payload_json
        for leak in ("52", "33300", "a distinctive note", "burgundy", "tops"):
            assert leak not in blob, f"{leak!r} leaked into {event.name}"


def test_event_names_are_emitted_for_the_lifecycle(client, owner, db_session):
    from app.commerce.models import AnalyticsEvent

    client.patch("/api/v1/me/style-dna", headers=owner, json={"care_effort": "any-care"})
    client.patch("/api/v1/me/style-dna", headers=owner, json={"personalization_enabled": False})
    client.patch("/api/v1/me/style-dna", headers=owner, json={"personalization_enabled": True})
    client.delete("/api/v1/me/style-dna", headers=owner)

    names = {
        e.name
        for e in db_session.scalars(
            select(AnalyticsEvent).where(AnalyticsEvent.name.like("style_profile%"))
        ).all()
    }
    assert {
        "style_profile_created",
        "style_profile_updated",
        "style_profile_disabled",
        "style_profile_enabled",
        "style_profile_deleted",
    } <= names


# --------------------------------------------------------------------------- options


def test_options_endpoint_serves_the_whole_vocabulary(client):
    body = client.get("/api/v1/style-dna/options").json()
    for key in (
        "style_directions",
        "colours",
        "colour_approaches",
        "garment_categories",
        "fits",
        "size_systems",
        "materials",
        "care_efforts",
        "seasonalities",
        "limits",
        "budget_currencies",
        "stances",
    ):
        assert key in body, key
    assert body["stances"] == ["PREFERRED", "AVOIDED"]
    assert body["budget_currencies"] == ["EUR"]
    assert {t["slug"] for t in body["style_directions"]} == tax.STYLE_DIRECTION_SLUGS


def test_service_level_profile_read_is_not_n_plus_one(db_session):
    """One profile read must not fan out into a query per collection."""

    customer = _customer(db_session, "eager@example.test")
    profile = StyleProfile(customer_id=customer.id)
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        StyleColourPreference(profile_id=profile.id, colour_slug="black", stance="PREFERRED")
    )
    db_session.commit()
    db_session.expunge_all()

    loaded = style_dna_service.get_profile(db_session, customer=customer)
    assert loaded is not None
    from sqlalchemy import inspect as sa_inspect

    state = sa_inspect(loaded)
    for relation in ("style_directions", "colours", "fits", "sizes", "materials", "brands"):
        assert relation not in state.unloaded, f"{relation} was not eagerly loaded"
