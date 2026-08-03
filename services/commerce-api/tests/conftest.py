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
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")

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
