# Repository Restructure Plan (Milestone R0)

| Control | Value |
|---|---|
| Artifact ID | ARCH-R0-004 |
| Version | 1.0 |
| Owner | Technical lead |
| Status | SELF-VALIDATED |
| Machine-readable companion | `REPOSITORY_PATH_MIGRATION_MAP.csv` (67 rows, generated) |
| Constraint | **Behaviour-preserving.** No feature work in the restructure commit |

## Scope

67 tracked files move. 175 stay. No file is created or deleted except `platform/poc/.gitignore`,
which is superseded by the root `.gitignore` restored during the Git-root normalisation.

**Explicitly excluded from this milestone** (§13): PostgreSQL, notifications, rate limiting,
staging, DEDUNET schemas or imports, mobile features, payment changes, business-rule changes, and
the MERET→DEDUNET rebrand.

## Moves

| From | To | Files |
|---|---|---|
| `platform/poc/backend/` | `services/commerce-api/` | 36 |
| `platform/poc/docs/` | `docs/operations/` | 8 |
| `platform/poc/storefront/` | `apps/web/` | 5 |
| `platform/poc/mobile/` | `apps/mobile/` | 4 |
| `platform/poc/scripts/` | `scripts/validation/` | 3 |
| `platform/poc/admin/` | `apps/admin/` | 3 |
| `platform/poc/docs/api/openapi.json` | `packages/contracts/openapi/` | 1 |
| `platform/poc/.github/workflows/ci.yml` | `.github/workflows/` | 1 |
| `platform/poc/{docker-compose.yml, Makefile, .env.example, .dockerignore, README.md}` | repository root | 5 |
| `platform/poc/KNOWN_LIMITATIONS.md` | `docs/` | 1 |

`platform/` is removed entirely once empty. **No duplicate active source tree remains** — moves
use `git mv`, which cannot leave a copy behind.

## Reference updates required

Each is a known breakage, not a guess; every one is listed in the audit with its failure mode.

| File | Change |
|---|---|
| `services/commerce-api/tests/conftest.py` | `DATA_DIR` — depth unchanged, verify |
| `services/commerce-api/manage.py` | `CONTRACT_PATH` → `packages/contracts/openapi/openapi.json` |
| `services/commerce-api/tests/test_frontend_security.py` | `POC_ROOT` → repo root; `storefront` → `apps/web`, `admin` → `apps/admin` |
| `scripts/validation/mutation_guard_check.py` | `BACKEND` → `services/commerce-api` |
| `docker-compose.yml` | `build: ./services/commerce-api`; web context and dockerfile path |
| `apps/web/Dockerfile` | `COPY apps/web`, `COPY apps/admin` |
| `.github/workflows/ci.yml` | `working-directory: services/commerce-api`; contract path |
| `apps/admin/index.html` | `../storefront/styles.css` → own stylesheet |
| `Makefile` | target paths |
| `README.md`, `docs/operations/*` | documented commands and the repository map |

### One functional correction, isolated

`apps/admin/index.html` currently loads `../storefront/styles.css`. After separation that
reference crosses an application boundary the target architecture forbids. The fix is to give
`apps/admin` its own copy of the stylesheet.

This is a **file addition, not a behaviour change** — the rendered result is byte-identical
because the copied content is identical. It is called out here because §13 requires any
functional correction needed to make the moved repository run to be isolated and explained.

## Sequence

1. Commit the six planning documents. *(this commit)*
2. `git mv` every path in the migration map, most-specific first.
3. Update every reference in the table above.
4. Remove the emptied `platform/` directory.
5. Run the full 15-point verification.
6. Commit the restructure as one behaviour-preserving change.
7. Produce `BASELINE_AFTER_RESTRUCTURE.md` and `RESTRUCTURE_COMPLETION_REPORT.md`.

## Acceptance criteria — exact values, not impressions

| # | Criterion | Required |
|---|---|---|
| 1 | Backend tests | **83 passed**, 0 failed |
| 2 | Mutation guards | **19 run, 19 detected, 0 survived** |
| 3 | Product validator | 3 products, 9 unique SKUs, exit 0 |
| 4 | Candidate validator | exit 0 |
| 5 | Sellable assessment | exit **non-zero** |
| 6 | `products.json` | `536f91ab…bce8d` |
| 6 | `candidate_products.json` | `7f052e4c…ab8323` |
| 7 | Docker | build + start, api healthy |
| 8 | `/ready` | 200, `database: ok` |
| 9 | Storefront | HTTP 200 |
| 10 | Admin portal | HTTP 200 |
| 11 | OpenAPI | 29 paths, no drift |
| 12 | Secrets / runtime artefacts | 0 tracked |
| 13 | Stale paths / duplicate trees | 0 |
| 14 | Side A manifest | **54/54** |
| 15 | `git status` | clean |

A reduced test count is a failure even if nothing reports as failed — it means tests stopped
being discovered. Counts are compared exactly.

## Risks

| Risk | Mitigation |
|---|---|
| Test discovery silently drops | Assert the exact count 83, not "no failures" |
| Fixture checksum gate trips | Fixtures stay with the service; checksums re-verified |
| Docker context breaks | `docker compose config` before build; full up + smoke |
| CI paths break undetected | No runner available — paths reviewed by hand and marked UNVERIFIED |
| Immutable evidence rewritten | `.gitattributes -text`; 54 checksums re-verified after moves |
| History lost | `git mv` preserves it; backup bundle exists |
