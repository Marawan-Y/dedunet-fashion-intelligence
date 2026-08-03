from __future__ import annotations

import os
from dataclasses import dataclass

from .money import to_minor_units


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _minor_units_from_env(
    minor_var: str,
    legacy_decimal_var: str,
    default_minor: int,
    currency: str,
) -> int:
    """Resolve an authoritative money setting as integer minor units.

    Preference order: explicit minor-unit variable, then the legacy decimal variable
    converted EXACTLY from its string form (never via ``float``), then the default.
    """

    raw_minor = os.getenv(minor_var)
    if raw_minor is not None and raw_minor.strip():
        return to_minor_units(int(raw_minor.strip()), currency, already_minor=True)

    raw_decimal = os.getenv(legacy_decimal_var)
    if raw_decimal is not None and raw_decimal.strip():
        # The env value is read as a string and converted with Decimal, so "8.90"
        # becomes 890 exactly. float() is never applied to a money string.
        return to_minor_units(raw_decimal.strip(), currency)

    return default_minor


_STORE_CURRENCY = os.getenv("STORE_CURRENCY", "EUR")


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    admin_api_token: str = os.getenv("ADMIN_API_TOKEN", "change-me")
    cors_origins: tuple[str, ...] = tuple(
        _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:13000"))
    )
    store_currency: str = _STORE_CURRENCY
    default_shipping_minor_units: int = _minor_units_from_env(
        "DEFAULT_SHIPPING_MINOR_UNITS", "DEFAULT_SHIPPING_EUR", 890, _STORE_CURRENCY
    )
    free_shipping_threshold_minor_units: int = _minor_units_from_env(
        "FREE_SHIPPING_THRESHOLD_MINOR_UNITS",
        "FREE_SHIPPING_THRESHOLD_EUR",
        10_000,
        _STORE_CURRENCY,
    )
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str | None = os.getenv("OPENAI_MODEL") or None

    @property
    def admin_token_is_default(self) -> bool:
        """True when the shipped placeholder admin token is still in use."""

        return self.admin_api_token in {"", "change-me"}


settings = Settings()
