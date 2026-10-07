"""Reading, validating, mutating and deleting a customer's Style DNA.

Three things in here are worth knowing before reading the code.

**Every write is validated against the taxonomy BEFORE anything is applied.** The patch is
checked whole, then written whole. A half-applied update that accepted the colours and
rejected the sizes would leave a profile the customer never asked for and cannot see the
shape of, and "which parts landed?" is not a question an editor should ever raise.

**The revision check is the first thing that happens, not the last.** Validating a stale
patch and then rejecting it wastes nothing, but applying part of one does real harm.

**Absence and emptiness are different, and both are different from "unset".** A field
missing from a PATCH body means "leave this alone". A field present and empty means "I am
clearing this". Collapsing those two would make it impossible to clear a preference without
sending the entire profile, and impossible to change one field without risking the rest.
`_MISSING` is the sentinel that keeps them apart.
"""

from __future__ import annotations

from typing import Any, Final

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from .brands import Brand
from .models import Customer
from .services import record_event
from .style_dna import (
    STYLE_DNA_CHILD_MODELS,
    StyleBrandPreference,
    StyleColourPreference,
    StyleDirectionPreference,
    StyleFitPreference,
    StyleMaterialPreference,
    StyleProfile,
    StyleSize,
)
from . import style_taxonomy as tax


class StyleDnaError(ValueError):
    """A patch the customer sent that cannot be applied. Maps to 400."""


class RevisionConflict(Exception):
    """The profile moved on since the caller read it. Maps to 409.

    Carries the current revision so the client can tell the customer what happened without
    a second round trip.
    """

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"expected revision {expected}, profile is at {actual}")
        self.expected = expected
        self.actual = actual


#: Distinguishes "the caller did not mention this field" from "the caller sent null/[]".
_MISSING: Final = object()


# --------------------------------------------------------------------------- reads


def get_profile(session: Session, *, customer: Customer) -> StyleProfile | None:
    """The customer's profile with every child collection, in ONE round trip.

    `selectinload` rather than lazy access: the editor renders all six collections every
    time, and lazy loading would make that seven queries to draw one page. Section 35 asks
    for one reasonable profile request, and that has to be true on the server too -- a
    single HTTP call that fans out into N+1 behind it is the same cost wearing a disguise.
    """

    return session.scalar(
        select(StyleProfile)
        .where(StyleProfile.customer_id == customer.id)
        .options(
            selectinload(StyleProfile.style_directions),
            selectinload(StyleProfile.colours),
            selectinload(StyleProfile.fits),
            selectinload(StyleProfile.sizes),
            selectinload(StyleProfile.materials),
            selectinload(StyleProfile.brands).selectinload(StyleBrandPreference.profile),
        )
    )


def empty_profile_payload() -> dict[str, Any]:
    """What a signed-in customer with no Style DNA gets. 200, not 404.

    A 404 would mean "this URL is wrong", and the URL is not wrong -- the customer simply
    has not made a profile yet. More practically: a client that has to read absence out of
    an error status cannot tell "you have no profile" apart from "your session expired",
    and those two need opposite responses from the UI. So absence is a normal body with
    `exists: false`, and 401 keeps its one meaning.
    """

    return {
        "exists": False,
        "revision": 0,
        "personalization_enabled": False,
        "style_directions": [],
        "colours": [],
        "colour_approach": None,
        "fits": [],
        "sizes": [],
        "materials": [],
        "care_effort": None,
        "seasonality": None,
        "fit_notes": "",
        "brands": [],
        "budget": {"per_piece_minor_units": None, "per_look_minor_units": None, "currency": None},
        "sections_with_preferences": 0,
        "section_count": len(SECTIONS),
        "created_at": None,
        "updated_at": None,
    }


#: The five conceptual sections the accepted My Style shell already established, kept
#: because the repository showed them to people and this phase was told to preserve the
#: structure absent a concrete contradiction. There was none.
SECTIONS: Final[tuple[str, ...]] = (
    "how-you-dress",
    "colour",
    "fit-and-size",
    "material",
    "brands-and-budget",
)


