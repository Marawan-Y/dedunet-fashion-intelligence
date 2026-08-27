"""The multi-brand fashion network domain: ownership, commerce routing and provenance.

Three ideas are kept deliberately separate here, because collapsing any two of them is how a
marketplace starts lying to its customers.

WHO OWNS THE BRAND  -- `BrandOwnershipType`. A platform-curated brand, a merchant-owned one,
    or one DEDUNET curates from outside without any relationship to the brand at all.

WHERE YOU CAN BUY   -- `CommerceRoute`. Hosted here, bought on the brand's own site, referred
    with attribution, or not purchasable.

WHAT WE ACTUALLY KNOW -- provenance. Where a fact came from, when it was last checked, and how
    confident we are. Never "in stock"; at most "said to be in stock, checked at 14:02".

**Ownership and routing are orthogonal and neither may be inferred from the other.** A
merchant-owned brand can be `EXTERNAL`; a platform-curated one can be `NON_PURCHASABLE`; an
externally curated one is typically `REFERRAL`. `test_commerce_route_independence` asserts
this in both directions, because the tempting shortcut -- "merchant-owned implies we host it"
-- would be wrong the first time a merchant kept their own checkout, and wrong silently.

THE OUTER GATE IS UNCHANGED. `modes.current_mode()` still decides whether anything at all is
purchasable, and `BRAND_PREVIEW_MODE` collapses every route to "not available to buy"
regardless of what a product carries. A route is a *capability*, never a permission.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import Product


class BrandOwnershipType(str, enum.Enum):
    """Who is accountable for a brand on this platform.

    PLATFORM_CURATED is a real, explicit value and NOT the absence of a row. A missing
    ownership row means "no merchant owns this"; it cannot distinguish "DEDUNET's own brand"
    from "a brand we list without any relationship", and those two have different legal and
    editorial consequences.
    """

    PLATFORM_CURATED = "PLATFORM_CURATED"
    MERCHANT_OWNED = "MERCHANT_OWNED"
    EXTERNAL_CURATED = "EXTERNAL_CURATED"


class CommerceRoute(str, enum.Enum):
    """How -- and whether -- a product can be bought.

    HOSTED is declarable but NOT yet reachable. Merchant commerce does not exist, so
    `commerce_action()` refuses it with its own reason rather than opening a checkout that
    has no seller behind it. An enum value is not a feature.
    """

    HOSTED = "HOSTED"
    EXTERNAL = "EXTERNAL"
    REFERRAL = "REFERRAL"
    NON_PURCHASABLE = "NON_PURCHASABLE"


class ProvenanceSource(str, enum.Enum):
    """Where the information about a brand came from. Consumers see prose, never this."""

    PLATFORM_AUTHORED = "PLATFORM_AUTHORED"
    MERCHANT_MANAGED = "MERCHANT_MANAGED"
    EXTERNAL_SOURCED = "EXTERNAL_SOURCED"


class AvailabilityConfidence(str, enum.Enum):
    """How much a stated availability is worth.

    There is no `IN_STOCK`. The platform does not have real-time stock for anything it does
    not fulfil, and a column that can say "in stock" will eventually be rendered as a fact.
    UNKNOWN is the default and the honest answer for an unsynced external product.
    """

    UNKNOWN = "UNKNOWN"
    REPORTED_AVAILABLE = "REPORTED_AVAILABLE"
    REPORTED_UNAVAILABLE = "REPORTED_UNAVAILABLE"
    VERIFIED_AVAILABLE = "VERIFIED_AVAILABLE"


# --------------------------------------------------------------------------- URL safety

ALLOWED_URL_SCHEMES = frozenset({"https"})


class UnsafeUrlError(ValueError):
    """An external URL that must never reach a browser."""


def validate_external_url(url: str | None, *, allow_empty: bool = True) -> str:
    """Reject anything that is not a plain https URL.

    External and referral routes are a NEW ATTACK BOUNDARY: this is the first place in the
    platform where a URL supplied by data -- not by our own code -- ends up in an anchor a
    customer clicks. `javascript:` in an href executes in the customer's session; `data:`
    can carry a whole credential-harvesting document; `file:` probes the local machine.

    Scheme allow-LIST, never a deny-list. A deny-list of "javascript, data, file" misses
    `vbscript:`, `blob:`, and whatever a browser ships next. https only, and the check runs
    at write time so bad data cannot enter the database, not merely at render time where one
    forgotten call site is an exploit.

    A protocol-relative `//evil.example` is rejected too: it has no scheme, so it inherits
    the page's, which makes it a scheme-bypass rather than a relative link.
    """

    if url is None or url == "":
        if allow_empty:
            return ""
        raise UnsafeUrlError("a URL is required here and none was given")

    candidate = url.strip()
    if candidate != url:
        # Leading/trailing whitespace is how " javascript:..." slips past a naive check.
        raise UnsafeUrlError("URL has leading or trailing whitespace")
    if "\n" in candidate or "\r" in candidate or "\t" in candidate:
        raise UnsafeUrlError("URL contains a control character")
    if candidate.startswith("//"):
        raise UnsafeUrlError("protocol-relative URL: the scheme cannot be verified")

    parsed = urlparse(candidate)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        raise UnsafeUrlError(
            f"URL scheme {scheme or '(none)'!r} is not allowed; permitted: "
            f"{sorted(ALLOWED_URL_SCHEMES)}"
        )
    if not parsed.netloc:
        raise UnsafeUrlError("URL has no host")
    return candidate


# --------------------------------------------------------------------------- entities


class MerchantOrganization(Base):
    """The tenant root, and the ONLY one. Consumers are never tenants.

    Created in this phase because `BrandOwnership` needs something real to point at and a
    foreign key to a table that does not exist is not an invariant. It is deliberately
    minimal -- billing, plans, entitlements, seats and the merchant portal are Phase 5 and
    none of them is started here.

    **No row is created for DEDUNET.** DEDUNET's own brand is `PLATFORM_CURATED`; inventing a
    merchant organisation to own it would make the first-party brand indistinguishable from a
    tenant's, which is exactly the distinction `ownership_type` exists to keep.
    """

    __tablename__ = "merchant_organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    ownerships: Mapped[list["BrandOwnership"]] = relationship(
        back_populates="merchant_organization"
    )


class Brand(Base):
    """A brand in the fashion network. First-class, per the target architecture.

    Every field here has a product use today. `founded_year`, `employee_count`, social
    handles and the rest of the usual brand-table speculation are absent on purpose: an
    unused column is a column nobody maintains and everybody eventually trusts.
    """

    __tablename__ = "brands"
    __table_args__ = (
        # A fixture must never be publishable. This is the database half of the production
        # gate -- the API half can be edited by someone who does not know about this rule.
        CheckConstraint(
            "NOT (is_development_fixture AND publication_status = 'published')",
            name="ck_brand_fixture_never_published",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))

    ownership_type: Mapped[BrandOwnershipType] = mapped_column(
        Enum(BrandOwnershipType, native_enum=False, length=30), index=True
    )

    # preview | published | archived. Same vocabulary as Product.publication_status, so a
    # reader does not have to learn a second lifecycle for the same idea.
    publication_status: Mapped[str] = mapped_column(String(30), default="preview", index=True)

    story: Mapped[str] = mapped_column(Text, default="")
    logo_media_path: Mapped[str] = mapped_column(String(300), default="")
    website_url: Mapped[str] = mapped_column(String(500), default="")
    # ISO-3166-1 alpha-2 where it is a FACT. Empty when unknown -- never guessed from a name.
    country_code: Mapped[str] = mapped_column(String(2), default="")

    # --------------------------------------------------------------- provenance
    provenance_source: Mapped[ProvenanceSource] = mapped_column(
        Enum(ProvenanceSource, native_enum=False, length=30),
        default=ProvenanceSource.PLATFORM_AUTHORED,
    )
    # Identity in the SOURCE system (a Shopify shop id, a feed id). Ours is `slug`.
    source_identifier: Mapped[str] = mapped_column(String(200), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # --------------------------------------------------------------- fixture gate
    # Marks a brand that exists ONLY to exercise the architecture. It is not a partner, not
    # a relationship, and not a real company. Serialised to every consumer so no surface can
    # render one as genuine by omission, and constrained above so it can never be published.
    is_development_fixture: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    ownership: Mapped["BrandOwnership | None"] = relationship(
        back_populates="brand", uselist=False, cascade="all, delete-orphan"
    )
    # RESTRICT on the foreign key, not cascade: deleting a brand that still has products
    # would silently delete a catalogue. A brand with products must be archived, not removed.
    products: Mapped[list["Product"]] = relationship(back_populates="brand")

    @property
    def is_merchant_owned(self) -> bool:
        return self.ownership_type is BrandOwnershipType.MERCHANT_OWNED


class BrandOwnership(Base):
    """The merchant relationship, and ONLY that.

    Exists solely for `MERCHANT_OWNED`. `brand_id` is UNIQUE, which makes "at most one owner"
    a key constraint the database enforces rather than a rule the application remembers.

    The other half -- "exactly one when merchant-owned, none otherwise" -- is a biconditional
    across two tables. `assert_ownership_consistent` enforces it on every sanctioned write
    and `verify_ownership_invariants` re-checks it over the whole table, because the failure
    mode is silent: a brand that flips to MERCHANT_OWNED without an owner row is a brand with
    no accountable seller, and nothing would notice.
    """

    __tablename__ = "brand_ownership"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), unique=True, index=True
    )
    merchant_organization_id: Mapped[int] = mapped_column(
        ForeignKey("merchant_organizations.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    brand: Mapped[Brand] = relationship(back_populates="ownership")
    merchant_organization: Mapped[MerchantOrganization] = relationship(
        back_populates="ownerships"
    )


# --------------------------------------------------------------------------- invariants


class BrandOwnershipError(ValueError):
    """The ownership type and the ownership row disagree."""


def assert_ownership_consistent(brand: Brand) -> None:
    """The biconditional, asserted in BOTH directions.

    Changing the type without changing the row must fail, and changing the row without the
    type must fail. One direction alone leaves the other as the way in.
    """

    has_owner = brand.ownership is not None
    if brand.ownership_type is BrandOwnershipType.MERCHANT_OWNED:
        if not has_owner:
            raise BrandOwnershipError(
                f"brand {brand.slug!r} is MERCHANT_OWNED but has no BrandOwnership row; "
                "a merchant-owned brand must have exactly one accountable owner"
            )
    elif has_owner:
        raise BrandOwnershipError(
            f"brand {brand.slug!r} is {brand.ownership_type.value} but carries a "
            "BrandOwnership row; only MERCHANT_OWNED brands may have one"
        )


def verify_ownership_invariants(session) -> list[str]:
    """Re-check every brand. Returns human-readable violations; empty means clean.

    A whole-table sweep rather than a per-write check, because the per-write check can only
    see writes that went through it. Used by the tests and available to an operator.
    """

    from sqlalchemy import select

    violations: list[str] = []
    for brand in session.scalars(select(Brand)).all():
        try:
            assert_ownership_consistent(brand)
        except BrandOwnershipError as exc:
            violations.append(str(exc))
    return violations
