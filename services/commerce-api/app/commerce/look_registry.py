"""The curated looks, defined ONCE.

Transcribed verbatim from the editorial content that previously lived in the consumer
bundle (`apps/consumer/src/features/content.ts`). Extracted programmatically rather than
retyped, because a story paragraph copied by hand is a story paragraph that quietly diverges
from the one a reviewer approved.

WHAT A LOOK IS HERE: a person's arrangement of real catalogue products, with an editorial
sentence about why each piece is present. There is no total price and no field for one --
every DEDUNET product is a prototype, so a look total would be invented. There is no
reasoning engine, no scoring and no generation. See `looks.py`.

The importer, the seed and the migration all read this module, so a look cannot differ
between environments.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .looks import Look, LookItem
from .models import Product

# Occasion slugs match the client's editorial taxonomy. They are labels, not a domain.
CURATED_LOOKS: tuple[dict, ...] = (
    {
        "slug": 'quiet-interview',
        "name": 'The Quiet Interview',
        "occasion": 'interview',
        "story": (
            'An interview outfit should be the least interesting thing in the room. This one holds a clean vertical line and keeps every decision reversible: nothing here reads as a costume, and nothing distracts from what you say.'
        ),
        "descriptors": ['Minimal', 'Structured', 'Neutral'],
        "items": [
            {"product_slug": 'the-passage-shirt', "role": 'The clean upper line'},
            {"product_slug": 'the-measure-trouser', "role": 'Volume, held straight'}
        ],
    },
    {
        "slug": 'long-weekend',
        "name": 'The Long Weekend',
        "occasion": 'weekend',
        "story": (
            'Off duty without giving up on shape. The tee carries the ease and the trouser keeps the proportion honest, so the whole thing survives being photographed.'
        ),
        "descriptors": ['Relaxed', 'Contemporary', 'Easy'],
        "items": [
            {"product_slug": 'the-source-tee', "role": 'Ease, with a defined shoulder'},
            {"product_slug": 'the-measure-trouser', "role": 'The line that keeps it from slumping'}
        ],
    },
    {
        "slug": 'transitional-layer',
        "name": 'The Transitional Layer',
        "occasion": 'travel',
        "story": (
            'Built for the part of the year that cannot decide. The overshirt does the work of a jacket without the bulk, and the scarf is the adjustment you make at the door rather than a decoration.'
        ),
        "descriptors": ['Layered', 'Practical', 'Considered'],
        "items": [
            {"product_slug": 'the-structure-overshirt', "role": 'A jacket that folds flat'},
            {"product_slug": 'the-source-tee', "role": 'The base layer'},
            {"product_slug": 'the-measure-trouser', "role": 'Straight through the leg'},
            {"product_slug": 'the-trace-scarf', "role": 'The last adjustment'}
        ],
    },
    {
        "slug": 'evening-shirt',
        "name": 'Evening, Unfussy',
        "occasion": 'dinner',
        "story": (
            'Dinner does not need a suit. A shirt with an exact collar and a trouser that hangs properly reads as effort without announcing it.'
        ),
        "descriptors": ['Classic', 'Understated', 'Evening'],
        "items": [
            {"product_slug": 'the-passage-shirt', "role": 'The collar does the formality'},
            {"product_slug": 'the-measure-trouser', "role": 'Weight and fall'}
        ],
    },
)


def ensure_curated_looks(session: Session) -> dict[str, Look]:
    """Create the curated looks if absent; return them by slug. Safe to re-run.

    Does NOT rewrite an existing look. Editorial copy is operator-editable, and a
    provisioning function that reverted an edit on every boot would be a data-loss bug that
    only shows up once somebody has made one.

    A look whose products are not all present is SKIPPED rather than created partially. A
    two-piece outfit rendered with one piece is not a reduced look, it is a wrong one.
    """

    created: dict[str, Look] = {}
    for spec in CURATED_LOOKS:
        existing = session.scalar(select(Look).where(Look.slug == spec["slug"]))
        if existing is not None:
            created[spec["slug"]] = existing
            continue

        products = {}
        for item in spec["items"]:
            product = session.scalar(
                select(Product).where(Product.slug == item["product_slug"])
            )
            if product is None:
                break
            products[item["product_slug"]] = product
        if len(products) != len(spec["items"]):
            # The catalogue this look is composed from is not fully present.
            continue

        look = Look(
            slug=spec["slug"],
            name=spec["name"],
            occasion=spec["occasion"],
            story=spec["story"],
            descriptors_json=json.dumps(spec["descriptors"]),
            publication_status="published",
        )
        session.add(look)
        session.flush()
        for order, item in enumerate(spec["items"]):
            session.add(
                LookItem(
                    look_id=look.id,
                    product_id=products[item["product_slug"]].id,
                    role=item["role"],
                    sort_order=order,
                )
            )
        session.flush()
        created[spec["slug"]] = look
    return created
