from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BusinessLifecycle(StrEnum):
    FIXTURE = "fixture"
    CANDIDATE = "candidate"
    SAMPLE = "sample"
    APPROVED = "approved"
    SELLABLE = "sellable"
    RETIRED = "retired"


class PublicationStatus(StrEnum):
    HIDDEN = "hidden"
    PREVIEW = "preview"
    PUBLIC = "public"


class FibreComponent(BaseModel):
    fibre_name: str = Field(min_length=2, max_length=80)
    percentage: int = Field(strict=True, ge=1, le=100)


class Claim(BaseModel):
    claim_id: str = Field(min_length=3, max_length=80)
    text: str = Field(min_length=2, max_length=240)
    scope: str = Field(min_length=2, max_length=80)
    evidence_id: str = Field(min_length=3, max_length=120)
    approved_by: str = Field(min_length=2, max_length=120)
    expires_at: datetime


class Dimensions(BaseModel):
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class CandidateVariant(BaseModel):
    sku: str = Field(min_length=3, max_length=64)
    size_code: str = Field(min_length=1, max_length=32)
    color_name: str = Field(min_length=1, max_length=80)
    barcode: str | None = Field(default=None, max_length=120)
    weight_g: int | None = Field(default=None, strict=True, gt=0)
    item_dimensions_cm: Dimensions | None = None
    opening_stock: int = Field(default=0, strict=True, ge=0)
    count_evidence_id: str | None = Field(default=None, max_length=120)


