"""Authoritative money primitives for the PoC (artifact SB-AR-B3-003).

Rules enforced here
-------------------
1. Authoritative monetary values are INTEGER MINOR UNITS of a known currency.
   EUR 59.00 is stored and calculated as ``5900``.
2. A binary ``float`` is never an accepted authoritative money input. ``0.1 + 0.2``
   is not ``0.3`` in IEEE-754, so a float has no place on a money path. Callers must
   supply an ``int`` (minor units), a ``decimal.Decimal``, or a decimal string.
3. Conversion is exact or it fails. A value carrying more fractional digits than the
   currency permits raises rather than rounding silently.
4. Decimal values may be DERIVED from minor units for display, but a derived display
   value is never an input to further arithmetic.

This module is deliberately small and dependency-free so it can be reused unchanged
when the JSON fixture is replaced by a real database.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

__all__ = [
    "FloatMoneyRejected",
    "MINOR_UNIT_EXPONENTS",
    "from_minor_units",
    "format_minor_units",
    "sum_line_totals",
    "to_minor_units",
]


class FloatMoneyRejected(TypeError, ValueError):
    """Raised when a binary float is offered as an authoritative money value.

    It subclasses both ``TypeError`` (the input type is wrong) and ``ValueError`` so
    that Pydantic validators surface it as a ``ValidationError`` instead of letting an
    unhandled ``TypeError`` become a 500 response.
    """


# ISO-4217-style minor-unit exponents. Extend only with a reviewed currency decision;
# an unknown currency must fail rather than default to two digits.
MINOR_UNIT_EXPONENTS: dict[str, int] = {
    "EUR": 2,
}


def _exponent(currency: str) -> int:
    if not isinstance(currency, str) or len(currency) != 3 or currency != currency.upper():
        raise ValueError(f"currency must be an uppercase 3-letter code, got {currency!r}")
    try:
        return MINOR_UNIT_EXPONENTS[currency]
    except KeyError:
        raise ValueError(
            f"unknown currency {currency!r}; add a reviewed minor-unit exponent before use"
        ) from None


def to_minor_units(
    value: int | str | Decimal,
    currency: str,
    *,
    already_minor: bool = False,
) -> int:
    """Convert an exact money value to integer minor units.

    ``already_minor=True`` treats an ``int`` input as a minor-unit amount instead of a
    major-unit amount, for callers that already hold canonical storage values.

    Raises
    ------
    FloatMoneyRejected
        If ``value`` is a binary ``float``.
    ValueError
        If the currency is unknown, the value is not a valid decimal, or the value
        carries more fractional digits than the currency permits.
    """

    exponent = _exponent(currency)

    if isinstance(value, bool):
        raise FloatMoneyRejected("bool is not an accepted money value")

    if isinstance(value, float):
        raise FloatMoneyRejected(
            "binary float is not an accepted authoritative money input; "
            "supply an integer minor-unit value, a Decimal, or a decimal string"
        )

    if already_minor:
        if not isinstance(value, int):
            raise ValueError("already_minor requires an int minor-unit value")
        return value

    if isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, Decimal):
        amount = value
    elif isinstance(value, str):
        try:
            amount = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError(f"{value!r} is not a valid decimal money string") from exc
    else:
        raise ValueError(
            f"unsupported money type {type(value).__name__}; use int, str or Decimal"
        )

    if not amount.is_finite():
        raise ValueError(f"money value must be finite, got {amount!r}")

    # Reject excess precision explicitly rather than rounding it away silently.
    # Python's decimal module has no ROUND_UNNECESSARY, so the check is done here.
    scaled = amount.scaleb(exponent).normalize()
    if scaled != scaled.to_integral_value():
        raise ValueError(
            f"{amount} has more than {exponent} fractional digits and cannot be stored "
            f"exactly in {currency} minor units"
        )
    return int(scaled.to_integral_value())


def from_minor_units(minor_units: int, currency: str) -> Decimal:
    """Derive an exact ``Decimal`` display value from integer minor units."""

    exponent = _exponent(currency)
    if isinstance(minor_units, bool) or not isinstance(minor_units, int):
        raise ValueError("minor_units must be an int")
    return (Decimal(minor_units).scaleb(-exponent)).quantize(Decimal(1).scaleb(-exponent))


def format_minor_units(minor_units: int, currency: str) -> str:
    """Render minor units as a plain, locale-neutral amount string (e.g. ``59.00``)."""

    return f"{from_minor_units(minor_units, currency)}"


def sum_line_totals(line_items: Iterable[tuple[int, int]]) -> int:
    """Sum ``(unit_price_minor_units, quantity)`` pairs with integer arithmetic only.

    Extracted as a pure function so the exactness invariant is directly testable and
    so a reintroduced floating-point path is caught by the type contract rather than
    by luck of rounding.
    """

    total = 0
    for unit_minor_units, quantity in line_items:
        if isinstance(unit_minor_units, bool) or not isinstance(unit_minor_units, int):
            raise FloatMoneyRejected(
                f"unit price must be integer minor units, got "
                f"{type(unit_minor_units).__name__}"
            )
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError(f"quantity must be int, got {type(quantity).__name__}")
        total += unit_minor_units * quantity
    return total
