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
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

def contract_path() -> Path:
    """Locate the authoritative API contract.

    Resolved lazily, and only by ``export-openapi``. In the container this file lives at
    ``/app/manage.py``, so there is no repository root above it and computing this at
    import time raised IndexError, taking every other command down with it — including
    the ``seed`` the entrypoint runs on startup.

    Walks upward for the real ``packages/`` directory rather than assuming a fixed depth,
    so it survives the service moving again.
    """

    for candidate in (BACKEND_DIR, *BACKEND_DIR.parents):
        contract_dir = candidate / "packages" / "contracts" / "openapi"
        if contract_dir.is_dir():
            return contract_dir / "openapi.json"
    raise SystemExit(
        "cannot locate packages/contracts/openapi/ above "
        f"{BACKEND_DIR}; run export-openapi from a full checkout"
    )


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

    destination = contract_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    spec = app.openapi()
    destination.write_text(json.dumps(spec, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {destination} ({len(spec.get('paths', {}))} paths)")
    return 0


def cmd_create_admin(_args: argparse.Namespace) -> int:
    """Create the staging administrator from the environment. Idempotent.

    Deliberately MANUAL. The container entrypoint must never run this: an entrypoint that
    provisions a privileged account creates one automatically on every fresh volume, and
    the credentials would have to live in the compose environment to do it.

    The password is read from the environment, never from an argument (arguments appear
    in shell history and in `ps`), and is never printed or logged.
    """

    from app.commerce.db import SessionLocal, create_all
    from app.commerce.models import Customer
    from app.commerce.security import hash_password
    from sqlalchemy import select

    email = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "")

    if not email:
        print("ERROR: ADMIN_BOOTSTRAP_EMAIL is not set", file=sys.stderr)
        return 2
    if "@" not in email:
        print("ERROR: ADMIN_BOOTSTRAP_EMAIL is not a valid address", file=sys.stderr)
        return 2
    if not password:
        print("ERROR: ADMIN_BOOTSTRAP_PASSWORD is not set", file=sys.stderr)
        return 2
    if len(password) < 12:
        # Length only. The value itself is never echoed.
        print(
            f"ERROR: ADMIN_BOOTSTRAP_PASSWORD is {len(password)} characters; "
            "at least 12 are required",
            file=sys.stderr,
        )
        return 2

    create_all()
    with SessionLocal() as session:
        existing = session.scalar(select(Customer).where(Customer.email == email))
        if existing is not None:
            role = existing.role
            print(json.dumps({"created": False, "email": email, "role": role,
                              "detail": "account already exists; no change made"}))
            return 0

        session.add(Customer(
            email=email,
            password_hash=hash_password(password),
            full_name=os.getenv("ADMIN_BOOTSTRAP_NAME", "Administrator"),
            role="admin",
        ))
        session.commit()

    print(json.dumps({"created": True, "email": email, "role": "admin"}))
    return 0


def cmd_dispatch_notifications(args: argparse.Namespace) -> int:
    """Run ONE bounded dispatch cycle and exit.

    Deliberately not a loop and never a thread inside the API process. A background
    delivery thread would make /ready lie about a subsystem it does not check, would
    fight the per-request session model, and two API replicas would double-send every
    message. Scheduling belongs to the worker (notification_worker.py) or to an external
    scheduler, not to the web process.
    """

    from app.commerce.db import SessionLocal, create_all
    from app.commerce.services import dispatch_pending_notifications

    create_all()
    with SessionLocal() as session:
        counts = dispatch_pending_notifications(
            session, limit=args.limit, max_attempts=args.max_attempts
        )
    print(json.dumps({"dispatched": counts}))
    return 0


def cmd_check_config(_args: argparse.Namespace) -> int:
    """Validate security configuration only. Touches no database.

    Separate from ``check`` so the entrypoint can distinguish two very different
    failures. A database that is not up yet is TRANSIENT and worth retrying; a blank
    SESSION_SECRET is PERMANENT and retrying it thirty times only delays a clear error
    behind sixty seconds of misleading "waiting for database" output.
    """

    from app.commerce.security import assert_configured

    try:
        assert_configured()
    except RuntimeError as exc:
        print(json.dumps({"configuration": "invalid", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"configuration": "valid"}))
    return 0


def cmd_check(_args: argparse.Namespace) -> int:
    from sqlalchemy import text

    from app.commerce.db import DATABASE_URL, engine
    from app.commerce.security import assert_configured

    # Security configuration first: a container with a blank SESSION_SECRET must die at
    # boot, not on the first customer login.
    try:
        assert_configured()
    except RuntimeError as exc:
        print(json.dumps({"configuration": "invalid", "error": str(exc)}), file=sys.stderr)
        return 1

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
    "create-admin": cmd_create_admin,
    "check-config": cmd_check_config,
    "dispatch-notifications": cmd_dispatch_notifications,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    # Only dispatch-notifications reads these; harmless for the other commands.
    parser.add_argument("--limit", type=int, default=None, help="max rows per cycle")
    parser.add_argument("--max-attempts", type=int, default=None, dest="max_attempts")
    args = parser.parse_args()
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
