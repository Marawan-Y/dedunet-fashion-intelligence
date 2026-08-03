"""Pricing: discounts, shipping and VAT.

All arithmetic is integer minor units (DEC-010). Division appears only when extracting
the VAT component from a gross amount, and that division is done on integers with an
explicit, tested rounding rule.

VAT model
---------
Displayed prices are VAT-INCLUSIVE, which is the legal norm for consumer retail in the
EU. The tax figure on an order is therefore a COMPONENT of the total, not an addition
to it:

    total = subtotal - discount + shipping
    tax   = total - round(total / (1 + rate))

Computing tax as a component rather than an addend is what keeps the customer-facing
total identical to the advertised price. Adding VAT on top would silently change the
price the customer was shown.

Rates here are illustrative fictional-brand configuration. They are NOT tax advice and
carry no compliance conclusion; a real rate table requires qualified review (EXT-06).
"""

from __future__ import annotations

from dataclasses import dataclass

# Illustrative standard VAT rates in basis points (1900 = 19.00%).
# Fictional configuration for a demonstration store; not a compliance artifact.
VAT_RATE_BASIS_POINTS: dict[str, int] = {
    "DE": 1900,
    "FR": 2000,
    "NL": 2100,
    "AT": 2000,
    "IE": 2300,
}
DEFAULT_VAT_COUNTRY = "DE"

FREE_SHIPPING_THRESHOLD_MINOR_UNITS = 10_000
STANDARD_SHIPPING_MINOR_UNITS = 890


class PricingError(ValueError):
    """Raised when a pricing input is not usable."""


@dataclass(frozen=True)
class PriceBreakdown:
    subtotal_minor_units: int
    discount_minor_units: int
    shipping_minor_units: int
    tax_minor_units: int
    total_minor_units: int
    currency: str
    promotion_code: str = ""

    def as_dict(self) -> dict:
        return {
            "subtotal_minor_units": self.subtotal_minor_units,
            "discount_minor_units": self.discount_minor_units,
            "shipping_minor_units": self.shipping_minor_units,
            "tax_minor_units": self.tax_minor_units,
            "total_minor_units": self.total_minor_units,
            "currency": self.currency,
            "promotion_code": self.promotion_code,
        }


def vat_rate_basis_points(country_code: str) -> int:
    return VAT_RATE_BASIS_POINTS.get((country_code or "").upper(), VAT_RATE_BASIS_POINTS[DEFAULT_VAT_COUNTRY])


def extract_tax_component(gross_minor_units: int, rate_basis_points: int) -> int:
    """Extract the VAT component contained within a gross amount.

    ``net = gross * 10000 // (10000 + rate)`` with half-up rounding, then
    ``tax = gross - net``. Deriving tax by subtraction guarantees
    ``net + tax == gross`` exactly, so the parts can never fail to reconcile to the
    total the customer actually pays.
    """

    if isinstance(gross_minor_units, bool) or not isinstance(gross_minor_units, int):
        raise PricingError("gross amount must be integer minor units")
    if gross_minor_units < 0:
        raise PricingError("gross amount must not be negative")
    if rate_basis_points < 0:
        raise PricingError("VAT rate must not be negative")

    denominator = 10_000 + rate_basis_points
    # Half-up rounding on integers: add half the denominator before flooring.
    net = (gross_minor_units * 10_000 + denominator // 2) // denominator
    return gross_minor_units - net


def compute_discount(
    subtotal_minor_units: int,
    *,
    kind: str,
    value: int,
    min_subtotal_minor_units: int = 0,
) -> int:
    """Return the discount amount, never exceeding the subtotal."""

    if subtotal_minor_units < min_subtotal_minor_units:
        return 0
    if kind == "percent":
        # value is basis points, e.g. 1000 = 10%
        discount = (subtotal_minor_units * value + 5_000) // 10_000
    elif kind == "fixed":
        discount = value
    else:
        raise PricingError(f"unknown promotion kind {kind!r}")
    # A discount may never exceed the subtotal, which would produce a negative
    # merchandise value and a refund the customer never paid for.
    return max(0, min(discount, subtotal_minor_units))


def compute_shipping(
    subtotal_after_discount_minor_units: int,
    *,
    threshold_minor_units: int = FREE_SHIPPING_THRESHOLD_MINOR_UNITS,
    standard_minor_units: int = STANDARD_SHIPPING_MINOR_UNITS,
) -> int:
    """Free above the threshold, otherwise the flat rate.

    The threshold is applied to the POST-discount amount: a discount that drops the
    basket below the threshold reinstates shipping, which is what prevents a promotion
    from silently granting free delivery it was never scoped to fund.
    """

    if subtotal_after_discount_minor_units >= threshold_minor_units:
        return 0
    return standard_minor_units


def price_basket(
    line_items: list[tuple[int, int]],
    *,
    currency: str = "EUR",
    country_code: str = DEFAULT_VAT_COUNTRY,
    promotion: dict | None = None,
) -> PriceBreakdown:
    """Price a basket of ``(unit_price_minor_units, quantity)`` pairs."""

    from ..money import sum_line_totals

    subtotal = sum_line_totals(line_items)

    discount = 0
    code = ""
    if promotion:
        discount = compute_discount(
            subtotal,
            kind=promotion["kind"],
            value=promotion["value"],
            min_subtotal_minor_units=promotion.get("min_subtotal_minor_units", 0),
        )
        if discount > 0:
            code = promotion.get("code", "")

    shipping = compute_shipping(subtotal - discount)
    total = subtotal - discount + shipping
    tax = extract_tax_component(total, vat_rate_basis_points(country_code))

    return PriceBreakdown(
        subtotal_minor_units=subtotal,
        discount_minor_units=discount,
        shipping_minor_units=shipping,
        tax_minor_units=tax,
        total_minor_units=total,
        currency=currency,
        promotion_code=code,
    )
