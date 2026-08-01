# Launch-Blocker Audit — executed evidence

- Artifact ID: SB-EV-G1-007
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `docs/side-b/SIDE_B_LAUNCH_BLOCKER_AUDIT.md` (SB-AR-B19-001); controller M1 task F
- Acceptance criteria: every claim in the audit that is testable is backed by an executed command with its exact output and exit code; every claim that is *not* tested is labelled as untested.
- Validation procedure/result: commands below executed in this working tree; results preserved.
- Evidence path: this file
- Readiness status: AUTOMATED-TESTED (admin defaults) / SELF-VALIDATED (source-review findings)
- Downstream consumer: controller; Side A risk owner
- Remaining risks/next action: XSS, non-transactional inventory and secrets handling are recorded as **open** with no test claiming otherwise.

## 1. Unsafe admin defaults — tested

### 1.1 Test suite

```text
WORKING DIRECTORY: ...\platform\poc\backend
COMMAND: python -m pytest -q -p no:cacheprovider tests/test_admin_security.py -rA

PASSED tests/test_admin_security.py::test_admin_write_without_token_is_rejected
PASSED tests/test_admin_security.py::test_admin_write_with_wrong_token_is_rejected
PASSED tests/test_admin_security.py::test_admin_write_with_shipped_placeholder_token_is_rejected
PASSED tests/test_admin_security.py::test_rejected_admin_write_does_not_persist
PASSED tests/test_admin_security.py::test_placeholder_token_disables_admin_api_in_every_environment[development]
PASSED tests/test_admin_security.py::test_placeholder_token_disables_admin_api_in_every_environment[staging]
PASSED tests/test_admin_security.py::test_placeholder_token_disables_admin_api_in_every_environment[production]
PASSED tests/test_admin_security.py::test_admin_token_default_detection
PASSED tests/test_admin_security.py::test_config_module_imports_cleanly
EXIT_CODE: 0
```

(These 9 results are part of the 53-test green run preserved in `SB-EV-G1-002_green_pytest_transcript.txt`.)

### 1.2 Runtime proof in a container

```text
COMMAND: docker run --rm -e APP_ENV=production -e ADMIN_API_TOKEN=change-me -p 18200:8000 -d --name sb-g1-m1-unsafe-probe sb-g1-m1-final-api
92ba575fdad26708e7e48a36f2e6c350112559fd066a9543182974e71a75a946
EXIT_CODE: 0

--- POST http://127.0.0.1:18200/api/v1/admin/products   header X-Admin-Token: change-me
HTTP_STATUS: 503

COMMAND: docker stop sb-g1-m1-unsafe-probe
sb-g1-m1-unsafe-probe
EXIT_CODE: 0
```

Against the normally configured stack (a real, non-placeholder token in `.env`):

```text
--- POST http://127.0.0.1:18100/api/v1/admin/products   header X-Admin-Token: change-me
HTTP_STATUS: 401
--- POST http://127.0.0.1:18100/api/v1/admin/products   no header
HTTP_STATUS: 401
```

### 1.3 The exploit that actually occurred

Before the guard existed, this sequence succeeded and rewrote the preserved fixture:

```text
--- POST /api/v1/admin/products   header X-Admin-Token: change-me
HTTP_STATUS: 200
sha256(backend/data/products.json) 536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
                                -> 39e5651cbdc937509edf870d2b2d8a2032c0e52b8d362db56d5105062df339ce
```

Restored and verified:

```text
COMMAND: sha256sum backend/data/products.json
536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
RESTORE: OK (byte-identical to original fixture)
EXIT_CODE: 0
```

### 1.4 Regression guard

```text
COMMAND: python -m pytest -q -p no:cacheprovider     (full suite, 53 tests)
EXIT_CODE: 0
COMMAND: sha256sum backend/data/products.json backend/data/candidate_products.json
536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d *backend/data/products.json
7f052e4c8d75302695faa23b44efa7ed4e2f28ad64aaff9746d0109d8dab8323 *backend/data/candidate_products.json
EXIT_CODE: 0
```

