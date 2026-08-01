# Side B Environment and Setup Evidence

- Artifact ID: SB-EV-BOOT-001
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: repository manifests; `platform/poc/README.md`; `platform/poc/Makefile`; `platform/poc/backend/requirements.txt`; `platform/poc/mobile/package.json`
- Acceptance criteria: exact commands, observed outputs, exit codes, timestamps, setup mutations, and limitations are recorded without converting local/sandbox evidence into a production claim.
- Validation procedure/result: compared this record to the captured terminal output on 2026-08-01; SELF-VALIDATED.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-001_environment_and_setup.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: SB-AR-B2-001 repository/PoC audit; controller G0 reconciliation
- Remaining risks/next action: repeat in an isolated Python 3.12 virtual environment and resolve the mobile peer dependency under an approved change cycle.

## Context

Working directory: `C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack`

Captured: 2026-08-01 (Europe/Berlin). The repository is an extracted pack and is not a Git worktree (`git status --short` returned `fatal: not a git repository`). No baseline source repair preceded the initial checks.

## Tool discovery

```text
COMMAND: python --version
Python 3.14.4
EXIT_CODE: 0
COMMAND: python -m pip --version
pip 26.0.1 from C:\Python314\Lib\site-packages\pip (python 3.14)
EXIT_CODE: 0
COMMAND: python -m pytest --version
EXIT_CODE: 1
COMMAND: node --version
v24.15.0
EXIT_CODE: 0
COMMAND: cmd /c npm --version
11.12.1
EXIT_CODE: 0
COMMAND: docker --version
Docker version 29.6.1, build 8900f1d
EXIT_CODE: 0
COMMAND: docker compose version
Docker Compose version v5.3.0
EXIT_CODE: 0
COMMAND: cmd /c make --version
EXIT_CODE: 1
cmd : Der Befehl "make" ist entweder falsch geschrieben oder konnte nicht gefunden werden.
```

Resolved executables:

```text
python.exe  Application  C:\Python314\python.exe  3.14.4150.1013
node.exe    Application  C:\Program Files\nodejs\node.exe  24.15.0.0
npm.ps1     ExternalScript C:\Program Files\nodejs\npm.ps1
docker.exe  Application  C:\Program Files\Docker\Docker\resources\bin\docker.exe
make        NOT FOUND
```

## Initial dependency-state failures

Command from `platform/poc/backend`:

```text
COMMAND: python -m pytest -q
EXIT_CODE: 1
C:\Python314\python.exe: No module named pytest
```

Command from `platform/poc`:

```text
COMMAND: python scripts/validate_product_data.py
EXIT_CODE: 1
Traceback (most recent call last):
  File "C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\scripts\validate_product_data.py", line 8, in <module>
    from app.schemas import Product  # noqa: E402
  File "C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend\app\schemas.py", line 5, in <module>
    from pydantic import BaseModel, Field, HttpUrl, field_validator
ModuleNotFoundError: No module named 'pydantic'
```

## Dependency installation

First sandboxed attempt from `platform/poc/backend`:

```text
COMMAND: python -m pip install -r requirements.txt
EXIT_CODE: 1
Defaulting to user installation because normal site-packages is not writeable
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError(... [WinError 10013] Der Zugriff auf einen Socket war aufgrund der Zugriffsrechte des Sockets unzulässig')': /simple/fastapi/
WARNING: Retrying (Retry(total=3, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError(... [WinError 10013] Der Zugriff auf einen Socket war aufgrund der Zugriffsrechte des Sockets unzulässig')': /simple/fastapi/
WARNING: Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError(... [WinError 10013] Der Zugriff auf einen Socket war aufgrund der Zugriffsrechte des Sockets unzulässig')': /simple/fastapi/
WARNING: Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError(... [WinError 10013] Der Zugriff auf einen Socket war aufgrund der Zugriffsrechte des Sockets unzulässig')': /simple/fastapi/
WARNING: Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError(... [WinError 10013] Der Zugriff auf einen Socket war aufgrund der Zugriffsrechte des Sockets unzulässig')': /simple/fastapi/
ERROR: Could not find a version that satisfies the requirement fastapi==0.139.2 (from versions: none)
ERROR: No matching distribution found for fastapi==0.139.2
```

Approved network retry:

```text
COMMAND: python -m pip install -r requirements.txt
EXIT_CODE: 0
Defaulting to user installation because normal site-packages is not writeable
Collected and installed the six pinned direct requirements and their transitive dependencies.
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.14.2 certifi-2026.7.22 click-8.4.2 colorama-0.4.6 fastapi-0.139.2 h11-0.16.0 httpcore-1.0.9 httptools-0.8.0 httpx-0.28.1 idna-3.18 iniconfig-2.3.0 packaging-26.2 pluggy-1.6.0 pydantic-2.13.4 pydantic-core-2.46.4 pygments-2.20.0 pytest-9.0.2 python-dotenv-1.1.1 pyyaml-6.0.3 starlette-1.3.1 typing-extensions-4.16.0 typing-inspection-0.4.2 uvicorn-0.35.0 watchfiles-1.2.0 websockets-17.0.1
WARNING: user-level Scripts directory `C:\Users\User\AppData\Roaming\Python\Python314\Scripts` is not on PATH.
```

The install changed the user Python environment, not repository source. It did not create the README-prescribed isolated `.venv`, so reproducibility remains limited.

## Local environment file

After the no-`.env` Docker failures were captured, Side B created ignored local file `platform/poc/.env` from `.env.example`, with `ADMIN_API_TOKEN=local-baseline-only-not-for-sharing`. It is synthetic local configuration, not a secret-management or production control claim.
