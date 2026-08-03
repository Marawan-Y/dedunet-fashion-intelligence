# Baseline After Restructure

| Control | Value |
|---|---|
| Artifact ID | EV-R0-002 |
| Version | 1.0 |
| Captured | 2026-08-03 |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| Compared against | `BASELINE_BEFORE_RESTRUCTURE.md` (EV-R0-001) |
| Status | AUTOMATED-TESTED |

Counts are compared **exactly**. A reduced test count is a failure even when nothing reports as
failed, because it means tests stopped being discovered.

## 15-point gate

| # | Check | Before | After | Verdict |
|---|---|---|---|---|
| 1 | Backend test suite | 83 passed | **83 passed** | PASS — exact |
| 2 | Mutation guards | 19 run / 19 detected / 0 survived | **19 / 19 / 0** | PASS — exact |
| 3 | Product validator | 3 products, 9 unique SKUs, exit 0 | identical, exit 0 | PASS |
| 4 | Candidate validator | exit 0 | exit 0 | PASS |
| 5 | Sellable fail-closed | exit 1 | exit 1, reason `ACTIVATION_BLOCKED` | PASS |
| 6 | `products.json` | `536f91ab…bce8d` | `536f91ab…bce8d` | PASS — byte-identical |
| 6 | `candidate_products.json` | `7f052e4c…ab8323` | `7f052e4c…ab8323` | PASS — byte-identical |
| 7 | Docker build + startup | healthy | built from new paths, **healthy** | PASS |
| 8 | API `/ready` | 200, `database: ok` | 200, `database: ok` | PASS |
| 9 | Storefront startup | 200 | 200 (container and local) | PASS |
| 10 | Admin portal startup | 200 | 200, own stylesheet 200 | PASS |
| 11 | OpenAPI export | 29 paths | **29 paths** at new contract home | PASS |
| 12 | Secrets / runtime tracked | 0 | 0; `.env` in history: 0 | PASS |
| 13 | Stale paths / duplicate trees | n/a | 0 live stale, 0 duplicate trees | PASS |
| 14 | Side A immutable manifest | 54/54 | **54/54** | PASS |
| 15 | Git status | clean | 66 renames + reference updates, nothing stray | PASS |

## Independent completeness check

Re-running the classifier over the **current** tree reports:

```text
tracked files          : 248
moves still outstanding: 0
RESULT: PASS - migration complete
```

This is a genuine second check, not a restatement: the same rules that produced the plan were
re-applied to the moved tree. Any file still mapping to a different target would surface here.

## Exact commands

```bash
cd services/commerce-api && PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider
python -B scripts/validation/validate_product_data.py
python -B scripts/validation/validate_candidate_data.py
python -B scripts/validation/validate_candidate_data.py --assess-sellable   # must be non-zero
python -B scripts/validation/mutation_guard_check.py
python -B -m compileall -q services/commerce-api scripts
cd services/commerce-api && python -B manage.py export-openapi
docker compose config && docker compose up --build --detach
curl -s localhost:18000/ready
curl -s -o /dev/null -w '%{http_code}' localhost:13000/storefront/
curl -s -o /dev/null -w '%{http_code}' localhost:13000/admin/
```

## Three defects the restructure exposed

Each was a latent coupling that only surfaced once paths moved. All three are fixed and verified;
each is a **functional correction isolated from the moves**, as §13 requires.

**1. Validators crashed, and the crash masqueraded as a pass.**
`ModuleNotFoundError: No module named 'app'` — both validators hard-coded `ROOT/"backend"`. The
dangerous part is check 5: `--assess-sellable` still exited 1, so a status-code-only check would
have recorded PASS while the validator was in fact crashing before evaluating anything. Caught by
asserting the *reason* (`ACTIVATION_BLOCKED`), not just the exit code. Fixed to resolve
`services/commerce-api` from the repository root.

**2. The API container died on startup.**
`manage.py` resolved the contract path at import time with `BACKEND_DIR.parents[1]`. In the image
the file lives at `/app/manage.py`, so there is no repository root above it and `IndexError` took
down every command — including the `seed` the entrypoint runs. Fixed by resolving lazily inside
`export-openapi`, walking upward for a real `packages/contracts/openapi/` directory rather than
assuming a fixed depth, so it survives the service moving again.

**3. Local and container URLs genuinely diverge.**
Served from the repository root the clients are at `/apps/web/` and `/apps/admin/`; nginx maps
them to `/storefront/` and `/admin/`. Both documented, all paths verified 200.

## Deliberate non-changes

**32 files still reference `platform/poc` and were left untouched.** 25 are historical evidence
(`SB-EV-BOOT-*`, past status reports, completed handoffs) and 7 are the R0 planning documents,
which describe the pre-move state by design.

Rewriting them would falsify the record. An evidence file asserting that a command ran at a path
which did not exist when it ran is worse than a stale path. Every **live** operational document —
`AGENTS.md`, `README.md`, `README_CODEX_SETUP.md`, the Codex agent definition, the Side B start
prompt, the operations runbooks — is at **0** stale references.

## Not verified

**CI has still never executed.** No runner exists in this environment. Its paths were updated and
reviewed by hand, but a green pipeline is not evidenced and must not be claimed. This is unchanged
from before the restructure and remains recorded in `docs/KNOWN_LIMITATIONS.md`.

**Mobile remains BLOCKED.** Moved to `apps/mobile/` but still never installed, built or
type-checked. The peer-dependency conflict is untouched — it is Workstream F, not R0.
