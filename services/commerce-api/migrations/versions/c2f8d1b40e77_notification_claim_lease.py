"""notification claim lease

Bounds the window in which a worker killed mid-send can hold a claim.

Without an expiry a durable 'sending' claim is held forever: the row is excluded from
every future claim query and is invisible to any delivered-count report. The lease makes
an abandoned claim eventually eligible again, while a LIVE claim stays protected.

claim_expires_at is indexed because the claim query filters on it every cycle.

Revision ID: c2f8d1b40e77
Revises: b1a7c4e2f903
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c2f8d1b40e77"
down_revision = "b1a7c4e2f903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notifications", schema=None) as batch:
        batch.add_column(sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "claim_token", sa.String(length=64), nullable=False, server_default=""
            )
        )

    op.create_index(
        "ix_notifications_claim_expires_at", "notifications", ["claim_expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_claim_expires_at", table_name="notifications")
    with op.batch_alter_table("notifications", schema=None) as batch:
        batch.drop_column("claim_token")
        batch.drop_column("claim_expires_at")
        batch.drop_column("claimed_at")
