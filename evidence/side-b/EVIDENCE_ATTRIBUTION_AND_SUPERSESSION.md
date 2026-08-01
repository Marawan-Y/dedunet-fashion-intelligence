# Side B Evidence Attribution and Supersession Register

- Artifact ID: SB-EV-ATTR-001
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `evidence/side-b/bootstrap/SB-EV-BOOT-001..005`, `evidence/side-b/g1/SB-EV-G1-001_regression_red.md`, controller M1 instruction
- Acceptance criteria: every prior Side B evidence artifact whose attribution to this working tree is uncertain is named, the exact discrepancy is quoted, the mechanism is proven, the superseding artifact is identified, and no prior file is deleted or silently rewritten.
- Validation procedure/result: filesystem inspection, SHA-256 comparison against the other checkout, and bytecode header inspection; findings reproduced below with exact commands.
- Evidence path: this file
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller integrity review; Side B G1 evidence chain
- Remaining risks/next action: the superseded bootstrap records remain on disk unmodified; the controller decides whether to retire or re-run them.

## 1. This working tree

```text
C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack
```

## 2. Finding A — prior evidence names a different checkout

`evidence/side-b/g1/SB-EV-G1-001_regression_red.md` line 21 records:

```text
ImportError while importing test module 'C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend\tests\test_candidate_activation.py'.
```

`evidence/side-b/bootstrap/SB-EV-BOOT-001_environment_and_setup.md` line 16 records:

```text
Working directory: C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack
```

`evidence/side-b/bootstrap/SB-EV-BOOT-004_docker_checks.md` lines 22, 30 and 143–144 also name `C:\Users\User\Desktop\Platform\...`.

All of these name `Desktop\Platform\...`, not `Desktop\Claude\...`. **Every bootstrap evidence artifact SB-EV-BOOT-001..005 and the red-stage record SB-EV-G1-001 are therefore of uncertain attribution to this working tree.** They are preserved unmodified; they are superseded, not corrected.

## 3. Finding B — the other checkout exists and is byte-identical

```text
COMMAND: ls -d "C:/Users/User/Desktop/Platform/Fashion_Commerce_Codex_Multi_Agent_Pack/platform/poc"
C:/Users/User/Desktop/Platform/Fashion_Commerce_Codex_Multi_Agent_Pack/platform/poc
EXIT_CODE: 0
```

SHA-256 comparison (this checkout = `claude`, other checkout = `platform`), taken before any change in this cycle:

```text
backend/app/__init__.py                 claude=e3b0c442...b7852b855  platform=e3b0c442...b7852b855  -> IDENTICAL
backend/app/candidate_activation.py     claude=b9639fae...c36542c4c82 platform=b9639fae...c36542c4c82 -> IDENTICAL
backend/tests/test_api.py               claude=42dfe0c3...c7ff50a68f  platform=42dfe0c3...c7ff50a68f  -> IDENTICAL
backend/tests/test_candidate_activation.py claude=1d3051c1...43651f6d3 platform=1d3051c1...43651f6d3 -> IDENTICAL
backend/data/products.json              claude=536f91ab...c59bce8d    platform=536f91ab...c59bce8d    -> IDENTICAL
backend/data/candidate_products.json    claude=7f052e4c...8dab8323    platform=7f052e4c...8dab8323    -> IDENTICAL
```

File size and modification timestamps are also identical, e.g.:

```text
claude   candidate_activation.py size=13793 mtime=2026-08-01 17:56:11.799905600 +0200
platform candidate_activation.py size=13793 mtime=2026-08-01 17:56:11.799905600 +0200
```

**Interpretation:** this checkout is a timestamp-preserving copy of, or a common-source sibling of, `C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack`. Source content was equivalent, so the earlier results were not behaviourally wrong — but they were not *produced by* this tree and cannot be cited as evidence for it.

Note: this is a *third* pack directory, distinct from the read-only reference the controller named (`C:\Users\User\Desktop\Claude\Fashion_Commerce_Two_Agent_Execution_Pack`). Neither was modified during this cycle; `Desktop\Platform\...` was read only, once, to restore a fixture (section 5).

## 4. Finding C — stale bytecode from the other checkout was being executed (new)

The copy carried `__pycache__` directories with it. Because Python validates a cached `.pyc` against the source *mtime and size* — both preserved by the copy — the stale bytecode was accepted as current and executed. Its embedded `co_filename` proves its origin:

```text
COMMAND: python inspect_pyc.py   (marshal.loads of each .pyc, printing code.co_filename)
backend/app/__pycache__/__init__.cpython-314.pyc                       -> C:\Users\User\Desktop\Platform\...\app\__init__.py
backend/app/__pycache__/candidate_activation.cpython-314.pyc           -> C:\Users\User\Desktop\Platform\...\app\candidate_activation.py
backend/tests/__pycache__/test_api.cpython-314-pytest-9.0.2.pyc        -> C:\Users\User\Desktop\Platform\...\tests\test_api.py
backend/tests/__pycache__/test_candidate_activation.cpython-314-pytest-9.0.2.pyc -> C:\Users\User\Desktop\Platform\...\tests\test_candidate_activation.py
EXIT_CODE: 0
```

This was observable in a live traceback from this tree:

```text
ERROR collecting tests/test_api.py
ImportError while importing test module
'C:\Users\User\Desktop\Claude\...\platform\poc\backend\tests\test_api.py'
Traceback:
..\..\..\..\..\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend\tests\test_api.py:3: in <module>
```

**This is the concrete mechanism behind the attribution problem.** The controller-verified baseline (`17 passed`) was executed with at least four modules loaded from bytecode compiled in the other tree.

### Remediation applied

```text
COMMAND: find . -name "__pycache__" -type d -prune -exec rm -rf {} +
COMMAND: find . -name ".pytest_cache" -type d -prune -exec rm -rf {} +
EXIT_CODE: 0
```

All subsequent evidence in this cycle was produced with `PYTHONDONTWRITEBYTECODE=1` and `pytest -p no:cacheprovider`, so no cache can be created or reused. The same flags are now set in `platform/poc/.github/workflows/ci.yml`.

## 5. Finding D — a test run mutated the preserved sample fixture, and it was restored

While adding the admin-security tests, an intermediate run reached the admin write path (the PoC accepted the shipped placeholder token `change-me` in the default configuration) and rewrote `platform/poc/backend/data/products.json`.

```text
mutated  sha256 = 39e5651cbdc937509edf870d2b2d8a2032c0e52b8d362db56d5105062df339ce
original sha256 = 536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
```

Restored from the byte-identical reference copy and verified:

```text
COMMAND: cp "<Desktop\Platform\...>/backend/data/products.json" "<this tree>/backend/data/products.json"
COMMAND: sha256sum backend/data/products.json
536f91ab8dc4b43af80935696cc5485dd53afdbdd6d6541160fe37c7c59bce8d
RESTORE: OK (byte-identical to original fixture)
EXIT_CODE: 0
```

Two permanent controls were added so this cannot recur silently:

1. `platform/poc/backend/tests/conftest.py` — a session-scoped autouse fixture that snapshots the protected data fixtures, restores them, and **fails the run** if any test changed them.
2. `require_admin` in `platform/poc/backend/app/main.py` — the shipped placeholder token now authorizes nothing in any environment (HTTP 503).

This finding is reported rather than concealed: it is simultaneously the proof of launch-blocker risk SB-RISK-B5-001 (unsafe admin defaults).

## 6. Supersession table

| Superseded artifact | Status of the old record | Superseding artifact | Reason |
|---|---|---|---|
| SB-EV-BOOT-001 environment and setup | preserved unmodified; attribution UNCERTAIN | SB-EV-G1-005 v2.0.0 | working directory named `Desktop\Platform\...` |
| SB-EV-BOOT-002 backend checks | preserved unmodified; attribution UNCERTAIN | SB-EV-G1-005 v2.0.0 | same tree ambiguity; also executed stale bytecode |
| SB-EV-BOOT-003 mobile checks | preserved unmodified; still BLOCKED | SB-EV-G1-005 §6 | mobile dependency conflict not retested this cycle |
| SB-EV-BOOT-004 docker checks | preserved unmodified; BLOCKED by port collision | SB-EV-G1-005 §4 | isolated project + non-colliding ports now succeed |
| SB-EV-BOOT-005 intake validation | preserved unmodified; attribution UNCERTAIN | SB-EV-G1-005 v2.0.0 | derived from the above |
| SB-EV-G1-001 regression RED | preserved unmodified; RED stage still valid as intent | SB-EV-G1-002 (GREEN) | the matching green stage did not exist |

No superseded file was edited or deleted.
