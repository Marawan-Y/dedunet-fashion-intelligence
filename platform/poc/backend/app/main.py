from __future__ import annotations

import json
import logging
import secrets
import sys
import time
from hmac import compare_digest
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
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
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=[
        "Content-Type",
        "X-Admin-Token",
        "Authorization",
        "X-Cart-Token",
        "X-Correlation-ID",
    ],
    expose_headers=["X-Correlation-ID"],
)

repo = CatalogRepository(Path(__file__).resolve().parents[1] / "data" / "products.json")
candidate_path = Path(__file__).resolve().parents[1] / "data" / "candidate_products.json"


# --------------------------------------------------------------------- observability

_logger = logging.getLogger("fashion_commerce")
if not _logger.handlers:  # pragma: no cover - configured once per process
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

# Field names that must never reach a log line, in any casing. Logging a password or a
# session token turns the log store into a credential store.
_REDACTED_KEYS = {
    "password", "token", "authorization", "access_token", "admin_token",
    "payment_method_token", "card", "cvv", "secret",
}


def redact(payload: dict) -> dict:
    """Replace sensitive values with a marker, recursively."""

    clean: dict = {}
    for key, value in payload.items():
        if key.lower() in _REDACTED_KEYS:
            clean[key] = "[REDACTED]"
        elif isinstance(value, dict):
            clean[key] = redact(value)
        else:
            clean[key] = value
    return clean


@app.middleware("http")
async def correlation_and_access_log(request: Request, call_next):
    """Attach a correlation ID to every request and emit one structured log line.

    The ID is echoed in the ``X-Correlation-ID`` response header and stored on
    ``request.state`` so domain code can stamp analytics events and audit rows with it.
    That is what makes a single customer journey traceable across catalog, checkout,
    payment and fulfilment instead of appearing as unrelated log entries.
    """

    correlation_id = request.headers.get("X-Correlation-ID") or secrets.token_hex(8)
    request.state.correlation_id = correlation_id

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        _logger.exception(
            json.dumps(
                {
                    "event": "request_failed",
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            )
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    _logger.info(
        json.dumps(
            redact(
                {
                    "event": "request",
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
        )
    )
    response.headers["X-Correlation-ID"] = correlation_id
    # Baseline security headers. HSTS is intentionally omitted here because it is a
    # TLS-termination concern and setting it over plain HTTP would be misleading.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


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
    """Liveness: the process is up. Deliberately does no I/O."""

    return {"status": "ok", "environment": settings.app_env}


@app.get("/ready")
def ready() -> dict[str, object]:
    """Readiness: the process can actually serve traffic.

    Distinct from liveness because a reachable process with an unreachable database
    must be taken out of the load-balancer rotation, not restarted.
    """

    checks: dict[str, str] = {}
    healthy = True

    try:
        from sqlalchemy import text as _text

        from .commerce.db import engine

        with engine.connect() as connection:
            connection.execute(_text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness must report, never raise
        checks["database"] = f"unavailable: {type(exc).__name__}"
        healthy = False

    checks["catalog_fixture"] = "ok" if repo.path.exists() else "missing"
    if checks["catalog_fixture"] != "ok":
        healthy = False

    if not healthy:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}


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


# ---------------------------------------------------------------- commerce domain

# Registered last so the pre-existing PoC routes keep their exact paths and behaviour.
# The commerce router owns /api/v1/catalog, /cart, /checkout, /me and /admin; the
# legacy /api/v1/products fixture endpoints are untouched and still fixture-backed.
from .commerce.api import router as commerce_router  # noqa: E402

app.include_router(commerce_router)
