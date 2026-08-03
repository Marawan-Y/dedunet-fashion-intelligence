"""Rate limiting.

Verification discipline: a 429 alone proves nothing. Every negative-path test here
asserts the status code, a structured machine-readable reason, the required headers, and
the absence of a traceback — because a crashing middleware can also produce a non-2xx
response, and the two must never be confused. Readiness is re-checked after each burst.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import rate_limit
from app.main import app

ORIGIN = "http://localhost:13000"
BAD_LOGIN = {"email": "nobody@meret.example", "password": "definitely-wrong"}


class FakeClock:
    """Advanceable monotonic clock so tests never sleep."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def assert_no_traceback(response) -> None:
    body = response.text
    for marker in ("Traceback", "File \"", "Internal Server Error"):
        assert marker not in body, f"response leaked a crash, not a controlled refusal:\n{body[:400]}"


def assert_rate_limit_headers(response) -> None:
    for header in ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"):
        assert header in response.headers, f"missing {header}; headers={dict(response.headers)}"


# ----------------------------------------------------------------- burst behaviour


def test_fifteen_rapid_invalid_logins_give_ten_401_then_five_429(client, seeded):
    statuses = [
        client.post("/api/v1/auth/login", json=BAD_LOGIN).status_code for _ in range(15)
    ]

    assert statuses.count(401) == 10, f"expected exactly ten 401s, got {statuses}"
    assert statuses.count(429) == 5, f"expected exactly five 429s, got {statuses}"
    # Ordering matters: the limit must engage after the allowance, not before it.
    assert statuses[:10] == [401] * 10
    assert statuses[10:] == [429] * 5


def test_first_429_is_fully_formed(client, seeded):
    """Status, structured reason, headers, CORS and correlation ID together."""

    first_429 = None
    for _ in range(15):
        response = client.post(
            "/api/v1/auth/login", json=BAD_LOGIN, headers={"Origin": ORIGIN}
        )
        if response.status_code == 429:
            first_429 = response
            break

    assert first_429 is not None, "limiter never engaged"
    assert_no_traceback(first_429)

    body = first_429.json()
    assert body["reason"] == "RATE_LIMIT_EXCEEDED"
    assert body["scope"] == "login"
    assert isinstance(body["retry_after_seconds"], int) and body["retry_after_seconds"] >= 1
    assert body["detail"] == "rate limit exceeded"

    assert "retry-after" in first_429.headers
    assert int(first_429.headers["retry-after"]) >= 1
    assert_rate_limit_headers(first_429)
    assert first_429.headers["x-ratelimit-remaining"] == "0"

    # The 429 is short-circuited by the innermost middleware, yet must still pass back
    # out through CORS and the correlation logger. This is the middleware-order proof.
    assert first_429.headers.get("access-control-allow-origin") == ORIGIN, (
        "429 lacks CORS headers: the limiter is registered outside CORSMiddleware, so a "
        "browser would see an opaque network error instead of a readable rejection"
    )
    assert first_429.headers.get("x-correlation-id"), "429 lost its correlation ID"

    # Presence on the wire is not enough. Without Access-Control-Expose-Headers a browser
    # is FORBIDDEN from reading these, so client code cannot honour Retry-After even
    # though the server sent it. An earlier version of this test checked only
    # Access-Control-Allow-Origin and survived deleting expose_headers entirely.
    exposed = {
        h.strip().lower()
        for h in first_429.headers.get("access-control-expose-headers", "").split(",")
        if h.strip()
    }
    for required in (
        "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining",
        "x-ratelimit-reset", "x-correlation-id",
    ):
        assert required in exposed, (
            f"{required} is sent but not exposed to the browser; a cross-origin client "
            f"cannot read it. exposed={sorted(exposed)}"
        )