class PriceRecord(BaseModel):
    gross_minor_units: int = Field(strict=True, gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    tax_class: str = Field(min_length=1, max_length=80)
    valid_from: datetime
    valid_to: datetime | None = None
    approved: bool = False
    approval_evidence_id: str | None = Field(default=None, max_length=120)


class BatchRecord(BaseModel):
    batch_id: str = Field(min_length=3, max_length=120)
    qc_release_status: Literal["quarantined", "released", "rejected"] = "quarantined"
    qc_evidence_id: str | None = Field(default=None, max_length=120)


class AssetRecord(BaseModel):
    asset_id: str = Field(min_length=3, max_length=120)
    alt_text: str = Field(min_length=2, max_length=400)
    rights_evidence_id: str | None = Field(default=None, max_length=120)
    approved: bool = False


class EvidenceRecord(BaseModel):
    evidence_id: str = Field(min_length=3, max_length=120)
    status: Literal[
        "DRAFT",
        "SELF-VALIDATED",
        "AUTOMATED-TESTED",
        "HUMAN-VERIFIED",
        "EXTERNALLY-VERIFIED",
        "BLOCKED",
        "REJECTED",
    ]
    scope: list[str] = Field(min_length=1)
    issuer: str = Field(min_length=2, max_length=160)
    approved_by: str = Field(min_length=2, max_length=120)
    issued_at: datetime
    expires_at: datetime | None = None
    synthetic_fixture: bool = True


class ActivationError(BaseModel):
    code: str
    field: str
    message: str


class CandidateProduct(BaseModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    synthetic_fixture: bool = True
    product_id: str = Field(min_length=3, max_length=64)
    style_code: str | None = Field(default=None, max_length=64)
    lifecycle_status: BusinessLifecycle = BusinessLifecycle.FIXTURE
    publication_status: PublicationStatus = PublicationStatus.HIDDEN
    product_name: str = Field(min_length=2, max_length=120)
    category_code: str = Field(min_length=2, max_length=80)
    target_market_codes: list[str] = Field(default_factory=list)
    fibre_composition: list[FibreComponent] = Field(default_factory=list)
    country_of_origin: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    care_instructions: list[str] = Field(default_factory=list)
    approved_claims: list[Claim] = Field(default_factory=list)
    fit_summary: str | None = Field(default=None, max_length=500)
    measurement_set_id: str | None = Field(default=None, max_length=120)
    variants: list[CandidateVariant] = Field(min_length=1)
    price: PriceRecord | None = None
    locale_codes: list[str] = Field(default_factory=list)
    merchant_identity_id: str | None = Field(default=None, max_length=120)
    importer_responsible_operator_id: str | None = Field(default=None, max_length=120)
    withdrawal_return_policy_id: str | None = Field(default=None, max_length=120)
    delivery_promise_id: str | None = Field(default=None, max_length=120)
    batch: BatchRecord | None = None
    assets: list[AssetRecord] = Field(default_factory=list)
    warehouse_location_id: str | None = Field(default=None, max_length=120)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    field_evidence: dict[str, str] = Field(default_factory=dict)
    approved_by: str | None = Field(default=None, max_length=120)

    @field_validator("target_market_codes")
    @classmethod
    def validate_market_codes(cls, values: list[str]) -> list[str]:
        for value in values:
            if len(value) != 2 or value != value.upper():
                raise ValueError("market codes must be ISO-style uppercase alpha-2 values")
        return values

    @field_validator("locale_codes")
    @classmethod
    def validate_locale_codes(cls, values: list[str]) -> list[str]:
        for value in values:
            if len(value) < 2 or len(value) > 35 or " " in value:
                raise ValueError("locale codes must be BCP-47-style tokens")
        return values

    @property
    def sellable_quantity(self) -> int:
        if self.lifecycle_status is not BusinessLifecycle.SELLABLE:
            return 0
        return sum(item.opening_stock for item in self.variants)


ACTIVATION_REQUIRED_FIELDS: tuple[str, ...] = (
    "style_code",
    "fibre_composition",
    "country_of_origin",
    "care_instructions",
    "measurement_set_id",
    "price",
    "locale_codes",
    "merchant_identity_id",
    "importer_responsible_operator_id",
    "withdrawal_return_policy_id",
    "delivery_promise_id",
    "batch",
    "assets",
    "warehouse_location_id",
    "approved_by",
)

FIELD_EVIDENCE_SCOPES: dict[str, str] = {
    "fibre_composition": "fibre_composition",
    "country_of_origin": "country_of_origin",
    "care_instructions": "care_instructions",
    "measurement_set_id": "measurements",
    "importer_responsible_operator_id": "responsible_operator",
    "withdrawal_return_policy_id": "policy",
    "delivery_promise_id": "policy",
    "target_market_codes": "market",
}


def _error(code: str, field: str, message: str) -> ActivationError:
    return ActivationError(code=code, field=field, message=message)


def _is_missing(value: object) -> bool:
    return value is None or value == "" or value == []


def _evidence_errors(
    evidence_id: str | None,
    required_scope: str,
    evidence_by_id: dict[str, EvidenceRecord],
    now: datetime,
    field: str,
) -> list[ActivationError]:
    if not evidence_id or evidence_id not in evidence_by_id:
        return [_error("MISSING_EVIDENCE", field, f"current {required_scope} evidence is required")]
    evidence = evidence_by_id[evidence_id]
    errors: list[ActivationError] = []
    if evidence.expires_at is not None and evidence.expires_at <= now:
        errors.append(_error("EXPIRED_EVIDENCE", field, f"evidence {evidence_id} is expired"))
    if evidence.status not in {"HUMAN-VERIFIED", "EXTERNALLY-VERIFIED"}:
        errors.append(_error("UNVERIFIED_EVIDENCE", field, f"evidence {evidence_id} is not human/external verified"))
    if evidence.synthetic_fixture:
        errors.append(_error("SYNTHETIC_EVIDENCE", field, f"synthetic evidence {evidence_id} cannot activate sellable/public state"))
    if required_scope not in evidence.scope:
        errors.append(_error("EVIDENCE_SCOPE_MISMATCH", field, f"evidence {evidence_id} does not cover {required_scope}"))
    return errors


def validate_candidate_activation(
    candidate: CandidateProduct,
    *,
    now: datetime | None = None,
) -> list[ActivationError]:
    now = now or datetime.now(UTC)
    errors: list[ActivationError] = []
    activation_requested = (
        candidate.lifecycle_status is BusinessLifecycle.SELLABLE
        or candidate.publication_status is PublicationStatus.PUBLIC
    )

    if candidate.publication_status is PublicationStatus.PUBLIC and candidate.lifecycle_status is not BusinessLifecycle.SELLABLE:
        errors.append(_error("PUBLIC_REQUIRES_SELLABLE", "publication_status", "public publication requires business lifecycle sellable"))

    if not activation_requested:
        return errors

    if candidate.synthetic_fixture:
        errors.append(_error("SYNTHETIC_CANNOT_ACTIVATE", "synthetic_fixture", "synthetic fixtures cannot become sellable or public"))

    for field_name in ACTIVATION_REQUIRED_FIELDS:
        if _is_missing(getattr(candidate, field_name)):
            errors.append(_error("MISSING_REQUIRED_FIELD", field_name, f"{field_name} is required for activation"))

    if not candidate.importer_responsible_operator_id:
        errors.append(_error("MISSING_OPERATOR", "importer_responsible_operator_id", "a verified responsible operator is required"))

    evidence_counts = Counter(item.evidence_id for item in candidate.evidence)
    for evidence_id, count in evidence_counts.items():
        if count > 1:
            errors.append(_error("DUPLICATE_EVIDENCE_ID", "evidence", f"duplicate evidence ID: {evidence_id}"))
    evidence_by_id = {item.evidence_id: item for item in candidate.evidence}

    for field_name, required_scope in FIELD_EVIDENCE_SCOPES.items():
        errors.extend(
            _evidence_errors(
                candidate.field_evidence.get(field_name),
                required_scope,
                evidence_by_id,
                now,
                field_name,
            )
        )

    if candidate.fibre_composition and sum(item.percentage for item in candidate.fibre_composition) != 100:
        errors.append(_error("INVALID_FIBRE_TOTAL", "fibre_composition", "fibre percentages must total 100"))

    for index, claim in enumerate(candidate.approved_claims):
        claim_errors = _evidence_errors(claim.evidence_id, "claim", evidence_by_id, now, f"approved_claims[{index}]")
        if claim.expires_at <= now or claim_errors:
            errors.append(_error("UNSUPPORTED_CLAIM", f"approved_claims[{index}]", "claim lacks current scoped approval evidence"))
        errors.extend(claim_errors)

    if candidate.batch is None or candidate.batch.qc_release_status != "released":
        errors.append(_error("BATCH_NOT_RELEASED", "batch.qc_release_status", "only a released batch can activate"))

    if candidate.price is None or not candidate.price.approved:
        errors.append(_error("UNAPPROVED_PRICE", "price", "an approved price is required"))
    elif candidate.price:
        if candidate.price.valid_from > now or (candidate.price.valid_to is not None and candidate.price.valid_to <= now):
            errors.append(_error("PRICE_NOT_CURRENT", "price.valid_from_to", "price validity does not include validation time"))
        errors.extend(
            _evidence_errors(candidate.price.approval_evidence_id, "price", evidence_by_id, now, "price.approval_evidence_id")
        )

    positive_stock = [item for item in candidate.variants if item.opening_stock > 0]
    if positive_stock:
        if candidate.batch is None or not candidate.batch.qc_evidence_id:
            errors.append(_error("POSITIVE_STOCK_WITHOUT_QC_EVIDENCE", "batch.qc_evidence_id", "positive stock requires QC evidence"))
        else:
            errors.extend(
                _evidence_errors(candidate.batch.qc_evidence_id, "qc_release", evidence_by_id, now, "batch.qc_evidence_id")
            )
        if not candidate.warehouse_location_id:
            errors.append(_error("POSITIVE_STOCK_WITHOUT_LOCATION", "warehouse_location_id", "positive stock requires an accepted location"))
        for variant in positive_stock:
            if not variant.count_evidence_id:
                errors.append(_error("POSITIVE_STOCK_WITHOUT_COUNT_EVIDENCE", f"variants[{variant.sku}].count_evidence_id", "positive stock requires count evidence"))
            else:
                errors.extend(
                    _evidence_errors(variant.count_evidence_id, "inventory_count", evidence_by_id, now, f"variants[{variant.sku}].count_evidence_id")
                )

    for index, asset in enumerate(candidate.assets):
        if not asset.approved:
            errors.append(_error("UNAPPROVED_ASSET", f"assets[{index}]", "public assets require approval"))
        errors.extend(
            _evidence_errors(asset.rights_evidence_id, "asset_rights", evidence_by_id, now, f"assets[{index}].rights_evidence_id")
        )

    if errors:
        errors.append(_error("ACTIVATION_BLOCKED", "lifecycle_status", "sellable/public activation is blocked"))
    return errors


def validate_candidate_collection(
    candidates: list[CandidateProduct],
    *,
    now: datetime | None = None,
) -> list[ActivationError]:
    errors: list[ActivationError] = []
    product_counts = Counter(item.product_id for item in candidates)
    for product_id, count in product_counts.items():
        if count > 1:
            errors.append(_error("DUPLICATE_PRODUCT_ID", "product_id", f"duplicate product ID: {product_id}"))

    skus = [variant.sku for candidate in candidates for variant in candidate.variants]
    for sku, count in Counter(skus).items():
        if count > 1:
            errors.append(_error("DUPLICATE_SKU", "variants.sku", f"duplicate SKU: {sku}"))

    for candidate in candidates:
        errors.extend(validate_candidate_activation(candidate, now=now))
    return errors
