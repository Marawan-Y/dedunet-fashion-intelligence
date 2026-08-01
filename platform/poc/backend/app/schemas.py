from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
    model_validator,
)

from .money import from_minor_units, to_minor_units

DEFAULT_CURRENCY = "EUR"


class ProductVariant(BaseModel):
    sku: str = Field(min_length=3, max_length=64)
    size: str = Field(min_length=1, max_length=16)
    color: str = Field(min_length=1, max_length=40)
    stock: int = Field(strict=True, ge=0)


class Product(BaseModel):
    """PoC catalog product.

    Money rule (SB-AR-B3-003): ``price_minor_units`` is the only authoritative price
    representation. ``price_display`` is derived for presentation and must never be
    used as an arithmetic input. The legacy decimal key ``price_eur`` is accepted at
    ingestion only as an exact ``Decimal``/string; a binary float is rejected.
    """

    id: str = Field(min_length=3, max_length=64)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=2, max_length=120)
    category: Literal["t-shirt", "abaya", "shirt", "hoodie", "trousers", "accessory"]
    collection: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=1200)
    fibre_composition: str = Field(min_length=2, max_length=120)
    made_in: str = Field(min_length=2, max_length=80)
    price_minor_units: int = Field(strict=True, gt=0)
    currency: str = Field(default=DEFAULT_CURRENCY, pattern=r"^[A-Z]{3}$")
    image_url: HttpUrl | str
    style_tags: list[str] = Field(default_factory=list)
    variants: list[ProductVariant] = Field(min_length=1)
    active: bool = True

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_decimal_price(cls, data: Any) -> Any:
        """Accept the legacy ``price_eur`` key without ever accepting a binary float."""

        if not isinstance(data, dict):
            return data
        if "price_minor_units" in data or "price_eur" not in data:
            return data
        data = dict(data)
        currency = data.get("currency", DEFAULT_CURRENCY)
        # to_minor_units raises FloatMoneyRejected (a TypeError) for binary floats;
        # Pydantic surfaces it as a ValidationError for the caller.
        data["price_minor_units"] = to_minor_units(data.pop("price_eur"), currency)
        return data

    @field_validator("style_tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in tags if tag.strip()})

    @computed_field  # type: ignore[prop-decorator]
    @property
    def price_display(self) -> Decimal:
        """Derived, display-only amount. Never an arithmetic input."""

        return from_minor_units(self.price_minor_units, self.currency)


class StylistRequest(BaseModel):
    """Customer-supplied discovery filter.

    ``budget_minor_units`` is the canonical field. ``budget_eur`` is accepted for
    backward compatibility as an exact ``Decimal``/string/int only; a binary float is
    rejected so no client can push an inexact amount onto the server.
    """

    occasion: str = Field(min_length=2, max_length=120)
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    budget_minor_units: int = Field(strict=True, gt=0, le=500_000)
    currency: str = Field(default=DEFAULT_CURRENCY, pattern=r"^[A-Z]{3}$")
    style_notes: str = Field(default="", max_length=500)

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_decimal_budget(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "budget_minor_units" in data or "budget_eur" not in data:
            return data
        data = dict(data)
        currency = data.get("currency", DEFAULT_CURRENCY)
        data["budget_minor_units"] = to_minor_units(data.pop("budget_eur"), currency)
        return data


class StylistRecommendation(BaseModel):
    rationale: str
    product_ids: list[str]
    total_minor_units: int = Field(strict=True, ge=0)
    currency: str = DEFAULT_CURRENCY

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_display(self) -> Decimal:
        return from_minor_units(self.total_minor_units, self.currency)


class QuoteItem(BaseModel):
    sku: str
    quantity: int = Field(strict=True, ge=1, le=20)


class OrderQuoteRequest(BaseModel):
    items: list[QuoteItem] = Field(min_length=1)
    destination_country: str = Field(min_length=2, max_length=2)


class OrderQuote(BaseModel):
    currency: str
    subtotal_minor_units: int = Field(strict=True, ge=0)
    shipping_minor_units: int = Field(strict=True, ge=0)
    total_minor_units: int = Field(strict=True, ge=0)
    note: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subtotal_display(self) -> Decimal:
        return from_minor_units(self.subtotal_minor_units, self.currency)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def shipping_display(self) -> Decimal:
        return from_minor_units(self.shipping_minor_units, self.currency)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_display(self) -> Decimal:
        return from_minor_units(self.total_minor_units, self.currency)
