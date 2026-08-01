# G1 M1 Candidate Activation — GREEN Stage

- Artifact ID: SB-EV-G1-002
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: SB-EV-G1-001 (RED stage); `platform/poc/backend/app/candidate_activation.py`; `platform/poc/backend/tests/test_candidate_activation.py`; HO-A-B-001 v1.0 controller conditions
- Acceptance criteria: the negative regression tests recorded as failing in SB-EV-G1-001 now pass; the full backend suite is green; the exact command, full output and exit code are preserved; the run is attributable to this working tree.
- Validation procedure/result: full suite executed in this checkout with bytecode caching disabled; 53 passed, exit 0.
- Evidence path: `evidence/side-b/g1/SB-EV-G1-002_candidate_green.md` (+ attached transcript `SB-EV-G1-002_green_pytest_transcript.txt`)
- Readiness status: AUTOMATED-TESTED
- Downstream consumer: controller M1 review; SB-AR-B3-002; SB-AR-B3-003; SB-AR-B3-004
- Remaining risks/next action: passing tests prove the *gates*, not business truth. No approved product, price, batch, operator, policy or evidence record exists. Nothing here authorizes sale or publication.

## Attribution

```text
WORKING DIRECTORY: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend
PYTHONDONTWRITEBYTECODE=1        (no .pyc may be written)
pytest -p no:cacheprovider       (no pytest cache may be written or reused)
All __pycache__ / .pytest_cache directories were purged before this run — see
evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md §4.
```

## Environment

```text
COMMAND: python --version
Python 3.14.4
EXIT_CODE: 0

COMMAND: python -c "import sys;print(sys.executable)"
C:\Python314\python.exe
EXIT_CODE: 0
```

**Recorded divergence:** the Side B ExecPlan and the API Dockerfile target Python **3.12**; the workstation and every local result in this cycle are Python **3.14.4**. The container image (`python:3.12-slim`) is therefore the only 3.12 evidence in this cycle. CI has been extended to a 3.12/3.13/3.14 matrix so the divergence is proven rather than assumed (`platform/poc/.github/workflows/ci.yml`). Risk: SB-RISK-B2-001.

## RED → GREEN transition

SB-EV-G1-001 preserved this failure:

```text
COMMAND: python -m pytest -q tests/test_candidate_activation.py
E   ModuleNotFoundError: No module named 'app.candidate_activation'
EXIT_CODE: 2
```

The same command now succeeds in this tree:

```text
COMMAND: python -m pytest -q -p no:cacheprovider tests/test_candidate_activation.py
...............                                                          [100%]
15 passed, 1 warning
EXIT_CODE: 0
```

## Full backend suite

```text
WORKING DIRECTORY: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend
COMMAND: python -m pytest -q -p no:cacheprovider

.....................................................                    [100%]
============================== warnings summary ===============================
..\..\..\..\..\..\AppData\Roaming\Python\Python314\site-packages\fastapi\testclient.py:1
  C:\Users\User\AppData\Roaming\Python\Python314\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
53 passed, 1 warning in 2.21s
EXIT_CODE: 0
```

The per-test `PASSED` list is preserved verbatim in `SB-EV-G1-002_green_pytest_transcript.txt`.

The single warning is a third-party deprecation notice from `starlette.testclient` about `httpx`. It is not suppressed and is tracked as SB-RISK-B2-002.

## Required negative coverage — controller condition 6 on HO-A-B-001

| Required negative case | Test | Result |
|---|---|---|
| duplicate product IDs | `test_duplicate_product_ids_and_skus_are_rejected` | PASSED |
| duplicate SKUs (same product) | `test_duplicate_product_ids_and_skus_are_rejected` | PASSED |
| duplicate SKUs (across distinct products) | `test_duplicate_sku_across_distinct_products_is_rejected` | PASSED (added this cycle) |
| missing evidence | `test_missing_required_evidence_prevents_sellable_public_activation` | PASSED |
| expired evidence | `test_expired_evidence_prevents_activation` | PASSED |
| unreleased batch | `test_unreleased_batch_prevents_activation` | PASSED |
| missing operator | `test_missing_responsible_operator_prevents_activation` | PASSED |
| unapproved price | `test_unapproved_price_prevents_activation` | PASSED |
| unauthorized positive stock | `test_positive_stock_requires_qc_location_and_count_evidence` | PASSED |
| unsupported claim publication | `test_unsupported_claim_prevents_publication` | PASSED |
| expired claim publication | `test_expired_claim_prevents_publication` | PASSED (added this cycle) |
| synthetic fixture activation | `test_synthetic_fixture_cannot_activate` | PASSED (added this cycle) |
| publication bypassing lifecycle | `test_publication_cannot_bypass_sellable_lifecycle` | PASSED |
| float authoritative money | `test_authoritative_money_rejects_float_minor_units` | PASSED |

Whether each of these tests *actually guards* its rule — rather than passing for an unrelated reason — is proven separately by mutation testing in SB-EV-G1-003.

## Validators

```text
WORKING DIRECTORY: C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc

COMMAND: python scripts/validate_candidate_data.py
{
  "schema_version": "0.1.0",
  "candidate_count": 1,
  "synthetic_fixture_count": 1,
  "assessment": "current_state",
  "current_state_valid": true,
  "sellable_public_eligible": false,
  "errors": []
}
EXIT_CODE: 0
```

```text
COMMAND: python scripts/validate_candidate_data.py --assess-sellable
{
  "schema_version": "0.1.0",
  "candidate_count": 1,
  "synthetic_fixture_count": 1,
  "assessment": "sellable_public",
  "current_state_valid": true,
  "sellable_public_eligible": false,
  "errors": [ 27 activation errors — SYNTHETIC_CANNOT_ACTIVATE, 14 x MISSING_REQUIRED_FIELD,
              MISSING_OPERATOR, 8 x MISSING_EVIDENCE, BATCH_NOT_RELEASED, UNAPPROVED_PRICE,
              ACTIVATION_BLOCKED ]
}
EXIT_CODE: 1
```

Exit code 1 here is the **correct fail-closed result**, not a defect: the synthetic candidate must never be reported eligible for sellable/public activation. CI asserts that this command exits non-zero. The full 27-error payload is reproduced in `SB-EV-G1-005_attributed_baseline_rerun_v2.md` §3.

## Fixture preservation

```text
COMMAND: sha256sum backend/data/products.json backend/data/candidate_products.json
536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d *backend/data/products.json
7f052e4c8d75302695faa23b44efa7ed4e2f28ad64aaff9746d0109d8dab8323 *backend/data/candidate_products.json
EXIT_CODE: 0
```

Both match the pre-cycle originals. See EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md §5 for the one intermediate mutation that occurred, how it was detected, and the two controls that now prevent it.

## Scope limitation

This is a local, non-public proof of concept running on synthetic fixtures. It is **not** production-ready. No payment, tax, customs, identity, carrier, database transaction, monitoring or legal control is implemented or claimed.
