"""Order commerce-mode provenance

Revision ID: a7c31f9be402
Revises: e4b7a91c2d55
Create Date: 2026-08-06

Adds `orders.commerce_mode_at_checkout`.

Existing orders are backfilled to `LEGACY_UNCLASSIFIED`, which is the only honest value:
they were placed before commerce modes existed, so labelling them `PUBLIC_COMMERCE_MODE`
would fabricate a commercial history that never happened, and labelling them
`COMMERCE_TEST_MODE` would be a guess. Unknown is a real answer and is recorded as one.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7c31f9be402"
down_revision = "e4b7a91c2d55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.add_column(
            sa.Column(
                "commerce_mode_at_checkout",
                sa.String(30),
                nullable=False,
                server_default="LEGACY_UNCLASSIFIED",
            )
        )
    op.create_index(
        "ix_orders_commerce_mode_at_checkout", "orders", ["commerce_mode_at_checkout"]
    )
    # Explicit, even though the server default already covers existing rows: this states
    # the intent in the migration rather than leaving it implied by a DDL default.
    op.execute(
        "UPDATE orders SET commerce_mode_at_checkout = 'LEGACY_UNCLASSIFIED' "
        "WHERE commerce_mode_at_checkout IS NULL OR commerce_mode_at_checkout = ''"
    )


def downgrade() -> None:
    op.drop_index("ix_orders_commerce_mode_at_checkout", table_name="orders")
    with op.batch_alter_table("orders") as batch:
        batch.drop_column("commerce_mode_at_checkout")
