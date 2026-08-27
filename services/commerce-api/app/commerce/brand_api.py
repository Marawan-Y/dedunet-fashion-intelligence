"""Consumer-facing serialisation for the fashion network.

WHAT A CONSUMER IS AND IS NOT TOLD.

`ownership_type` is an INTERNAL security and accountability concept. `MERCHANT_OWNED` names a
tenant relationship; `EXTERNAL_CURATED` says we list a brand we have no relationship with.
Neither belongs in a customer's browser as a raw enum, and `relationship_label` exists so no
surface has to invent its own wording for them -- which is how "EXTERNAL_CURATED" becomes
"Partner" in someone's JSX and the platform starts claiming a relationship it does not have.

The mapping is deliberately unexciting:

    PLATFORM_CURATED  -> "DEDUNET"        (our own label)
    MERCHANT_OWNED    -> "Brand-managed"  (they run it; not "partner", not "official")
    EXTERNAL_CURATED  -> "External brand" (we list it; there is no relationship at all)

None of these words claims a partnership, an agreement, an authorisation or an integration,
because none of those exists. `LEGAL_CLEARANCE_PENDING` is unchanged.

The merchant organisation behind a brand is NEVER serialised to a consumer. Its existence is
the tenant boundary; leaking its id or name would hand every visitor a tenant enumeration.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import modes
from .brands import (
    Brand,
    BrandOwnershipType,
    CommerceRoute,
    ProvenanceSource,
)
from .commerce_action import commerce_action
from .models import Product, as_utc

# Consumer-safe wording for an internal enum. No word here implies an agreement.
RELATIONSHIP_LABELS: dict[BrandOwnershipType, str] = {
    BrandOwnershipType.PLATFORM_CURATED: "DEDUNET",
    BrandOwnershipType.MERCHANT_OWNED: "Brand-managed",
    BrandOwnershipType.EXTERNAL_CURATED: "External brand",
}

# How the information got here, in plain words. Also not a claim of partnership.
PROVENANCE_LABELS: dict[ProvenanceSource, str] = {
    ProvenanceSource.PLATFORM_AUTHORED: "Written by DEDUNET",
    ProvenanceSource.MERCHANT_MANAGED: "Maintained by the brand",
    ProvenanceSource.EXTERNAL_SOURCED: "Collected from public sources",
}

# The unmistakable label for a development fixture. Deliberately blunt: a fixture must be
# impossible to mistake for a real brand, including by someone skim-reading a screenshot.
FIXTURE_NOTICE = "Development fixture — not a real brand and not a partner."


def brands_visible(session: Session, *, include_fixtures: bool | None = None):
    """The brands a consumer may see, as a SELECT.

    Two filters, for two different reasons.

    PUBLICATION excludes archived and draft brands, the same way the catalogue already hides
    unpublished products.

    FIXTURES are excluded whenever public commerce is enabled. That gate is not a convenience
    flag: `modes.public_commerce_enabled()` is false in every mode this platform can actually
    be configured into, and `PUBLIC_COMMERCE_MODE` cannot be enabled by configuration at all.
    So a fixture is visible while the platform is a preview and structurally invisible the
    moment it is not -- which is the production gate the phase brief requires, expressed as a
    property of the mode rather than as a checkbox someone can forget.
    """

    if include_fixtures is None:
        include_fixtures = not modes.public_commerce_enabled()

    stmt = select(Brand).where(Brand.publication_status.in_(("published", "preview")))
    if not include_fixtures:
        stmt = stmt.where(Brand.is_development_fixture.is_(False))
    return stmt


def product_count_map(session: Session, brand_ids: list[int]) -> dict[int, int]:
    """Active product counts per brand, in ONE query.

    A count per brand inside a serialiser is the N+1 that turns a 12-brand page into 13
    round trips; the brands listing is a page every visitor loads.
    """

    if not brand_ids:
        return {}
    stmt = (
        select(Product.brand_id, func.count(Product.id))
        .where(Product.brand_id.in_(brand_ids), Product.is_active.is_(True))
        .group_by(Product.brand_id)
    )
    # THE SAME SCOPING THE BRAND DETAIL PAGE APPLIES.
    #
    # Without this the count and the page disagree: the legacy fixture row is `is_active`
    # but has no external identity, so preview mode hides it on the detail page while the
    # card still advertised "1 piece". A count that does not match the list under it is a
    # defect a customer notices before anyone else does.
    if modes.is_preview_mode():
        stmt = stmt.where(Product.external_product_id.is_not(None))
    return {brand_id: count for brand_id, count in session.execute(stmt).all()}


def cover_image_map(session: Session, brand_ids: list[int]) -> dict[int, str]:
    """One representative product image per brand, in ONE query.

    A brand card wants to show CLOTHES, not a logo on a coloured square. The brands page
    used to reach into the catalogue for this; doing it server-side means the client needs
    only the brand request, and a brand with no products correctly gets nothing rather than
    borrowing another brand's artwork.
    """

    from .models import ProductMedia

    if not brand_ids:
        return {}
    stmt = (
        select(Product.brand_id, ProductMedia.path)
        .join(ProductMedia, ProductMedia.product_id == Product.id)
        .where(Product.brand_id.in_(brand_ids), Product.is_active.is_(True))
        .order_by(Product.brand_id, Product.name, ProductMedia.sort_order)
    )
    if modes.is_preview_mode():
        stmt = stmt.where(Product.external_product_id.is_not(None))

    covers: dict[int, str] = {}
    for brand_id, path in session.execute(stmt).all():
        covers.setdefault(brand_id, f"/api/v1/media/{path}")
    return covers


def brand_summary(brand: Brand, *, product_count: int = 0, cover_image_url: str = "") -> dict:
    """A brand as a consumer sees it in a listing."""

    return {
        "slug": brand.slug,
        "name": brand.name,
        # Consumer wording, never the enum. The enum itself is not serialised here at all.
        "relationship_label": RELATIONSHIP_LABELS[brand.ownership_type],
        "publication_status": brand.publication_status,
        "story": brand.story,
        "logo_media_path": brand.logo_media_path,
        "logo_url": f"/api/v1/media/{brand.logo_media_path}" if brand.logo_media_path else "",
        # A representative product image. Empty for a brand with no catalogue -- borrowing
        # another brand's artwork would imply it has a collection.
        "cover_image_url": cover_image_url,
        "website_url": brand.website_url,
        "country_code": brand.country_code,
        "product_count": product_count,
        # The fixture flag IS serialised, and on purpose: a client that forgets to check it
        # still cannot render a fixture as genuine, because `fixture_notice` is right there
        # in the payload and every surface shows it.
        "is_development_fixture": brand.is_development_fixture,
        "fixture_notice": FIXTURE_NOTICE if brand.is_development_fixture else "",
        "provenance": {
            "label": PROVENANCE_LABELS[brand.provenance_source],
            "source_url": brand.source_url,
            "last_checked_at": _iso(brand.last_checked_at),
            "last_synced_at": _iso(brand.last_synced_at),
        },
    }


def brand_detail(session: Session, brand: Brand, *, products: list[Product]) -> dict:
    """A brand plus its catalogue, as the brand detail page needs it."""

    covers = cover_image_map(session, [brand.id])
    payload = brand_summary(
        brand, product_count=len(products), cover_image_url=covers.get(brand.id, "")
    )
    payload["products"] = [brand_product_summary(p, brand=brand) for p in products]
    return payload


def brand_product_summary(product: Product, *, brand: Brand) -> dict:
    """A product as it appears inside a brand, or on a card.

    Carries enough for attribution, navigation, price and the commerce control -- and
    nothing that would let a client decide purchasability for itself.
    """

    prices = [v.price_minor_units for v in product.variants if v.price_minor_units]
    action = commerce_action(
        route=_route_of(product),
        sellable=product.sellable,
        brand=brand,
        external_url=product.external_buy_url,
    )
    return {
        "slug": product.slug,
        "name": product.name,
        "category": product.category,
        "collection": product.collection,
        "currency": product.currency,
        # Authoritative minor units only. The client formats; see SIDE_B_MONEY_CONTRACT.
        "price_minor_units_min": min(prices) if prices else None,
        "price_minor_units_max": max(prices) if prices else None,
        "brand": {
            "slug": brand.slug,
            "name": brand.name,
            "relationship_label": RELATIONSHIP_LABELS[brand.ownership_type],
            "is_development_fixture": brand.is_development_fixture,
        },
        "commerce_route": _route_of(product).value,
        "commerce_action": action.as_dict(),
        "image_url": _primary_media_url(product),
        "availability": availability_payload(product),
    }


def availability_payload(product: Product) -> dict:
    """Availability as a CONFIDENCE with a timestamp, never as a fact.

    `is_fact` is serialised explicitly and is true only for VERIFIED_AVAILABLE, which nothing
    currently sets. A client is expected to render anything else with its qualifier and its
    timestamp -- "reported available, checked 3 hours ago" -- never as "in stock".
    """

    confidence = product.availability_confidence or "UNKNOWN"
    return {
        "confidence": confidence,
        "is_fact": confidence == "VERIFIED_AVAILABLE",
        "checked_at": _iso(product.availability_checked_at),
        "last_synced_at": _iso(product.source_last_synced_at),
    }


def _route_of(product: Product) -> CommerceRoute:
    """Read the stored route defensively.

    A row written before this column existed, or by a direct SQL edit, must not take down a
    catalogue page. An unrecognised value is treated as NON_PURCHASABLE, which is the safe
    direction: the failure mode of guessing wrong here is offering a purchase we cannot honour.
    """

    try:
        return CommerceRoute(product.commerce_route)
    except (ValueError, TypeError):
        return CommerceRoute.NON_PURCHASABLE


def _primary_media_url(product: Product) -> str:
    for media in sorted(product.media, key=lambda m: (m.sort_order, m.asset_id)):
        return f"/api/v1/media/{media.path}"
    return product.image_url or ""


def _iso(value) -> str:
    normalised = as_utc(value)
    return normalised.isoformat() if normalised else ""


# --------------------------------------------------------------------------- admin


def brand_admin_row(session: Session, brand: Brand, *, product_count: int) -> dict:
    """What an internal operator needs, which is more than a consumer gets.

    The raw `ownership_type`, the merchant organisation, the fixture flag and the routes in
    use -- the things you need to answer "who is accountable for this and what can be bought
    from it". Behind the admin token; never reachable from the consumer API.
    """

    ownership = brand.ownership
    routes = session.execute(
        select(Product.commerce_route, func.count(Product.id))
        .where(Product.brand_id == brand.id)
        .group_by(Product.commerce_route)
    ).all()
    return {
        "slug": brand.slug,
        "name": brand.name,
        "ownership_type": brand.ownership_type.value,
        "publication_status": brand.publication_status,
        "is_development_fixture": brand.is_development_fixture,
        "merchant_organization": (
            {
                "slug": ownership.merchant_organization.slug,
                "name": ownership.merchant_organization.name,
                "status": ownership.merchant_organization.status,
            }
            if ownership is not None
            else None
        ),
        "provenance_source": brand.provenance_source.value,
        "source_identifier": brand.source_identifier,
        "source_url": brand.source_url,
        "last_checked_at": _iso(brand.last_checked_at),
        "last_synced_at": _iso(brand.last_synced_at),
        "product_count": product_count,
        "commerce_routes": {route or "": count for route, count in routes},
        "created_at": _iso(brand.created_at),
        "updated_at": _iso(brand.updated_at),
    }
