from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.candidate_activation import (  # noqa: E402
    BusinessLifecycle,
    CandidateProduct,
    PublicationStatus,
    validate_candidate_collection,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate evidence-gated candidate product data")
    parser.add_argument(
        "--path",
        type=Path,
        default=ROOT / "backend" / "data" / "candidate_products.json",
    )
    parser.add_argument(
        "--assess-sellable",
        action="store_true",
        help="Assess a sellable/public transition without modifying the source fixture",
    )
    args = parser.parse_args()

    payload = json.loads(args.path.read_text(encoding="utf-8"))
    candidates = [CandidateProduct.model_validate(item) for item in payload]
    current_errors = validate_candidate_collection(candidates)
    assessed = candidates
    if args.assess_sellable:
        assessed = [
            item.model_copy(
                update={
                    "lifecycle_status": BusinessLifecycle.SELLABLE,
                    "publication_status": PublicationStatus.PUBLIC,
                }
            )
            for item in candidates
        ]

    errors = validate_candidate_collection(assessed)
    result = {
        "schema_version": "0.1.0",
        "candidate_count": len(candidates),
        "synthetic_fixture_count": sum(item.synthetic_fixture for item in candidates),
        "assessment": "sellable_public" if args.assess_sellable else "current_state",
        "current_state_valid": not current_errors,
        "sellable_public_eligible": not errors if args.assess_sellable else False,
        "errors": [item.model_dump(mode="json") for item in errors],
    }
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