def _sections_with_preferences(profile: StyleProfile) -> int:
    """How many of the five sections hold at least one thing the customer said.

    A COUNT, not a score. "3 of 5" is checkable by the person reading it; "Style DNA
    strength: 78%" is a number with no definition, no validation and no model behind it,
    and it would be the first piece of pseudo-science on the page. There is no model here,
    so there is no percentage.
    """

    filled = 0
    if profile.style_directions:
        filled += 1
    if profile.colours or profile.colour_approach:
        filled += 1
    if profile.fits or profile.sizes or profile.fit_notes:
        filled += 1
    if profile.materials or profile.care_effort or profile.seasonality:
        filled += 1
    if (
        profile.brands
        or profile.budget_per_piece_minor_units is not None
        or profile.budget_per_look_minor_units is not None
    ):
        filled += 1
    return filled


def serialize(session: Session, profile: StyleProfile) -> dict[str, Any]:
    """The profile as the client sees it.

    Brand preferences carry slug and name, because an interface that showed a customer
    `brand_id: 1` would be exposing a database key as if it meant something to them.
    Everything else is slugs, which the options endpoint turns into labels -- one place
    owns the words.
    """

    brand_rows = session.execute(
        select(Brand.id, Brand.slug, Brand.name)
        .where(Brand.id.in_([b.brand_id for b in profile.brands]))
    ).all() if profile.brands else []
    brands_by_id = {row.id: row for row in brand_rows}

    def stances(rows, attr: str) -> list[dict[str, str]]:
        return sorted(
            ({"slug": getattr(r, attr), "stance": r.stance, "source": r.source} for r in rows),
            key=lambda d: d["slug"],
        )

    return {
        "exists": True,
        "revision": profile.revision,
        "personalization_enabled": profile.personalization_enabled,
        "style_directions": stances(profile.style_directions, "style_slug"),
        "colours": stances(profile.colours, "colour_slug"),
        "colour_approach": profile.colour_approach,
        "fits": sorted(
            (
                {
                    "garment_category": f.garment_category,
                    "fit": f.fit_slug,
                    "source": f.source,
                }
                for f in profile.fits
            ),
            key=lambda d: d["garment_category"],
        ),
        "sizes": sorted(
            (
                {
                    "garment_category": s.garment_category,
                    "size_system": s.size_system,
                    "size_label": s.size_label,
                    "source": s.source,
                }
                for s in profile.sizes
            ),
            key=lambda d: (d["garment_category"], d["size_system"]),
        ),
        "materials": stances(profile.materials, "material_slug"),
        "care_effort": profile.care_effort,
        "seasonality": profile.seasonality,
        "fit_notes": profile.fit_notes,
        "brands": sorted(
            (
                {
                    "slug": brands_by_id[b.brand_id].slug,
                    "name": brands_by_id[b.brand_id].name,
                    "stance": b.stance,
                    "source": b.source,
                }
                for b in profile.brands
                if b.brand_id in brands_by_id
            ),
            key=lambda d: d["slug"],
        ),
        "budget": {
            "per_piece_minor_units": profile.budget_per_piece_minor_units,
            "per_look_minor_units": profile.budget_per_look_minor_units,
            "currency": profile.budget_currency,
        },
        "sections_with_preferences": _sections_with_preferences(profile),
        "section_count": len(SECTIONS),
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


# --------------------------------------------------------------------------- validation


def _require_list(value: Any, field: str) -> list:
    if not isinstance(value, list):
        raise StyleDnaError(f"{field} must be a list")
    return value


def _validate_stance_list(
    value: Any, *, field: str, vocabulary: frozenset[str], limit: int, key: str
) -> list[tuple[str, str]]:
    """Parse and check a list of `{slug, stance}` entries.

    Duplicate slugs are rejected here rather than left to the unique constraint. The
    constraint is the guarantee; this is the error message. A caller that sends
    `black: PREFERRED` and `black: AVOIDED` in one patch has made a mistake worth naming,
    and an IntegrityError would tell them only that something collided.
    """

    rows = _require_list(value, field)
    if len(rows) > limit:
        raise StyleDnaError(f"{field} accepts at most {limit} entries")

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for entry in rows:
        if not isinstance(entry, dict):
            raise StyleDnaError(f"{field} entries must be objects")
        slug = entry.get(key)
        stance = entry.get("stance")
        if not isinstance(slug, str) or slug not in vocabulary:
            raise StyleDnaError(f"unknown {field} value: {slug!r}")
        if stance not in tax.STANCES:
            raise StyleDnaError(f"{field} stance must be one of {list(tax.STANCES)}")
        if slug in seen:
            raise StyleDnaError(f"{field} contains {slug!r} twice")
        seen.add(slug)
        out.append((slug, stance))
    return out


def _validate_single(value: Any, *, field: str, vocabulary: frozenset[str]) -> str | None:
    """A single-select field. `None` clears it."""

    if value is None:
        return None
    if not isinstance(value, str) or value not in vocabulary:
        raise StyleDnaError(f"unknown {field} value: {value!r}")
    return value


def _validate_budget(patch: dict, profile_currency: str | None) -> dict[str, Any]:
    """Budgets: integer minor units, explicit currency, nothing else.

    A float is rejected rather than coerced. `int(199.99 * 100)` is 19998 on this hardware,
    and a money value that is quietly one cent wrong is worse than a rejected request --
    SIDE_B_MONEY_CONTRACT rule 1 exists because that error is invisible until it is
    reconciled. `bool` is excluded explicitly because `isinstance(True, int)` is True in
    Python and `True` is not a budget.
    """

    out: dict[str, Any] = {}
    for key, column in (
        ("per_piece_minor_units", "budget_per_piece_minor_units"),
        ("per_look_minor_units", "budget_per_look_minor_units"),
    ):
        if key not in patch:
            continue
        value = patch[key]
        if value is None:
            out[column] = None
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            raise StyleDnaError(
                f"budget.{key} must be an integer number of minor units, not {type(value).__name__}"
            )
        if value < 0:
            raise StyleDnaError(f"budget.{key} cannot be negative")
        if value > tax.MAX_BUDGET_MINOR_UNITS:
            raise StyleDnaError(f"budget.{key} exceeds the maximum")
        out[column] = value

    if "currency" in patch:
        currency = patch["currency"]
        if currency is None:
            out["budget_currency"] = None
        elif (
            not isinstance(currency, str)
            or currency.upper() not in tax.SUPPORTED_BUDGET_CURRENCIES
        ):
            raise StyleDnaError(f"unsupported budget currency: {currency!r}")
        else:
            out["budget_currency"] = currency.upper()

    # A budget amount with no currency anywhere is a number pretending to be money.
    amounts = [out.get(c) for c in ("budget_per_piece_minor_units", "budget_per_look_minor_units")]
    if any(a is not None for a in amounts):
        currency = out.get("budget_currency", profile_currency)
        if not currency:
            raise StyleDnaError("a budget requires a currency")
        out["budget_currency"] = currency
    return out


def _resolve_brands(session: Session, value: Any) -> list[tuple[int, str]]:
    """Turn `{slug, stance}` entries into `(brand_id, stance)` against the real Brand domain.

    Development fixtures are refused. `internal-development-fixtures` exists so that
    pre-brand products have a non-null `brand_id` without being attributed to a real label;
    offering it to a customer as something they could "follow" would present a scaffold as a
    fashion house. Unpublished brands are refused for the same reason the catalogue hides
    them -- and with a 400 naming the slug, because unlike a save endpoint this is a form
    the client populated from our own options, so an unknown slug is our bug, not a probe.
    """

    rows = _require_list(value, "brands")
    if len(rows) > tax.MAX_BRANDS:
        raise StyleDnaError(f"brands accepts at most {tax.MAX_BRANDS} entries")

    seen: set[str] = set()
    parsed: list[tuple[str, str]] = []
    for entry in rows:
        if not isinstance(entry, dict):
            raise StyleDnaError("brands entries must be objects")
        slug = entry.get("slug")
        stance = entry.get("stance")
        if not isinstance(slug, str) or not slug:
            raise StyleDnaError("brands entries need a slug")
        if stance not in tax.STANCES:
            raise StyleDnaError(f"brand stance must be one of {list(tax.STANCES)}")
        if slug in seen:
            raise StyleDnaError(f"brands contains {slug!r} twice")
        seen.add(slug)
        parsed.append((slug, stance))

    if not parsed:
        return []

    found = {
        b.slug: b
        for b in session.scalars(
            select(Brand).where(Brand.slug.in_([s for s, _ in parsed]))
        ).all()
    }
    out: list[tuple[int, str]] = []
    for slug, stance in parsed:
        brand = found.get(slug)
        if brand is None:
            raise StyleDnaError(f"unknown brand: {slug!r}")
        if brand.is_development_fixture:
            raise StyleDnaError(f"{slug!r} is a development fixture and cannot be a preference")
        if brand.publication_status not in ("published", "preview"):
            raise StyleDnaError(f"unknown brand: {slug!r}")
        out.append((brand.id, stance))
    return out


def _validate_sizes(value: Any) -> list[tuple[str, str, str]]:
    rows = _require_list(value, "sizes")
    if len(rows) > tax.MAX_SIZES:
        raise StyleDnaError(f"sizes accepts at most {tax.MAX_SIZES} entries")

    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str, str]] = []
    for entry in rows:
        if not isinstance(entry, dict):
            raise StyleDnaError("sizes entries must be objects")
        category = entry.get("garment_category")
        system = entry.get("size_system")
        label = entry.get("size_label")
        if category not in tax.GARMENT_CATEGORY_SLUGS:
            raise StyleDnaError(f"unknown garment category: {category!r}")
        if system not in tax.SIZE_SYSTEM_SLUGS:
            raise StyleDnaError(f"unknown size system: {system!r}")
        if not isinstance(label, str):
            raise StyleDnaError("size_label must be a string")
        label = label.strip()
        if not label or len(label) > tax.MAX_SIZE_LABEL_LENGTH:
            raise StyleDnaError(
                f"size_label must be 1-{tax.MAX_SIZE_LABEL_LENGTH} characters"
            )
        if (category, system) in seen:
            raise StyleDnaError(f"sizes contains {category}/{system} twice")
        seen.add((category, system))
        out.append((category, system, label))
    return out


