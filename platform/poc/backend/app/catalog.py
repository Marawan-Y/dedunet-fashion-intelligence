from __future__ import annotations

import json
import threading
from decimal import Decimal
from pathlib import Path

from .schemas import Product


class DecimalPreservingEncoder(json.JSONEncoder):
    """Serialize ``Decimal`` exactly instead of degrading it to a binary float."""

    def default(self, o: object):  # noqa: ANN401 - json API signature
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


class CatalogRepository:
    """JSON-backed PoC catalog.

    Money rule (SB-AR-B3-003): the file is parsed with ``parse_float=Decimal`` so a
    decimal amount in the fixture never becomes a binary float in memory. The schema
    then converts it to authoritative integer minor units.

    Concurrency limitation: a process-local ``threading.Lock`` is NOT a transaction and
    does not protect against multi-process or multi-replica writes. See risk
    SB-RISK-B12-001 (non-transactional inventory/catalog persistence).
    """

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def read_raw(self) -> list[dict]:
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle, parse_float=Decimal)
        if not isinstance(data, list):
            raise ValueError("Catalog file must contain a JSON array")
        return data

    # Backwards-compatible private alias used by earlier revisions.
    _read_raw = read_raw

    def list_products(self, active_only: bool = True) -> list[Product]:
        products = [Product.model_validate(item) for item in self.read_raw()]
        return [p for p in products if p.active] if active_only else products

    def get_by_slug(self, slug: str) -> Product | None:
        return next((p for p in self.list_products(False) if p.slug == slug), None)

    def upsert(self, product: Product) -> Product:
        with self._lock:
            current = [Product.model_validate(item) for item in self.read_raw()]
            by_id = {item.id: item for item in current}
            by_id[product.id] = product
            payload = [
                item.model_dump(mode="json", exclude={"price_display"})
                for item in by_id.values()
            ]
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, cls=DecimalPreservingEncoder),
                encoding="utf-8",
            )
        return product