def test_readiness_and_health_survive_a_burst(client, seeded):
    for _ in range(30):
        client.post("/api/v1/auth/login", json=BAD_LOGIN)

    ready = client.get("/ready")
    assert ready.status_code == 200, "readiness was throttled; an orchestrator would restart a healthy API"
    assert ready.json()["checks"]["database"] == "ok"

    health = client.get("/health")
    assert health.status_code == 200


def test_health_and_ready_are_never_limited_even_when_hammered(client, seeded):
    """Well beyond the 300/min default bucket."""
    statuses = {client.get("/ready").status_code for _ in range(400)}
    assert statuses == {200}, f"readiness was limited: {statuses}"

    statuses = {client.get("/health").status_code for _ in range(400)}
    assert statuses == {200}


# ------------------------------------------------------------------ bucket isolation


def test_registration_uses_its_own_bucket(client, seeded):
    """Exhausting login must not block registration, and vice versa."""

    for _ in range(15):
        client.post("/api/v1/auth/login", json=BAD_LOGIN)
    assert client.post("/api/v1/auth/login", json=BAD_LOGIN).status_code == 429

    # Registration is a separate bucket and still has its allowance.
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "fresh1@meret.example", "password": "password-123", "full_name": "Fresh"},
    )
    assert response.status_code == 201, response.text


def test_registration_bucket_is_five_per_hour(client, seeded):
    statuses = []
    for i in range(7):
        statuses.append(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"reg{i}@meret.example",
                    "password": "password-123",
                    "full_name": f"Reg {i}",
                },
            ).status_code
        )
    assert statuses.count(429) == 2, f"expected 5 allowed then 2 refused, got {statuses}"


def test_tokenless_cart_creation_is_limited(client, seeded):
    """Every tokenless cart call creates a Cart row, so it must be bounded."""

    from sqlalchemy import select

    from app.commerce.db import SessionLocal
    from app.commerce.models import Variant

    with SessionLocal() as session:
        variant_id = session.scalar(select(Variant).where(Variant.sku == "MRT-TEE-BLK-M")).id

    statuses = [
        client.post("/api/v1/cart/items", json={"variant_id": variant_id, "quantity": 1}).status_code
        for _ in range(25)
    ]
    assert statuses.count(429) == 5, f"expected 20 allowed then 5 refused, got {statuses}"


def test_request_with_cart_token_does_not_consume_the_anonymous_bucket(client, seeded):
    """A returning shopper must not be throttled by the anti-abuse bucket."""

    from sqlalchemy import select

    from app.commerce.db import SessionLocal
    from app.commerce.models import Variant

    with SessionLocal() as session:
        variant_id = session.scalar(select(Variant).where(Variant.sku == "MRT-TEE-BLK-M")).id

    token = client.post(
        "/api/v1/cart/items", json={"variant_id": variant_id, "quantity": 1}
    ).json()["cart_token"]

    # Exhaust the tokenless bucket entirely.
    for _ in range(30):
        client.post("/api/v1/cart/items", json={"variant_id": variant_id, "quantity": 1})
    assert (
        client.post("/api/v1/cart/items", json={"variant_id": variant_id, "quantity": 1}).status_code
        == 429
    )

    # The tokenized request falls to the generous default bucket and still succeeds.
    with_token = client.get("/api/v1/cart", headers={"X-Cart-Token": token})
    assert with_token.status_code == 200, with_token.text


# ------------------------------------------------------------------- proxy handling


def test_spoofed_forwarded_for_does_not_mint_a_fresh_bucket(client, seeded, monkeypatch):
    """Default posture. Trusting XFF unconditionally is worse than no limiter at all."""

    monkeypatch.delenv("RATE_LIMIT_TRUSTED_PROXY_COUNT", raising=False)

    statuses = []
    for i in range(15):
        statuses.append(
            client.post(
                "/api/v1/auth/login",
                json=BAD_LOGIN,
                headers={"X-Forwarded-For": f"10.0.0.{i}"},  # a different "IP" each time
            ).status_code
        )
    assert statuses.count(429) == 5, (
        f"spoofed X-Forwarded-For changed the bucket key; limiter is trivially bypassable: {statuses}"
    )


