"""The canonical brands, defined ONCE.

Three places need to agree about what the DEDUNET brand is: the Alembic migration that
backfills an existing database, `seed()` on a fresh one, and the DEDUNET importer. When each
carried its own literal, they drifted -- and a brand that differs between environments is a
brand whose slug appears in a URL that works in staging and 404s in test.

So the definitions live here as plain data, and every writer uses `ensure_canonical_brands`.

WHY THERE ARE EXACTLY TWO.

`DEDUNET_BRAND_SLUG` is the first-party brand. It is `PLATFORM_CURATED`, it owns the five
accepted prototypes, and it has NO merchant organisation -- inventing one to own our own
brand would make the first-party catalogue indistinguishable from a tenant's.

`LEGACY_FIXTURE_BRAND_SLUG` exists because `brand_id` is NOT NULL and the database already
contains products that are not DEDUNET's: the MERET demo catalogue and the restore-runbook's
test row. They are not a brand and never were. Rather than invent a plausible-looking
company for them -- which is precisely the "fake partner presented as real" failure this
phase forbids -- they are attached to an unmistakable development fixture that a check
constraint forbids ever publishing.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .brands import Brand, BrandOwnershipType, ProvenanceSource

DEDUNET_BRAND_SLUG = "dedunet"
LEGACY_FIXTURE_BRAND_SLUG = "internal-development-fixtures"

# The first-party brand. Copy is factual and carries no claim the programme cannot support:
# no partnership, no verified manufacturing claim, no origin asserted as substantiated.
DEDUNET_BRAND = {
    "slug": DEDUNET_BRAND_SLUG,
    "name": "DEDUNET",
    "ownership_type": BrandOwnershipType.PLATFORM_CURATED,
    "publication_status": "published",
    "story": (
        "DEDUNET is the platform's own label. The first capsule is a prototype run: the "
        "pieces are designed and specified, and the imagery is concept artwork rather than "
        "product photography. Material, composition and origin are stated intentions "
        "pending supplier documents, samples and testing, and are not substantiated claims."
    ),
    "logo_media_path": "assets/brand-prototype/logos/logo-primary.svg",
    # Empty rather than a guess. DEDUNET has no live public site to link a customer to, and
    # a broken or placeholder URL in a brand record is a customer-visible defect.
    "website_url": "",
    # Deliberately EMPTY. `intended_origin` on the products is "EG" and its claim status is
    # explicitly unverified; asserting a country on the brand record would launder an
    # intention into a fact at a different level of the domain.
    "country_code": "",
    "provenance_source": ProvenanceSource.PLATFORM_AUTHORED,
    "source_identifier": "",
    "source_url": "",
    "is_development_fixture": False,
}

LEGACY_FIXTURE_BRAND = {
    "slug": LEGACY_FIXTURE_BRAND_SLUG,
    "name": "Internal development fixtures",
    "ownership_type": BrandOwnershipType.PLATFORM_CURATED,
    # NOT published, and the check constraint on `brands` makes that structural rather than
    # a convention: a development fixture cannot be published even by a direct UPDATE.
    "publication_status": "preview",
    "story": (
        "Not a brand. This record groups internal demonstration and test rows -- the MERET "
        "sandbox catalogue and the backup-restore runbook's fixture -- so that every product "
        "has an accountable owner. It is not a company, not a partner, and nothing here is "
        "a commercial relationship."
    ),
    "logo_media_path": "",
    "website_url": "",
    "country_code": "",
    "provenance_source": ProvenanceSource.PLATFORM_AUTHORED,
    "source_identifier": "",
    "source_url": "",
    "is_development_fixture": True,
}

CANONICAL_BRANDS = (DEDUNET_BRAND, LEGACY_FIXTURE_BRAND)


def ensure_canonical_brands(session: Session) -> dict[str, Brand]:
    """Create the canonical brands if absent; return them by slug. Safe to re-run.

    Does NOT update an existing row. A brand's story and status are operator-editable, and a
    provisioning function that silently reverted an edit on every boot would be a data-loss
    bug that only shows up in production.
    """

    result: dict[str, Brand] = {}
    for spec in CANONICAL_BRANDS:
        brand = session.scalar(select(Brand).where(Brand.slug == spec["slug"]))
        if brand is None:
            brand = Brand(**spec)
            session.add(brand)
            session.flush()
        result[spec["slug"]] = brand
    return result


def brand_for_product(session: Session, *, external_product_id: str | None) -> Brand:
    """Which canonical brand a product belongs to.

    The rule the backfill uses, extracted so the migration and the importer cannot disagree:
    a product carrying a Side A external identity (`DDN-...`) is DEDUNET's; anything else is
    an internal fixture. That is a statement about provenance, not about quality -- and it is
    the same predicate `list_products` already uses to hide the legacy catalogue in preview
    mode, so nothing new becomes visible or invisible because of this phase.
    """

    brands = ensure_canonical_brands(session)
    if external_product_id:
        return brands[DEDUNET_BRAND_SLUG]
    return brands[LEGACY_FIXTURE_BRAND_SLUG]