def _validate_fits(value: Any) -> list[tuple[str, str]]:
    rows = _require_list(value, "fits")
    if len(rows) > tax.MAX_FITS:
        raise StyleDnaError(f"fits accepts at most {tax.MAX_FITS} entries")

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for entry in rows:
        if not isinstance(entry, dict):
            raise StyleDnaError("fits entries must be objects")
        category = entry.get("garment_category")
        fit = entry.get("fit")
        if category not in tax.GARMENT_CATEGORY_SLUGS:
            raise StyleDnaError(f"unknown garment category: {category!r}")
        if fit not in tax.FIT_SLUGS:
            raise StyleDnaError(f"unknown fit: {fit!r}")
        if category in seen:
            raise StyleDnaError(f"fits contains {category} twice")
        seen.add(category)
        out.append((category, fit))
    return out


# --------------------------------------------------------------------------- writes


def _replace(session: Session, profile: StyleProfile, model, rows: list[dict]) -> None:
    """Replace a child collection wholesale.

    Delete-then-insert rather than diffing. The collections are tens of rows at most, the
    customer is editing a form that submits its whole state, and a diff would add a way for
    the stored set to disagree with what the page showed. Cheap, and obviously correct.
    """

    session.execute(delete(model).where(model.profile_id == profile.id))
    for row in rows:
        session.add(model(profile_id=profile.id, **row))


