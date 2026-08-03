"""notification dispatch columns

Adds the outbox bookkeeping the dispatcher needs: attempt count, delivery timestamp,
error text, provider reference, a status CHECK constraint and a status index.

server_default is MANDATORY on the new NOT NULL columns. The ORM ``default=`` runs in
Python only, so adding a NOT NULL column without a server default fails outright on a
PostgreSQL table that already has rows. SQLite is more forgiving, which is exactly why
this is easy to get wrong locally and discover in staging.

``render_as_batch`` is already enabled in ``migrations/env.py``, so SQLite rebuilds the
table to attach the CHECK constraint. That rebuild drops and recreates the foreign key to
``customers`` — expected, and harmless.

Revision ID: b1a7c4e2f903
Revises: 8d2d3d0f9b6f
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b1a7c4e2f903"
down_revision = "8d2d3d0f9b6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notifications", schema=None) as batch:
        batch.add_column(
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("last_error", sa.Text(), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column(
                "provider_reference", sa.String(length=120), nullable=False, server_default=""
            )
        )
        batch.alter_column(
            "status",
            existing_type=sa.String(length=20),
            nullable=False,
            server_default="queued",
        )
        batch.create_check_constraint(
            "ck_notification_status",
            "status IN ('queued', 'sending', 'sent', 'failed', 'suppressed')",
        )

    # Indexed because the dispatcher's claim query filters on status every cycle.
    op.create_index("ix_notifications_status", "notifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_notifications_status", table_name="notifications")

    with op.batch_alter_table("notifications", schema=None) as batch:
        batch.drop_constraint("ck_notification_status", type_="check")
        batch.drop_column("provider_reference")
        batch.drop_column("last_error")
        batch.drop_column("sent_at")
        batch.drop_column("attempts")
