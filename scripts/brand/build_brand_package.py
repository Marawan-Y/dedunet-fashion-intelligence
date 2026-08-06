"""Build the normalized runtime brand package from the immutable Side A delivery.

    handoffs/incoming/side-a/DEDUNET_Platform_Integration_v1/   (immutable, read-only)
        -> validation
        -> normalization
        -> packages/brand/                                      (generated, committed)
        -> web, admin, mobile, notification consumers

Applications read `packages/brand/` and NEVER the incoming handoff. Two reasons, and both
have bitten this repository before:

  1. The handoff is checksum-protected evidence. A consumer reading it directly invites an
     "adjustment" that breaks its own manifest -- and `.gitattributes` already had to be
     re-scoped once to stop Git rewriting its bytes.
  2. Side A's shapes are business artefacts (decimal prices, prose origin, flat CSVs). The
     platform's contract is integer minor units and typed states. Normalising once, here,
     means exactly one place performs that transformation.

This script is READ-ONLY with respect to the handoff. It never writes inside it.

Run:
    python scripts/brand/build_brand_package.py --check    # verify, write nothing
    python scripts/brand/build_brand_package.py            # regenerate packages/brand/
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SIDE_A = ROOT / "handoffs" / "incoming" / "side-a" / "DEDUNET_Platform_Integration_v1"
SRC = SIDE_A / "data" / "brand-prototype"
OUT = ROOT / "packages" / "brand"

# The backend owns the money contract. Importing it rather than re-implementing keeps one
# definition of "integer minor units" in the repository.
sys.path.insert(0, str(ROOT / "services" / "commerce-api"))
from app.money import FloatMoneyRejected, to_minor_units  # noqa: E402

EXPECTED = {"products": 5, "variants": 62, "skus": 62, "assets": 31, "checksums": 54}

# Media roles derived from the Side A asset-id suffix. Ordering is DETERMINISTIC and is the
# display order; leaving it to dict iteration or file order would make the gallery reshuffle
# between builds.
MEDIA_ROLE_ORDER = ["front", "back", "detail", "lifestyle", "campaign", "collection"]

BRAND_ASSET_ROLES = {
    "LOGO-PRIMARY-001": "logo_primary",
    "LOGO-COMPACT-001": "logo_compact",
    "LOGO-MONO-001": "logo_monochrome",
    "LOGO-REVERSED-001": "logo_reversed",
    "FAVICON-001": "favicon",
    "APP-ICON-001": "app_icon",
    "PATTERN-001": "pattern",
    "MEDIA-HERO-001": "hero",
    "MEDIA-COLLECTION-001": "collection_cover",
    "MEDIA-ABOUT-001": "about",
    "MEDIA-EMAIL-001": "email_banner",
    "MEDIA-APP-001": "app_splash",
    "MEDIA-SOCIAL-001": "social_avatar",
}


class NormalizationError(Exception):
    """Raised when the source cannot be normalised safely. Never repaired silently."""


errors: list[str] = []
warnings: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------- money

def price_to_minor_units(raw: Any, currency: str, where: str) -> int:
    """Convert a Side A major-unit price to integer minor units, or raise.

    Delegates to `app.money.to_minor_units`, which accepts int/str/Decimal and REJECTS
    binary floats outright. A float is refused rather than rounded because 72.00 arriving
    as 71.99999999999999 must never become 7199.

    More than two decimal places is refused for EUR: the source contract carries no
    sub-cent prices, so a third decimal means the input is wrong, not that we should round
    it away.
    """
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        raise NormalizationError(f"{where}: price is empty")

    if isinstance(raw, float):
        raise NormalizationError(
            f"{where}: price {raw!r} is a binary float; authoritative money must not be float"
        )

    text = str(raw).strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", text):
        raise NormalizationError(f"{where}: price {raw!r} is not a decimal number")

    if "." in text:
        decimals = len(text.split(".", 1)[1])
        if decimals > 2:
            raise NormalizationError(
                f"{where}: price {raw!r} has {decimals} decimal places; EUR permits at most 2"
            )

    if text.startswith("-"):
        raise NormalizationError(f"{where}: price {raw!r} is negative")

    try:
        minor = to_minor_units(text, currency)
    except (FloatMoneyRejected, ValueError) as exc:
        raise NormalizationError(f"{where}: {exc}") from exc

    if minor <= 0:
        raise NormalizationError(f"{where}: price {raw!r} converts to {minor}, which is not positive")
    return minor


# -------------------------------------------------------------------- normalization

def normalize_brand(tokens: dict) -> dict:
    return {
        "name": "DEDUNET",
        "legal_name": None,
        "domain": "dedunet.com",
        "tagline": "Worth, worn.",
        "status": {
            "brand_selection": "FOUNDER_SELECTED",
            "prototype": "PROTOTYPE_APPROVED",
            "legal": "LEGAL_CLEARANCE_PENDING",
            "public_commercial_launch": "BLOCKED",
        },
        # Recorded so no consumer can present the name as cleared or as verified history.
        "naming_risk": {
            "status": "PRELIMINARY_RISK_DISCLOSED",
            "detail": (
                "A 'DeDeNet' conflict is disclosed by Side A as a high preliminary risk. "
                "Domain ownership is not trademark clearance."
            ),
            "prohibited_narrative": (
                "DEDUNET must not be described as a historically verified Egyptian or "
                "pharaonic weaving goddess. That claim is explicitly blocked by Side A."
            ),
        },
        "source_tokens": tokens.get("brand", {}),
    }


def normalize_tokens(tokens: dict) -> tuple[dict, str]:
    """Return normalized design tokens plus a CSS custom-property sheet."""
    colors = tokens.get("colors", {})
    typography = tokens.get("typography", {})
    shape = tokens.get("shape", {})
    spacing = tokens.get("spacing", {})

    flat: dict[str, str] = {}

    def flatten(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                flatten(f"{prefix}-{key}" if prefix else str(key), inner)
        elif isinstance(value, (str, int, float)):
            flat[prefix] = str(value)

    flatten("color", colors)
    flatten("type", typography)
    flatten("shape", shape)
    flatten("space", spacing)

    def css_name(key: str) -> str:
        return "--ddn-" + re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")

    lines = [
        "/* GENERATED by scripts/brand/build_brand_package.py -- do not edit by hand. */",
        "/* Source: Side A DEDUNET_Platform_Integration_v1 brand-tokens.json */",
        ":root {",
    ]
    lines += [f"  {css_name(k)}: {v};" for k, v in sorted(flat.items())]
    lines.append("}")
    css = "\n".join(lines) + "\n"

    return {
        "colors": colors,
        "typography": typography,
        "shape": shape,
        "spacing": spacing,
        "imagery": tokens.get("imagery", {}),
        "motion": tokens.get("motion", {}),
        "css_variables": {css_name(k): v for k, v in sorted(flat.items())},
    }, css


def media_role_for(asset_id: str) -> str | None:
    suffix = asset_id.rsplit("-", 1)[-1].lower()
    return suffix if suffix in MEDIA_ROLE_ORDER else None


def normalize_assets(rows: list[dict]) -> tuple[list[dict], dict[str, dict]]:
    assets = []
    by_id: dict[str, dict] = {}
    for row in rows:
        asset_id = row["asset_id"].strip()
        rel = row["path"].strip().lstrip("/")
        target = SIDE_A / rel
        if not target.is_file():
            fail(f"asset {asset_id}: file missing at {rel}")
            continue
        record = {
            "asset_id": asset_id,
            "path": rel,
            "purpose": row.get("purpose", "").strip(),
            "ratio": row.get("ratio", "").strip(),
            "status": row.get("status", "").strip(),
            "ownership_status": row.get("ownership_status", "").strip(),
            "alt_text": row.get("alt_text", "").strip(),
            "human_review_required": row.get("human_review_required", "").strip().lower() == "yes",
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size,
            "brand_role": BRAND_ASSET_ROLES.get(asset_id),
            "media_role": media_role_for(asset_id),
        }
        assets.append(record)
        if asset_id in by_id:
            fail(f"duplicate asset id {asset_id}")
        by_id[asset_id] = record
    return assets, by_id


def normalize_products(
    products_raw: list[dict], assets_by_id: dict[str, dict]
) -> tuple[list[dict], list[dict]]:
    products: list[dict] = []
    media: list[dict] = []
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()

    for item in products_raw:
        external_id = str(item["product_id"]).strip()
        if external_id in seen_ids:
            fail(f"duplicate external_product_id {external_id}")
            continue
        seen_ids.add(external_id)

        slug = str(item["slug"]).strip()
        if slug in seen_slugs:
            fail(f"duplicate slug {slug}")
        seen_slugs.add(slug)

        try:
            base_price = price_to_minor_units(
                item.get("prototype_price_eur"), "EUR", f"{external_id}.prototype_price_eur"
            )
        except NormalizationError as exc:
            fail(str(exc))
            continue

        compare_at = item.get("compare_at_price_eur")
        compare_at_minor = None
        if compare_at not in (None, ""):
            try:
                compare_at_minor = price_to_minor_units(
                    compare_at, "EUR", f"{external_id}.compare_at_price_eur"
                )
            except NormalizationError as exc:
                fail(str(exc))

        products.append(
            {
                "external_product_id": external_id,
                "slug": slug,
                "name": str(item["name"]).strip(),
                "category": str(item.get("category", "")).strip(),
                "collection_label": str(item.get("collection", "")).strip(),
                "short_description": str(item.get("short_description", "")).strip(),
                "long_description": str(item.get("long_description", "")).strip(),
                "currency": "EUR",
                "prototype_price_minor_units": base_price,
                "compare_at_price_minor_units": compare_at_minor,
                "sku_prefix": str(item.get("sku_prefix", "")).strip(),
                "sizes": item.get("sizes", []),
                "colorways": item.get("colorways", []),
                "care_instructions": str(item.get("care", "")).strip(),
                # --- typed states, never prose ---------------------------------------
                "publication_status": "preview",
                "sellable": False,
                "inventory_status": "prototype_unavailable",
                "evidence_status": "DRAFT",
                "material_claim_status": "UNVERIFIED",
                "origin_claim_status": "UNVERIFIED",
                "legal_brand_status": "LEGAL_CLEARANCE_PENDING",
                "media_status": "PROTOTYPE_CONCEPT",
                "country_of_origin": "XX",
                "intended_origin": "EG",
                # Side A's prose kept as NON-authoritative context only.
                "source_origin_statement": str(item.get("origin", "")).strip(),
                "source_material_statement": str(item.get("intended_material", "")).strip(),
                "source_composition_statement": str(item.get("intended_composition", "")).strip(),
                "source_evidence_statement": str(item.get("evidence_status", "")).strip(),
                "badges": item.get("badges", []),
                "search_terms": item.get("search_terms", []),
                "related_products": item.get("related_products", []),
                "recommendation_metadata": item.get("recommendation_metadata", {}),
            }
        )

        # ---- media, ordered deterministically by role then asset id -----------------
        imagery = item.get("imagery", [])
        ordered = sorted(
            imagery,
            key=lambda a: (
                MEDIA_ROLE_ORDER.index(media_role_for(a)) if media_role_for(a) else 99,
                a,
            ),
        )
        seen_pairs: set[tuple[str, str]] = set()
        for index, asset_id in enumerate(ordered):
            asset = assets_by_id.get(asset_id)
            if asset is None:
                fail(f"{external_id}: imagery references unknown asset {asset_id}")
                continue
            role = asset["media_role"]
            if role is None:
                fail(f"{external_id}: asset {asset_id} has no recognised media role")
                continue
            pair = (external_id, asset_id)
            if pair in seen_pairs:
                fail(f"{external_id}: duplicate media relationship for {asset_id}")
                continue
            seen_pairs.add(pair)
            media.append(
                {
                    "external_product_id": external_id,
                    "asset_id": asset_id,
                    "role": role,
                    "sort_order": index,
                    "path": asset["path"],
                    "alt_text": asset["alt_text"],
                    "status": asset["status"],
                    "sha256": asset["sha256"],
                }
            )

    return products, media


def normalize_variants(rows: list[dict], product_ids: set[str]) -> list[dict]:
    variants: list[dict] = []
    seen_skus: set[str] = set()
    seen_variant_ids: set[str] = set()
    seen_combo: set[tuple[str, str, str]] = set()

    for row in rows:
        external_variant_id = row["variant_id"].strip()
        external_product_id = row["product_id"].strip()
        sku = row["sku"].strip()

        if external_product_id not in product_ids:
            fail(f"orphan variant {external_variant_id}: unknown product {external_product_id}")
            continue
        if sku in seen_skus:
            fail(f"duplicate SKU {sku}")
            continue
        if external_variant_id in seen_variant_ids:
            fail(f"duplicate external_variant_id {external_variant_id}")
            continue

        combo = (external_product_id, row["size"].strip(), row["color"].strip())
        if combo in seen_combo:
            fail(f"duplicate option combination {combo}")
            continue

        currency = (row.get("currency") or "EUR").strip().upper()
        if currency != "EUR":
            fail(f"{external_variant_id}: unsupported currency {currency!r}")
            continue

        try:
            price = price_to_minor_units(row.get("price_eur"), currency, external_variant_id)
        except NormalizationError as exc:
            fail(str(exc))
            continue

        stock_raw = (row.get("stock_quantity") or "0").strip()
        if not stock_raw.isdigit():
            fail(f"{external_variant_id}: stock_quantity {stock_raw!r} is not a whole number")
            continue
        stock = int(stock_raw)
        if stock != 0:
            # Prototype data must never seed public stock. Loudly refused, not silently zeroed.
            fail(f"{external_variant_id}: prototype stock_quantity must be 0, found {stock}")
            continue

        seen_skus.add(sku)
        seen_variant_ids.add(external_variant_id)
        seen_combo.add(combo)

        variants.append(
            {
                "external_variant_id": external_variant_id,
                "external_product_id": external_product_id,
                "sku": sku,
                "size": row["size"].strip(),
                "color": row["color"].strip(),
                "color_code": row.get("color_code", "").strip(),
                "currency": currency,
                "price_minor_units": price,
                "source_price_eur": str(row.get("price_eur", "")).strip(),
                "stock_quantity": 0,
                "inventory_status": (row.get("inventory_status") or "prototype_unavailable").strip(),
                "evidence_status": (row.get("evidence_status") or "DRAFT").strip(),
                "sellable": False,
            }
        )
    return variants


def normalize_collections(rows: list[dict], product_ids: set[str]) -> list[dict]:
    collections = []
    for row in rows:
        raw_ids = row.get("product_ids", "").strip()
        try:
            members = json.loads(raw_ids) if raw_ids else []
        except json.JSONDecodeError:
            members = [p.strip() for p in raw_ids.split(",") if p.strip()]
        unknown = [m for m in members if m not in product_ids]
        if unknown:
            fail(f"collection {row.get('collection_id')}: unknown products {unknown}")
        collections.append(
            {
                "collection_id": row.get("collection_id", "").strip(),
                "slug": row.get("slug", "").strip(),
                "name": row.get("name", "").strip(),
                "status": row.get("status", "").strip(),
                "description": row.get("description", "").strip(),
                "product_ids": members,
                "hero_asset_id": row.get("hero_asset_id", "").strip(),
                "evidence_status": row.get("evidence_status", "").strip(),
            }
        )
    return collections


# ------------------------------------------------------------------------- build

def build(check_only: bool) -> int:
    print(f"source : {SIDE_A.relative_to(ROOT).as_posix()}")
    print(f"target : {OUT.relative_to(ROOT).as_posix()}")
    print(f"mode   : {'CHECK (writes nothing)' if check_only else 'BUILD'}\n")

    tokens_raw = read_json(SRC / "brand-tokens.json")
    products_raw = read_json(SRC / "product-master.json")
    products_raw = products_raw if isinstance(products_raw, list) else products_raw["products"]
    variants_raw = read_csv(SRC / "variant-master.csv")
    assets_raw = read_csv(SRC / "asset-register.csv")
    collections_raw = read_csv(SRC / "collection-master.csv")
    navigation = read_json(SRC / "navigation.json")
    content = read_json(SRC / "content-copy.json")
    fonts = read_json(SRC / "font-manifest.json")

    assets, assets_by_id = normalize_assets(assets_raw)
    products, media = normalize_products(products_raw, assets_by_id)
    product_ids = {p["external_product_id"] for p in products}
    variants = normalize_variants(variants_raw, product_ids)
    collections = normalize_collections(collections_raw, product_ids)
    brand = normalize_brand(tokens_raw)
    design_tokens, css = normalize_tokens(tokens_raw)

    counts = {
        "products": len(products),
        "variants": len(variants),
        "unique_skus": len({v["sku"] for v in variants}),
        "assets": len(assets),
        "product_media": len(media),
        "collections": len(collections),
    }

    for key, expected in (
        ("products", EXPECTED["products"]),
        ("variants", EXPECTED["variants"]),
        ("unique_skus", EXPECTED["skus"]),
        ("assets", EXPECTED["assets"]),
    ):
        if counts[key] != expected:
            fail(f"count mismatch: {key} expected {expected}, normalized {counts[key]}")

    print("normalized counts:")
    for key, value in counts.items():
        print(f"  {key:<16} {value}")
    print()

    if errors:
        print(f"ERRORS: {len(errors)}")
        for e in errors:
            print(f"  - {e}")
        print("\nRESULT: NORMALIZATION_FAILED")
        return 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/brand/build_brand_package.py",
        "source_package": SIDE_A.relative_to(ROOT).as_posix(),
        "source_manifest_entries": EXPECTED["checksums"],
        "counts": counts,
        "money": {
            "authoritative_unit": "integer minor units",
            "currency": "EUR",
            "converter": "app.money.to_minor_units (binary floats rejected)",
            "max_decimal_places": 2,
            "conversions": sorted({(v["source_price_eur"], v["price_minor_units"]) for v in variants}),
        },
        "states": {
            "publication_status": "preview",
            "sellable": False,
            "inventory_status": "prototype_unavailable",
            "evidence_status": "DRAFT",
            "material_claim_status": "UNVERIFIED",
            "origin_claim_status": "UNVERIFIED",
            "legal_brand_status": "LEGAL_CLEARANCE_PENDING",
            "media_status": "PROTOTYPE_CONCEPT",
            "country_of_origin": "XX",
            "intended_origin": "EG",
        },
        "media_roles": sorted({m["role"] for m in media}),
        "errors": [],
        "warnings": warnings,
    }

    outputs: dict[str, Any] = {
        "brand.json": brand,
        "tokens.json": design_tokens,
        "products.json": products,
        "variants.json": variants,
        "product-media.json": media,
        "assets.json": assets,
        "collections.json": collections,
        "navigation.json": navigation,
        "content.json": content,
        "fonts.json": fonts,
        "NORMALIZATION_REPORT.json": report,
    }

    if check_only:
        print("RESULT: NORMALIZATION_VERIFIED (nothing written)")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        (OUT / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    (OUT / "tokens.css").write_text(css, encoding="utf-8")

    (OUT / "README.md").write_text(
        "# packages/brand — GENERATED\n\n"
        "Normalized runtime brand package. **Do not edit by hand.**\n\n"
        "Regenerate with:\n\n"
        "```bash\npython scripts/brand/build_brand_package.py\n```\n\n"
        "Source of truth is the immutable Side A delivery at\n"
        "`handoffs/incoming/side-a/DEDUNET_Platform_Integration_v1/`, which this build reads\n"
        "and never modifies. Applications read THIS directory, never the handoff.\n\n"
        "Money here is integer minor units. Product and variant identity is the Side A\n"
        "`external_product_id` / `external_variant_id`, never array position or insertion order.\n",
        encoding="utf-8",
    )

    print(f"wrote {len(outputs) + 2} files to {OUT.relative_to(ROOT).as_posix()}")
    print("\nRESULT: BRAND_PACKAGE_BUILT")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate only; write nothing")
    args = parser.parse_args()
    return build(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
