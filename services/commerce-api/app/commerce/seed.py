"""Deterministic seed data for the fictional demonstration brand.

FICTIONAL DATA NOTICE
---------------------
"MERET" is an invented brand. It is not a real company. Every product, material,
origin, price, customer, order and support case below is fabricated for demonstration
and testing.

The material, origin and care fields are ILLUSTRATIVE ONLY. They are not substantiated
claims and must never be presented to a real customer as fact. Under the repository's
evidence rules, a fibre, origin, sustainability or certification claim requires
laboratory and supply-chain evidence (dossiers EXT-03 and EXT-04), and none exists.
Country-of-origin values are therefore recorded as ``XX`` — an intentionally invalid
placeholder that cannot be mistaken for a substantiated origin.

Determinism: seeding is idempotent and keyed on stable slugs, SKUs and emails, so
re-running it does not duplicate rows and produces byte-identical business values.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Customer, InventoryItem, Product, Promotion, Variant
from .security import hash_password

BRAND_NAME = "MERET"
BRAND_STORY = (
    "MERET is a fictional demonstration label used to exercise this platform. "
    "It imagines a modern Eastern silhouette in restrained, monochrome tailoring. "
    "Nothing about this brand describes a real company, product or supply chain."
)

# Design tokens consumed by the storefront and mobile clients.
BRAND_TOKENS = {
    "color": {
        "ink": "#12100E",
        "sand": "#C8B9A6",
        "bone": "#F4F0EA",
        "clay": "#8C6A4F",
        "accent": "#9A7B4F",
    },
    "font": {
        "display": "'Cormorant Garamond', Georgia, serif",
        "body": "'Inter', system-ui, sans-serif",
    },
    "radius": {"sm": "2px", "md": "6px", "lg": "14px"},
}

DEMO_ADMIN_EMAIL = "admin@meret.example"
DEMO_CUSTOMER_EMAIL = "customer@meret.example"
# Demonstration credentials for a local, non-public, fictional dataset. They are not a
# secret and grant access to nothing beyond a throwaway local database. Any deployment
# beyond localhost must reseed with fresh credentials.
DEMO_PASSWORD = "demo-password-123"

PRODUCTS: list[dict] = [
    {
        "slug": "oversized-crew-tee-black",
        "name": "Oversized Crew Tee",
        "category": "tops",
        "collection": "Core",
        "description": (
            "A relaxed crew-neck tee with a dropped shoulder and a straight hem. "
            "Illustrative demonstration product."
        ),
        "material": "Cotton jersey (illustrative, unsubstantiated)",
        "care_instructions": "Wash cool, dry flat, warm iron if needed.",
        "country_of_origin": "XX",
        "image_url": "/static/placeholder-tee.svg",
        "is_active": True,
        "variants": [
            {"sku": "MRT-TEE-BLK-S", "size": "S", "color": "Black", "price_minor_units": 5900, "on_hand": 12},
            {"sku": "MRT-TEE-BLK-M", "size": "M", "color": "Black", "price_minor_units": 5900, "on_hand": 18},
            {"sku": "MRT-TEE-BLK-L", "size": "L", "color": "Black", "price_minor_units": 5900, "on_hand": 7},
        ],
    },
    {
        "slug": "wide-leg-trouser-sand",
        "name": "Wide Leg Trouser",
        "category": "bottoms",
        "collection": "Core",
        "description": "High-rise wide-leg trouser with a pressed front. Illustrative demonstration product.",
        "material": "Woven blend (illustrative, unsubstantiated)",
        "care_instructions": "Dry clean recommended.",
        "country_of_origin": "XX",
        "image_url": "/static/placeholder-trouser.svg",
        "is_active": True,
        "variants": [
            {"sku": "MRT-TRS-SND-S", "size": "S", "color": "Sand", "price_minor_units": 12900, "on_hand": 6},
            {"sku": "MRT-TRS-SND-M", "size": "M", "color": "Sand", "price_minor_units": 12900, "on_hand": 9},
            {"sku": "MRT-TRS-SND-L", "size": "L", "color": "Sand", "price_minor_units": 12900, "on_hand": 4},
        ],
    },
    {
        "slug": "long-line-overshirt-ink",
        "name": "Long Line Overshirt",
        "category": "outerwear",
        "collection": "Atelier",
        "description": "An unlined overshirt cut long through the body. Illustrative demonstration product.",
        "material": "Midweight woven (illustrative, unsubstantiated)",
        "care_instructions": "Wash cool, hang dry.",
        "country_of_origin": "XX",
        "image_url": "/static/placeholder-overshirt.svg",
        "is_active": True,
        "variants": [
            {"sku": "MRT-OVS-INK-M", "size": "M", "color": "Ink", "price_minor_units": 18900, "on_hand": 5},
            {"sku": "MRT-OVS-INK-L", "size": "L", "color": "Ink", "price_minor_units": 18900, "on_hand": 3},
        ],
    },
    {
        "slug": "draped-scarf-clay",
        "name": "Draped Scarf",
        "category": "accessories",
        "collection": "Atelier",
        "description": "A long draped scarf with a rolled edge. Illustrative demonstration product.",
        "material": "Fine weave (illustrative, unsubstantiated)",
        "care_instructions": "Hand wash cold.",
        "country_of_origin": "XX",
        "image_url": "/static/placeholder-scarf.svg",
        "is_active": True,
        "variants": [
            {"sku": "MRT-SCF-CLY-OS", "size": "OS", "color": "Clay", "price_minor_units": 4500, "on_hand": 25},
        ],
    },
    {
        "slug": "archive-coat-ink",
        "name": "Archive Coat",
        "category": "outerwear",
        "collection": "Archive",
        "description": "Draft record for an unreleased piece. Intentionally inactive to exercise gating.",
        "material": "Undetermined",
        "care_instructions": "",
        "country_of_origin": "XX",
        "image_url": "",
        # Deliberately inactive: proves that an unreleased product is invisible to the
        # storefront and cannot be added to a cart.
        "is_active": False,
        "variants": [
            {"sku": "MRT-COA-INK-M", "size": "M", "color": "Ink", "price_minor_units": 32900, "on_hand": 0},
        ],
    },
]

PROMOTIONS: list[dict] = [
    {"code": "WELCOME10", "kind": "percent", "value": 1000, "min_subtotal_minor_units": 0},
    {"code": "SAVE20EUR", "kind": "fixed", "value": 2000, "min_subtotal_minor_units": 10000},
]


def seed(session: Session, *, include_demo_accounts: bool = True) -> dict:
    """Populate the database. Safe to run repeatedly."""

    created = {"products": 0, "variants": 0, "promotions": 0, "customers": 0}

    for spec in PRODUCTS:
        if session.scalar(select(Product).where(Product.slug == spec["slug"])) is not None:
            continue
        product = Product(
            slug=spec["slug"],
            name=spec["name"],
            description=spec["description"],
            category=spec["category"],
            collection=spec["collection"],
            material=spec["material"],
            care_instructions=spec["care_instructions"],
            country_of_origin=spec["country_of_origin"],
            image_url=spec["image_url"],
            is_active=spec["is_active"],
            # The demo catalogue is purchasable in sandbox and was before `sellable`
            # existed. It opts in explicitly because the column fails closed.
            sellable=spec["is_active"],
            publication_status="published" if spec["is_active"] else "draft",
        )
        session.add(product)
        session.flush()
        created["products"] += 1

        for variant_spec in spec["variants"]:
            variant = Variant(
                product_id=product.id,
                sku=variant_spec["sku"],
                size=variant_spec["size"],
                color=variant_spec["color"],
                price_minor_units=variant_spec["price_minor_units"],
                # Kept consistent with the parent. A sellable product whose variants all
                # read `sellable = false` is contradictory data, even though the purchase
                # gate reads the product flag.
                sellable=spec["is_active"],
                inventory_status="stocked" if spec["is_active"] else "",
            )
            session.add(variant)
            session.flush()
            session.add(
                InventoryItem(
                    variant_id=variant.id, on_hand=variant_spec["on_hand"], reserved=0
                )
            )
            created["variants"] += 1

    for promo in PROMOTIONS:
        if session.scalar(select(Promotion).where(Promotion.code == promo["code"])) is not None:
            continue
        session.add(Promotion(**promo, is_active=True))
        created["promotions"] += 1

    if include_demo_accounts:
        for email, name, role in (
            (DEMO_ADMIN_EMAIL, "Demo Administrator", "admin"),
            (DEMO_CUSTOMER_EMAIL, "Demo Customer", "customer"),
        ):
            if session.scalar(select(Customer).where(Customer.email == email)) is not None:
                continue
            session.add(
                Customer(
                    email=email,
                    password_hash=hash_password(DEMO_PASSWORD),
                    full_name=name,
                    role=role,
                )
            )
            created["customers"] += 1

    session.commit()
    return created
