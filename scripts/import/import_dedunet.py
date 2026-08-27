"""Transactional, idempotent importer for the normalized DEDUNET brand package.

Reads `packages/brand/` — never the immutable handoff — and writes products, variants and
product media.

Design commitments, each because the opposite has a specific failure mode:

  - **Validate everything BEFORE writing.** A half-imported catalogue is worse than none,
    because the missing half is invisible.
  - **One transaction.** Any failure rolls the whole import back.
  - **Idempotent on external identity.** Re-running matches `external_product_id` /
    `external_variant_id` and updates in place. Matching on slug or name would create a
    second copy the moment Side A renamed anything.
  - **Never silently deletes.** A record present in the database but absent from the
    package is REPORTED, not removed. Deleting a product silently would take its order
    history's referential integrity with it.
  - **Refuses rather than repairs.** Invalid money, orphan variants, duplicate SKUs,
    missing assets and non-zero prototype stock all abort.

Usage:
    python scripts/import/import_dedunet.py --dry-run
    python scripts/import/import_dedunet.py --only DDN-TS01
    python scripts/import/import_dedunet.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "packages" / "brand"
SIDE_A = ROOT / "handoffs" / "incoming" / "side-a" / "DEDUNET_Platform_Integration_v1"

sys.path.insert(0, str(ROOT / "services" / "commerce-api"))

from contextlib import contextmanager  # noqa: E402
from typing import Iterator  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.commerce.brand_registry import brand_for_product  # noqa: E402
from app.commerce.db import SessionLocal  # noqa: E402
from app.commerce.models import InventoryItem, Product, ProductMedia, Variant  # noqa: E402


@contextmanager
def session_scope(*, read_only: bool = False) -> Iterator[Session]:
    """One transaction for the whole import.

    Commits once at the end, rolls back everything on any exception. A per-record commit
    would leave a partially imported catalogue behind on failure, which is exactly what
    "transactional" is meant to prevent. `read_only` never commits, so a dry run cannot
    write even by accident.
    """

    session = SessionLocal()
    try:
        yield session
        if read_only:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class ImportError_(Exception):
    """Import refused. Never partially applied."""


def load(name: str) -> Any:
    path = BRAND / name
    if not path.is_file():
        raise ImportError_(
            f"{name} missing from packages/brand. Run scripts/brand/build_brand_package.py first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------ validation

def validate(products, variants, media, only: str | None) -> tuple[list, list, list, list[str]]:
    """Return the filtered payload plus a list of hard errors."""

    errors: list[str] = []

    if only:
        products = [p for p in products if p["external_product_id"] == only]
        if not products:
            errors.append(f"--only {only}: no such product in the brand package")
            return [], [], [], errors
        keep = {p["external_product_id"] for p in products}
        variants = [v for v in variants if v["external_product_id"] in keep]
        media = [m for m in media if m["external_product_id"] in keep]

    product_ids = {p["external_product_id"] for p in products}

    if len(product_ids) != len(products):
        errors.append("duplicate external_product_id in the brand package")

    slugs = [p["slug"] for p in products]
    if len(set(slugs)) != len(slugs):
        errors.append("duplicate slug in the brand package")

    skus = [v["sku"] for v in variants]
    duplicates = sorted({s for s in skus if skus.count(s) > 1})
    if duplicates:
        errors.append(f"duplicate SKUs: {duplicates}")

    variant_ids = [v["external_variant_id"] for v in variants]
    if len(set(variant_ids)) != len(variant_ids):
        errors.append("duplicate external_variant_id in the brand package")

    for v in variants:
        if v["external_product_id"] not in product_ids:
            errors.append(f"orphan variant {v['external_variant_id']}")
        if not isinstance(v["price_minor_units"], int) or isinstance(v["price_minor_units"], bool):
            errors.append(f"{v['external_variant_id']}: price is not an integer")
        elif v["price_minor_units"] <= 0:
            errors.append(f"{v['external_variant_id']}: price {v['price_minor_units']} is not positive")
        if v.get("stock_quantity", 0) != 0:
            errors.append(f"{v['external_variant_id']}: prototype stock must be 0")
        if v.get("sellable") is not False:
            errors.append(f"{v['external_variant_id']}: prototype variant must not be sellable")

    for p in products:
        if p.get("sellable") is not False:
            errors.append(f"{p['external_product_id']}: prototype product must not be sellable")
        if p.get("country_of_origin") != "XX":
            errors.append(f"{p['external_product_id']}: country_of_origin must be XX")
        if p.get("origin_claim_status") != "UNVERIFIED":
            errors.append(f"{p['external_product_id']}: origin_claim_status must be UNVERIFIED")

    seen_pairs = set()
    seen_slots = set()
    for m in media:
        if m["external_product_id"] not in product_ids:
            errors.append(f"media {m['asset_id']}: unknown product {m['external_product_id']}")
        # The asset must exist on disk. A media row pointing at nothing renders a broken
        # image in every consumer.
        if not (SIDE_A / m["path"]).is_file():
            errors.append(f"media {m['asset_id']}: file missing at {m['path']}")
        pair = (m["external_product_id"], m["asset_id"])
        if pair in seen_pairs:
            errors.append(f"duplicate media relationship {pair}")
        seen_pairs.add(pair)
        slot = (m["external_product_id"], m["role"], m["sort_order"])
        if slot in seen_slots:
            errors.append(f"duplicate media slot {slot}")
        seen_slots.add(slot)

    return products, variants, media, errors


# ---------------------------------------------------------------------------- import

def run_import(dry_run: bool, only: str | None) -> dict:
    products = load("products.json")
    variants = load("variants.json")
    media = load("product-media.json")

    products, variants, media, errors = validate(products, variants, media, only)

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "scope": only or "ALL",
        "planned": {"products": len(products), "variants": len(variants), "media": len(media)},
        "created": {"products": 0, "variants": 0, "media": 0, "inventory": 0},
        "updated": {"products": 0, "variants": 0, "media": 0},
        "unchanged": {"products": 0, "variants": 0, "media": 0},
        "conflicts": [],
        "orphans_in_database": [],
        "errors": errors,
    }

    if errors:
        result["outcome"] = "REFUSED"
        return result

    if dry_run:
        # Still touch the database read-only, so a dry run reports what WOULD change
        # rather than merely echoing the file.
        with session_scope(read_only=True) as session:
            for p in products:
                existing = session.scalar(
                    select(Product).where(Product.external_product_id == p["external_product_id"])
                )
                if existing is None:
                    result["created"]["products"] += 1
                else:
                    result["updated"]["products"] += 1
                    # A slug collision against a DIFFERENT product is a genuine conflict.
                    clash = session.scalar(select(Product).where(Product.slug == p["slug"]))
                    if clash is not None and clash.id != existing.id:
                        result["conflicts"].append(
                            f"slug {p['slug']} already used by product id {clash.id}"
                        )
            for p in products:
                clash = session.scalar(select(Product).where(Product.slug == p["slug"]))
                if clash is not None and clash.external_product_id != p["external_product_id"]:
                    result["conflicts"].append(
                        f"slug {p['slug']} belongs to external id {clash.external_product_id!r}"
                    )
            for v in variants:
                existing = session.scalar(
                    select(Variant).where(
                        Variant.external_variant_id == v["external_variant_id"]
                    )
                )
                if existing is None:
                    result["created"]["variants"] += 1
                    sku_clash = session.scalar(select(Variant).where(Variant.sku == v["sku"]))
                    if sku_clash is not None:
                        result["conflicts"].append(
                            f"SKU {v['sku']} already used by variant id {sku_clash.id}"
                        )
                else:
                    result["updated"]["variants"] += 1
            result["created"]["media"] = len(media)
        result["outcome"] = "DRY_RUN_OK" if not result["conflicts"] else "DRY_RUN_CONFLICTS"
        return result

    with session_scope() as session:
        product_row_by_external: dict[str, Product] = {}

        for p in products:
            row = session.scalar(
                select(Product).where(Product.external_product_id == p["external_product_id"])
            )
            slug_owner = session.scalar(select(Product).where(Product.slug == p["slug"]))
            if slug_owner is not None and slug_owner.external_product_id != p["external_product_id"]:
                raise ImportError_(
                    f"slug {p['slug']!r} is already used by external id "
                    f"{slug_owner.external_product_id!r}; refusing to reassign it"
                )

            created = row is None
            if created:
                row = Product(external_product_id=p["external_product_id"])
                session.add(row)

            # The DEDUNET first-party brand. Resolved through brand_registry so the importer,
            # seed() and the Alembic backfill cannot disagree about which brand this is --
            # three literals of the same slug is three chances to drift.
            row.brand_id = brand_for_product(
                session, external_product_id=p["external_product_id"]
            ).id
            # These are prototypes. NON_PURCHASABLE is the route, independently of the fact
            # that DEDUNET owns the brand -- ownership and routing are orthogonal, and the
            # commerce mode remains the outer gate over both.
            row.commerce_route = "NON_PURCHASABLE"

            # Mutable fields. `external_product_id` is never reassigned.
            row.slug = p["slug"]
            row.name = p["name"]
            row.description = p["long_description"] or p["short_description"]
            row.category = p["category"]
            row.collection = p["collection_label"][:80]
            row.collection_id = p.get("collection_id", "") or "FIRST-PASSAGE-01"
            row.material = p["source_material_statement"][:200]
            row.care_instructions = p["care_instructions"][:300]
            row.currency = p["currency"]
            row.country_of_origin = p["country_of_origin"]
            row.intended_origin = p["intended_origin"]
            row.is_active = True  # visible in the catalogue
            row.sellable = False  # but NOT purchasable
            row.publication_status = p["publication_status"]
            row.inventory_status = p["inventory_status"]
            row.evidence_status = p["evidence_status"]
            row.material_claim_status = p["material_claim_status"]
            row.origin_claim_status = p["origin_claim_status"]
            row.legal_brand_status = p["legal_brand_status"]
            row.media_status = p["media_status"]

            session.flush()
            product_row_by_external[p["external_product_id"]] = row
            result["created" if created else "updated"]["products"] += 1

        for v in variants:
            parent = product_row_by_external[v["external_product_id"]]
            row = session.scalar(
                select(Variant).where(Variant.external_variant_id == v["external_variant_id"])
            )
            sku_owner = session.scalar(select(Variant).where(Variant.sku == v["sku"]))
            if sku_owner is not None and sku_owner.external_variant_id != v["external_variant_id"]:
                raise ImportError_(
                    f"SKU {v['sku']!r} is already used by external variant "
                    f"{sku_owner.external_variant_id!r}; refusing to reassign it"
                )

            created = row is None
            if created:
                row = Variant(external_variant_id=v["external_variant_id"])
                session.add(row)

            row.product_id = parent.id
            row.sku = v["sku"]
            row.size = v["size"]
            row.color = v["color"]
            row.price_minor_units = v["price_minor_units"]
            row.sellable = False
            row.inventory_status = v["inventory_status"]
            row.evidence_status = v["evidence_status"]
            session.flush()

            inventory = session.scalar(
                select(InventoryItem).where(InventoryItem.variant_id == row.id)
            )
            if inventory is None:
                # Zero stock, explicitly. A prototype must never seed public inventory.
                session.add(InventoryItem(variant_id=row.id, on_hand=0, reserved=0))
                result["created"]["inventory"] += 1

            result["created" if created else "updated"]["variants"] += 1

        for m in media:
            parent = product_row_by_external[m["external_product_id"]]
            row = session.scalar(
                select(ProductMedia).where(
                    ProductMedia.product_id == parent.id,
                    ProductMedia.asset_id == m["asset_id"],
                )
            )
            created = row is None
            if created:
                row = ProductMedia(product_id=parent.id, asset_id=m["asset_id"])
                session.add(row)
            row.role = m["role"]
            row.sort_order = m["sort_order"]
            row.path = m["path"]
            row.alt_text = m["alt_text"][:400]
            row.status = m["status"]
            row.checksum_sha256 = m["sha256"]
            result["created" if created else "updated"]["media"] += 1

        # Derived, non-authoritative convenience for legacy consumers.
        for external_id, row in product_row_by_external.items():
            front = session.scalar(
                select(ProductMedia).where(
                    ProductMedia.product_id == row.id, ProductMedia.role == "front"
                )
            )
            row.image_url = front.path if front is not None else ""

        # Report, never delete. An imported product missing from a later package is a
        # decision for a human, not for this script.
        in_package = {p["external_product_id"] for p in products}
        for row in session.scalars(
            select(Product).where(Product.external_product_id.is_not(None))
        ).all():
            if row.external_product_id not in in_package and only is None:
                result["orphans_in_database"].append(row.external_product_id)

        session.flush()

    result["outcome"] = "IMPORTED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate and report; write nothing")
    parser.add_argument("--only", help="import a single external product id, e.g. DDN-TS01")
    parser.add_argument("--json", action="store_true", help="print machine-readable output only")
    args = parser.parse_args()

    try:
        result = run_import(dry_run=args.dry_run, only=args.only)
    except ImportError_ as exc:
        print(json.dumps({"outcome": "REFUSED", "errors": [str(exc)]}, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0 if result["outcome"] in {"IMPORTED", "DRY_RUN_OK"} else 1


if __name__ == "__main__":
    sys.exit(main())