def test_forwarded_for_is_honoured_only_when_a_proxy_count_is_configured(monkeypatch):
    class Req:
        def __init__(self, xff: str, host: str = "203.0.113.9") -> None:
            self.headers = {"x-forwarded-for": xff}
            self.client = type("C", (), {"host": host})()

    request = Req("1.1.1.1, 2.2.2.2, 3.3.3.3")

    # Default: direct peer only.
    monkeypatch.delenv("RATE_LIMIT_TRUSTED_PROXY_COUNT", raising=False)
    assert rate_limit.client_key(request) == "203.0.113.9"

    # One trusted proxy -> take the entry one hop from the right.
    monkeypatch.setenv("RATE_LIMIT_TRUSTED_PROXY_COUNT", "1")
    assert rate_limit.client_key(request) == "3.3.3.3"

    monkeypatch.setenv("RATE_LIMIT_TRUSTED_PROXY_COUNT", "2")
    assert rate_limit.client_key(request) == "2.2.2.2"

    # Garbage configuration must fail safe to the direct peer, not crash.
    monkeypatch.setenv("RATE_LIMIT_TRUSTED_PROXY_COUNT", "not-a-number")
    assert rate_limit.client_key(request) == "203.0.113.9"


# ------------------------------------------------------------------ enabled by default


def test_limiter_is_enabled_when_the_variable_is_absent(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    assert rate_limit.rate_limiting_enabled() is True, "an unset variable must never mean disabled"


@pytest.mark.parametrize("value,expected", [
    ("1", True), ("true", True), ("yes", True), ("anything", True),
    ("0", False), ("false", False), ("no", False), ("FALSE", False),
])
def test_enable_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", value)
    assert rate_limit.rate_limiting_enabled() is expected


# --------------------------------------------------------------------- bucket maths


def test_bucket_refills_over_time():
    clock = FakeClock()
    limiter = rate_limit.TokenBucketLimiter(clock=clock)
    rule = rate_limit.RULES["login"]

    for _ in range(10):
        assert limiter.check("k", rule).allowed
    assert not limiter.check("k", rule).allowed

    clock.advance(6)          # 10 per 60s -> one token per 6s
    assert limiter.check("k", rule).allowed
    assert not limiter.check("k", rule).allowed

    clock.advance(600)        # long idle refills to capacity, never beyond
    assert sum(limiter.check("k", rule).allowed for _ in range(20)) == 10


def test_retry_after_is_at_least_one_second():
    clock = FakeClock()
    limiter = rate_limit.TokenBucketLimiter(clock=clock)
    rule = rate_limit.RULES["login"]
    for _ in range(10):
        limiter.check("k", rule)
    decision = limiter.check("k", rule)
    assert decision.allowed is False
    assert decision.retry_after >= 1, "Retry-After of 0 invites an immediate retry storm"


def test_buckets_are_independent_per_key():
    clock = FakeClock()
    limiter = rate_limit.TokenBucketLimiter(clock=clock)
    rule = rate_limit.RULES["login"]
    for _ in range(10):
        limiter.check("a", rule)
    assert not limiter.check("a", rule).allowed
    assert limiter.check("b", rule).allowed, "one client's burst throttled another"


def test_exempt_paths_have_no_rule():
    assert rate_limit.limit_for("GET", "/health", has_cart_token=False) is None
    assert rate_limit.limit_for("GET", "/ready", has_cart_token=False) is None
    assert rate_limit.limit_for("GET", "/api/v1/catalog/products", has_cart_token=False) is not None


def test_module_level_client_still_subject_to_the_limiter(seeded):
    """The autouse reset must cover clients built outside the `client` fixture."""

    module_client = TestClient(app)
    statuses = [
        module_client.post("/api/v1/auth/login", json=BAD_LOGIN).status_code for _ in range(15)
    ]
    assert 429 in statuses, "a module-level TestClient escaped the limiter"
