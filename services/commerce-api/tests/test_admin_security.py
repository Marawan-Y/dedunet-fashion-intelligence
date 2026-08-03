"""Admin access-control tests for the PoC (risk SB-RISK-B5-001).

Scope limitation: these tests cover only the minimum fail-closed behavior of the PoC
admin token gate. They do NOT demonstrate an authentication system. There is no
identity provider, no MFA, no session model, no rate limiting, no audit trail and no
secret rotation. The admin surface remains a launch blocker until B5/B19 deliver
those controls.
"""

from __future__ import annotations

import importlib
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)

VALID_PRODUCT = {
    "id": "admin-security-probe",
    "slug": "admin-security-probe",
    "name": "Admin Security Probe",
    "category": "t-shirt",
    "collection": "Probe",
    "description": "Synthetic probe payload; must never be persisted by these tests.",
    "fibre_composition": "100% cotton",
    "made_in": "Egypt",
    "price_minor_units": 100,
    "currency": "EUR",
    "image_url": "https://example.invalid/probe.png",
    "variants": [{"sku": "ADMIN-PROBE-S", "size": "S", "color": "Black", "stock": 0}],
}


@pytest.fixture
def configured_admin_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Replace the placeholder token with a real one for the duration of a test."""

    import app.main as main_module

    token = "test-only-high-entropy-token-4d1f9c"
    monkeypatch.setattr(
        main_module, "settings", Settings(admin_api_token=token, app_env="development")
    )
    return token


def test_admin_write_without_token_is_rejected(configured_admin_token: str) -> None:
    response = client.post("/api/v1/admin/products", json=deepcopy(VALID_PRODUCT))
    assert response.status_code == 401


def test_admin_write_with_wrong_token_is_rejected(configured_admin_token: str) -> None:
    response = client.post(
        "/api/v1/admin/products",
        headers={"X-Admin-Token": "definitely-not-the-token"},
        json=deepcopy(VALID_PRODUCT),
    )
    assert response.status_code == 401


def test_admin_write_with_shipped_placeholder_token_is_rejected() -> None:
    """The `.env.example` placeholder must never authorize a write, in any environment.

    Regression: before this guard existed, a default-configured PoC accepted
    `X-Admin-Token: change-me` and destructively rewrote the sample catalog fixture.
    """

    response = client.post(
        "/api/v1/admin/products",
        headers={"X-Admin-Token": "change-me"},
        json=deepcopy(VALID_PRODUCT),
    )
    assert response.status_code == 503
    assert "placeholder ADMIN_API_TOKEN" in response.json()["detail"]


def test_rejected_admin_write_does_not_persist(configured_admin_token: str) -> None:
    """A rejected privileged write must leave the catalog byte-identical."""

    from app.main import repo

    before = repo.path.read_bytes()
    client.post("/api/v1/admin/products", json=deepcopy(VALID_PRODUCT))
    client.post(
        "/api/v1/admin/products",
        headers={"X-Admin-Token": "change-me"},
        json=deepcopy(VALID_PRODUCT),
    )
    client.post(
        "/api/v1/admin/products",
        headers={"X-Admin-Token": "wrong"},
        json=deepcopy(VALID_PRODUCT),
    )
    assert repo.path.read_bytes() == before


@pytest.mark.parametrize("app_env", ["development", "staging", "production"])
def test_placeholder_token_disables_admin_api_in_every_environment(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    """Unsafe-default guard: placeholder credentials fail closed everywhere."""

    import app.main as main_module

    unsafe = Settings(admin_api_token="change-me", app_env=app_env)
    monkeypatch.setattr(main_module, "settings", unsafe)

    response = client.post(
        "/api/v1/admin/products",
        headers={"X-Admin-Token": "change-me"},
        json=deepcopy(VALID_PRODUCT),
    )
    assert response.status_code == 503
    assert "placeholder ADMIN_API_TOKEN" in response.json()["detail"]


def test_admin_token_default_detection() -> None:
    assert Settings(admin_api_token="change-me").admin_token_is_default is True
    assert Settings(admin_api_token="").admin_token_is_default is True
    assert Settings(admin_api_token="a-real-high-entropy-token").admin_token_is_default is False


def test_config_module_imports_cleanly() -> None:
    """Guards against a settings import-time regression breaking the security gate."""

    module = importlib.import_module("app.config")
    assert hasattr(module.settings, "admin_token_is_default")
