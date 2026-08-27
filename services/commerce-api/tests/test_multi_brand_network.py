"""The multi-brand fashion network: ownership, routing, provenance and the brand API.

The defects these exist to prevent, stated once so each test has a reason:

  * a brand whose ownership type and ownership row disagree -- a merchant-owned brand with
    no accountable merchant, or a platform brand carrying a tenant relationship;
  * commerce capability inferred from ownership, or ownership inferred from capability;
  * a `javascript:` URL reaching a customer's browser through an external buy link;
  * a development fixture rendered as a real partner;
  * an enum name leaking into consumer copy as if it were a relationship;
  * the accepted DEDUNET catalogue drifting during the migration that gave it a brand.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.commerce import modes
from app.commerce.brand_api import (
    FIXTURE_NOTICE,
    RELATIONSHIP_LABELS,
    brand_summary,
    brands_visible,
)
from app.commerce.brand_registry import (
    DEDUNET_BRAND_SLUG,
    LEGACY_FIXTURE_BRAND_SLUG,
    brand_for_product,
    ensure_canonical_brands,
)
from app.commerce.brands import (
    Brand,
    BrandOwnership,
    BrandOwnershipError,
    BrandOwnershipType,
    CommerceRoute,
    MerchantOrganization,
    UnsafeUrlError,
    assert_ownership_consistent,
    validate_external_url,
    verify_ownership_invariants,
)
from app.commerce.commerce_action import (
    HOSTED_NOT_IMPLEMENTED,
    CommerceAction,
    CommerceActionKind,
    commerce_action,
)
from app.commerce.models import Product


# --------------------------------------------------------------------------- helpers


def _merchant(session, slug="acme-apparel") -> MerchantOrganization:
    org = MerchantOrganization(slug=slug, name="Acme Apparel", status="active")
    session.add(org)
    session.flush()
    return org


def _brand(session, slug, ownership_type, **kw) -> Brand:
    brand = Brand(slug=slug, name=kw.pop("name", slug.title()), ownership_type=ownership_type, **kw)
    session.add(brand)
    session.flush()
    return brand


# --------------------------------------------------------------------------- brand model


def test_the_canonical_brands_are_created_once_and_are_idempotent(db_session):
    first = ensure_canonical_brands(db_session)
    second = ensure_canonical_brands(db_session)
    assert first[DEDUNET_BRAND_SLUG].id == second[DEDUNET_BRAND_SLUG].id
    assert db_session.scalar(select(Brand).where(Brand.slug == DEDUNET_BRAND_SLUG)) is not None


def test_dedunet_is_platform_curated_and_owns_no_merchant_relationship(db_session):
    """The first-party brand must never look like a tenant's."""

    dedunet = ensure_canonical_brands(db_session)[DEDUNET_BRAND_SLUG]
    assert dedunet.ownership_type is BrandOwnershipType.PLATFORM_CURATED
    assert dedunet.ownership is None
    assert db_session.scalar(select(MerchantOrganization)) is None, (
        "no MerchantOrganization may be invented to own DEDUNET's own brand"
    )


