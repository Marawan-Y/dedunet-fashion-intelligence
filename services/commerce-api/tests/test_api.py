from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_catalog_returns_products() -> None:
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 3
    assert all(item["made_in"] == "Egypt" for item in payload)
    # Money contract SB-AR-B3-003: the wire carries authoritative integer minor units.
    assert all(isinstance(item["price_minor_units"], int) for item in payload)
    assert all(item["currency"] == "EUR" for item in payload)
    assert all("price_eur" not in item for item in payload)


def test_stylist_recommendation_respects_budget() -> None:
    response = client.post(
        "/api/v1/stylist/recommend",
        json={
            "occasion": "summer city dinner",
            "preferred_colors": ["Black", "Off White"],
            "preferred_categories": ["t-shirt", "shirt"],
            "budget_minor_units": 16000,
            "style_notes": "eastern streetwear",
        },
    )
    assert response.status_code == 200
    assert response.json()["total_minor_units"] <= 16000


def test_quote_rejects_unknown_sku() -> None:
    response = client.post(
        "/api/v1/orders/quote",
        json={"items": [{"sku": "UNKNOWN", "quantity": 1}], "destination_country": "DE"},
    )
    assert response.status_code == 400


def test_candidate_endpoint_is_synthetic_non_sellable_preview() -> None:
    response = client.get("/api/v1/candidate-products")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["synthetic_fixture"] is True
    assert payload[0]["lifecycle_status"] == "candidate"
    assert payload[0]["publication_status"] == "preview"
    assert sum(item["opening_stock"] for item in payload[0]["variants"]) == 0
    assert payload[0]["approved_claims"] == []
    assert payload[0]["price"] is None


def test_candidate_activation_endpoint_fails_closed() -> None:
    response = client.get("/api/v1/candidate-products/VS-TEE-001/activation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["eligible"] is False
    codes = {item["code"] for item in payload["errors"]}
    assert "SYNTHETIC_CANNOT_ACTIVATE" in codes
    assert "MISSING_OPERATOR" in codes
    assert "UNAPPROVED_PRICE" in codes
    assert "BATCH_NOT_RELEASED" in codes
    assert "ACTIVATION_BLOCKED" in codes
