from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from app.candidate_activation import (
    CandidateProduct,
    validate_candidate_collection,
)


NOW = datetime(2026, 8, 1, tzinfo=UTC)


def candidate_payload() -> dict:
    future = (NOW + timedelta(days=30)).isoformat()
    return {
        "schema_version": "0.1.0",
        "synthetic_fixture": True,
        "product_id": "VS-TEE-001",
        "style_code": "SYNTHETIC-STYLE-001",
        "lifecycle_status": "sellable",
        "publication_status": "public",
        "product_name": "Synthetic candidate T-shirt",
        "category_code": "t-shirt",
        "target_market_codes": ["DE"],
        "fibre_composition": [{"fibre_name": "cotton", "percentage": 100}],
        "country_of_origin": "EG",
        "care_instructions": ["synthetic-test-care"],
        "approved_claims": [
            {
                "claim_id": "claim-synthetic-001",
                "text": "Synthetic supported test claim",
                "scope": "product",
                "evidence_id": "ev-claim",
                "approved_by": "test-approver",
                "expires_at": future,
            }
        ],
        "fit_summary": "Synthetic oversized fit",
        "measurement_set_id": "measure-synthetic-001",
        "variants": [
            {
                "sku": "VS-TEE-001-BLK-S",
                "size_code": "S",
                "color_name": "Black",
                "barcode": "SYNTHETIC-NOT-A-REAL-BARCODE",
                "weight_g": 200,
                "item_dimensions_cm": {"length": 30, "width": 20, "height": 2},
                "opening_stock": 1,
                "count_evidence_id": "ev-count",
            },
            {
                "sku": "VS-TEE-001-BLK-M",
                "size_code": "M",
                "color_name": "Black",
                "barcode": "SYNTHETIC-NOT-A-REAL-BARCODE-2",
                "weight_g": 210,
                "item_dimensions_cm": {"length": 31, "width": 21, "height": 2},
                "opening_stock": 0,
            },
            {
                "sku": "VS-TEE-001-BLK-L",
                "size_code": "L",
                "color_name": "Black",
                "barcode": "SYNTHETIC-NOT-A-REAL-BARCODE-3",
                "weight_g": 220,
                "item_dimensions_cm": {"length": 32, "width": 22, "height": 2},
                "opening_stock": 0,
            },
        ],
        "price": {
            "gross_minor_units": 5900,
            "currency": "EUR",
            "tax_class": "synthetic-tax-class",
            "valid_from": "2026-07-01T00:00:00Z",
            "valid_to": future,
            "approved": True,
            "approval_evidence_id": "ev-price",
        },
        "locale_codes": ["de-DE", "en-DE"],
        "merchant_identity_id": "merchant-synthetic-001",
        "importer_responsible_operator_id": "operator-synthetic-001",
        "withdrawal_return_policy_id": "policy-return-synthetic-001",
        "delivery_promise_id": "policy-delivery-synthetic-001",
        "batch": {
            "batch_id": "batch-synthetic-001",
            "qc_release_status": "released",
            "qc_evidence_id": "ev-qc",
        },
        "assets": [
            {
                "asset_id": "asset-synthetic-001",
                "alt_text": "Synthetic placeholder; not a real product image",
                "rights_evidence_id": "ev-rights",
                "approved": True,
            }
        ],
        "warehouse_location_id": "warehouse-synthetic-001",
        "evidence": [
            {
                "evidence_id": evidence_id,
                "status": "EXTERNALLY-VERIFIED",
                "scope": [scope],
                "issuer": "Synthetic test issuer",
                "approved_by": "test-approver",
                "issued_at": "2026-07-01T00:00:00Z",
                "expires_at": future,
                "synthetic_fixture": False,
            }
            for evidence_id, scope in [
                ("ev-claim", "claim"),
                ("ev-count", "inventory_count"),
                ("ev-price", "price"),
                ("ev-qc", "qc_release"),
                ("ev-rights", "asset_rights"),
                ("ev-fibre", "fibre_composition"),
                ("ev-origin", "country_of_origin"),
                ("ev-care", "care_instructions"),
                ("ev-measure", "measurements"),
                ("ev-operator", "responsible_operator"),
                ("ev-policy", "policy"),
                ("ev-market", "market"),
            ]
        ],
        "field_evidence": {
            "fibre_composition": "ev-fibre",
            "country_of_origin": "ev-origin",
            "care_instructions": "ev-care",
            "measurement_set_id": "ev-measure",
            "importer_responsible_operator_id": "ev-operator",
            "withdrawal_return_policy_id": "ev-policy",
            "delivery_promise_id": "ev-policy",
            "target_market_codes": "ev-market",
        },
        "approved_by": "test-approver",
    }


def error_codes(payload: dict) -> set[str]:
    candidate = CandidateProduct.model_validate(payload)
    return {item.code for item in validate_candidate_collection([candidate], now=NOW)}


def test_duplicate_product_ids_and_skus_are_rejected() -> None:
    payload = candidate_payload()
    duplicate = deepcopy(payload)
    duplicate["variants"][1]["sku"] = duplicate["variants"][0]["sku"]
    candidate = CandidateProduct.model_validate(duplicate)
    errors = validate_candidate_collection([candidate, candidate], now=NOW)
    codes = {item.code for item in errors}
    assert "DUPLICATE_PRODUCT_ID" in codes
    assert "DUPLICATE_SKU" in codes