def test_brand_slug_is_unique(db_session):
    from sqlalchemy.exc import IntegrityError

    _brand(db_session, "duplicate-me", BrandOwnershipType.PLATFORM_CURATED)
    db_session.add(Brand(slug="duplicate-me", name="Other", ownership_type=BrandOwnershipType.EXTERNAL_CURATED))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_a_development_fixture_can_never_be_published(db_session):
    """The production gate, enforced by the DATABASE rather than by an API check.

    An API-level rule is one direct UPDATE away from being bypassed, and the consequence
    here is a fake partner appearing in a real customer's brand list.
    """

    from sqlalchemy.exc import IntegrityError

    db_session.add(
        Brand(
            slug="fixture-brand",
            name="Fixture",
            ownership_type=BrandOwnershipType.PLATFORM_CURATED,
            is_development_fixture=True,
            publication_status="published",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


# --------------------------------------------------------------------------- ownership


def test_merchant_owned_brand_requires_exactly_one_owner(db_session):
    brand = _brand(db_session, "acme", BrandOwnershipType.MERCHANT_OWNED)
    with pytest.raises(BrandOwnershipError, match="no BrandOwnership row"):
        assert_ownership_consistent(brand)

    brand.ownership = BrandOwnership(merchant_organization_id=_merchant(db_session).id)
    db_session.flush()
    assert_ownership_consistent(brand)  # now consistent


def test_platform_curated_brand_may_not_carry_an_owner(db_session):
    """The OTHER direction. Enforcing only one side leaves the other as the way in."""

    brand = _brand(db_session, "platform-brand", BrandOwnershipType.PLATFORM_CURATED)
    brand.ownership = BrandOwnership(merchant_organization_id=_merchant(db_session).id)
    db_session.flush()
    with pytest.raises(BrandOwnershipError, match="only MERCHANT_OWNED"):
        assert_ownership_consistent(brand)


def test_external_curated_brand_may_not_carry_an_owner(db_session):
    brand = _brand(db_session, "external-brand", BrandOwnershipType.EXTERNAL_CURATED)
    brand.ownership = BrandOwnership(merchant_organization_id=_merchant(db_session).id)
    db_session.flush()
    with pytest.raises(BrandOwnershipError):
        assert_ownership_consistent(brand)


def test_a_brand_can_have_at_most_one_owner_by_key_constraint(db_session):
    """"At most one" is a database key, not an application convention."""

    from sqlalchemy.exc import IntegrityError

    brand = _brand(db_session, "acme2", BrandOwnershipType.MERCHANT_OWNED)
    one = _merchant(db_session, "org-one")
    two = _merchant(db_session, "org-two")
    db_session.add(BrandOwnership(brand_id=brand.id, merchant_organization_id=one.id))
    db_session.flush()
    db_session.add(BrandOwnership(brand_id=brand.id, merchant_organization_id=two.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_the_whole_table_sweep_finds_a_violation_a_per_write_check_would_miss(db_session):
    ensure_canonical_brands(db_session)
    assert verify_ownership_invariants(db_session) == []

    # A write that did not go through the sanctioned path -- exactly what the sweep is for.
    rogue = _brand(db_session, "rogue", BrandOwnershipType.MERCHANT_OWNED)
    db_session.flush()
    violations = verify_ownership_invariants(db_session)
    assert any("rogue" in v for v in violations)


# --------------------------------------------------------------------------- independence


def test_commerce_route_is_independent_of_ownership_in_both_directions(db_session):
    """THE ORTHOGONALITY ASSERTION.

    The tempting shortcut -- "merchant-owned implies we host the sale" -- is wrong the first
    time a merchant keeps their own checkout, and wrong silently. Every combination below is
    legitimate, and none of the four routes is predictable from the ownership type.
    """

    combinations = [
        (BrandOwnershipType.PLATFORM_CURATED, CommerceRoute.NON_PURCHASABLE),
        (BrandOwnershipType.PLATFORM_CURATED, CommerceRoute.HOSTED),
        (BrandOwnershipType.MERCHANT_OWNED, CommerceRoute.HOSTED),
        (BrandOwnershipType.MERCHANT_OWNED, CommerceRoute.EXTERNAL),
        (BrandOwnershipType.EXTERNAL_CURATED, CommerceRoute.REFERRAL),
        (BrandOwnershipType.EXTERNAL_CURATED, CommerceRoute.NON_PURCHASABLE),
    ]

    seen_routes_by_ownership: dict[BrandOwnershipType, set[CommerceRoute]] = {}
    for index, (ownership, route) in enumerate(combinations):
        brand = _brand(db_session, f"combo-{index}", ownership)
        if ownership is BrandOwnershipType.MERCHANT_OWNED:
            brand.ownership = BrandOwnership(
                merchant_organization_id=_merchant(db_session, f"org-{index}").id
            )
        product = Product(
            slug=f"combo-product-{index}",
            name=f"Combo {index}",
            category="tops",
            brand_id=brand.id,
            commerce_route=route.value,
        )
        db_session.add(product)
        db_session.flush()
        assert_ownership_consistent(brand)
        assert product.commerce_route == route.value
        seen_routes_by_ownership.setdefault(ownership, set()).add(route)

    # Neither direction determines the other: at least two ownership types carry more than
    # one route, and at least one route appears under more than one ownership type.
    assert any(len(routes) > 1 for routes in seen_routes_by_ownership.values())
    non_purchasable_owners = {
        o for o, r in combinations if r is CommerceRoute.NON_PURCHASABLE
    }
    assert len(non_purchasable_owners) > 1


# --------------------------------------------------------------------------- URL safety


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(document.cookie)",
        "JavaScript:alert(1)",
        "  javascript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "file:///etc/passwd",
        "vbscript:msgbox(1)",
        "blob:https://evil.example/abc",
        "//evil.example/path",
        "http://insecure.example",
        "https:/malformed",
        "https://",
        "ftp://files.example/x",
        "https://ok.example\nLocation: https://evil.example",
    ],
)
def test_unsafe_external_urls_are_refused(url):
    """Allow-list, not deny-list.

    A deny-list of "javascript, data, file" misses vbscript, blob and whatever ships next.
    `http://` is refused too: an external buy link downgraded to cleartext is a link a
    network attacker can rewrite.
    """

    with pytest.raises(UnsafeUrlError):
        validate_external_url(url, allow_empty=False)


@pytest.mark.parametrize(
    "url",
    [
        "https://brand.example",
        "https://brand.example/product/123?ref=dedunet",
        "https://sub.brand.example:8443/path",
    ],
)
def test_safe_external_urls_are_accepted(url):
    assert validate_external_url(url, allow_empty=False) == url


def test_empty_url_is_allowed_only_where_declared():
    assert validate_external_url("", allow_empty=True) == ""
    with pytest.raises(UnsafeUrlError):
        validate_external_url("", allow_empty=False)


# --------------------------------------------------------------------------- action


def _dedunet(db_session) -> Brand:
    return ensure_canonical_brands(db_session)[DEDUNET_BRAND_SLUG]


def test_preview_mode_collapses_every_route_to_not_available(db_session, monkeypatch):
    """THE OUTER GATE. A route is a capability, never a permission.

    If this ordering ever reverses, a HOSTED product looks purchasable in a preview
    deployment -- which is precisely what PUBLIC_COMMERCIAL_LAUNCH_BLOCKED exists to stop.
    """

    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    brand = _dedunet(db_session)
    for route in CommerceRoute:
        action = commerce_action(
            route=route,
            sellable=True,
            brand=brand,
            external_url="https://brand.example/buy",
        )
        assert action.kind is CommerceActionKind.NOT_AVAILABLE, route
        assert action.enabled is False
        assert action.url == ""


def test_hosted_is_declarable_but_never_reachable(db_session, monkeypatch):
    """An enum value is not a feature. No merchant commerce exists behind a hosted sale."""

    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    action = commerce_action(
        route=CommerceRoute.HOSTED, sellable=True, brand=_dedunet(db_session)
    )
    assert action.kind is CommerceActionKind.NOT_AVAILABLE
    assert action.enabled is False
    assert action.reason == HOSTED_NOT_IMPLEMENTED


def test_a_non_sellable_product_is_refused_before_the_route_is_consulted(db_session, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    action = commerce_action(
        route=CommerceRoute.EXTERNAL,
        sellable=False,
        brand=_dedunet(db_session),
        external_url="https://brand.example/buy",
    )
    assert action.kind is CommerceActionKind.NOT_AVAILABLE
    assert action.url == ""


def test_external_and_referral_carry_a_safe_link_and_browser_protections(db_session, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    brand = _brand(db_session, "acme-live", BrandOwnershipType.EXTERNAL_CURATED, name="Acme")

    external = commerce_action(
        route=CommerceRoute.EXTERNAL,
        sellable=True,
        brand=brand,
        external_url="https://acme.example/buy",
    )
    assert external.kind is CommerceActionKind.EXTERNAL_PURCHASE
    assert external.enabled is True
    assert external.label == "Buy from Acme"
    # Reverse tabnabbing: without noopener the opened page can navigate this tab.
    assert "noopener" in external.link_rel and "noreferrer" in external.link_rel
    assert external.link_target == "_blank"

    referral = commerce_action(
        route=CommerceRoute.REFERRAL,
        sellable=True,
        brand=brand,
        external_url="https://acme.example/view",
    )
    assert referral.kind is CommerceActionKind.REFERRAL_VIEW
    assert referral.label == "View at Acme"


def test_an_external_route_with_an_unsafe_link_is_refused_not_rendered(db_session, monkeypatch):
    """A route that promises a destination and has an unusable one is refused outright."""

    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    action = commerce_action(
        route=CommerceRoute.EXTERNAL,
        sellable=True,
        brand=_dedunet(db_session),
        external_url="javascript:alert(1)",
    )
    assert action.kind is CommerceActionKind.NOT_AVAILABLE
    assert action.enabled is False
    assert action.url == ""


def test_the_action_payload_never_leaks_an_unsafe_url(db_session, monkeypatch):
    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    payload = commerce_action(
        route=CommerceRoute.REFERRAL,
        sellable=True,
        brand=_dedunet(db_session),
        external_url="data:text/html,<script>alert(1)</script>",
    ).as_dict()
    assert payload["url"] == ""
    assert "script" not in str(payload).lower()


# --------------------------------------------------------------------------- presentation


def test_no_ownership_enum_name_reaches_a_consumer_payload(db_session):
    """`EXTERNAL_CURATED` in a payload becomes "Partner" in someone's JSX."""

    for ownership in BrandOwnershipType:
        brand = _brand(db_session, f"pres-{ownership.value.lower()}", ownership)
        payload = brand_summary(brand)
        serialised = str(payload)
        assert ownership.value not in serialised
        assert payload["relationship_label"] == RELATIONSHIP_LABELS[ownership]


def test_consumer_labels_never_claim_a_partnership(db_session):
    """No agreement, authorisation or integration exists. No word may imply one."""

    forbidden = ("partner", "official", "authorised", "authorized", "verified seller")
    for label in RELATIONSHIP_LABELS.values():
        assert not any(word in label.lower() for word in forbidden), label


def test_a_fixture_brand_is_labelled_unmistakably_in_its_payload(db_session):
    fixture = ensure_canonical_brands(db_session)[LEGACY_FIXTURE_BRAND_SLUG]
    payload = brand_summary(fixture)
    assert payload["is_development_fixture"] is True
    assert payload["fixture_notice"] == FIXTURE_NOTICE
    assert "not a real brand" in payload["fixture_notice"].lower()


def test_a_real_brand_carries_no_fixture_notice(db_session):
    payload = brand_summary(_dedunet(db_session))
    assert payload["is_development_fixture"] is False
    assert payload["fixture_notice"] == ""


def test_the_merchant_organization_is_never_serialised_to_a_consumer(db_session):
    """Leaking it would hand every visitor a tenant enumeration."""

    brand = _brand(db_session, "merchant-brand", BrandOwnershipType.MERCHANT_OWNED)
    org = _merchant(db_session, "secret-org")
    brand.ownership = BrandOwnership(merchant_organization_id=org.id)
    db_session.flush()
    serialised = str(brand_summary(brand))
    assert "secret-org" not in serialised
    assert "Acme Apparel" not in serialised


# --------------------------------------------------------------------------- visibility


def test_fixtures_are_structurally_invisible_once_public_commerce_is_enabled(
    db_session, monkeypatch
):
    """The production gate is a property of the MODE, not a flag someone can forget."""

    ensure_canonical_brands(db_session)

    monkeypatch.setattr(modes, "public_commerce_enabled", lambda: False)
    with_fixtures = db_session.scalars(brands_visible(db_session)).all()
    assert any(b.is_development_fixture for b in with_fixtures)

    monkeypatch.setattr(modes, "public_commerce_enabled", lambda: True)
    without = db_session.scalars(brands_visible(db_session)).all()
    assert not any(b.is_development_fixture for b in without)
    assert any(b.slug == DEDUNET_BRAND_SLUG for b in without), "the real brand still shows"


def test_an_archived_brand_is_not_visible(db_session):
    _brand(db_session, "archived-brand", BrandOwnershipType.EXTERNAL_CURATED, publication_status="archived")
    visible = {b.slug for b in db_session.scalars(brands_visible(db_session)).all()}
    assert "archived-brand" not in visible


# --------------------------------------------------------------------------- backfill rule


def test_the_backfill_rule_sends_dedunet_products_to_dedunet(db_session):
    assert brand_for_product(db_session, external_product_id="DDN-TS01").slug == DEDUNET_BRAND_SLUG


def test_the_backfill_rule_sends_unidentified_products_to_the_fixture_brand(db_session):
    """Rather than inventing a plausible company for them, which is the forbidden failure."""

    for missing in (None, ""):
        brand = brand_for_product(db_session, external_product_id=missing)
        assert brand.slug == LEGACY_FIXTURE_BRAND_SLUG
        assert brand.is_development_fixture is True


def test_every_canonical_brand_logo_exists_in_the_brand_package():
    """A brand logo path that resolves to nothing is a broken image on the Brands page.

    This was a real defect: the DEDUNET brand shipped with `assets/brand/dedunet-logo.svg`,
    a path that was never in the packaged assets and answered 404. Nothing caught it except
    a browser test counting how many images the page painted, which reported it as
    "brands paints at least 2 images" -- a symptom two steps from the cause.
    """

    import json
    from pathlib import Path

    from app.commerce.brand_registry import CANONICAL_BRANDS

    root = Path(__file__).resolve()
    while not (root / "packages").is_dir():
        root = root.parent

    manifest = json.loads((root / "packages" / "brand" / "assets.json").read_text(encoding="utf-8"))
    entries = manifest if isinstance(manifest, list) else manifest.get("assets", [])
    known = {entry.get("path", "") for entry in entries}

    for spec in CANONICAL_BRANDS:
        path = spec.get("logo_media_path", "")
        if not path:
            continue  # an empty logo is a deliberate "we have no artwork", not a defect
        assert path in known, (
            f"brand {spec['slug']!r} points at logo {path!r}, which is not in the brand "
            "package and will 404 as a broken image"
        )
