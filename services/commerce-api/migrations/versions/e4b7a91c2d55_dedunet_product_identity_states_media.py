"""DEDUNET integration: external identity, typed states and product media

Revision ID: e4b7a91c2d55
Revises: c2f8d1b40e77
Create Date: 2026-08-06

Additive only. No existing column is dropped, renamed or retyped, so an existing populated
database upgrades without rewriting a single legacy row and the MERET seed keeps loading
unchanged.

One deliberate data step: `sellable` fails CLOSED (server default false), so rows that
existed BEFORE this revision are backfilled to `is_active`. Without that, upgrading a
populated database would silently make its entire catalogue unpurchasable — a fail-closed
default is right for new rows and wrong for existing ones.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e4b7a91c2d55"
down_revision = "c2f8d1b40e77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ products
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("external_product_id", sa.String(40), nullable=True))
        batch.add_column(
            sa.Column("collection_id", sa.String(60), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("intended_origin", sa.String(2), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column(
                "publication_status", sa.String(30), nullable=False, server_default="preview"
            )
        )
        batch.add_column(
            sa.Column("sellable", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("inventory_status", sa.String(40), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("evidence_status", sa.String(40), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("material_claim_status", sa.String(30), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("origin_claim_status", sa.String(30), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("legal_brand_status", sa.String(40), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("media_status", sa.String(40), nullable=False, server_default="")
        )

    op.create_index(
        "ix_products_external_product_id", "products", ["external_product_id"], unique=True
    )
    op.create_index("ix_products_collection_id", "products", ["collection_id"])
    op.create_index("ix_products_publication_status", "products", ["publication_status"])

    # Preserve the behaviour every existing row already had. A product that was active was
    # purchasable before this column existed, so it must remain so.
    op.execute(
        "UPDATE products SET sellable = is_active, "
        "publication_status = CASE WHEN is_active THEN 'published' ELSE 'draft' END"
    )

    # ------------------------------------------------------------------ variants
    with op.batch_alter_table("variants") as batch:
        batch.add_column(sa.Column("external_variant_id", sa.String(60), nullable=True))
        batch.add_column(
            sa.Column("sellable", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("inventory_status", sa.String(40), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("evidence_status", sa.String(40), nullable=False, server_default="")
        )

    op.create_index(
        "ix_variants_external_variant_id", "variants", ["external_variant_id"], unique=True
    )

    op.execute(
        "UPDATE variants SET sellable = ("
        "  SELECT products.is_active FROM products WHERE products.id = variants.product_id"
        ")"
    )

    # -------------------------------------------------------------- product_media
    op.create_table(
        "product_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.String(60), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("path", sa.String(300), nullable=False),
        sa.Column("alt_text", sa.String(400), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default=""),
        sa.Column("checksum_sha256", sa.String(64), nullable=False, server_default=""),
        sa.UniqueConstraint("product_id", "asset_id", name="uq_product_media_asset"),
        sa.UniqueConstraint("product_id", "role", "sort_order", name="uq_product_media_slot"),
        sa.CheckConstraint("sort_order >= 0", name="ck_product_media_sort_order"),
        sa.CheckConstraint(
            "role IN ('front','back','detail','lifestyle','campaign','collection')",
            name="ck_product_media_role",
        ),
    )
    op.create_index("ix_product_media_product_id", "product_media", ["product_id"])
    op.create_index("ix_product_media_asset_id", "product_media", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_product_media_asset_id", table_name="product_media")
    op.drop_index("ix_product_media_product_id", table_name="product_media")
    op.drop_table("product_media")

    op.drop_index("ix_variants_external_variant_id", table_name="variants")
    with op.batch_alter_table("variants") as batch:
        batch.drop_column("evidence_status")
        batch.drop_column("inventory_status")
        batch.drop_column("sellable")
        batch.drop_column("external_variant_id")

    op.drop_index("ix_products_publication_status", table_name="products")
    op.drop_index("ix_products_collection_id", table_name="products")
    op.drop_index("ix_products_external_product_id", table_name="products")
    with op.batch_alter_table("products") as batch:
        batch.drop_column("media_status")
        batch.drop_column("legal_brand_status")
        batch.drop_column("origin_claim_status")
        batch.drop_column("material_claim_status")
        batch.drop_column("evidence_status")
        batch.drop_column("inventory_status")
        batch.drop_column("sellable")
        batch.drop_column("publication_status")
        batch.drop_column("intended_origin")
        batch.drop_column("collection_id")
        batch.drop_column("external_product_id")