`backend/tests/conftest.py` raises `AssertionError` and restores the file if any future test changes it.

## 2. Stored XSS — recorded, NOT tested, NOT fixed

No test asserts that the storefront is safe, because it is not. The finding is a source-review result over `platform/poc/storefront/app.js` (`renderProducts` and the stylist result handler both assign to `innerHTML` with unescaped interpolation of stored catalog fields).

Confirmed by inspection only:

```text
storefront/app.js:  container.innerHTML = items.map(product => `... <h3>${product.name}</h3> <p>${product.description}</p> ...`)
storefront/app.js:  result.innerHTML = `<strong>${recommendation.rationale}</strong>...`
backend/app/schemas.py:  image_url: HttpUrl | str      <- accepts any string, including javascript:
```

No security headers are configured. Verified by inspection of the storefront build, not by a runtime header capture:

```text
COMMAND: cat storefront/Dockerfile
FROM nginx:1.27-alpine
COPY . /usr/share/nginx/html
EXIT_CODE: 0

COMMAND: grep -rn "Content-Security-Policy|add_header" storefront/
(no security headers configured in storefront/)
EXIT_CODE: 1
```

There is no nginx configuration file in the image build and `nginx:1.27-alpine` sets no `Content-Security-Policy`, `X-Content-Type-Options` or `Referrer-Policy` by default. A runtime header capture was **not** performed this cycle.

**Status: OPEN.** See SB-AR-B19-001 for the remediation specification.

## 3. Non-transactional inventory — recorded, NOT tested, NOT fixed

Source-review result over `platform/poc/backend/app/catalog.py`:

```text
self._lock = threading.Lock()          <- process-local; no protection across workers/replicas/hosts
self.path.write_text(...)              <- non-atomic whole-file rewrite; no temp+rename, no backup
```

and over `main.py`: the quote endpoint reads `variant.stock` and reserves nothing; no order entity, no inventory ledger, no adjustment audit exists anywhere in the codebase.

No concurrency test was written, because a passing concurrency test would be misleading against a design that cannot satisfy the requirement. **Status: OPEN**, remediation specified in SB-AR-B19-001.

## 4. Secrets handling — recorded, NOT fixed

```text
COMMAND: ls platform/poc/.env
platform/poc/.env          <- present in the distributed pack
CONTENT: ADMIN_API_TOKEN=local-baseline-only-not-for-sharing
```

`.gitignore` lists `.env`, but the pack is not a Git working tree, so the file ships with the archive. `docker-compose.yml` mounts it via `env_file`, so the value is visible to `docker inspect`. `OPENAI_API_KEY` is declared but never read by any code path.

**Status: OPEN.** Not removed in this cycle because deleting the local `.env` would break the reproducible local run that this cycle's Docker evidence depends on. The remediation (ship only `.env.example`, generate the token at setup, move real secrets to a managed store) is a B18 action requiring the named account owner.

## 5. Runtime divergence — recorded and partially mitigated

```text
COMMAND: python --version
Python 3.14.4
EXIT_CODE: 0
```

versus `backend/Dockerfile` → `FROM python:3.12-slim`, and `SIDE_B_G0_EXECPLAN.md` §9 → "Python 3.12 isolated setup".

Mitigation applied: `.github/workflows/ci.yml` now runs a 3.12/3.13/3.14 matrix plus `compileall`, both validators, the fail-closed activation assertion, the mutation harness and fixture-checksum verification. The CI workflow itself has **not** been executed — there is no CI runner in this environment. **CI status: UNVERIFIED.**

## 6. Stale cross-checkout bytecode — fixed and verified

```text
COMMAND: find . -name "*.pyc" -o -name "__pycache__" -o -name ".pytest_cache"
(no output)
EXIT_CODE: 0
```

All subsequent runs used `PYTHONDONTWRITEBYTECODE=1` and `pytest -p no:cacheprovider`. Full finding in `evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md` §4.
