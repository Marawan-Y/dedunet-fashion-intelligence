"""Payment provider abstraction and a deterministic sandbox adapter.

No real payment provider account exists for this fictional brand, so the shipped
implementation is a sandbox adapter. It is NOT a stub that always returns success: it
implements the same contract a real adapter must implement, including declines, provider
errors and idempotent replay, so the failure paths in checkout are genuinely exercised.

Activating a real provider means implementing ``PaymentGateway`` against their SDK and
setting ``PAYMENT_PROVIDER``. No caller changes, because callers depend on this
interface rather than on the sandbox.

Outcome is selected by the payment-method token, which is how real sandboxes work:

    pm_success  -> authorized
    pm_decline  -> declined (insufficient funds)
    pm_error    -> provider error (retryable)

Anything else is treated as a successful authorization so seeded demo data flows.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Protocol


class PaymentError(Exception):
    """Provider-side failure. Retryable; the charge did not complete."""


class PaymentDeclined(Exception):
    """The provider positively declined. Not retryable without customer action."""


@dataclass(frozen=True)
class AuthorizationResult:
    provider_reference: str
    status: str  # "authorized" | "captured"
    amount_minor_units: int
    currency: str


class PaymentGateway(Protocol):
    """Contract every payment adapter must satisfy."""

    name: str

    def authorize(
        self,
        *,
        amount_minor_units: int,
        currency: str,
        payment_method_token: str,
        idempotency_key: str,
    ) -> AuthorizationResult: ...

    def refund(
        self, *, provider_reference: str, amount_minor_units: int, idempotency_key: str
    ) -> AuthorizationResult: ...


class SandboxGateway:
    """Deterministic in-process gateway.

    Replay safety: results are cached by idempotency key. Re-authorizing with the same
    key returns the ORIGINAL result rather than charging again, which is the behaviour a
    duplicate provider callback or a customer double-click must produce.
    """

    name = "sandbox"

    def __init__(self) -> None:
        self._authorizations: dict[str, AuthorizationResult] = {}
        self._refunds: dict[str, AuthorizationResult] = {}

    @staticmethod
    def _reference(prefix: str, idempotency_key: str) -> str:
        digest = hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]
        return f"{prefix}_{digest}"

    def authorize(
        self,
        *,
        amount_minor_units: int,
        currency: str,
        payment_method_token: str,
        idempotency_key: str,
    ) -> AuthorizationResult:
        if isinstance(amount_minor_units, bool) or not isinstance(amount_minor_units, int):
            raise PaymentError("amount must be integer minor units")
        if amount_minor_units <= 0:
            raise PaymentError("amount must be positive")
        if not idempotency_key:
            raise PaymentError("idempotency key is required")

        cached = self._authorizations.get(idempotency_key)
        if cached is not None:
            return cached

        if payment_method_token == "pm_decline":
            raise PaymentDeclined("card declined (sandbox: insufficient funds)")
        if payment_method_token == "pm_error":
            raise PaymentError("provider unavailable (sandbox)")

        result = AuthorizationResult(
            provider_reference=self._reference("auth", idempotency_key),
            status="authorized",
            amount_minor_units=amount_minor_units,
            currency=currency,
        )
        self._authorizations[idempotency_key] = result
        return result

    def refund(
        self, *, provider_reference: str, amount_minor_units: int, idempotency_key: str
    ) -> AuthorizationResult:
        if amount_minor_units <= 0:
            raise PaymentError("refund amount must be positive")

        cached = self._refunds.get(idempotency_key)
        if cached is not None:
            return cached

        result = AuthorizationResult(
            provider_reference=self._reference("rfnd", idempotency_key),
            status="refunded",
            amount_minor_units=amount_minor_units,
            currency="EUR",
        )
        self._refunds[idempotency_key] = result
        return result


_gateway: PaymentGateway = SandboxGateway()


def get_gateway() -> PaymentGateway:
    """Return the configured gateway.

    Only the sandbox is implemented. An unknown provider name fails loudly rather than
    falling back to the sandbox, so a misconfigured deployment cannot silently process
    live money through a mock.
    """

    provider = os.getenv("PAYMENT_PROVIDER", "sandbox").strip().lower()
    if provider != "sandbox":
        raise PaymentError(
            f"payment provider {provider!r} is configured but no adapter is implemented; "
            "implement PaymentGateway for it before enabling"
        )
    return _gateway


def reset_gateway() -> None:
    """Test hook: clear cached idempotent results."""

    global _gateway
    _gateway = SandboxGateway()
