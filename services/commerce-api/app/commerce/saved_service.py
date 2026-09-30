"""Saving and unsaving, with the visibility rules in ONE place.

THE RULE THAT MATTERS MOST: you may only save what you could already see.

A saveable target must pass the same visibility test the catalogue applies — published,
active, and in brand-preview mode carrying a DEDUNET external identity. A target that fails
it answers **404, not 403**, because 403 confirms the row exists and turns `POST
/me/saved/products/1..1000` into a catalogue enumeration for unpublished and fixture content.
That is the whole reason this is a service function rather than three copies of a `select`:
one of the copies would eventually forget the filter.

READ-TIME BEHAVIOUR IS DIFFERENT FROM WRITE-TIME, deliberately. You cannot *create* a save
for something you cannot see. But something already saved that later becomes unpublished is
still returned in your list, marked `available: false` and carrying no link — because it was
yours, and silently vanishing from your own saved page is worse than being told it is not
currently available. Nothing hidden leaks: you can only reach that state for a target you
were legitimately shown once.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import modes
from .brands import Brand
from .looks import Look
from .models import Customer, Product
from .saved import FavoriteBrand, FavoriteProduct, SavedLook
from .services import NotFound, record_event


@dataclass(frozen=True)
class SaveOutcome:
    """What happened, so the API can answer honestly rather than guess a status code."""

    created: bool
    """False when the row already existed. The request still succeeded."""


# --------------------------------------------------------------------------- visibility


def visible_products(session: Session) -> Select:
    stmt = select(Product).where(Product.is_active.is_(True))
    # The same scoping `list_products` applies, so a saved endpoint cannot become a way
    # around the preview-mode catalogue filter.
    if modes.is_preview_mode():
        stmt = stmt.where(Product.external_product_id.is_not(None))
    return stmt


def visible_brands(session: Session) -> Select:
    from .brand_api import brands_visible

    return brands_visible(session)


def visible_looks(session: Session) -> Select:
    return select(Look).where(Look.publication_status == "published")


def _resolve_or_404(session: Session, stmt: Select, *, kind: str, identifier) -> object:
    row = session.scalar(stmt)
    if row is None:
        # 404 rather than 403. See the module docstring: 403 leaks existence.
        raise NotFound(f"{kind} not found")
    return row


def resolve_product(session: Session, *, slug: str) -> Product:
    return _resolve_or_404(
        session, visible_products(session).where(Product.slug == slug),
        kind="product", identifier=slug,
    )


def resolve_brand(session: Session, *, slug: str) -> Brand:
    return _resolve_or_404(
        session, visible_brands(session).where(Brand.slug == slug),
        kind="brand", identifier=slug,
    )


def resolve_look(session: Session, *, slug: str) -> Look:
    return _resolve_or_404(
        session, visible_looks(session).where(Look.slug == slug),
        kind="look", identifier=slug,
    )


# --------------------------------------------------------------------------- mutation

_RELATION = {
    "products": (FavoriteProduct, "product_id"),
    "brands": (FavoriteBrand, "brand_id"),
    "looks": (SavedLook, "look_id"),
}


def save(
    session: Session, *, customer: Customer, kind: str, target_id: int, target_slug: str
) -> SaveOutcome:
    """Idempotent save. Saving something already saved succeeds and creates nothing.

    The IntegrityError branch is not defensive decoration: two concurrent taps on a phone
    with a flaky connection genuinely race, both find no existing row, and both insert. The
    unique constraint is what makes the second one harmless, and catching it here is what
    turns a 500 into the correct answer.
    """

    model, column = _RELATION[kind]
    existing = session.scalar(
        select(model).where(
            model.customer_id == customer.id, getattr(model, column) == target_id
        )
    )
    if existing is not None:
        return SaveOutcome(created=False)

    row = model(customer_id=customer.id, **{column: target_id})
    session.add(row)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        # Lost the race. The desired state holds, which is what the caller asked for.
        return SaveOutcome(created=False)

    _emit(session, kind, target_slug, saved=True)
    session.commit()
    return SaveOutcome(created=True)


def unsave(session: Session, *, customer: Customer, kind: str, target_id: int, target_slug: str) -> bool:
    """Idempotent unsave. Returns whether a row was actually removed.

    Unsaving something that is not saved is a SUCCESS, not a 404. The caller asked for a
    state -- "not saved" -- and that state holds either way. Answering 404 would make a
    double tap look like an error and push clients into checking before deleting, which is a
    race they would then have to handle.
    """

    model, column = _RELATION[kind]
    result = session.execute(
        delete(model).where(
            model.customer_id == customer.id, getattr(model, column) == target_id
        )
    )
    removed = bool(result.rowcount)
    if removed:
        _emit(session, kind, target_slug, saved=False)
    session.commit()
    return removed


def _emit(session: Session, kind: str, target_slug: str, *, saved: bool) -> None:
    """Domain event through the existing analytics seam.

    NO CUSTOMER IDENTIFIER. The event records that a thing was saved, not who saved it:
    "product_saved" plus a slug is a product-popularity signal, while the same event plus a
    customer id is a behavioural profile, and this phase has no consent basis for the second.
    `record_event` already writes a correlation id, which is enough to debug a request
    without building a per-person history nobody asked for.
    """

    singular = {"products": "product", "brands": "brand", "looks": "look"}[kind]
    record_event(
        session,
        f"{singular}_{'saved' if saved else 'unsaved'}",
        {singular: target_slug},
    )


# --------------------------------------------------------------------------- reads


def saved_state(session: Session, *, customer: Customer) -> dict[str, list[str]]:
    """Every slug this customer has saved, in ONE query per kind.

    This exists so a page with twenty cards makes ONE request instead of twenty. A
    per-card `GET /saved/status?product=x` is the obvious implementation and it is a
    guaranteed N+1 against the API: Home alone renders enough cards to spend a rate-limit
    budget on nothing but heart icons.

    Slugs rather than ids, because the client already routes by slug and would otherwise
    hold a second identifier space to map between.
    """

    products = session.scalars(
        select(Product.slug)
        .join(FavoriteProduct, FavoriteProduct.product_id == Product.id)
        .where(FavoriteProduct.customer_id == customer.id)
    ).all()
    brands = session.scalars(
        select(Brand.slug)
        .join(FavoriteBrand, FavoriteBrand.brand_id == Brand.id)
        .where(FavoriteBrand.customer_id == customer.id)
    ).all()
    looks = session.scalars(
        select(Look.slug)
        .join(SavedLook, SavedLook.look_id == Look.id)
        .where(SavedLook.customer_id == customer.id)
    ).all()
    return {
        "products": sorted(products),
        "brands": sorted(brands),
        "looks": sorted(looks),
    }


def saved_counts(session: Session, *, customer: Customer) -> dict[str, int]:
    """Counts in three aggregate queries rather than by loading the rows."""

    return {
        "products": session.scalar(
            select(func.count())
            .select_from(FavoriteProduct)
            .where(FavoriteProduct.customer_id == customer.id)
        ) or 0,
        "brands": session.scalar(
            select(func.count())
            .select_from(FavoriteBrand)
            .where(FavoriteBrand.customer_id == customer.id)
        ) or 0,
        "looks": session.scalar(
            select(func.count())
            .select_from(SavedLook)
            .where(SavedLook.customer_id == customer.id)
        ) or 0,
    }


def delete_all_for_customer(session: Session, *, customer: Customer) -> dict[str, int]:
    """Remove every saved row for a customer. Used by the erasure path.

    Needed because `erase_customer` PSEUDONYMIZES -- it keeps the customer row so order
    history stays reconcilable -- which means the `ondelete=CASCADE` foreign keys never
    fire. Saved items have no accounting value and are personal preference data, so they are
    deleted outright, exactly as addresses already are.
    """

    removed = {}
    for kind, (model, _column) in _RELATION.items():
        result = session.execute(delete(model).where(model.customer_id == customer.id))
        removed[kind] = int(result.rowcount or 0)
    return removed


# --------------------------------------------------------------------------- serialisation
#
# SUMMARIES, not full payloads. A saved list of forty products should not carry forty
# complete product documents with every variant, media role and claim status -- that is
# kilobytes per row for a card that renders a name, an image and a price. Each entry carries
# what the card needs plus the slug to fetch the rest.
#
# `available` is the read-time half of the visibility rule. A target that has since been
# unpublished stays in your list, flagged and unlinked, rather than vanishing: it was yours,
# and silent disappearance from your own saved page is worse than being told it is not
# currently available. Nothing hidden leaks, because you could only have saved it while it
# was visible.


def _price_bounds(product: Product) -> tuple[int | None, int | None]:
    prices = [v.price_minor_units for v in product.variants if v.price_minor_units]
    return (min(prices), max(prices)) if prices else (None, None)


def _media_url(product: Product) -> str:
    for media in sorted(product.media, key=lambda m: (m.sort_order, m.asset_id)):
        return f"/api/v1/media/{media.path}"
    return product.image_url or ""


def _iso(value) -> str:
    from .models import as_utc

    normalised = as_utc(value)
    return normalised.isoformat() if normalised else ""


def saved_product_entry(session: Session, *, favorite, product: Product, available: bool) -> dict:
    from .brand_api import RELATIONSHIP_LABELS, _route_of

    low, high = _price_bounds(product)
    brand = product.brand
    return {
        "kind": "product",
        "slug": product.slug,
        "name": product.name,
        "category": product.category,
        "currency": product.currency,
        "price_minor_units_min": low,
        "price_minor_units_max": high,
        "image_url": _media_url(product) if available else "",
        "brand": (
            {
                "slug": brand.slug,
                "name": brand.name,
                "relationship_label": RELATIONSHIP_LABELS[brand.ownership_type],
                "is_development_fixture": brand.is_development_fixture,
            }
            if brand is not None
            else None
        ),
        "commerce_route": _route_of(product).value,
        "saved_at": _iso(favorite.created_at),
        # False once the target stops being visible. The client renders it as unavailable
        # and does NOT link to it.
        "available": available,
    }


def saved_brand_entry(session: Session, *, favorite, brand: Brand, available: bool) -> dict:
    from .brand_api import FIXTURE_NOTICE, RELATIONSHIP_LABELS

    return {
        "kind": "brand",
        "slug": brand.slug,
        "name": brand.name,
        "relationship_label": RELATIONSHIP_LABELS[brand.ownership_type],
        "logo_url": (
            f"/api/v1/media/{brand.logo_media_path}" if brand.logo_media_path else ""
        ),
        # The fixture flag travels with the saved entry too. Saving a fixture must not
        # launder it into looking production-valid on a different surface.
        "is_development_fixture": brand.is_development_fixture,
        "fixture_notice": FIXTURE_NOTICE if brand.is_development_fixture else "",
        "saved_at": _iso(favorite.created_at),
        "available": available,
    }


def saved_look_entry(session: Session, *, saved, look: Look, available: bool) -> dict:
    payload = look_payload(session, look) if available else {
        "slug": look.slug, "name": look.name, "items": []
    }
    return {
        "kind": "look",
        "slug": look.slug,
        "name": look.name,
        "occasion": look.occasion,
        "item_count": len(payload.get("items", [])),
        "image_url": (payload.get("items") or [{}])[0].get("image_url", ""),
        "saved_at": _iso(saved.created_at),
        "available": available,
    }


def look_payload(session: Session, look: Look) -> dict:
    """A look and the products it is composed of.

    NO TOTAL PRICE, and no field for one. Every DEDUNET product is a prototype carrying a
    price for a piece nobody can buy, so summing them would produce a figure for an outfit
    that cannot be purchased as an outfit. Its absence is the same decision the look detail
    page already states in words, and inventing it here would undo that.
    """

    return {
        "slug": look.slug,
        "name": look.name,
        "occasion": look.occasion,
        "story": look.story,
        "descriptors": look.descriptors,
        "publication_status": look.publication_status,
        "items": [entry for entry in (_look_item_entry(session, i) for i in sorted(
            look.items, key=lambda i: i.sort_order)) if entry is not None],
    }


def _look_item_entry(session: Session, item) -> dict | None:
    """One garment's part in a look, or None if its product has gone.

    Returning None rather than a half-filled entry: a look item whose product cannot be
    loaded is a broken reference, and rendering it as a nameless card is worse than
    rendering one fewer garment. The `RESTRICT` foreign key means this should be
    unreachable -- it is here because "should be unreachable" is not "is".
    """

    product = _item_product(session, item)
    if product is None:
        return None
    return {
        "product_slug": product.slug,
        "product_name": product.name,
        "role": item.role,
        "image_url": _media_url(product),
        "category": product.category,
    }


def _item_product(session: Session, item) -> Product | None:
    """The product behind a look item.

    `LookItem` has no `product` relationship on purpose -- adding one would make `looks.py`
    import the models module and recreate the cycle that was removed in the brand phase --
    so it is fetched here. `session.get` hits the identity map, so a look whose four items
    were already loaded costs no additional queries.
    """

    return session.get(Product, item.product_id)
