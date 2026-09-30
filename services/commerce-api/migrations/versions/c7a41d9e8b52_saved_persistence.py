"""Saved persistence: curated looks, and saved looks / products / brands

Revision ID: c7a41d9e8b52
Revises: f5c2a8d13b70
Create Date: 2026-09-30

TWO DOMAINS, one revision, because the second cannot exist without the first.

**Looks become real rows.** They were a hardcoded array in the consumer bundle, identified
only by a slug whose authority was a TypeScript constant. Saving against that would have
been persistence in name only -- a row pointing at a string no foreign key could protect,
silently wrong the moment somebody edited the array. A `Look` here is still exactly what it
was: a curated editorial arrangement of real products, composed by a person. There is no
total price and no column for one, no reasoning and no generation. The outfit engine is a
later phase and none of it is started.

**Saved items become personal data with integrity.** `saved_looks`, `favorite_products` and
`favorite_brands` each carry `UNIQUE(customer_id, target_id)`, so a double tap or a retried
request is a no-op rather than a duplicate row, and `ondelete=CASCADE` on `customer_id`, so
deleting a customer takes their taste with them. There is deliberately **no
`organization_id`** on any of them: a merchant has no business knowing who saved their
products, and a tenant column would put that one query away.

THE LOOK CONTENT IS EMBEDDED BELOW, generated from `app/commerce/look_registry.py` rather
than retyped. Two properties were wanted at once: a self-contained migration whose replay
reproduces this revision's content, and prose that does not diverge from the reviewed copy
through a transcription slip.

DATA SAFETY. No existing table is altered. Not one column is added to `products`,
`variants`, `brands`, `customers` or `orders`; no price, publication state, sellable flag or
catalogue row is read or rewritten. This revision only creates tables and inserts looks
composed of products that already exist. A look whose products are not all present is
skipped rather than created partially, because a two-piece outfit rendered with one piece is
not a reduced look, it is a wrong one.

ROLLBACK. Honest and genuinely cheap this time, unlike the brand revision: nothing outside
these five tables references them, so `downgrade()` drops them and the catalogue is
untouched. What is lost is **customers' saved items** -- real user data, not derivable from
anything. It cannot be reconstructed by re-running `upgrade()`. Export `saved_looks`,
`favorite_products` and `favorite_brands` first if the rows matter.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "c7a41d9e8b52"
down_revision = "f5c2a8d13b70"
branch_labels = None
depends_on = None


CURATED_LOOKS = [   {   'slug': 'quiet-interview',
        'name': 'The Quiet Interview',
        'occasion': 'interview',
        'story': 'An interview outfit should be the least interesting thing in the room. '
                 'This one holds a clean vertical line and keeps every decision reversible: '
                 'nothing here reads as a costume, and nothing distracts from what you say.',
        'descriptors': ['Minimal', 'Structured', 'Neutral'],
        'items': [   {'product_slug': 'the-passage-shirt', 'role': 'The clean upper line'},
                     {   'product_slug': 'the-measure-trouser',
                         'role': 'Volume, held straight'}]},
    {   'slug': 'long-weekend',
        'name': 'The Long Weekend',
        'occasion': 'weekend',
        'story': 'Off duty without giving up on shape. The tee carries the ease and the '
                 'trouser keeps the proportion honest, so the whole thing survives being '
                 'photographed.',
        'descriptors': ['Relaxed', 'Contemporary', 'Easy'],
        'items': [   {   'product_slug': 'the-source-tee',
                         'role': 'Ease, with a defined shoulder'},
                     {   'product_slug': 'the-measure-trouser',
                         'role': 'The line that keeps it from slumping'}]},
    {   'slug': 'transitional-layer',
        'name': 'The Transitional Layer',
        'occasion': 'travel',
        'story': 'Built for the part of the year that cannot decide. The overshirt does the '
                 'work of a jacket without the bulk, and the scarf is the adjustment you '
                 'make at the door rather than a decoration.',
        'descriptors': ['Layered', 'Practical', 'Considered'],
        'items': [   {   'product_slug': 'the-structure-overshirt',
                         'role': 'A jacket that folds flat'},
                     {'product_slug': 'the-source-tee', 'role': 'The base layer'},
                     {   'product_slug': 'the-measure-trouser',
                         'role': 'Straight through the leg'},
                     {'product_slug': 'the-trace-scarf', 'role': 'The last adjustment'}]},
    {   'slug': 'evening-shirt',
        'name': 'Evening, Unfussy',
        'occasion': 'dinner',
        'story': 'Dinner does not need a suit. A shirt with an exact collar and a trouser '
                 'that hangs properly reads as effort without announcing it.',
        'descriptors': ['Classic', 'Understated', 'Evening'],
        'items': [   {   'product_slug': 'the-passage-shirt',
                         'role': 'The collar does the formality'},
                     {'product_slug': 'the-measure-trouser', 'role': 'Weight and fall'}]}]


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------ 1. look domain
    op.create_table(
        "looks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("occasion", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("story", sa.Text(), nullable=False, server_default=""),
        sa.Column("descriptors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "publication_status", sa.String(length=30), nullable=False, server_default="published"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_looks_slug", "looks", ["slug"], unique=True)
    op.create_index("ix_looks_occasion", "looks", ["occasion"])
    op.create_index("ix_looks_publication_status", "looks", ["publication_status"])

    op.create_table(
        "look_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "look_id", sa.Integer(), sa.ForeignKey("looks.id", ondelete="CASCADE"), nullable=False
        ),
        # RESTRICT: dropping a garment out of a curated outfit because a product was deleted
        # would leave an arrangement that no longer says what its author meant.
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("look_id", "product_id", name="uq_look_item_look_product"),
        # One slot per position, so rendered order cannot depend on row order.
        sa.UniqueConstraint("look_id", "sort_order", name="uq_look_item_look_sort"),
    )
    op.create_index("ix_look_items_look_id", "look_items", ["look_id"])
    op.create_index("ix_look_items_product_id", "look_items", ["product_id"])

    # ------------------------------------------------------------------ 2. saved domain
    for table, target, target_table, uq in (
        ("saved_looks", "look_id", "looks", "uq_saved_look_customer_look"),
        ("favorite_products", "product_id", "products", "uq_favorite_product_customer_product"),
        ("favorite_brands", "brand_id", "brands", "uq_favorite_brand_customer_brand"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "customer_id",
                sa.Integer(),
                sa.ForeignKey("customers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                target,
                sa.Integer(),
                sa.ForeignKey(f"{target_table}.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            # Duplicate prevention in the DATABASE. An application check loses the race
            # between two taps on a phone with a flaky connection; a unique constraint does
            # not, which is what makes save idempotent rather than merely usually-idempotent.
            sa.UniqueConstraint("customer_id", target, name=uq),
        )
        op.create_index(f"ix_{table}_customer_id", table, ["customer_id"])
        op.create_index(f"ix_{table}_{target}", table, [target])
        # Saved lists sort most-recent-first, so the ordering column is indexed rather than
        # sorted in memory once a customer has saved more than a screenful.
        op.create_index(f"ix_{table}_created_at", table, ["created_at"])

    # ------------------------------------------------------------------ 3. seed the looks
    for spec in CURATED_LOOKS:
        product_ids = {}
        for item in spec["items"]:
            pid = bind.execute(
                sa.text("SELECT id FROM products WHERE slug = :slug").bindparams(
                    slug=item["product_slug"]
                )
            ).scalar()
            if pid is None:
                break
            product_ids[item["product_slug"]] = pid
        if len(product_ids) != len(spec["items"]):
            # Catalogue not fully present -- skip rather than build a partial outfit.
            continue

        bind.execute(
            sa.text(
                "INSERT INTO looks (slug, name, occasion, story, descriptors_json, "
                "publication_status, created_at, updated_at) VALUES (:slug, :name, :occasion, "
                ":story, :descriptors, 'published', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ).bindparams(
                slug=spec["slug"],
                name=spec["name"],
                occasion=spec["occasion"],
                story=spec["story"],
                descriptors=json.dumps(spec["descriptors"]),
            )
        )
        look_id = bind.execute(
            sa.text("SELECT id FROM looks WHERE slug = :slug").bindparams(slug=spec["slug"])
        ).scalar_one()

        for order, item in enumerate(spec["items"]):
            bind.execute(
                sa.text(
                    "INSERT INTO look_items (look_id, product_id, role, sort_order) "
                    "VALUES (:look_id, :product_id, :role, :sort_order)"
                ).bindparams(
                    look_id=look_id,
                    product_id=product_ids[item["product_slug"]],
                    role=item["role"],
                    sort_order=order,
                )
            )

    # ------------------------------------------------------------------ 4. verify
    orphan_items = bind.execute(
        sa.text(
            "SELECT count(*) FROM look_items li "
            "LEFT JOIN products p ON p.id = li.product_id WHERE p.id IS NULL"
        )
    ).scalar_one()
    if orphan_items:
        raise RuntimeError(f"{orphan_items} look_items reference a missing product")

    empty_looks = bind.execute(
        sa.text(
            "SELECT count(*) FROM looks l "
            "LEFT JOIN look_items li ON li.look_id = l.id "
            "WHERE li.id IS NULL"
        )
    ).scalar_one()
    if empty_looks:
        raise RuntimeError(f"{empty_looks} look(s) were created with no items")


def downgrade() -> None:
    """Drop the five tables. The catalogue is untouched.

    **This destroys customers' saved items.** They are real user data and are not derivable
    from anything, so re-running `upgrade()` does not bring them back -- unlike the brand
    revision, whose association was reconstructible. Export the three saved tables first if
    the rows matter.
    """

    for table, target in (
        ("saved_looks", "look_id"),
        ("favorite_products", "product_id"),
        ("favorite_brands", "brand_id"),
    ):
        op.drop_index(f"ix_{table}_created_at", table_name=table)
        op.drop_index(f"ix_{table}_{target}", table_name=table)
        op.drop_index(f"ix_{table}_customer_id", table_name=table)
        op.drop_table(table)

    op.drop_index("ix_look_items_product_id", table_name="look_items")
    op.drop_index("ix_look_items_look_id", table_name="look_items")
    op.drop_table("look_items")

    op.drop_index("ix_looks_publication_status", table_name="looks")
    op.drop_index("ix_looks_occasion", table_name="looks")
    op.drop_index("ix_looks_slug", table_name="looks")
    op.drop_table("looks")
