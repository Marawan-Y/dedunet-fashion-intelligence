"""Process-local request rate limiting.

Standard library only. ``security.py`` already establishes that security-critical paths
carry no unvetted third-party dependency, and a token bucket is a few lines of integer
arithmetic — importing a library for it would add supply-chain surface for no benefit.

**Token bucket, not fixed window.** A fixed window allows a 2x burst across the boundary:
ten requests at 11:59:59 and ten more at 12:00:00 pass a "10 per minute" window. A
sliding log has unbounded memory. A token bucket is O(1) per key, allows a deliberate
burst up to capacity, and refills smoothly.

**The clock is injectable.** Without that, every test would have to sleep, and a suite
that sleeps stops being run. Tests advance a fake clock instead.

SCOPE LIMIT — read before deploying more than one replica
---------------------------------------------------------
Buckets live in this process's memory. Two API processes mean two independent sets of
buckets and therefore twice the effective limit; ``uvicorn --workers N`` multiplies it by
N. **This limiter is valid only for a single API process or replica.** Horizontal scaling
must stay blocked until a shared backend (Redis) or a gateway-level limiter exists. That
is a deployment constraint, not a code TODO.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

__all__ = [
    "Decision",
    "REWRITTEN_PEER_KEY",
    "TokenBucketLimiter",
    "client_key",
    "get_limiter",
    "limit_for",
    "rate_limiting_enabled",
    "reset_limiter",
]

# Paths that must never be limited. The compose healthcheck polls /ready every 10s; if a
# burst of customer traffic could exhaust a shared bucket and start returning 429 there,
# the orchestrator would conclude the service is unhealthy and restart a working API.
EXEMPT_PATHS = frozenset({"/health", "/ready"})


@dataclass(frozen=True)
class Decision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    reset_after: int


@dataclass(frozen=True)
class Rule:
    name: str
    capacity: int
    per_seconds: int

    @property
    def refill_per_second(self) -> float:
        return self.capacity / self.per_seconds


# Buckets are keyed per client IP. Values chosen against real abuse cost, not taste:
#   login     - PBKDF2 at 240k rounds makes each attempt expensive server-side, so this
#               is a CPU-exhaustion vector as much as a credential-stuffing one.
#   register  - account farming; an hour window because legitimate humans register once.
#   cart      - a tokenless cart call CREATES a Cart row every time, so an unlimited
#               attacker grows the table without bound.
#   default   - blanket backstop so no endpoint is entirely unprotected.
RULES: dict[str, Rule] = {
    "login": Rule("login", 10, 60),
    "register": Rule("register", 5, 3600),
    "cart_anonymous": Rule("cart_anonymous", 20, 60),
    "default": Rule("default", 300, 60),
}


class TokenBucketLimiter:
    """One bucket per key. Not thread-safe by design of use: Starlette's middleware runs
    on a single event loop, so calls are serialised without a lock."""

    def __init__(self, *, clock=time.monotonic) -> None:
        self._clock = clock
        # key -> (tokens, last_refill_timestamp)
        self._buckets: dict[str, tuple[float, float]] = {}
        self._last_prune = 0.0

    def check(self, key: str, rule: Rule) -> Decision:
        now = self._clock()
        self._maybe_prune(now)

        tokens, last = self._buckets.get(key, (float(rule.capacity), now))
        tokens = min(rule.capacity, tokens + (now - last) * rule.refill_per_second)

        if tokens >= 1.0:
            self._buckets[key] = (tokens - 1.0, now)
            remaining = int(tokens - 1.0)
            return Decision(True, rule.capacity, remaining, 0, self._reset(tokens - 1.0, rule))

        self._buckets[key] = (tokens, now)
        # Seconds until one whole token is available again, rounded up so a client that
        # obeys Retry-After is never rejected a second time for being one moment early.
        retry_after = max(1, int((1.0 - tokens) / rule.refill_per_second) + 1)
        return Decision(False, rule.capacity, 0, retry_after, self._reset(tokens, rule))

    @staticmethod
    def _reset(tokens: float, rule: Rule) -> int:
        missing = rule.capacity - tokens
        return max(0, int(missing / rule.refill_per_second) + 1)

    def _maybe_prune(self, now: float) -> None:
        """Drop full, idle buckets so memory stays bounded under IP churn."""
        if now - self._last_prune < 60.0:
            return
        self._last_prune = now
        self._buckets = {
            key: value
            for key, value in self._buckets.items()
            if not (value[0] >= RULES["default"].capacity and now - value[1] > 600.0)
        }


_limiter: TokenBucketLimiter | None = None


def get_limiter() -> TokenBucketLimiter:
    global _limiter
    if _limiter is None:
        _limiter = TokenBucketLimiter()
    return _limiter


def reset_limiter(*, clock=time.monotonic) -> None:
    """Test hook. Mirrors ``payments.reset_gateway``.

    This is a test hook, not a production bypass: it discards bucket state, it does not
    disable enforcement. The suite runs with the limiter fully enabled.
    """
    global _limiter
    _limiter = TokenBucketLimiter(clock=clock)


def rate_limiting_enabled() -> bool:
    """Read at call time, not at import.

    ``config.Settings`` is a frozen dataclass evaluated once at import, so a value read
    there could not vary per test. This follows the ``payments.get_gateway`` precedent.
    Default is ENABLED: an unset variable must never mean "off".
    """
    return os.getenv("RATE_LIMIT_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def limit_for(method: str, path: str, *, has_cart_token: bool) -> Rule | None:
    """Return the rule governing a request, or None when exempt."""
    if path in EXEMPT_PATHS:
        return None
    if method == "POST" and path.endswith("/auth/login"):
        return RULES["login"]
    if method == "POST" and path.endswith("/auth/register"):
        return RULES["register"]
    if "/cart" in path and not has_cart_token:
        # Scoped to TOKENLESS requests only. A request carrying a cart token reuses an
        # existing row and is not the abuse case; charging it to this bucket would
        # throttle ordinary shoppers while leaving the actual attack unaddressed.
        return RULES["cart_anonymous"]
    return RULES["default"]


# Bucket key used when the ASGI server has already replaced the peer address from a
# forwarded header that this application does not trust. See _peer_was_rewritten_upstream.
REWRITTEN_PEER_KEY = "_forwarded_peer_untrusted"


def _peer_was_rewritten_upstream(request) -> bool:
    """True when the ASGI server replaced ``scope['client']`` from a forwarded header.

    SECOND LAYER, not the fix. The fix is ``app/server.py``, which configures the server
    never to interpret forwarded headers unless a real proxy is declared. This exists
    because that configuration lives on a command line, and a command line can be
    bypassed -- ``uvicorn app.main:app`` run by hand, or ``FORWARDED_ALLOW_IPS`` set in
    the environment, both restore uvicorn's unsafe default without touching this repo.

    Detection is exact rather than heuristic. uvicorn's ``ProxyHeadersMiddleware`` cannot
    recover the forwarded client's source port, so it writes a literal
    ``scope["client"] = (host, 0)``. A real TCP peer never has source port 0: it is
    reserved and a connecting socket is always assigned a real ephemeral port. Port 0 in
    an inbound scope therefore means "this address was asserted by a header", not
    "this address is who connected".

    The true peer is unrecoverable at this point -- the middleware overwrote it and the
    scope keeps no copy -- so this cannot restore the correct key. What it can do is
    refuse to honour the forged one: every such request shares ONE bucket. An attacker
    varying the header gains nothing, and no legitimate client's bucket can be exhausted
    on their behalf, because a legitimate direct client keys on its real address.
    """

    client = getattr(request, "client", None)
    return client is not None and getattr(client, "port", None) == 0


def client_key(request, *, trusted_proxy_count: int | None = None) -> str:
    """Derive the bucket key for a request.

    ``X-Forwarded-For`` is IGNORED by default. Honouring it unconditionally is worse than
    having no limiter at all: any client can put an arbitrary value in that header and
    mint themselves a fresh bucket per request. It is trusted only when the operator
    declares how many proxies actually sit in front, via
    ``RATE_LIMIT_TRUSTED_PROXY_COUNT``, and then only the entry that many hops from the
    right — the rightmost entries are the ones your own infrastructure appended.

    This check runs LATE — after the ASGI server has already built the scope. It is
    therefore not sufficient on its own, because an ASGI server configured to interpret
    forwarded headers has by then replaced ``request.client`` with a header value.
    ``app/server.py`` is what stops that happening; ``_peer_was_rewritten_upstream``
    below contains the damage if something starts the server without it.
    """
    if trusted_proxy_count is None:
        try:
            trusted_proxy_count = int(os.getenv("RATE_LIMIT_TRUSTED_PROXY_COUNT", "0"))
        except ValueError:
            trusted_proxy_count = 0

    direct = request.client.host if request.client else "unknown"
    if trusted_proxy_count <= 0:
        if _peer_was_rewritten_upstream(request):
            return REWRITTEN_PEER_KEY
        return direct

    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if not parts:
        return direct
    index = len(parts) - trusted_proxy_count
    return parts[index] if 0 <= index < len(parts) else parts[0]
