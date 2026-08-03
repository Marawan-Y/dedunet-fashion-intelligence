"""HTTP API for the commerce domain.

Error handling policy: domain rule violations become 4xx with a short, non-leaking
message. Provider and infrastructure failures become 502/503. Nothing returns a raw
exception string, stack trace or provider payload to the client.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import payments, services
from .db import get_session
from .models import Customer, Order, Product, ReturnRequest, Variant
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


@router.get("/catalog/products")
def list_products(
    session: Annotated[Session, Depends(get_session)],
    category: str = "",
    collection: str = "",
    q: str = "",
    sort: str = "name",
):
    stmt = select(Product).where(Product.is_active.is_(True))
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
        "image_url": product.image_url,
        "variants": [
            {
                "id": v.id,
                "sku": v.sku,
                "size": v.size,
                "color": v.color,
                "price_minor_units": v.price_minor_units,
                "available": available_quantity(session, v.id),
            }
            for v in product.variants
        ],
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
        "currency": order.currency,
        "subtotal_minor_units": order.subtotal_minor_units,
        "discount_minor_units": order.discount_minor_units,
        "shipping_minor_units": order.shipping_minor_units,
        "tax_minor_units": order.tax_minor_units,
        "total_minor_units": order.total_minor_units,
        "promotion_code": order.promotion_code,
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
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
