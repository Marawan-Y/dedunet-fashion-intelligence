"""Commerce operating modes.

Three modes, and the important property is what CANNOT be reached:

  BRAND_PREVIEW_MODE   products visible, stock zero, nothing purchasable, no payment call
  COMMERCE_TEST_MODE   explicit synthetic stock, sandbox payments, orders marked as tests
  PUBLIC_COMMERCE_MODE refused

`PUBLIC_COMMERCE_MODE` is deliberately NOT reachable through configuration. Setting
`COMMERCE_MODE=PUBLIC_COMMERCE_MODE` raises at load rather than enabling public commerce.
Real money for real customers must not be one environment variable away from a prototype
whose brand is `LEGAL_CLEARANCE_PENDING` and whose products carry `origin_claim_status =
UNVERIFIED`. Reaching it requires a code change AND the existing activation gate, which is
the point.

Read at call time, not import time, following the `payments.get_gateway` and
`rate_limit` precedent: `Settings` is a frozen dataclass evaluated once at import and could
not otherwise vary per test.
"""

from __future__ import annotations

import os

BRAND_PREVIEW = "BRAND_PREVIEW_MODE"
COMMERCE_TEST = "COMMERCE_TEST_MODE"
PUBLIC_COMMERCE = "PUBLIC_COMMERCE_MODE"

SELECTABLE_MODES = frozenset({BRAND_PREVIEW, COMMERCE_TEST})
ALL_MODES = frozenset({BRAND_PREVIEW, COMMERCE_TEST, PUBLIC_COMMERCE})

DEFAULT_MODE = COMMERCE_TEST


class CommerceModeError(RuntimeError):
    """Raised when the configured mode is unknown or refused."""


def current_mode() -> str:
    """The configured commerce mode.

    Defaults to `COMMERCE_TEST_MODE`, which is what every existing environment already
    behaves as: a sandbox-payment store with seeded demo stock. Defaulting to
    `BRAND_PREVIEW_MODE` would silently disable checkout everywhere.
    """

    raw = (os.getenv("COMMERCE_MODE") or DEFAULT_MODE).strip().upper()

    if raw == PUBLIC_COMMERCE:
        raise CommerceModeError(
            "PUBLIC_COMMERCE_MODE cannot be enabled by configuration. Public commercial "
            "launch is BLOCKED: brand legal clearance is pending and product origin, "
            "material and evidence states are UNVERIFIED. Enabling it requires a code "
            "change and the documented activation gate."
        )
    if raw not in SELECTABLE_MODES:
        raise CommerceModeError(
            f"unknown COMMERCE_MODE {raw!r}; expected one of {sorted(SELECTABLE_MODES)}"
        )
    return raw


def is_preview_mode() -> bool:
    return current_mode() == BRAND_PREVIEW


def public_commerce_enabled() -> bool:
    """Always False. Kept as an explicit, testable statement rather than an absence."""

    return False


def assert_purchasable(*, sellable: bool, product_name: str) -> None:
    """Refuse a purchase that the current mode or the product's own state forbids.

    Two independent gates, deliberately not collapsed into one:

      - the MODE gate blocks every purchase in brand preview, whatever the product says;
      - the PRODUCT gate blocks a non-sellable product in any mode.

    A prototype must not become purchasable merely because it has a price.
    """

    if is_preview_mode():
        raise PurchaseBlocked(
            "this catalogue is in brand preview; nothing is available to purchase"
        )
    if not sellable:
        raise PurchaseBlocked(f"{product_name} is not available for purchase")


class PurchaseBlocked(Exception):
    """A purchase was refused by mode or by product state."""
