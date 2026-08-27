"""HTTP API for the commerce domain.

Error handling policy: domain rule violations become 4xx with a short, non-leaking
message. Provider and infrastructure failures become 502/503. Nothing returns a raw
exception string, stack trace or provider payload to the client.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import brand_api, modes, payments, services
from .brand_registry import DEDUNET_BRAND_SLUG
from .brands import Brand, BrandOwnershipType, CommerceRoute
from .db import get_session
from .models import Customer, Order, Product, ReturnRequest, Variant, as_utc
from .security import InvalidToken, issue_token, verify_token

router = APIRouter(prefix="/api/v1", tags=["commerce"])


# ------------------------------------------------------------------------ dependencies


def current_customer(
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[str, Header()] = "",
) -> Customer:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    try:
        payload = verify_token(authorization.split(" ", 1)[1].strip())
    except InvalidToken:
        # Deliberately uniform: do not reveal whether the token was forged or expired.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired session")

    customer = session.get(Customer, payload["sub"])
    if customer is None or customer.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired session")
    return customer


def current_admin(customer: Annotated[Customer, Depends(current_customer)]) -> Customer:
    if customer.role != "admin":
        # 403, not 404: the caller is authenticated but not permitted.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "administrator role required")
    return customer


def correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


# ------------------------------------------------------------------------ brand media


# Served from the GENERATED package, never from `handoffs/incoming/`. The handoff is
# checksum-protected evidence, and a file server pointed at it is one path-handling bug away
# from serving something it must not.
#
# WHERE that package lives is configuration, not an assumption about the filesystem.
# It used to be computed purely from `__file__`, which silently encoded "the API always runs
# from a full repository checkout". In a container it resolved to `/packages/brand/assets` --
# outside `/app`, a directory that could not exist, because the image build context was
# `services/commerce-api` and `packages/` was never in it. Nothing failed loudly: the image
# built, the container started, `/ready` returned 200, and every brand and product media URL
# returned 404 in every containerised deployment.
BRAND_MEDIA_ROOT_ENV = "BRAND_MEDIA_ROOT"

def _checkout_media_root() -> Path | None:
    """The checkout's asset directory, or None when this file is not in a checkout.

    LAZY, and computed defensively. Written first as a module-level
    `Path(__file__).resolve().parents[4]`, it raised IndexError on import inside the
    container -- `/app/app/commerce/api.py` simply does not have four parents -- which
    took the whole application down before the configured root could even be consulted.
    That is the same module-level path assumption this change exists to remove, so it is
    worth being explicit: there is no guaranteed repository above this file.
    """

    here = Path(__file__).resolve()
    if len(here.parents) < 5:
        return None
    # app/commerce -> app -> commerce-api -> services -> repository root
    return here.parents[4] / "packages" / "brand" / "assets"


def resolve_media_root() -> Path | None:
    """The directory brand and product assets are served from, or None if undeterminable.

    Read at call time, not bound at import, so a test can vary it and so a deployment is
    not required to set it before the module graph is imported.
    """

    configured = os.getenv(BRAND_MEDIA_ROOT_ENV, "").strip()
    if configured:
        return Path(configured).resolve()
    checkout = _checkout_media_root()
    return checkout.resolve() if checkout is not None else None


class MediaRootUnavailable(Exception):
    """The configured asset root is absent. Deployment fault, not a missing asset."""


def assert_media_root() -> Path:
    """Return the asset root, or raise if it is not there.

    The distinction this preserves is the whole point: a MISSING ASSET is a 404, and a
    MISSING ASSET ROOT is a deployment failure. Collapsing them into 404 is precisely how
    an image shipped with no assets at all looked healthy for two days.
    """

    root = resolve_media_root()
    if root is None:
        raise MediaRootUnavailable(
            f"{BRAND_MEDIA_ROOT_ENV} is not set and this installation is not inside a "
            "repository checkout, so there is nowhere to serve brand assets from."
        )
    if not root.is_dir():
        raise MediaRootUnavailable(
            f"brand media root {root} does not exist. Set {BRAND_MEDIA_ROOT_ENV} to the "
            "packaged asset directory, or run from a repository checkout containing "
            "packages/brand/assets."
        )
    return root

# Allow-list, not a deny-list. A deny-list has to anticipate every dangerous extension; an
# allow-list only has to name the four types this package actually contains.
_MEDIA_TYPES = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


@router.get("/media/{asset_path:path}")
def get_media(asset_path: str) -> FileResponse:
    """Serve one brand or product asset.

    Deliberately narrow. Everything that is not an explicitly allowed file under the
    generated asset root is a 404 — including directories, dotfiles and anything whose
    resolved path escapes the root.
    """

    # Reject traversal on the RAW input first. `..` never has a legitimate meaning here, and
    # checking before normalisation means an encoded or nested form cannot slip through by
    # collapsing into something innocent.
    if ".." in asset_path or asset_path.startswith("/") or "\\" in asset_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "asset not found")

    # A dot-prefixed segment is never a published asset, but it is exactly what a probe for
    # .git/.env looks like.
    if any(segment.startswith(".") for segment in asset_path.split("/") if segment):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "asset not found")

    # Resolved per request so the traversal and containment checks below run against the
    # SAME root the file is read from, and so a misdeployment reports itself as 503
    # rather than masquerading as 404 on every asset.
    try:
        media_root = assert_media_root()
    except MediaRootUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    candidate = (media_root / asset_path).resolve()

    # The containment check is the real control; the checks above are cheap early exits.
    # `is_relative_to` compares resolved paths, so a symlink pointing outside is caught too.
    if not candidate.is_relative_to(media_root):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "asset not found")

    # A directory is a 404, not a listing. There is no index and no autoindex anywhere.
    if not candidate.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "asset not found")

    media_type = _MEDIA_TYPES.get(candidate.suffix.lower())
    if media_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "asset not found")

    return FileResponse(
        candidate,
        media_type=media_type,
        headers={
            # These are prototype SVGs — active content. nosniff stops a browser
            # re-interpreting a response as something more dangerous than we declared.
            "X-Content-Type-Options": "nosniff",
            # Concept artwork is regenerated by the build; a long cache would serve stale
            # imagery after a rebuild without any way to invalidate it.
            "Cache-Control": "public, max-age=300",
        },
    )


# ---------------------------------------------------------------------------- schemas


# A deliberately permissive address pattern. Strict RFC 5322 validation rejects
# addresses that real mail systems accept; deliverability is proven by sending a
# confirmation, not by a regex.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=1, max_length=200)
    marketing_consent: bool = False


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class AddToCartRequest(BaseModel):
    variant_id: int
    quantity: int = Field(gt=0, le=100)


class CheckoutRequest(BaseModel):
    payment_method_token: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=80)
    country_code: str = Field(default="DE", pattern=r"^[A-Z]{2}$")
    promotion_code: str = Field(default="", max_length=40)


class VariantSpec(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    size: str = Field(min_length=1, max_length=20)
    color: str = Field(min_length=1, max_length=40)
    price_minor_units: int = Field(gt=0, strict=True)
    on_hand: int = Field(default=0, ge=0, strict=True)


class CreateProductRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=140, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=4000)
    material: str = Field(default="", max_length=200)
    care_instructions: str = Field(default="", max_length=300)
    country_of_origin: str = Field(default="", max_length=2)
    collection: str = Field(default="", max_length=80)
    image_url: str = Field(default="", max_length=300)
    is_active: bool = False
    variants: list[VariantSpec] = Field(min_length=1)


class StockAdjustRequest(BaseModel):
    delta: int = Field(strict=True)
    reason: str = Field(min_length=1, max_length=200)


class ReturnRequestBody(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


# ------------------------------------------------------------------------------- auth


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, session: Annotated[Session, Depends(get_session)]):
    try:
        customer = services.register_customer(
            session,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            marketing_consent=body.marketing_consent,
        )
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    session.commit()
    return TokenResponse(access_token=issue_token(customer.id, customer.role), role=customer.role)


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Annotated[Session, Depends(get_session)]):
    try:
        customer = services.authenticate(session, email=body.email, password=body.password)
    except services.DomainError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(access_token=issue_token(customer.id, customer.role), role=customer.role)


# --------------------------------------------------------------------------- discovery


@router.get("/commerce/mode")
def commerce_mode() -> dict:
    """What this deployment is, so a client can say so truthfully.

    Unauthenticated and read-only: the disclosure is for every visitor, and a storefront
    banner must be right before anyone signs in. It reveals nothing that the behaviour of
    the cart and checkout endpoints does not already reveal.

    A refused or unknown mode answers 200 with the BLOCKED disclosure rather than 500.
    `current_mode()` raises for PUBLIC_COMMERCE_MODE, and a client that receives an
    unexplained error has no way to say anything honest -- it would fall back to whatever
    its markup shipped with, which is precisely the defect this closes. The refusal itself
    is untouched: every purchase path still calls `current_mode()` and still raises.
    """

    try:
        mode = modes.current_mode()
    except modes.CommerceModeError:
        mode = None
    return modes.describe(mode)


@router.get("/catalog/products")
def list_products(
    session: Annotated[Session, Depends(get_session)],
    category: str = "",
    collection: str = "",
    q: str = "",
    sort: str = "name",
):
    stmt = select(Product).where(Product.is_active.is_(True))

    # Legacy-catalogue isolation.
    #
    # In the DEDUNET customer-facing mode the catalogue is the DEDUNET catalogue: exactly
    # the 5 imported products. The legacy MERET fixture is not deleted — it is referenced by
    # existing orders, whose line items are financial records — it is simply not shown.
    #
    # Scoped by MODE rather than by a new setting, because a second switch could disagree
    # with the first and there is then no single answer to "what is a customer looking at".
    # COMMERCE_TEST_MODE keeps showing everything, which is what the sandbox demo needs.
    if modes.is_preview_mode():
        stmt = stmt.where(Product.external_product_id.is_not(None))

    if category:
        stmt = stmt.where(Product.category == category)
    if collection:
        stmt = stmt.where(Product.collection == collection)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))

    products = list(session.scalars(stmt).all())
    if sort == "price":
        products.sort(key=lambda p: min((v.price_minor_units for v in p.variants), default=0))
    else:
        products.sort(key=lambda p: p.name)

    return [_product_payload(session, p) for p in products]


@router.get("/catalog/products/{slug}")
def get_product(slug: str, session: Annotated[Session, Depends(get_session)]):
    product = session.scalar(select(Product).where(Product.slug == slug))
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    # Same scope as the listing. Filtering only the list would leave every legacy product
    # reachable by direct URL, which is a filter a deep link simply walks around.
    if modes.is_preview_mode() and product.external_product_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "product not found")
    return _product_payload(session, product)


def _product_payload(session: Session, product: Product) -> dict:
    from .inventory import available_quantity

    return {
        "slug": product.slug,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "collection": product.collection,
        "material": product.material,
        "care_instructions": product.care_instructions,
        "country_of_origin": product.country_of_origin,
        "currency": product.currency,
        # Retained as a DERIVED convenience for legacy consumers. `media` below is the
        # authoritative representation (CONFLICT-007).
        "image_url": product.image_url,
        # --- stable external identity ----------------------------------------------
        "external_product_id": product.external_product_id,
        "collection_id": product.collection_id,
        # --- typed states, so a consumer never parses prose to decide -------------
        "publication_status": product.publication_status,
        "sellable": product.sellable,
        "inventory_status": product.inventory_status,
        "evidence_status": product.evidence_status,
        "material_claim_status": product.material_claim_status,
        # `intended_origin` is shipped alongside `origin_claim_status` deliberately: a
        # consumer that reads one without the other could render an intended origin as a
        # verified one, which is the exact claim this programme may not make.
        "origin_claim_status": product.origin_claim_status,
        "intended_origin": product.intended_origin,
        "legal_brand_status": product.legal_brand_status,
        "media_status": product.media_status,
        "media": [
            {
                "asset_id": m.asset_id,
                "role": m.role,
                "sort_order": m.sort_order,
                "path": m.path,
                # Fetchable URL. Clients use this; `path` stays for provenance only, so no
                # consumer has to build a URL from a filesystem path itself.
                "url": f"/api/v1/media/{m.path}",
                "alt_text": m.alt_text,
                "status": m.status,
            }
            for m in sorted(product.media, key=lambda m: (m.sort_order, m.asset_id))
        ],
        "variants": [
            {
                "id": v.id,
                "sku": v.sku,
                "size": v.size,
                "color": v.color,
                "price_minor_units": v.price_minor_units,
                "available": available_quantity(session, v.id),
                "external_variant_id": v.external_variant_id,
                "sellable": v.sellable,
                "inventory_status": v.inventory_status,
                "evidence_status": v.evidence_status,
            }
            for v in product.variants
        ],
        # ------------------------------------------------------- fashion network
        #
        # ADDITIVE ONLY. Every key above is unchanged and in the same place, so the admin
        # client, the Android preview and the accepted consumer build all keep working
        # against this payload without a change. A consumer that ignores everything below
        # behaves exactly as it did before this phase.
        "brand": brand_api.brand_summary(product.brand) if product.brand else None,
        "commerce_route": brand_api._route_of(product).value,
        # THE COMMERCE CONTRACT. One server-side decision, so no client re-derives a
        # purchase gate and drifts from the server's answer -- the defect that shipped once
        # already, when the page offered a purchase the API then refused with a 409.
        "commerce_action": brand_api.commerce_action(
            route=brand_api._route_of(product),
            sellable=product.sellable,
            brand=product.brand,
            external_url=product.external_buy_url,
        ).as_dict(),
        "availability": brand_api.availability_payload(product),
    }


# ------------------------------------------------------------------------ fashion network


@router.get("/brands")
def list_brands(
    session: Annotated[Session, Depends(get_session)],
    q: str = "",
    country: str = "",
    sort: str = "name",
    limit: int = 50,
    offset: int = 0,
):
    """The brand network, as a consumer sees it.

    Pagination is bounded rather than optional. `limit` is clamped to 100: an unbounded
    `?limit=` on a list endpoint is a cheap way to make the database do arbitrary work from
    an unauthenticated request, and the media-heavy brand payload makes that worse.

    Development fixtures are included or excluded by `brands_visible`, which keys the
    decision off the commerce mode rather than a flag -- see the note there.
    """

    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    stmt = brand_api.brands_visible(session)
    if q:
        stmt = stmt.where(Brand.name.ilike(f"%{q}%"))
    if country:
        stmt = stmt.where(Brand.country_code == country.upper()[:2])

    total = session.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0

    if sort == "newest":
        stmt = stmt.order_by(Brand.created_at.desc(), Brand.name)
    else:
        # Fixtures last whatever the sort, so a real brand is never displaced by one.
        stmt = stmt.order_by(Brand.is_development_fixture, Brand.name)

    brands = list(session.scalars(stmt.limit(limit).offset(offset)).all())
    brand_ids = [b.id for b in brands]
    counts = brand_api.product_count_map(session, brand_ids)
    covers = brand_api.cover_image_map(session, brand_ids)

    return {
        "items": [
            brand_api.brand_summary(
                b,
                product_count=counts.get(b.id, 0),
                cover_image_url=covers.get(b.id, ""),
            )
            for b in brands
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/brands/{slug}")
def get_brand(slug: str, session: Annotated[Session, Depends(get_session)]):
    """One brand and its catalogue.

    404 rather than 403 for a brand the caller may not see. A 403 confirms the row exists,
    which is the enumeration leak the target architecture calls out for tenant-scoped reads;
    the same reasoning applies to an unpublished brand.
    """

    brand = session.scalar(brand_api.brands_visible(session).where(Brand.slug == slug))
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "brand not found")

    stmt = select(Product).where(Product.brand_id == brand.id, Product.is_active.is_(True))
    # The same preview-mode scoping the catalogue listing applies, so a brand page cannot
    # become a way around it.
    if modes.is_preview_mode():
        stmt = stmt.where(Product.external_product_id.is_not(None))
    products = sorted(session.scalars(stmt).all(), key=lambda p: p.name)

    return brand_api.brand_detail(session, brand, products=products)


@router.get("/admin/brands")
def admin_list_brands(
    session: Annotated[Session, Depends(get_session)],
    admin: Annotated[Customer, Depends(current_admin)],
):
    """Internal brand inspection. NOT the merchant portal -- that is Phase 5.

    Shows what a consumer is deliberately not shown: the raw ownership type, the merchant
    organisation behind a merchant-owned brand, the fixture flag, provenance and the routes
    actually in use. Read-only: this phase gives operators sight of the new domain, not a
    way to reassign ownership, which needs the audited write path Phase 5 builds.
    """

    brands = list(session.scalars(select(Brand).order_by(Brand.name)).all())
    counts = brand_api.product_count_map(session, [b.id for b in brands])
    return {
        "items": [
            brand_api.brand_admin_row(session, b, product_count=counts.get(b.id, 0))
            for b in brands
        ],
        "total": len(brands),
    }


# -------------------------------------------------------------------------------- cart


@router.post("/cart/items")
def add_item(
    body: AddToCartRequest,
    session: Annotated[Session, Depends(get_session)],
    x_cart_token: Annotated[str, Header()] = "",
):
    cart = services.get_or_create_cart(session, token=x_cart_token or None, customer_id=None)
    try:
        services.add_to_cart(session, cart, variant_id=body.variant_id, quantity=body.quantity)
    except services.NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    session.commit()
    return _cart_payload(cart)


@router.delete("/cart/items/{variant_id}")
def remove_item(
    variant_id: int,
    session: Annotated[Session, Depends(get_session)],
    x_cart_token: Annotated[str, Header()] = "",
):
    cart = services.get_or_create_cart(session, token=x_cart_token or None, customer_id=None)
    try:
        services.remove_from_cart(session, cart, variant_id=variant_id)
    except services.NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    session.commit()
    return _cart_payload(cart)


@router.get("/cart")
def view_cart(
    session: Annotated[Session, Depends(get_session)],
    x_cart_token: Annotated[str, Header()] = "",
):
    cart = services.get_or_create_cart(session, token=x_cart_token or None, customer_id=None)
    session.commit()
    return _cart_payload(cart)


def _cart_payload(cart) -> dict:
    return {
        "cart_token": cart.token,
        "status": cart.status,
        "lines": [
            {
                "variant_id": line.variant_id,
                "sku": line.variant.sku,
                "product_name": line.variant.product.name,
                "size": line.variant.size,
                "color": line.variant.color,
                "quantity": line.quantity,
                "unit_price_minor_units": line.variant.price_minor_units,
            }
            for line in cart.lines
        ],
    }


@router.get("/cart/quote")
def quote(
    session: Annotated[Session, Depends(get_session)],
    x_cart_token: Annotated[str, Header()] = "",
    country_code: str = "DE",
    promotion_code: str = "",
):
    cart = services.get_or_create_cart(session, token=x_cart_token or None, customer_id=None)
    try:
        breakdown = services.quote_cart(
            session, cart, country_code=country_code, promotion_code=promotion_code
        )
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    session.commit()
    return breakdown.as_dict()


# ---------------------------------------------------------------------------- checkout


@router.post("/checkout", status_code=201)
def do_checkout(
    body: CheckoutRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    customer: Annotated[Customer, Depends(current_customer)],
    x_cart_token: Annotated[str, Header()] = "",
):
    if not x_cart_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Cart-Token header is required")
    cart = services.get_or_create_cart(session, token=x_cart_token, customer_id=customer.id)

    try:
        result = services.checkout(
            session,
            cart,
            customer=customer,
            payment_method_token=body.payment_method_token,
            idempotency_key=body.idempotency_key,
            country_code=body.country_code,
            promotion_code=body.promotion_code,
            correlation_id=correlation_id(request),
        )
    except payments.PaymentDeclined:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "payment was declined")
    except payments.PaymentError:
        # 503 signals "retry later"; the customer was not charged.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "payment provider unavailable, please retry"
        )
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    return {"order": _order_payload(result.order), "replayed": result.replayed}


def _order_payload(order: Order) -> dict:
    return {
        "order_number": order.order_number,
        "status": order.status.value,
        # Provenance. A consumer must be able to tell a sandbox test order from anything
        # else without inferring it from a payment token or a product name.
        "commerce_mode_at_checkout": order.commerce_mode_at_checkout,
        "is_test_order": order.commerce_mode_at_checkout == "COMMERCE_TEST_MODE",
        "currency": order.currency,
        "subtotal_minor_units": order.subtotal_minor_units,
        "discount_minor_units": order.discount_minor_units,
        "shipping_minor_units": order.shipping_minor_units,
        "tax_minor_units": order.tax_minor_units,
        "total_minor_units": order.total_minor_units,
        "promotion_code": order.promotion_code,
        "placed_at": as_utc(order.placed_at).isoformat() if order.placed_at else None,
        "lines": [
            {
                "sku": line.sku,
                "product_name": line.product_name,
                "size": line.size,
                "color": line.color,
                "quantity": line.quantity,
                "unit_price_minor_units": line.unit_price_minor_units,
                "line_total_minor_units": line.line_total_minor_units,
            }
            for line in order.lines
        ],
        "shipments": [
            {
                "carrier": s.carrier,
                "tracking_number": s.tracking_number,
                "status": s.status.value,
            }
            for s in order.shipments
        ],
    }


# ------------------------------------------------------------------------ my account


@router.get("/me/orders")
def my_orders(
    session: Annotated[Session, Depends(get_session)],
    customer: Annotated[Customer, Depends(current_customer)],
):
    orders = session.scalars(
        select(Order).where(Order.customer_id == customer.id).order_by(Order.id.desc())
    ).all()
    return [_order_payload(o) for o in orders]


@router.get("/me/orders/{order_number}")
def my_order(
    order_number: str,
    session: Annotated[Session, Depends(get_session)],
    customer: Annotated[Customer, Depends(current_customer)],
):
    order = session.scalar(select(Order).where(Order.order_number == order_number))
    # Ownership is checked before existence is revealed, so this endpoint cannot be used
    # to enumerate other customers' order numbers.
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    return _order_payload(order)


@router.post("/me/orders/{order_number}/returns", status_code=201)
def create_return(
    order_number: str,
    body: ReturnRequestBody,
    session: Annotated[Session, Depends(get_session)],
    customer: Annotated[Customer, Depends(current_customer)],
):
    order = session.scalar(select(Order).where(Order.order_number == order_number))
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    try:
        request_row = services.request_return(session, order, reason=body.reason)
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return {"return_id": request_row.id, "status": request_row.status.value}


@router.get("/me/data-export")
def data_export(
    session: Annotated[Session, Depends(get_session)],
    customer: Annotated[Customer, Depends(current_customer)],
):
    return services.export_customer_data(session, customer)


@router.delete("/me", status_code=200)
def erase_me(
    session: Annotated[Session, Depends(get_session)],
    customer: Annotated[Customer, Depends(current_customer)],
):
    services.erase_customer(session, customer, actor=f"customer:{customer.id}")
    return {"erased": True, "note": "order history retained for financial reconciliation"}


# ------------------------------------------------------------------------------ admin


# Namespaced under /admin/catalog to avoid colliding with the legacy fixture-backed
# /api/v1/admin/products endpoint, which is a different resource with a different auth
# model (shared header token vs. role-based session). Two auth models on one path would
# make the effective guard depend on router registration order.
@router.post("/admin/catalog/products", status_code=201)
def admin_create_product(
    body: CreateProductRequest,
    session: Annotated[Session, Depends(get_session)],
    admin: Annotated[Customer, Depends(current_admin)],
):
    try:
        product = services.create_product(
            session,
            actor=admin.email,
            slug=body.slug,
            name=body.name,
            category=body.category,
            description=body.description,
            material=body.material,
            care_instructions=body.care_instructions,
            country_of_origin=body.country_of_origin,
            collection=body.collection,
            image_url=body.image_url,
            is_active=body.is_active,
            variants=[v.model_dump() for v in body.variants],
        )
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return _product_payload(session, product)


@router.post("/admin/variants/{variant_id}/stock")
def admin_adjust_stock(
    variant_id: int,
    body: StockAdjustRequest,
    session: Annotated[Session, Depends(get_session)],
    admin: Annotated[Customer, Depends(current_admin)],
):
    try:
        item = services.adjust_stock(
            session, actor=admin.email, variant_id=variant_id, delta=body.delta, reason=body.reason
        )
    except services.NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return {"variant_id": variant_id, "on_hand": item.on_hand, "reserved": item.reserved}


@router.get("/admin/orders")
def admin_list_orders(
    session: Annotated[Session, Depends(get_session)],
    admin: Annotated[Customer, Depends(current_admin)],
    order_status: str = "",
):
    stmt = select(Order).order_by(Order.id.desc())
    orders = list(session.scalars(stmt).all())
    if order_status:
        orders = [o for o in orders if o.status.value == order_status]
    return [_order_payload(o) for o in orders]


@router.post("/admin/orders/{order_number}/fulfil")
def admin_fulfil(
    order_number: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    admin: Annotated[Customer, Depends(current_admin)],
):
    order = session.scalar(select(Order).where(Order.order_number == order_number))
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    try:
        shipment = services.fulfil_order(
            session, order, actor=admin.email, correlation_id=correlation_id(request)
        )
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return {
        "order_number": order.order_number,
        "status": order.status.value,
        "tracking_number": shipment.tracking_number,
    }


@router.post("/admin/orders/{order_number}/cancel")
def admin_cancel(
    order_number: str,
    session: Annotated[Session, Depends(get_session)],
    admin: Annotated[Customer, Depends(current_admin)],
):
    order = session.scalar(select(Order).where(Order.order_number == order_number))
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    try:
        services.cancel_order(session, order, actor=admin.email)
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return {"order_number": order.order_number, "status": order.status.value}


@router.post("/admin/returns/{return_id}/approve")
def admin_approve_return(
    return_id: int,
    session: Annotated[Session, Depends(get_session)],
    admin: Annotated[Customer, Depends(current_admin)],
):
    request_row = session.get(ReturnRequest, return_id)
    if request_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "return not found")
    try:
        services.approve_return(session, request_row, actor=admin.email)
    except services.DomainError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return {"return_id": return_id, "status": request_row.status.value}