def update_profile(
    session: Session,
    *,
    customer: Customer,
    patch: dict[str, Any],
    expected_revision: int | None,
    correlation_id: str = "",
) -> StyleProfile:
    """Create or update the profile. The only write path for preference data.

    Creates on first write: a customer does not "open an empty profile" as a separate act,
    they set a preference, and requiring an explicit create would be a round trip that
    exists only to satisfy the schema.
    """

    profile = get_profile(session, customer=customer)
    created = profile is None

    # Revision check FIRST, before any validation or mutation. On a brand-new profile
    # there is nothing to conflict with, and `expected_revision: 0` is how a client says
    # "I believe there is no profile yet".
    if not created and expected_revision is not None and expected_revision != profile.revision:
        raise RevisionConflict(expected_revision, profile.revision)
    if created and expected_revision not in (None, 0):
        raise RevisionConflict(expected_revision, 0)

    # ---- validate the whole patch before touching anything
    directions = _MISSING
    colours = _MISSING
    materials = _MISSING
    fits = _MISSING
    sizes = _MISSING
    brands = _MISSING
    scalars: dict[str, Any] = {}

    if "style_directions" in patch:
        directions = _validate_stance_list(
            patch["style_directions"],
            field="style_directions",
            vocabulary=tax.STYLE_DIRECTION_SLUGS,
            limit=tax.MAX_STYLE_DIRECTIONS,
            key="slug",
        )
    if "colours" in patch:
        colours = _validate_stance_list(
            patch["colours"],
            field="colours",
            vocabulary=tax.COLOUR_SLUGS,
            limit=tax.MAX_COLOURS,
            key="slug",
        )
    if "materials" in patch:
        materials = _validate_stance_list(
            patch["materials"],
            field="materials",
            vocabulary=tax.MATERIAL_SLUGS,
            limit=tax.MAX_MATERIALS,
            key="slug",
        )
    if "fits" in patch:
        fits = _validate_fits(patch["fits"])
    if "sizes" in patch:
        sizes = _validate_sizes(patch["sizes"])
    if "brands" in patch:
        brands = _resolve_brands(session, patch["brands"])

    if "colour_approach" in patch:
        scalars["colour_approach"] = _validate_single(
            patch["colour_approach"], field="colour_approach", vocabulary=tax.COLOUR_APPROACH_SLUGS
        )
    if "care_effort" in patch:
        scalars["care_effort"] = _validate_single(
            patch["care_effort"], field="care_effort", vocabulary=tax.CARE_EFFORT_SLUGS
        )
    if "seasonality" in patch:
        scalars["seasonality"] = _validate_single(
            patch["seasonality"], field="seasonality", vocabulary=tax.SEASONALITY_SLUGS
        )
    if "fit_notes" in patch:
        notes = patch["fit_notes"]
        if notes is None:
            notes = ""
        if not isinstance(notes, str):
            raise StyleDnaError("fit_notes must be a string")
        notes = notes.strip()
        if len(notes) > tax.MAX_FIT_NOTES_LENGTH:
            raise StyleDnaError(
                f"fit_notes is limited to {tax.MAX_FIT_NOTES_LENGTH} characters"
            )
        scalars["fit_notes"] = notes
    if "personalization_enabled" in patch:
        enabled = patch["personalization_enabled"]
        if not isinstance(enabled, bool):
            raise StyleDnaError("personalization_enabled must be a boolean")
        scalars["personalization_enabled"] = enabled
    if "budget" in patch:
        budget = patch["budget"]
        if not isinstance(budget, dict):
            raise StyleDnaError("budget must be an object")
        scalars.update(_validate_budget(budget, profile.budget_currency if profile else None))

    # ---- everything validated; now apply
    if profile is None:
        profile = StyleProfile(customer_id=customer.id, revision=1)
        session.add(profile)
        session.flush()

    for column, value in scalars.items():
        setattr(profile, column, value)

    if directions is not _MISSING:
        _replace(
            session, profile, StyleDirectionPreference,
            [{"style_slug": s, "stance": st} for s, st in directions],
        )
    if colours is not _MISSING:
        _replace(
            session, profile, StyleColourPreference,
            [{"colour_slug": s, "stance": st} for s, st in colours],
        )
    if materials is not _MISSING:
        _replace(
            session, profile, StyleMaterialPreference,
            [{"material_slug": s, "stance": st} for s, st in materials],
        )
    if fits is not _MISSING:
        _replace(
            session, profile, StyleFitPreference,
            [{"garment_category": c, "fit_slug": f} for c, f in fits],
        )
    if sizes is not _MISSING:
        _replace(
            session, profile, StyleSize,
            [
                {"garment_category": c, "size_system": sy, "size_label": lb}
                for c, sy, lb in sizes
            ],
        )
    if brands is not _MISSING:
        _replace(
            session, profile, StyleBrandPreference,
            [{"brand_id": bid, "stance": st} for bid, st in brands],
        )

    if not created:
        profile.revision += 1

    _emit(
        session,
        "style_profile_created" if created else "style_profile_updated",
        correlation_id=correlation_id,
    )
    if "personalization_enabled" in scalars:
        _emit(
            session,
            "style_profile_enabled" if scalars["personalization_enabled"]
            else "style_profile_disabled",
            correlation_id=correlation_id,
        )

    session.commit()
    session.refresh(profile)
    return profile


