from decimal import Decimal
from pathlib import Path
import json
import sys

# parents[2] is the repository root: validation/ -> scripts/ -> root
ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "commerce-api"
sys.path.insert(0, str(SERVICE))

from app.money import from_minor_units  # noqa: E402
from app.schemas import Product  # noqa: E402

path = SERVICE / "data" / "products.json"
# parse_float=Decimal keeps fixture money exact; a binary float never enters the path.
items = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
products = [Product.model_validate(item) for item in items]

ids = [product.id for product in products]
if len(ids) != len(set(ids)):
    raise SystemExit("Duplicate product ID detected")

skus = [variant.sku for product in products for variant in product.variants]
if len(skus) != len(set(skus)):
    raise SystemExit("Duplicate SKU detected")

for product in products:
    if not isinstance(product.price_minor_units, int):
        raise SystemExit(f"{product.id}: price is not stored as integer minor units")
    # Round-trip proves the stored integer represents the source amount exactly.
    if from_minor_units(product.price_minor_units, product.currency) * 100 != product.price_minor_units:
        raise SystemExit(f"{product.id}: minor-unit round trip is not exact")

print(f"Validated {len(products)} products and {len(skus)} unique SKUs")
print(
    "Authoritative prices (integer minor units): "
    + ", ".join(f"{p.id}={p.price_minor_units} {p.currency}" for p in products)
)
