from __future__ import annotations

from hmac import compare_digest
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .ai_stylist import recommend_products
from .candidate_activation import (
    BusinessLifecycle,
    CandidateProduct,
    PublicationStatus,
    validate_candidate_collection,
)
from .catalog import CatalogRepository
from .config import settings
from .money import sum_line_totals
from .schemas import OrderQuote, OrderQuoteRequest, Product, StylistRecommendation, StylistRequest

app = FastAPI(
    title="Fashion Commerce Platform PoC API",
    version="0.1.0",
    description="Vertical-slice API for catalog, inventory visibility, quote and AI stylist demo.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)

repo = CatalogRepository(Path(__file__).resolve().parents[1] / "data" / "products.json")
candidate_path = Path(__file__).resolve().parents[1] / "data" / "candidate_products.json"


def load_candidate_products() -> list[CandidateProduct]:
    import json

    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    return [CandidateProduct.model_validate(item) for item in payload]


def require_admin(x_admin_token: str = Header(default="")) -> None:
    """Fail-closed admin gate for the PoC.

    Risk SB-RISK-B5-001: the shipped placeholder token (`change-me`/empty) must never
    authorize a privileged write outside a local development environment. This is a
    minimum PoC control, NOT an authentication system: there is no identity, no MFA,
    no rate limiting, no audit trail and no rotation. See the launch-blocker audit.
    """

    if settings.admin_token_is_default:
        # Unsafe-default guard: a shipped placeholder credential authorizes nothing,
        # in ANY environment. The operator must configure a real token first.
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin API disabled: the placeholder ADMIN_API_TOKEN authorizes nothing. "
                f"Configure a unique token before use (current APP_ENV={settings.app_env})."
            ),
        )
    if not x_admin_token or not compare_digest(x_admin_token, settings.admin_api_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/api/v1/products", response_model=list[Product])
def list_products(
    category: str | None = Query(default=None),
    collection: str | None = Query(default=None),
) -> list[Product]:
    products = repo.list_products(active_only=True)
    if category:
        products = [item for item in products if item.category == category]
    if collection:
        products = [item for item in products if item.collection.lower() == collection.lower()]
    return products


@app.get("/api/v1/products/{slug}", response_model=Product)
def get_product(slug: str) -> Product:
    product = repo.get_by_slug(slug)
    if not product or not product.active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/v1/candidate-products", response_model=list[CandidateProduct])
def list_candidate_products() -> list[CandidateProduct]:
    """Return local synthetic candidates, never an activated sellable catalog."""

    return load_candidate_products()


@app.get("/api/v1/candidate-products/{product_id}/activation")
def assess_candidate_activation(product_id: str) -> dict:
    candidate = next(
        (item for item in load_candidate_products() if item.product_id == product_id),
        None,
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate product not found")
    requested = candidate.model_copy(
        update={
            "lifecycle_status": BusinessLifecycle.SELLABLE,
            "publication_status": PublicationStatus.PUBLIC,
        }
    )
    errors = validate_candidate_collection([requested])
    return {
        "product_id": product_id,
        "current_lifecycle": candidate.lifecycle_status,
        "current_publication": candidate.publication_status,
        "requested_lifecycle": BusinessLifecycle.SELLABLE,
        "requested_publication": PublicationStatus.PUBLIC,
        "eligible": not errors,
        "errors": [item.model_dump(mode="json") for item in errors],
    }


@app.post(
    "/api/v1/admin/products",
    response_model=Product,
    dependencies=[Depends(require_admin)],
)
def upsert_product(product: Product) -> Product:
    return repo.upsert(product)


@app.post("/api/v1/stylist/recommend", response_model=StylistRecommendation)
def stylist(request: StylistRequest) -> StylistRecommendation:
    return recommend_products(request, repo.list_products(active_only=True))


@app.post("/api/v1/orders/quote", response_model=OrderQuote)
def quote_order(request: OrderQuoteRequest) -> OrderQuote:
    products = repo.list_products(active_only=True)
    variant_index = {
        variant.sku: (product, variant)
        for product in products
        for variant in product.variants
    }
    # Authoritative arithmetic is integer minor units only (SB-AR-B3-003).
    line_items: list[tuple[int, int]] = []
    for item in request.items:
        if item.sku not in variant_index:
            raise HTTPException(status_code=400, detail=f"Unknown SKU: {item.sku}")
        product, variant = variant_index[item.sku]
        if product.currency != settings.store_currency:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Currency mismatch for {item.sku}: product is {product.currency}, "
                    f"store is {settings.store_currency}"
                ),
            )
        if item.quantity > variant.stock:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for {item.sku}; available={variant.stock}",
            )
        line_items.append((product.price_minor_units, item.quantity))

    subtotal_minor_units = sum_line_totals(line_items)
    shipping_minor_units = (
        0
        if subtotal_minor_units >= settings.free_shipping_threshold_minor_units
        else settings.default_shipping_minor_units
    )
    return OrderQuote(
        currency=settings.store_currency,
        subtotal_minor_units=subtotal_minor_units,
        shipping_minor_units=shipping_minor_units,
        total_minor_units=subtotal_minor_units + shipping_minor_units,
        note=(
            "PoC quote excludes VAT, customs, payment authorization and carrier rates. "
            "Amounts are integer minor units; *_display values are derived for presentation "
            "only. Production must calculate tax/duty/carrier rates from the merchant/import "
            "model and destination."
        ),
    )
