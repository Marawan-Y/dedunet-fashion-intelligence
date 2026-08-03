"""Notification delivery adapters.

Mirrors ``payments.py`` deliberately: two typed exceptions separating retryable from
terminal, a frozen result dataclass, a ``Protocol`` contract, a default in-process
implementation, a selector that reads configuration at call time and RAISES on an unknown
value, and a reset hook for tests. One pattern for every external integration means one
set of habits for reviewing them.

Default is ``console``. An unconfigured deployment must never attempt to send real mail:
silently reaching for SMTP with half-configured credentials is how a staging box starts
emailing real people.

Nothing here logs a credential, and no raw provider response is surfaced to a caller —
SMTP servers routinely echo the envelope, and some echo the AUTH line.
"""

from __future__ import annotations

import hashlib
import os
import smtplib
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Protocol

__all__ = [
    "ConsoleSender",
    "DeliveryResult",
    "NotificationError",
    "NotificationRejected",
    "NotificationSender",
    "SmtpSender",
    "get_sender",
    "reset_sender",
]

# Header carrying our own row identity, so a duplicate arriving at a real mailbox can be
# traced back to the outbox row that produced it. At-least-once delivery makes duplicates
# possible; this makes them investigable.
IDEMPOTENCY_HEADER = "X-Notification-Key"


class NotificationError(Exception):
    """Retryable transport or provider failure. The message may not have been sent."""


class NotificationRejected(Exception):
    """Terminal rejection of the recipient or message. Retrying will not help.

    Retrying a positively refused address forever is how a sender reputation is destroyed
    and a domain ends up on a blocklist.
    """


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    provider_reference: str
    accepted: bool
    delivered_at: datetime
    diagnostics: str = ""
    # Deliberately excludes any credential, raw provider banner or AUTH exchange.
    metadata: dict = field(default_factory=dict)


class NotificationSender(Protocol):
    """Contract every notification adapter must satisfy."""

    name: str

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> DeliveryResult: ...


def _reference(prefix: str, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]
    return f"{prefix}_{digest}"


class ConsoleSender:
    """Default adapter. No credentials, no network, deterministic.

    Logs only routing information — recipient, subject and the idempotency key. The
    message body is NOT printed: notification bodies carry order numbers and amounts, and
    a container log is not a place to accumulate them.
    """

    name = "console"

    def __init__(self) -> None:
        self._sent: dict[str, DeliveryResult] = {}

    def send(
        self, *, recipient: str, subject: str, body: str, idempotency_key: str
    ) -> DeliveryResult:
        if not recipient or "@" not in recipient:
            raise NotificationRejected(f"invalid recipient address: {recipient!r}")
        if not idempotency_key:
            raise NotificationError("idempotency key is required")

        cached = self._sent.get(idempotency_key)
        if cached is not None:
            return cached

        result = DeliveryResult(
            provider=self.name,
            provider_reference=_reference("console", idempotency_key),
            accepted=True,
            delivered_at=datetime.now(timezone.utc),
            diagnostics="written to stdout",
            metadata={"body_bytes": len(body.encode())},
        )
        self._sent[idempotency_key] = result
        print(
            f"[notification] to={recipient} subject={subject!r} "
            f"key={idempotency_key} ref={result.provider_reference}",
            flush=True,
        )
        return result


class SmtpSender:
    """Real SMTP over the standard library.

    A five-second timeout is explicit and not negotiable: without one, a wedged server
    hangs the dispatcher indefinitely, and in CI it hangs the job until the runner kills
    it. Slow mail is recoverable; a stuck worker is not.
    """

    name = "smtp"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        sender: str = "",
        use_tls: bool = True,
        timeout: float = 5.0,
    ) -> None:
        if not host:
            raise NotificationError("SMTP_HOST is not configured")
        if not sender:
            raise NotificationError("SMTP_FROM is not configured")
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._use_tls = use_tls
        self._timeout = timeout

    def send(
        self, *, recipient: str, subject: str, body: str, idempotency_key: str
    ) -> DeliveryResult:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = subject
        message[IDEMPOTENCY_HEADER] = idempotency_key
        message.set_content(body)

        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
                client.ehlo()
                if self._use_tls:
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                if self._username:
                    client.login(self._username, self._password)
                client.send_message(message)
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as exc:
            # The server positively refused this address. Retrying cannot fix it.
            raise NotificationRejected(f"{type(exc).__name__}: recipient or sender refused") from exc
        except smtplib.SMTPAuthenticationError as exc:
            # Terminal for THIS configuration: the same bad credential will fail forever.
            # The exception text is not echoed - it can contain the attempted username.
            raise NotificationRejected("SMTP authentication failed") from exc
        except (smtplib.SMTPException, OSError, socket.timeout) as exc:
            raise NotificationError(f"{type(exc).__name__}: SMTP transport failure") from exc

        return DeliveryResult(
            provider=self.name,
            provider_reference=_reference("smtp", idempotency_key),
            accepted=True,
            delivered_at=datetime.now(timezone.utc),
            diagnostics="accepted by SMTP server",
            metadata={"host": self._host, "port": self._port},  # never the credentials
        )


_sender: NotificationSender | None = None


def get_sender() -> NotificationSender:
    """Return the configured sender.

    Configuration is read at CALL time, not import time, matching
    ``payments.get_gateway``: ``config.Settings`` is a frozen dataclass evaluated once at
    import and could not vary per test.

    An unknown channel RAISES rather than falling back to console. A silent fallback would
    mean an operator who configured ``sendgrid`` sees "sent" in the logs while nothing
    ever left the building.
    """

    global _sender
    if _sender is not None:
        return _sender

    channel = os.getenv("NOTIFICATION_CHANNEL", "console").strip().lower()

    if channel == "console":
        _sender = ConsoleSender()
    elif channel == "smtp":
        host = os.getenv("SMTP_HOST", "").strip()
        sender_address = os.getenv("SMTP_FROM", "").strip()
        missing = [
            name for name, value in (("SMTP_HOST", host), ("SMTP_FROM", sender_address))
            if not value
        ]
        if missing:
            raise NotificationError(
                f"NOTIFICATION_CHANNEL=smtp but {', '.join(missing)} is not set"
            )
        _sender = SmtpSender(
            host=host,
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            sender=sender_address,
            use_tls=os.getenv("SMTP_USE_TLS", "1").strip().lower() not in {"0", "false", "no"},
        )
    else:
        raise NotificationError(
            f"notification channel {channel!r} is configured but no adapter implements it; "
            "implement NotificationSender for it before enabling"
        )
    return _sender


def reset_sender() -> None:
    """Test hook. Mirrors ``payments.reset_gateway``."""

    global _sender
    _sender = None
