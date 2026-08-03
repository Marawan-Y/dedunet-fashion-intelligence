# Baseline Before Restructure

| Control | Value |
|---|---|
| Artifact ID | EV-R0-001 |
| Version | 1.0 |
| Captured | 2026-08-03 |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| Base commit | `9b7e256` |
| Purpose | Prove functional parity after restructuring; without this, "nothing broke" is an opinion |
| Status | AUTOMATED-TESTED |

All commands were executed in
`C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc`
with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`, before any file was moved.

## Results

| # | Check | Command | Result | Exit |
|---|---|---|---|---|
| B1 | Backend suite | `python -B -m pytest -q -p no:cacheprovider` | **83 passed**, 1 warning, 25.22s | 0 |
| B2 | Byte-compile | `python -B -m compileall -q backend scripts` | silent | 0 |
| B3 | Product validator | `python -B scripts/validate_product_data.py` | `Validated 3 products and 9 unique SKUs` | 0 |
| B4 | Candidate validator | `python -B scripts/validate_candidate_data.py` | valid | 0 |
| B5 | Sellable fail-closed | `... --assess-sellable` | blocked | **1 (required)** |
| B6 | Mutation harness | `python -B scripts/mutation_guard_check.py` | **19 run / 19 detected / 0 survived** | 0 |
| B7 | Docker stack | `docker compose ps` | api healthy (32h), storefront up | — |

## Fixture checksums

```text
536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d  backend/data/products.json
7f052e4c8d75302695faa23b44efa7ed4e2f28ad64aaff9746d0109d8dab8323  backend/data/candidate_products.json
```

## Repository state at capture

| Metric | Value |
|---|---|
| Tracked files in active project | 177 |
| Untracked | `platform/poc.zip` only |
| Modified tracked files | none — working tree otherwise clean |
| Markdown / Python / CSV files | 80 / 35 / 26 |
| Runtime artefacts on disk (not tracked) | 11 `__pycache__` dirs, 3 SQLite files, 1 `.pytest_cache` |
| Secret-bearing files | `platform/poc/.env` — present on disk, correctly git-ignored, absent from history |
| Legacy MERET references | 19 files (12 live source, 7 runtime artefacts) |

## Parity criteria for after the restructure

The post-restructure baseline must reproduce **all** of the following, or the gate fails:

1. 83 tests pass, zero failures. A reduced count means tests stopped being discovered.
2. Mutation harness: 19 run, 19 detected, 0 survived.
3. Product validator: 3 products, 9 unique SKUs, exit 0.
4. `--assess-sellable` exits **non-zero**. A zero exit is a defect, not an improvement.
5. Both fixture checksums byte-identical to the values above.
6. Docker stack builds and reaches healthy.
7. `/ready` returns 200 with `database: ok`.
8. OpenAPI export produces 29 paths with no drift.

Counts must be compared exactly. "Tests still pass" is not evidence when the number of collected
tests has silently dropped.
