"""Password hashing and session tokens.

Implemented with the standard library only. PBKDF2-HMAC-SHA256 is used rather than a
third-party KDF so the platform has no unvetted dependency on a security-critical path.

Threat notes
------------
- Password hashes are salted per user, so identical passwords produce different digests
  and a stolen database cannot be attacked with a single precomputed table.
- Verification uses ``compare_digest`` to avoid leaking match length through timing.
- Session tokens are HMAC-signed and carry an expiry. They are integrity-protected, not
  encrypted: never place anything confidential in a token payload.
- ``SESSION_SECRET`` must be supplied outside development. A missing secret in a
  non-development environment raises rather than silently using a known default, which
  would let anyone forge an administrator session.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

_PBKDF2_ROUNDS = 240_000
_DIGEST = "sha256"

_DEV_SECRET = "dev-only-session-secret-not-for-deployment"


class InvalidToken(Exception):
    """Raised when a session token is malformed, forged or expired."""


def _session_secret() -> str:
    secret = os.getenv("SESSION_SECRET", "").strip()
    if secret:
        return secret
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "test"}:
        raise RuntimeError(
            "SESSION_SECRET must be set outside development; refusing to sign sessions "
            "with a publicly known development secret"
        )
    return _DEV_SECRET


def hash_password(password: str) -> str:
    """Return ``pbkdf2_sha256$rounds$salt$digest``."""

    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("password must be a string of at least 8 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(_DIGEST, password.encode(), salt, _PBKDF2_ROUNDS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(_PBKDF2_ROUNDS),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verification. Returns False on any malformed stored value."""

    try:
        algorithm, rounds_raw, salt_b64, digest_b64 = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        rounds = int(rounds_raw)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac(_DIGEST, password.encode(), salt, rounds)
    return hmac.compare_digest(candidate, expected)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def issue_token(customer_id: int, role: str, *, ttl_seconds: int = 3600) -> str:
    payload = {
        "sub": customer_id,
        "role": role,
        "exp": int(time.time()) + ttl_seconds,
        # A nonce keeps two tokens issued in the same second distinct, so logout or
        # revocation lists can address an individual session.
        "jti": secrets.token_hex(8),
    }
    body = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signature = hmac.new(_session_secret().encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url(signature)}"


def verify_token(token: str) -> dict:
    """Return the payload of a valid token, else raise ``InvalidToken``."""

    if not isinstance(token, str) or token.count(".") != 1:
        raise InvalidToken("malformed token")
    body, signature = token.split(".")

    expected = hmac.new(_session_secret().encode(), body.encode(), hashlib.sha256).digest()
    try:
        provided = _unb64url(signature)
    except (ValueError, TypeError) as exc:
        raise InvalidToken("malformed signature") from exc

    # Signature is checked BEFORE the payload is parsed, so unverified attacker-supplied
    # data is never deserialized.
    if not hmac.compare_digest(expected, provided):
        raise InvalidToken("bad signature")

    try:
        payload = json.loads(_unb64url(body))
    except (ValueError, TypeError) as exc:
        raise InvalidToken("malformed payload") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise InvalidToken("expired")
    return payload