def delete_profile(
    session: Session, *, customer: Customer, correlation_id: str = ""
) -> bool:
    """Delete the profile and every preference row it owns. Nothing else.

    Explicitly NOT touching Saved items, orders, addresses or the account. "Delete my Style
    DNA" is a narrow request and must stay narrow -- a delete that took the Saved list with
    it would be destroying data the customer never mentioned, and they would find out by
    noticing it gone.

    Child rows are removed explicitly as well as by cascade. SQLite enforces foreign keys
    only when the pragma is on, so a cascade is a guarantee on PostgreSQL and a hope on the
    test database; doing it in both places makes the behaviour identical everywhere.
    """

    profile = session.scalar(
        select(StyleProfile).where(StyleProfile.customer_id == customer.id)
    )
    if profile is None:
        # Idempotent, like unsave. The caller asked for a state, and that state holds.
        return False

    for model in STYLE_DNA_CHILD_MODELS:
        session.execute(delete(model).where(model.profile_id == profile.id))
    session.delete(profile)
    _emit(session, "style_profile_deleted", correlation_id=correlation_id)
    session.commit()
    return True


def delete_all_for_customer(session: Session, *, customer: Customer) -> int:
    """Remove a customer's Style DNA during account erasure.

    The same shape as `saved_service.delete_all_for_customer`, and needed for the same
    reason: `erase_customer` pseudonymizes the customer row rather than deleting it, so the
    `ondelete=CASCADE` foreign keys never fire. Without this the most personal data in the
    system -- sizes, budgets, fit notes -- would outlive the erasure request that was
    supposed to remove it.

    Returns the number of profiles removed, which is 0 or 1.
    """

    profile_ids = list(
        session.scalars(select(StyleProfile.id).where(StyleProfile.customer_id == customer.id))
    )
    if not profile_ids:
        return 0
    for model in STYLE_DNA_CHILD_MODELS:
        session.execute(delete(model).where(model.profile_id.in_(profile_ids)))
    result = session.execute(delete(StyleProfile).where(StyleProfile.id.in_(profile_ids)))
    return int(result.rowcount or 0)


def _emit(session: Session, name: str, *, correlation_id: str = "") -> None:
    """A domain event with NO PROFILE CONTENT and no customer identifier.

    The event records that a profile changed. It does not record sizes, budgets, colours,
    brand exclusions or fit notes, because an analytics table holding those is a copy of
    the most personal data in the system sitting outside every control built to protect the
    original -- outside the delete endpoint, outside account erasure, and outside the
    customer's ability to inspect what is held about them.

    Section 23 promises the customer can see every Style DNA signal the platform holds. A
    payload of preference values here would make that promise false in a place they cannot
    look.
    """

    record_event(session, name, {})
