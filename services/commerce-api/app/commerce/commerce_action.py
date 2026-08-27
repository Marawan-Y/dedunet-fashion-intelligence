"""ONE deterministic contract for "what can this customer do with this product".

WHY THIS IS SERVER-SIDE AND SINGULAR.

The platform already learned this once. `apps/web` computed a purchase gate in the browser,
the API computed its own in `assert_purchasable`, and the two disagreed -- the page offered a
purchase the server then refused with a 409. The fix was to mirror both gates in the client,
which works but leaves TWO implementations of one rule, in two languages, drifting.

Multi-brand makes that untenable: four routes times three ownership types times the commerce
mode is not a thing to re-derive in TypeScript. So the server decides, once, and every client
renders what it is told. A client's only job is to display `label` and honour `enabled`.

THE ORDER OF THE GATES MATTERS and is asserted by tests:

  1. commerce mode   -- the outer gate. BRAND_PREVIEW_MODE collapses everything.
  2. product sellable flag -- fails closed.
  3. commerce route  -- only now does the route decide anything.

Reversing 1 and 3 would let a HOSTED product look purchasable in preview mode, which is the
precise defect `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` exists to prevent.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from . import modes
from .brands import Brand, CommerceRoute, validate_external_url


class CommerceActionKind(str, enum.Enum):
    """What the control on the product page actually is."""

    NOT_AVAILABLE = "NOT_AVAILABLE"
    EXTERNAL_PURCHASE = "EXTERNAL_PURCHASE"
    REFERRAL_VIEW = "REFERRAL_VIEW"
    HOSTED_PURCHASE = "HOSTED_PURCHASE"


@dataclass(frozen=True)
class CommerceAction:
    """The complete instruction to a client. Nothing is left for it to infer.

    `enabled` is separate from `kind` on purpose: a control can be the right KIND and still
    be refused right now. An EXTERNAL product in BRAND_PREVIEW_MODE is not "an external
    product with no link" -- it is not available, and it says why.
    """

    kind: CommerceActionKind
    label: str
    enabled: bool
    reason: str = ""
    url: str = ""
    # Set only when `url` is present. The client must apply both.
    link_rel: str = ""
    link_target: str = ""
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "enabled": self.enabled,
            "reason": self.reason,
            "url": self.url,
            "link_rel": self.link_rel,
            "link_target": self.link_target,
            "notes": list(self.notes),
        }


# `noopener` is the one that matters: without it the opened page gets a handle on
# `window.opener` and can navigate this tab somewhere else -- a one-line phishing primitive
# known as reverse tabnabbing. `noreferrer` additionally withholds the referrer, which also
# implies noopener in older browsers that ignore the first. `nofollow` says this is not an
# editorial endorsement, which is exactly true of a curated external link.
EXTERNAL_LINK_REL = "noopener noreferrer nofollow"
EXTERNAL_LINK_TARGET = "_blank"

NOT_AVAILABLE_LABEL = "Not available to buy"

# The reason HOSTED cannot be honoured yet. Stated once so the API, the tests and the phase
# report cannot describe it differently.
HOSTED_NOT_IMPLEMENTED = (
    "Hosted checkout is not available: no merchant commerce exists on this platform yet."
)


def commerce_action(
    *,
    route: CommerceRoute,
    sellable: bool,
    brand: Brand | None,
    external_url: str = "",
    mode=None,
) -> CommerceAction:
    """Decide the single action a client may offer.

    Deliberately takes primitives rather than an ORM Product, so it is testable without a
    database and cannot be tempted into loading more state to make a decision with.
    """

    brand_name = brand.name if brand is not None else "the brand"

    # ---- GATE 1: the commerce mode. Outermost, always.
    try:
        current = modes.current_mode() if mode is None else mode
    except modes.CommerceModeError:
        # An unknown or refused mode is not a reason to guess permissively.
        current = None

    if current is None or not modes.describe(current).get("purchasable", False):
        disclosure = modes.describe(current)
        return CommerceAction(
            kind=CommerceActionKind.NOT_AVAILABLE,
            label=NOT_AVAILABLE_LABEL,
            enabled=False,
            reason=disclosure.get("headline", "This catalogue is not purchasable."),
            notes=list(disclosure.get("detail", [])),
        )

    # ---- GATE 2: the product's own flag. Fails closed.
    if not sellable:
        return CommerceAction(
            kind=CommerceActionKind.NOT_AVAILABLE,
            label=NOT_AVAILABLE_LABEL,
            enabled=False,
            reason="This product is not offered for sale.",
        )

    # ---- GATE 3: only now does the route decide.
    if route is CommerceRoute.NON_PURCHASABLE:
        return CommerceAction(
            kind=CommerceActionKind.NOT_AVAILABLE,
            label=NOT_AVAILABLE_LABEL,
            enabled=False,
            reason="This product is not available to buy.",
        )

    if route is CommerceRoute.HOSTED:
        # Declarable, not reachable. An enum value is not a feature: there is no merchant,
        # no settlement and no fulfilment behind a hosted sale for a brand we do not own.
        return CommerceAction(
            kind=CommerceActionKind.NOT_AVAILABLE,
            label=NOT_AVAILABLE_LABEL,
            enabled=False,
            reason=HOSTED_NOT_IMPLEMENTED,
        )

    # EXTERNAL and REFERRAL both leave the platform and both need a safe URL.
    try:
        safe_url = validate_external_url(external_url, allow_empty=False)
    except ValueError as exc:
        # A route that promises a destination and has none is a broken promise, not a
        # button that does nothing.
        return CommerceAction(
            kind=CommerceActionKind.NOT_AVAILABLE,
            label=NOT_AVAILABLE_LABEL,
            enabled=False,
            reason=f"No usable link for this product ({exc}).",
        )

    if route is CommerceRoute.EXTERNAL:
        return CommerceAction(
            kind=CommerceActionKind.EXTERNAL_PURCHASE,
            label=f"Buy from {brand_name}",
            enabled=True,
            reason="",
            url=safe_url,
            link_rel=EXTERNAL_LINK_REL,
            link_target=EXTERNAL_LINK_TARGET,
            notes=[f"You will leave DEDUNET and buy directly from {brand_name}."],
        )

    return CommerceAction(
        kind=CommerceActionKind.REFERRAL_VIEW,
        label=f"View at {brand_name}",
        enabled=True,
        reason="",
        url=safe_url,
        link_rel=EXTERNAL_LINK_REL,
        link_target=EXTERNAL_LINK_TARGET,
        notes=[f"You will leave DEDUNET to view this at {brand_name}."],
    )
