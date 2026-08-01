# Side B Backend Check Evidence

- Artifact ID: SB-EV-BOOT-002
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `platform/poc/backend/`, `platform/poc/scripts/validate_product_data.py`, SB-EV-BOOT-001
- Acceptance criteria: configured tests, validator, and Python syntax compilation execute; exact results and warnings remain visible.
- Validation procedure/result: commands executed locally on 2026-08-01; all three post-install checks exited 0.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-002_backend_checks.md`
- Readiness status: AUTOMATED-TESTED
- Downstream consumer: SB-AR-B2-001; G0 controller review
- Remaining risks/next action: add coverage for admin auth/upsert, product detail, successful/out-of-stock quote, duplicate IDs/slugs, out-of-stock recommendations, and malformed catalog/runtime recovery.

## Syntax compilation

Working directory: `platform/poc`

```text
COMMAND: python -m compileall -q backend scripts
EXIT_CODE: 0
```

## Configured backend suite

Working directory: `platform/poc/backend`

```text
COMMAND: python -m pytest -q
....                                                                     [100%]
============================== warnings summary ===============================
..\..\..\..\..\..\AppData\Roaming\Python\Python314\site-packages\fastapi\testclient.py:1
  C:\Users\User\AppData\Roaming\Python\Python314\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
4 passed, 1 warning in 1.81s
EXIT_CODE: 0
```

## Product data validator

Working directory: `platform/poc`

```text
COMMAND: python scripts/validate_product_data.py
Validated 3 products and 9 unique SKUs
EXIT_CODE: 0
```

Interpretation: these checks prove only the covered local code paths and schema/unique-SKU checks over sample JSON. They do not verify cotton/origin claims, actual stock, prices, customer data, production transactions, payment, tax, carrier, identity, security, or deployment readiness.
