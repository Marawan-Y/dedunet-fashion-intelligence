# G1 M1 Regression Tests — Failing Before Implementation

- Artifact ID: SB-EV-G1-001
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: HO-A-B-001 v1.0; SOR-G0-009; `platform/poc/backend/tests/test_candidate_activation.py`
- Acceptance criteria: required negative regression tests exist and fail before the candidate activation implementation exists; exact command/output/exit code is preserved.
- Validation procedure/result: targeted pytest executed after adding tests and before adding implementation; expected collection failure observed.
- Evidence path: `evidence/side-b/g1/SB-EV-G1-001_regression_red.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: candidate activation implementation; controller M1 review
- Remaining risks/next action: implement only enough schema/validation behavior to make these tests pass, then preserve green evidence separately.

Working directory: `platform/poc/backend`

```text
COMMAND: python -m pytest -q tests/test_candidate_activation.py

=================================== ERRORS ====================================
_____________ ERROR collecting tests/test_candidate_activation.py _____________
ImportError while importing test module 'C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend\tests\test_candidate_activation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\test_candidate_activation.py:8: in <module>
    from app.candidate_activation import (
E   ModuleNotFoundError: No module named 'app.candidate_activation'
=========================== short test summary info ===========================
ERROR tests/test_candidate_activation.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.62s
EXIT_CODE: 2
```

This is intentional red-stage evidence, not an unresolved final result.
