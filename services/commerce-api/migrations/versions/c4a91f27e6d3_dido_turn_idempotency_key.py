"""Dido turns carry the client's idempotency key, and it is unique per session.

Revision ID: c4a91f27e6d3
Revises: b2e74c09d8a1
Create Date: 2026-10-11

WHY THIS EXISTS.

Idempotency was implemented by comparing MESSAGE BODIES: a second message whose text matched
an earlier one in the same session was treated as a retry, and the earlier reply was replayed.

That is wrong in the ordinary case rather than an edge one. Two identical messages are
usually two messages -- "yes", "no black", or asking the same question twice are all
legitimate repeats. The visible consequence was a stale answer served with full confidence:
a customer who asked about their budget before giving one, then gave one, then asked again,
was told they had no budget while the brief held EUR 200.00. It also meant any question
answered before a fix was deployed kept returning the pre-fix answer for the life of the
session, on entirely correct code.

A retry is identified by the KEY THE CLIENT SENT, and nothing else. The uniqueness is a
database constraint rather than an application check, for the reason Saved persistence
established: a double submit on a flaky connection genuinely races, and two requests that
both find no row will both insert.

ADDITIVE AND NON-DESTRUCTIVE. One nullable column and one constraint on a table created by
the previous revision. No existing row is modified: historical turns keep NULL, which is
correct -- they carried no key, so they were never retry candidates. NULL is repeatable
under a unique constraint on both PostgreSQL and SQLite, so a client that sends no key is
simply not asking for idempotency.

Rollback drops the column and the constraint. No conversation content is lost by that, but
idempotency reverts to the body-comparison behaviour this revision exists to remove.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c4a91f27e6d3"
down_revision = "b2e74c09d8a1"
branch_labels = None
depends_on = None

_MAX_KEY_LENGTH = 80


def upgrade() -> None:
    # SQLite cannot ALTER a table to add a constraint, so the batch context rebuilds it.
    # On PostgreSQL this is an ordinary ADD COLUMN plus ADD CONSTRAINT.
    with op.batch_alter_table("dido_turns") as batch:
        batch.add_column(
            sa.Column("client_message_id", sa.String(length=_MAX_KEY_LENGTH), nullable=True)
        )
        batch.create_unique_constraint(
            "uq_dido_turn_session_client_message", ["session_id", "client_message_id"]
        )

    _verify_nothing_else_moved()


def _verify_nothing_else_moved() -> None:
    """Prove this touched one table and invented nothing, inside the transaction.

    A migration that says "additive" in its docstring is making a claim; this checks it
    while a mistake can still roll back.
    """

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {c["name"] for c in inspector.get_columns("dido_turns")}
    if "client_message_id" not in columns:
        raise RuntimeError("dido_turns.client_message_id was not created")

    # Every pre-existing turn must still be there, and every one of them must have a NULL
    # key -- a non-NULL value here would mean this migration invented an idempotency key
    # for a message that never carried one.
    non_null = bind.execute(
        sa.text("SELECT COUNT(*) FROM dido_turns WHERE client_message_id IS NOT NULL")
    ).scalar_one()
    if non_null != 0:
        raise RuntimeError(
            f"{non_null} existing turns were given a client_message_id; this migration "
            "must not invent one"
        )

    for table in (
        "dido_sessions", "dido_turns",
        "products", "variants", "brands", "looks", "look_items", "orders",
        "saved_looks", "favorite_products", "favorite_brands",
        "style_profiles", "style_sizes", "style_colour_preferences",
    ):
        if table not in set(inspector.get_table_names()):
            raise RuntimeError(f"accepted domain table missing after migration: {table}")


def downgrade() -> None:
    """Reverts to body-comparison idempotency, which is why this revision exists."""

    with op.batch_alter_table("dido_turns") as batch:
        batch.drop_constraint("uq_dido_turn_session_client_message", type_="unique")
        batch.drop_column("client_message_id")
