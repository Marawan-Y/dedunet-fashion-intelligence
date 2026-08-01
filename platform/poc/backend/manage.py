#!/usr/bin/env python
"""Management CLI for the Fashion Commerce Platform backend.

    python manage.py migrate        apply migrations to head
    python manage.py seed           load the fictional MERET dataset (idempotent)
    python manage.py bootstrap      migrate + seed, for a clean checkout
    python manage.py export-openapi write the versioned API contract to disk
    python manage.py check          report readiness of the configured database

Every command is safe to re-run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

CONTRACT_PATH = BACKEND_DIR.parent / "docs" / "api" / "openapi.json"


def cmd_migrate(_args: argparse.Namespace) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR
    )
    return result.returncode


def cmd_seed(_args: argparse.Namespace) -> int:
    from app.commerce.db import SessionLocal, create_all
    from app.commerce.seed import seed

    # create_all is a no-op when migrations already built the schema; it makes the
    # command usable on a fresh database without a migration step.
    create_all()
    with SessionLocal() as session:
        created = seed(session)
    print(json.dumps({"seeded": created}, indent=2))
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    code = cmd_migrate(args)
    if code != 0:
        return code
    return cmd_seed(args)


def cmd_export_openapi(_args: argparse.Namespace) -> int:
    from app.main import app

    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    spec = app.openapi()
    CONTRACT_PATH.write_text(json.dumps(spec, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {CONTRACT_PATH} ({len(spec.get('paths', {}))} paths)")
    return 0


def cmd_check(_args: argparse.Namespace) -> int:
    from sqlalchemy import text

    from app.commerce.db import DATABASE_URL, engine

    # Never print the full URL: it may carry a password in a real deployment.
    scheme = DATABASE_URL.split("://", 1)[0]
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"database": scheme, "status": "unavailable", "error": type(exc).__name__}))
        return 1
    print(json.dumps({"database": scheme, "status": "ok"}))
    return 0


COMMANDS = {
    "migrate": cmd_migrate,
    "seed": cmd_seed,
    "bootstrap": cmd_bootstrap,
    "export-openapi": cmd_export_openapi,
    "check": cmd_check,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    args = parser.parse_args()
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
