"""Multi-brand fashion network: Brand, ownership, commerce route and provenance

Revision ID: f5c2a8d13b70
Revises: a7c31f9be402
Create Date: 2026-08-27

STAGED, because `products.brand_id` must end NOT NULL over a database that already holds
products. A single `add_column(nullable=False)` against a populated table fails outright on
PostgreSQL, and a nullable column left nullable "for now" is the retrofit the target
architecture spent a section warning about. The stages are:

  1. create brands, merchant_organizations, brand_ownership
  2. INSERT the two canonical brands -- inside the migration, so the constraint in stage 6
     has something to point at on any database, not only one where seed() has been run
  3. add products.brand_id NULLABLE, plus commerce_route and the provenance columns
  4. BACKFILL every existing product
  5. VERIFY -- count rows still NULL and abort the whole transaction if any remain
  6. ALTER brand_id to NOT NULL and add the foreign key

Stage 5 is the one that matters. Without it stage 6 fails with a constraint error that says
nothing about which rows were wrong, and on SQLite -- where batch mode rebuilds the table --
it could rebuild with nulls and only fail later. Verifying first turns a puzzle into a
sentence.

DATA SAFETY. No product, variant, price, media row, publication state or sellable flag is
read, rewritten or deleted here. The only writes to `products` are to columns this revision
itself creates. `commerce_route` defaults to NON_PURCHASABLE for every existing row, which
preserves the accepted preview safety state exactly: the five DEDUNET prototypes were not
purchasable before this migration and are not purchasable after it.

ROLLBACK IS NOT FREE, and §19 of the phase brief is right to insist it be stated. Once
products reference brands, `downgrade()` DROPS `products.brand_id` -- so the brand
association is destroyed, not merely detached. The products, variants, prices and media all
survive untouched; what is lost is which brand each product belonged to. That is recoverable
here only because the assignment is derivable from `external_product_id` by the same rule
`brand_for_product` applies, and re-running `upgrade()` reproduces it exactly. It would NOT
be recoverable once an operator has assigned brands by hand, and at that point this
downgrade needs a data export first. Recorded in the phase evidence.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f5c2a8d13b70"
down_revision = "a7c31f9be402"
branch_labels = None
depends_on = None


# Kept in step with app/commerce/brand_registry.py. Duplicated as literals ON PURPOSE: a
# migration must describe the schema and data as they were at THIS revision, and importing
# application code into a migration means a future edit to that code silently rewrites
# history for anyone replaying migrations from zero.
DEDUNET_SLUG = "dedunet"
FIXTURE_SLUG = "internal-development-fixtures"


def upgrade() -> None:
    bind = op.get_bind()

    # ---------------------------------------------------------------- 1. new tables
    op.create_table(
        "merchant_organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_merchant_organizations_slug", "merchant_organizations", ["slug"], unique=True
    )
    op.create_index("ix_merchant_organizations_status", "merchant_organizations", ["status"])

    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("ownership_type", sa.String(length=30), nullable=False),
        sa.Column(
            "publication_status", sa.String(length=30), nullable=False, server_default="preview"
        ),
        sa.Column("story", sa.Text(), nullable=False, server_default=""),
        sa.Column("logo_media_path", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("website_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default=""),
        sa.Column(
            "provenance_source",
            sa.String(length=30),
            nullable=False,
            server_default="PLATFORM_AUTHORED",
        ),
        sa.Column("source_identifier", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("source_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_development_fixture",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        # The production gate, in the database. A development fixture can never be published,
        # whatever an API or an operator's UPDATE tries to do.
        sa.CheckConstraint(
            "NOT (is_development_fixture AND publication_status = 'published')",
            name="ck_brand_fixture_never_published",
        ),
    )
    op.create_index("ix_brands_slug", "brands", ["slug"], unique=True)
    op.create_index("ix_brands_ownership_type", "brands", ["ownership_type"])
    op.create_index("ix_brands_publication_status", "brands", ["publication_status"])
    op.create_index("ix_brands_is_development_fixture", "brands", ["is_development_fixture"])

    op.create_table(
        "brand_ownership",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "brand_id",
            sa.Integer(),
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "merchant_organization_id",
            sa.Integer(),
            sa.ForeignKey("merchant_organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    # UNIQUE, not merely indexed: "at most one owner per brand" becomes a key the database
    # enforces rather than a rule the application has to remember.
    op.create_index("ix_brand_ownership_brand_id", "brand_ownership", ["brand_id"], unique=True)
    op.create_index(
        "ix_brand_ownership_merchant_organization_id",
        "brand_ownership",
        ["merchant_organization_id"],
    )

    # ---------------------------------------------------------------- 2. canonical brands
    brands_table = sa.table(
        "brands",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("ownership_type", sa.String),
        sa.column("publication_status", sa.String),
        sa.column("story", sa.Text),
        sa.column("logo_media_path", sa.String),
        sa.column("is_development_fixture", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        brands_table,
        [
            {
                "slug": DEDUNET_SLUG,
                "name": "DEDUNET",
                "ownership_type": "PLATFORM_CURATED",
                "publication_status": "published",
                "story": (
                    "DEDUNET is the platform's own label. The first capsule is a prototype "
                    "run: the pieces are designed and specified, and the imagery is concept "
                    "artwork rather than product photography. Material, composition and "
                    "origin are stated intentions pending supplier documents, samples and "
                    "testing, and are not substantiated claims."
                ),
                "logo_media_path": "assets/brand-prototype/logos/logo-primary.svg",
                "is_development_fixture": False,
            },
            {
                "slug": FIXTURE_SLUG,
                "name": "Internal development fixtures",
                "ownership_type": "PLATFORM_CURATED",
                "publication_status": "preview",
                "story": (
                    "Not a brand. This record groups internal demonstration and test rows so "
                    "that every product has an accountable owner. It is not a company, not a "
                    "partner, and nothing here is a commercial relationship."
                ),
                "logo_media_path": "",
                "is_development_fixture": True,
            },
        ],
    )
    # bulk_insert cannot carry a SQL function per row, so the timestamps are set after.
    # CURRENT_TIMESTAMP rather than a Python value: the database's clock is the one the rest
    # of these rows will be compared against.
    op.execute(
        sa.text(
            "UPDATE brands SET created_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
            "WHERE created_at IS NULL"
        )
    )

    # ---------------------------------------------------------------- 3. product columns
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("brand_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "commerce_route",
                sa.String(length=20),
                nullable=False,
                server_default="NON_PURCHASABLE",
            )
        )
        batch.add_column(
            sa.Column("external_buy_url", sa.String(length=500), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column(
                "availability_confidence",
                sa.String(length=30),
                nullable=False,
                server_default="UNKNOWN",
            )
        )
        batch.add_column(sa.Column("availability_checked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("source_last_synced_at", sa.DateTime(timezone=True), nullable=True))

    # ---------------------------------------------------------------- 4. backfill
    # The same predicate `brand_for_product` uses, and the same one `list_products` already
    # applies to hide the legacy catalogue in preview mode -- so nothing becomes newly
    # visible or invisible as a result of this migration.
    op.execute(
        sa.text(
            "UPDATE products SET brand_id = (SELECT id FROM brands WHERE slug = :dedunet) "
            "WHERE external_product_id IS NOT NULL AND external_product_id <> ''"
        ).bindparams(dedunet=DEDUNET_SLUG)
    )
    op.execute(
        sa.text(
            "UPDATE products SET brand_id = (SELECT id FROM brands WHERE slug = :fixture) "
            "WHERE brand_id IS NULL"
        ).bindparams(fixture=FIXTURE_SLUG)
    )

    # ---------------------------------------------------------------- 5. VERIFY, then constrain
    # Abort with a sentence rather than a constraint violation. This runs inside the
    # migration transaction, so raising here rolls the whole revision back.
    orphans = bind.execute(
        sa.text("SELECT count(*) FROM products WHERE brand_id IS NULL")
    ).scalar_one()
    if orphans:
        raise RuntimeError(
            f"{orphans} product row(s) still have no brand after backfill; refusing to make "
            "products.brand_id NOT NULL. Inspect: SELECT id, slug, external_product_id FROM "
            "products WHERE brand_id IS NULL;"
        )

    total = bind.execute(sa.text("SELECT count(*) FROM products")).scalar_one()
    attached = bind.execute(
        sa.text("SELECT count(*) FROM products WHERE brand_id IS NOT NULL")
    ).scalar_one()
    if total != attached:
        raise RuntimeError(f"brand backfill incomplete: {attached} of {total} products attached")

    # ---------------------------------------------------------------- 6. NOT NULL + FK
    with op.batch_alter_table("products") as batch:
        batch.alter_column("brand_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_products_brand_id", "brands", ["brand_id"], ["id"], ondelete="RESTRICT"
        )
    op.create_index("ix_products_brand_id", "products", ["brand_id"])
    op.create_index("ix_products_commerce_route", "products", ["commerce_route"])


def downgrade() -> None:
    """Reverse the revision. NOT a no-impact operation -- see the module docstring.

    Dropping `products.brand_id` destroys the product-to-brand association. Products,
    variants, prices, media, publication and sellable states are all untouched. Re-running
    `upgrade()` reconstructs the association exactly, because it is derived from
    `external_product_id`; that ceases to be true once an operator assigns a brand by hand,
    and from that point a downgrade needs a data export first.
    """

    op.drop_index("ix_products_commerce_route", table_name="products")
    op.drop_index("ix_products_brand_id", table_name="products")
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("fk_products_brand_id", type_="foreignkey")
        batch.drop_column("source_last_synced_at")
        batch.drop_column("availability_checked_at")
        batch.drop_column("availability_confidence")
        batch.drop_column("external_buy_url")
        batch.drop_column("commerce_route")
        batch.drop_column("brand_id")

    op.drop_index("ix_brand_ownership_merchant_organization_id", table_name="brand_ownership")
    op.drop_index("ix_brand_ownership_brand_id", table_name="brand_ownership")
    op.drop_table("brand_ownership")

    op.drop_index("ix_brands_is_development_fixture", table_name="brands")
    op.drop_index("ix_brands_publication_status", table_name="brands")
    op.drop_index("ix_brands_ownership_type", table_name="brands")
    op.drop_index("ix_brands_slug", table_name="brands")
    op.drop_table("brands")

    op.drop_index("ix_merchant_organizations_status", table_name="merchant_organizations")
    op.drop_index("ix_merchant_organizations_slug", table_name="merchant_organizations")
    op.drop_table("merchant_organizations")
