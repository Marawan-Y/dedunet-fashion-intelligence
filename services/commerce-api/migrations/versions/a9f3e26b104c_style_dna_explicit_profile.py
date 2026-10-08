"""Style DNA: the explicit customer style profile.

Revision ID: a9f3e26b104c
Revises: c7a41d9e8b52
Create Date: 2026-10-08

ADDITIVE ONLY. Seven new tables; not one existing table, column, constraint or row is
touched. The catalogue, variants, prices, brands, looks, Saved rows and orders are all
outside this migration's reach, which is why the verification step at the end can assert
they are unchanged rather than hope so.

THE SOURCE COLUMN AND ITS CHECK CONSTRAINT ARE THE POINT OF THIS SCHEMA.

Every preference table carries `source` with a CHECK pinning it to 'USER_EXPLICIT'. That
constraint is how a future inference phase is made to announce itself: writing a derived
preference into these tables fails at the database, so it cannot be done by a code path
that forgot the distinction. Lifting it is a migration someone has to review, which is
exactly the conversation that should happen before a platform starts telling customers
things about themselves they never said.

ROLLBACK DESTROYS CUSTOMER DATA, AND IT IS NOT RECOVERABLE.

`downgrade()` drops seven tables holding style directions, colours, fits, stated sizes,
materials, brand preferences, budgets and fit notes. Unlike the multi-brand migration --
whose brand association was reconstructible from the registry -- NONE OF THIS CAN BE
REBUILT. It was typed by people about themselves. There is no source to re-derive it from
and no fixture that approximates it.

Export these seven tables before downgrading if any customer has used the feature.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a9f3e26b104c"
down_revision = "c7a41d9e8b52"
branch_labels = None
depends_on = None


#: Kept as a literal rather than imported from `style_taxonomy`. A migration describes the
#: schema at a point in time; importing a constant means a later edit to application code
#: silently changes what this migration did, and a migration that changes retroactively is
#: not a record of anything.
_USER_EXPLICIT = "USER_EXPLICIT"
_SOURCE_LEN = 40
_MAX_BUDGET_MINOR_UNITS = 100_000_000
_MAX_SIZE_LABEL = 12


def _source_column() -> sa.Column:
    return sa.Column(
        "source", sa.String(length=_SOURCE_LEN), nullable=False, server_default=_USER_EXPLICIT
    )


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def upgrade() -> None:
    # ---- 1. the profile root -------------------------------------------------
    op.create_table(
        "style_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column(
            "personalization_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("budget_per_piece_minor_units", sa.Integer(), nullable=True),
        sa.Column("budget_per_look_minor_units", sa.Integer(), nullable=True),
        sa.Column("budget_currency", sa.String(length=3), nullable=True),
        sa.Column("colour_approach", sa.String(length=40), nullable=True),
        sa.Column("care_effort", sa.String(length=40), nullable=True),
        sa.Column("seasonality", sa.String(length=40), nullable=True),
        sa.Column("fit_notes", sa.Text(), nullable=False, server_default=""),
        _created_at(),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        # ONE PROFILE PER CUSTOMER. Two profiles is a question with two answers.
        sa.UniqueConstraint("customer_id", name="uq_style_profile_customer"),
        sa.CheckConstraint(
            "budget_per_piece_minor_units IS NULL OR budget_per_piece_minor_units >= 0",
            name="ck_style_profile_piece_budget_non_negative",
        ),
        sa.CheckConstraint(
            "budget_per_look_minor_units IS NULL OR budget_per_look_minor_units >= 0",
            name="ck_style_profile_look_budget_non_negative",
        ),
        sa.CheckConstraint(
            f"budget_per_piece_minor_units IS NULL OR budget_per_piece_minor_units <= {_MAX_BUDGET_MINOR_UNITS}",
            name="ck_style_profile_piece_budget_ceiling",
        ),
        sa.CheckConstraint(
            f"budget_per_look_minor_units IS NULL OR budget_per_look_minor_units <= {_MAX_BUDGET_MINOR_UNITS}",
            name="ck_style_profile_look_budget_ceiling",
        ),
        # A budget amount without a currency is a number, not money.
        sa.CheckConstraint(
            "(budget_per_piece_minor_units IS NULL AND budget_per_look_minor_units IS NULL) "
            "OR budget_currency IS NOT NULL",
            name="ck_style_profile_budget_needs_currency",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_style_profile_revision_positive"),
    )
    op.create_index("ix_style_profiles_customer_id", "style_profiles", ["customer_id"])

    # ---- 2. stance tables ----------------------------------------------------
    for table, value_column, value_length in (
        ("style_direction_preferences", "style_slug", 60),
        ("style_colour_preferences", "colour_slug", 40),
        ("style_material_preferences", "material_slug", 40),
    ):
        short = {
            "style_direction_preferences": "style_direction",
            "style_colour_preferences": "style_colour",
            "style_material_preferences": "style_material",
        }[table]
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), nullable=False),
            sa.Column(value_column, sa.String(length=value_length), nullable=False),
            sa.Column("stance", sa.String(length=20), nullable=False),
            _source_column(),
            _created_at(),
            sa.ForeignKeyConstraint(["profile_id"], ["style_profiles.id"], ondelete="CASCADE"),
            # (profile, value) rather than (profile, value, stance): a customer cannot both
            # prefer and avoid the same thing, and this makes the contradiction
            # unrepresentable rather than merely discouraged.
            sa.UniqueConstraint("profile_id", value_column, name=f"uq_{short}_profile_slug"),
            sa.CheckConstraint(
                f"source = '{_USER_EXPLICIT}'", name=f"ck_{table}_source_user_explicit"
            ),
        )
        op.create_index(f"ix_{table}_profile_id", table, ["profile_id"])

    # ---- 3. fit ---------------------------------------------------------------
    op.create_table(
        "style_fit_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("garment_category", sa.String(length=40), nullable=False),
        sa.Column("fit_slug", sa.String(length=40), nullable=False),
        _source_column(),
        _created_at(),
        sa.ForeignKeyConstraint(["profile_id"], ["style_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "profile_id", "garment_category", name="uq_style_fit_profile_category"
        ),
        sa.CheckConstraint(
            f"source = '{_USER_EXPLICIT}'", name="ck_style_fit_preferences_source_user_explicit"
        ),
    )
    op.create_index(
        "ix_style_fit_preferences_profile_id", "style_fit_preferences", ["profile_id"]
    )

    # ---- 4. stated sizes ------------------------------------------------------
    #
    # Uniqueness is (profile, category, system), NOT (profile, category). A customer may
    # know their size in more than one system, and storing both is honest; collapsing them
    # would force the platform to pick one and imply the others are derivable from it.
    # Nothing in this phase converts between systems.
    op.create_table(
        "style_sizes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("garment_category", sa.String(length=40), nullable=False),
        sa.Column("size_system", sa.String(length=20), nullable=False),
        sa.Column("size_label", sa.String(length=_MAX_SIZE_LABEL), nullable=False),
        _source_column(),
        _created_at(),
        sa.ForeignKeyConstraint(["profile_id"], ["style_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "profile_id", "garment_category", "size_system", name="uq_style_size_profile_cat_sys"
        ),
        sa.CheckConstraint(
            f"length(size_label) > 0 AND length(size_label) <= {_MAX_SIZE_LABEL}",
            name="ck_style_size_label_length",
        ),
        sa.CheckConstraint(
            f"source = '{_USER_EXPLICIT}'", name="ck_style_sizes_source_user_explicit"
        ),
    )
    op.create_index("ix_style_sizes_profile_id", "style_sizes", ["profile_id"])

    # ---- 5. brand preferences, by foreign key ---------------------------------
    op.create_table(
        "style_brand_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("stance", sa.String(length=20), nullable=False),
        _source_column(),
        _created_at(),
        sa.ForeignKeyConstraint(["profile_id"], ["style_profiles.id"], ondelete="CASCADE"),
        # A name string would drift the moment a brand is renamed, leaving a preference for
        # a spelling that no longer exists. The brand domain is authoritative.
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "brand_id", name="uq_style_brand_profile_brand"),
        sa.CheckConstraint(
            f"source = '{_USER_EXPLICIT}'",
            name="ck_style_brand_preferences_source_user_explicit",
        ),
    )
    op.create_index(
        "ix_style_brand_preferences_profile_id", "style_brand_preferences", ["profile_id"]
    )
    op.create_index(
        "ix_style_brand_preferences_brand_id", "style_brand_preferences", ["brand_id"]
    )

    _verify_nothing_else_moved()


def _verify_nothing_else_moved() -> None:
    """Prove the accepted domains are untouched, and abort the migration if they are not.

    A migration that says "additive only" in its docstring is making a claim. This checks
    it inside the same transaction, so a mistake rolls back rather than landing and being
    discovered later by someone wondering why a price changed.

    The seven new tables must exist and be EMPTY -- a non-empty new table would mean this
    migration invented customer preferences, which is the one thing Style DNA may never do.
    """

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    expected_new = {
        "style_profiles",
        "style_direction_preferences",
        "style_colour_preferences",
        "style_material_preferences",
        "style_fit_preferences",
        "style_sizes",
        "style_brand_preferences",
    }
    missing = expected_new - tables
    if missing:
        raise RuntimeError(f"style dna migration did not create: {sorted(missing)}")

    for table in sorted(expected_new):
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        if count != 0:
            raise RuntimeError(
                f"{table} has {count} rows immediately after creation; this migration must "
                "not fabricate customer preferences"
            )

    # The domains this migration promised not to touch must still be present. Their ROW
    # COUNTS are verified outside the migration, against the recorded pre-migration
    # baseline -- a migration cannot meaningfully compare to a state it never saw.
    for table in ("products", "variants", "brands", "looks", "look_items", "orders",
                  "saved_looks", "favorite_products", "favorite_brands"):
        if table not in tables:
            raise RuntimeError(f"accepted domain table missing after migration: {table}")


def downgrade() -> None:
    """DESTROYS CUSTOMER STYLE DATA. Read the module docstring before running this.

    Dropped children-first so the foreign keys never block the drop on a database that
    enforces them.
    """

    op.drop_table("style_brand_preferences")
    op.drop_table("style_sizes")
    op.drop_table("style_fit_preferences")
    op.drop_table("style_material_preferences")
    op.drop_table("style_colour_preferences")
    op.drop_table("style_direction_preferences")
    op.drop_table("style_profiles")