def test_duplicate_sku_across_distinct_products_is_rejected() -> None:
    """Two different products must not be allowed to claim the same SKU."""

    first = candidate_payload()
    second = deepcopy(first)
    second["product_id"] = "VS-TEE-002"
    # Distinct product IDs, but the first variant SKU collides across products.
    candidates = [
        CandidateProduct.model_validate(first),
        CandidateProduct.model_validate(second),
    ]
    codes = {item.code for item in validate_candidate_collection(candidates, now=NOW)}
    assert "DUPLICATE_SKU" in codes
    assert "DUPLICATE_PRODUCT_ID" not in codes


def test_synthetic_fixture_cannot_activate() -> None:
    """A record flagged as a synthetic fixture can never become sellable/public."""

    payload = candidate_payload()
    assert payload["synthetic_fixture"] is True
    codes = error_codes(payload)
    assert "SYNTHETIC_CANNOT_ACTIVATE" in codes
    assert "ACTIVATION_BLOCKED" in codes


def test_expired_claim_prevents_publication() -> None:
    """A claim whose own expiry has passed cannot be published even with live evidence."""

    payload = candidate_payload()
    payload["approved_claims"][0]["expires_at"] = "2026-07-31T00:00:00Z"
    codes = error_codes(payload)
    assert "UNSUPPORTED_CLAIM" in codes
    assert "ACTIVATION_BLOCKED" in codes


def test_missing_required_evidence_prevents_sellable_public_activation() -> None:
    payload = candidate_payload()
    payload["evidence"] = []
    codes = error_codes(payload)
    assert "MISSING_EVIDENCE" in codes
    assert "ACTIVATION_BLOCKED" in codes


def test_expired_evidence_prevents_activation() -> None:
    payload = candidate_payload()
    payload["evidence"][0]["expires_at"] = "2026-07-31T00:00:00Z"
    assert "EXPIRED_EVIDENCE" in error_codes(payload)


def test_unreleased_batch_prevents_activation() -> None:
    payload = candidate_payload()
    payload["batch"]["qc_release_status"] = "quarantined"
    assert "BATCH_NOT_RELEASED" in error_codes(payload)


def test_missing_responsible_operator_prevents_activation() -> None:
    payload = candidate_payload()
    payload["importer_responsible_operator_id"] = None
    assert "MISSING_OPERATOR" in error_codes(payload)


def test_unapproved_price_prevents_activation() -> None:
    payload = candidate_payload()
    payload["price"]["approved"] = False
    assert "UNAPPROVED_PRICE" in error_codes(payload)


def test_positive_stock_requires_qc_location_and_count_evidence() -> None:
    payload = candidate_payload()
    payload["batch"]["qc_evidence_id"] = None
    payload["warehouse_location_id"] = None
    payload["variants"][0]["count_evidence_id"] = None
    codes = error_codes(payload)
    assert "POSITIVE_STOCK_WITHOUT_QC_EVIDENCE" in codes
    assert "POSITIVE_STOCK_WITHOUT_LOCATION" in codes
    assert "POSITIVE_STOCK_WITHOUT_COUNT_EVIDENCE" in codes


def test_unsupported_claim_prevents_publication() -> None:
    payload = candidate_payload()
    payload["approved_claims"][0]["evidence_id"] = "does-not-exist"
    assert "UNSUPPORTED_CLAIM" in error_codes(payload)


def test_publication_cannot_bypass_sellable_lifecycle() -> None:
    payload = candidate_payload()
    payload["lifecycle_status"] = "approved"
    assert "PUBLIC_REQUIRES_SELLABLE" in error_codes(payload)


def test_authoritative_money_rejects_float_minor_units() -> None:
    payload = candidate_payload()
    payload["price"]["gross_minor_units"] = 59.0
    try:
        CandidateProduct.model_validate(payload)
    except ValidationError as exc:
        assert "gross_minor_units" in str(exc)
    else:
        raise AssertionError("float minor units must not validate")


def test_non_sellable_candidate_with_zero_stock_and_no_claims_is_valid() -> None:
    payload = {
        "schema_version": "0.1.0",
        "synthetic_fixture": True,
        "product_id": "VS-TEE-001",
        "lifecycle_status": "candidate",
        "publication_status": "preview",
        "product_name": "Synthetic candidate; not approved for sale",
        "category_code": "t-shirt",
        "target_market_codes": ["DE"],
        "variants": [
            {"sku": "VS-TEE-001-BLK-S", "size_code": "S", "color_name": "Black", "opening_stock": 0},
            {"sku": "VS-TEE-001-BLK-M", "size_code": "M", "color_name": "Black", "opening_stock": 0},
            {"sku": "VS-TEE-001-BLK-L", "size_code": "L", "color_name": "Black", "opening_stock": 0},
        ],
        "locale_codes": ["de-DE", "en-DE"],
        "approved_claims": [],
        "evidence": [],
        "field_evidence": {},
        "assets": [],
    }
    candidate = CandidateProduct.model_validate(payload)
    assert validate_candidate_collection([candidate], now=NOW) == []
    assert candidate.sellable_quantity == 0
