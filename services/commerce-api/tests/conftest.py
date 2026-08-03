"""Shared test safeguards.

The PoC catalog is a JSON file that the admin endpoint writes in place. A test that
reaches the write path would silently mutate the preserved sample fixture
(`backend/data/products.json`). This module snapshots the data fixtures before the
session, restores them afterwards, and FAILS the run if any test changed them, so a
fixture mutation can never pass unnoticed.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

# Point the commerce domain at a private in-memory database BEFORE any application
# module is imported. Without this the suite would open (and write to) the developer's
# real commerce.sqlite3 file.
# EXPLICIT, not setdefault. With DATABASE_URL documented in .env.example a developer
# may well have it exported; setdefault would then silently point the whole suite at a
# real database - including the db_session fixture's drop_all. The test database is
# chosen only by COMMERCE_TEST_DATABASE_URL, which nothing else sets.
os.environ["DATABASE_URL"] = os.environ.get(
    "COMMERCE_TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:"
)
os.environ.setdefault("APP_ENV", "test")

if "COMMERCE_TEST_DATABASE_URL" not in os.environ and "postgres" in os.environ["DATABASE_URL"]:
    raise RuntimeError("refusing to run the suite against a PostgreSQL URL without an explicit opt-in")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROTECTED_FIXTURES = ("products.json", "candidate_products.json")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def protect_data_fixtures() -> object:
    snapshots = {
        name: (DATA_DIR / name).read_bytes()
        for name in PROTECTED_FIXTURES
        if (DATA_DIR / name).exists()
    }
    before = {name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()}

    yield

    mutated: list[str] = []
    for name, original in snapshots.items():
        path = DATA_DIR / name
        if _digest(path) != before[name]:
            mutated.append(f"{name} (sha256 {before[name]} -> {_digest(path)})")
            path.write_bytes(original)  # restore so the next run starts clean

    if mutated:
        raise AssertionError(
            "Test run mutated protected data fixtures and they were restored: "
            + "; ".join(mutated)
        )


# --------------------------------------------------------------- commerce fixtures


@pytest.fixture()
def db_session():
    """A clean commerce schema per test.

    Tables are dropped and recreated rather than reusing state, so no test can pass
    because of rows another test happened to leave behind.
    """

    from app.commerce.db import Base, SessionLocal, engine
    from app.commerce import models  # noqa: F401  (registers mappers)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded(db_session):
    """Database seeded with the fictional MERET catalog and demo accounts."""

    from app.commerce.seed import seed

    seed(db_session)
    return db_session


@pytest.fixture()
def client(seeded):
    """TestClient whose request sessions share the test's in-memory database."""

    from fastapi.testclient import TestClient

    from app.commerce import payments
    from app.commerce.db import SessionLocal, get_session
    from app.main import app

    # Reset the sandbox gateway so cached idempotent results never leak between tests.
    payments.reset_gateway()

    def _override():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth(client):
    """Helper returning bearer headers for the seeded demo accounts."""

    from app.commerce.seed import DEMO_ADMIN_EMAIL, DEMO_CUSTOMER_EMAIL, DEMO_PASSWORD

    def _login(email: str) -> dict[str, str]:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return {
        "admin": _login(DEMO_ADMIN_EMAIL),
        "customer": _login(DEMO_CUSTOMER_EMAIL),
    }

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear limiter buckets before EVERY test.

    Autouse, not a line inside the `client` fixture: test_admin_security.py,
    test_api.py and test_money_integrity.py each build a module-level TestClient(app)
    and never touch that fixture, so they would run against a shared, never-reset
    bucket.

    This matters because the `auth` fixture performs TWO logins before every test body
    that uses it. The suite finishes in seconds, so a monotonic clock barely advances
    and no refill occurs; without a reset the login bucket (10/min) would be exhausted
    part-way through the run and most of the suite would 429.

    It resets STATE. It does not disable enforcement - the whole suite runs with the
    limiter fully enabled.
    """

    from app import rate_limit

    rate_limit.reset_limiter()
    yield
    rate_limit.reset_limiter()

@pytest.fixture(autouse=True)
def reset_notification_sender():
    """Clear the cached sender and any SMTP configuration before every test.

    Without this a developer with SMTP_* exported in their shell would have the suite
    attempt real deliveries. The channel is forced back to the safe default.
    """

    import os

    from app.commerce import notifications

    for key in ("NOTIFICATION_CHANNEL", "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME",
                "SMTP_PASSWORD", "SMTP_FROM", "SMTP_USE_TLS"):
        os.environ.pop(key, None)
    notifications.reset_sender()
    yield
    notifications.reset_sender()
