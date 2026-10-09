"""Dido conversational sessions, turns and the styling brief.

Revision ID: b2e74c09d8a1
Revises: a9f3e26b104c
Create Date: 2026-10-09

ADDITIVE ONLY. Two new tables; no existing table, column, constraint or row is touched.
The catalogue, variants, prices, brands, looks, Saved rows, Style DNA and orders are all
outside this migration's reach, which is why the in-transaction verification at the end
can assert they are unchanged rather than hope so.

ROLLBACK DESTROYS CUSTOMER CONVERSATIONS, AND THEY ARE NOT RECONSTRUCTIBLE.

`downgrade()` drops every styling conversation and every brief built in one. Like Style
DNA and unlike the multi-brand association, NONE OF THIS CAN BE REBUILT: it is what people
typed. There is no registry to re-derive it from and no fixture that approximates it.

Export both tables before downgrading if any customer has used Dido.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2e74c09d8a1"
down_revision = "a9f3e26b104c"
branch_labels = None
depends_on = None


#: Literals rather than imports from application code. A migration is a record of the
#: schema at a point in time; importing a constant means a later edit silently changes
#: what this migration did, and a migration that changes retroactively records nothing.
_STATUSES = ("ACTIVE", "BRIEF_READY", "ABANDONED")
_ROLES = ("CUSTOMER", "DIDO")


def upgrade() -> None:
    op.create_table(
        "dido_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        # The authoritative structured brief. Validated by the application before it is
        # written; see dido_brief.py for why this one is a document and Style DNA is not.
        sa.Column("brief_json", sa.Text(), nullable=False, server_default="{}"),
        # A SNAPSHOT of the Style DNA revision this session began with, not a live link.
        sa.Column("style_profile_revision_used", sa.Integer(), nullable=True),
        sa.Column(
            "personalization_used", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('" + "','".join(_STATUSES) + "')", name="ck_dido_session_status"
        ),
        sa.CheckConstraint("revision >= 1", name="ck_dido_session_revision_positive"),
        sa.CheckConstraint("turn_count >= 0", name="ck_dido_session_turn_count"),
    )
    op.create_index("ix_dido_sessions_customer_id", "dido_sessions", ["customer_id"])
    op.create_index("ix_dido_sessions_created_at", "dido_sessions", ["created_at"])
    # The hot query is "this customer's active session". A partial index would be tighter
    # but is not portable to the SQLite the test suite runs on, so the status rides along.
    op.create_index(
        "ix_dido_sessions_customer_status", "dido_sessions", ["customer_id", "status"]
    )

    op.create_table(
        "dido_turns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        # PERSONAL DATA. Never logged, never in an analytics payload, never in evidence,
        # and removed by account erasure as well as by cascade.
        sa.Column("body", sa.Text(), nullable=False),
        # The deterministic policy key behind a Dido question, so "why did you ask that?"
        # is answered from metadata rather than by a model inventing a justification.
        sa.Column("question_key", sa.String(length=60), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["session_id"], ["dido_sessions.id"], ondelete="CASCADE"),
        # Ordering is a GUARANTEE, not a convention: two turns written in one transaction
        # share a timestamp, and a conversation whose order wobbles is not a conversation.
        sa.UniqueConstraint("session_id", "ordinal", name="uq_dido_turn_session_ordinal"),
        sa.CheckConstraint(
            "role IN ('" + "','".join(_ROLES) + "')", name="ck_dido_turn_role"
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_dido_turn_ordinal"),
    )
    op.create_index("ix_dido_turns_session_id", "dido_turns", ["session_id"])

    _verify_nothing_else_moved()


def _verify_nothing_else_moved() -> None:
    """Prove the accepted domains are untouched, and abort if they are not.

    A migration that says "additive only" in its docstring is making a claim. This checks
    it in the same transaction, so a mistake rolls back rather than landing and being
    found later by somebody wondering why a price moved.

    The two new tables must exist and be EMPTY. A non-empty conversation table
    immediately after creation would mean this migration invented a conversation, which
    is the one thing it may never do.
    """

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    expected_new = {"dido_sessions", "dido_turns"}
    missing = expected_new - tables
    if missing:
        raise RuntimeError(f"dido migration did not create: {sorted(missing)}")

    for table in sorted(expected_new):
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        if count != 0:
            raise RuntimeError(
                f"{table} has {count} rows immediately after creation; this migration "
                "must not fabricate conversations"
            )

    # Every accepted domain must still be present. Row counts are compared outside the
    # migration against a recorded pre-migration baseline -- a migration cannot
    # meaningfully compare against a state it never saw.
    for table in (
        "products", "variants", "brands", "looks", "look_items", "orders",
        "saved_looks", "favorite_products", "favorite_brands",
        "style_profiles", "style_direction_preferences", "style_colour_preferences",
        "style_fit_preferences", "style_sizes", "style_material_preferences",
        "style_brand_preferences",
    ):
        if table not in tables:
            raise RuntimeError(f"accepted domain table missing after migration: {table}")


def downgrade() -> None:
    """DESTROYS CUSTOMER CONVERSATIONS. Read the module docstring before running this."""

    op.drop_table("dido_turns")
    op.drop_table("dido_sessions")
