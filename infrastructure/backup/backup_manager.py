#!/usr/bin/env python
"""PostgreSQL backup and isolated restore rehearsal.

    python infrastructure/backup/backup_manager.py backup
    python infrastructure/backup/backup_manager.py verify   --name <backup-name>
    python infrastructure/backup/backup_manager.py restore  --name <backup-name>
    python infrastructure/backup/backup_manager.py parity   --name <backup-name>
    python infrastructure/backup/backup_manager.py cleanup  --name <backup-name>
    python infrastructure/backup/backup_manager.py rehearse            # all of the above

Design decisions that are not arbitrary
---------------------------------------
**An ephemeral client container, not the API image.** `pg_dump` must match the server's
major version, and the API image has no PostgreSQL client. Adding one would grow the
runtime image for a task the runtime never performs. `postgres:16-alpine` is already
present and is by construction the same major version as the server.

**The dump is written INSIDE the container to a mounted directory**, never streamed
through the host shell. `docker compose exec` allocates a TTY and would corrupt a binary
custom-format dump; it also avoids MSYS mangling container-absolute paths on Windows.

**The password travels in the environment, never in argv.** Command lines are visible in
`ps` and in shell history.

**Restore always targets a NEW database.** A restore script capable of writing to the live
database is one typo away from being the incident it exists to prevent. `cleanup` refuses
to drop the source database outright.

**Custom format, not plain SQL.** `--format=custom` supports selective restore, parallel
restore and `pg_restore` validation; a text dump is only replayable end to end.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = REPO_ROOT / "backups"
PG_IMAGE = "postgres:16-alpine"

# Tables whose row counts must match exactly after a restore. Listed explicitly rather
# than discovered, so a table silently disappearing from the dump is a failure rather
# than something the comparison quietly skips.
CRITICAL_TABLES = [
    "customers", "addresses", "products", "variants", "inventory_items",
    "carts", "cart_lines", "orders", "order_lines", "reservations",
    "payments", "shipments", "return_requests", "notifications",
    "promotions", "analytics_events", "audit_logs", "alembic_version",
]


class BackupError(RuntimeError):
    """Any failure that must stop the procedure with a non-zero exit."""


# ------------------------------------------------------------------ configuration


def config() -> dict:
    """Read connection settings. Missing required values are a hard failure."""

    env_file = REPO_ROOT / ".env.staging"
    values: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()

    settings = {
        "user": os.getenv("POSTGRES_USER", values.get("POSTGRES_USER", "")),
        "password": os.getenv("POSTGRES_PASSWORD", values.get("POSTGRES_PASSWORD", "")),
        "database": os.getenv("POSTGRES_DB", values.get("POSTGRES_DB", "")),
        "host": os.getenv("BACKUP_DB_HOST", "db"),
        "network": os.getenv("BACKUP_DOCKER_NETWORK", "dedunet-staging_default"),
        "environment": os.getenv("APP_ENV", values.get("APP_ENV", "staging")),
    }
    missing = [k for k in ("user", "password", "database") if not settings[k]]
    if missing:
        raise BackupError(
            f"missing required configuration: {', '.join(missing)}. "
            "Set POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB or provide .env.staging"
        )
    return settings


def _run_client(cfg: dict, args: list[str], *, mount_backups: bool = True,
                capture: bool = True) -> subprocess.CompletedProcess:
    """Run a PostgreSQL client command in an ephemeral container."""

    docker = [
        "docker", "run", "--rm",
        "--network", cfg["network"],
        "-e", f"PGPASSWORD={cfg['password']}",   # environment, never argv
    ]
    if mount_backups:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        host_path = str(BACKUP_DIR).replace("\\", "/")
        docker += ["-v", f"{host_path}:/backups"]
    docker += [PG_IMAGE] + args

    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    return subprocess.run(docker, capture_output=capture, text=True, env=env)


def _psql(cfg: dict, database: str, sql: str) -> str:
    result = _run_client(
        cfg,
        ["psql", "-h", cfg["host"], "-U", cfg["user"], "-d", database, "-tAc", sql],
        mount_backups=False,
    )
    if result.returncode != 0:
        raise BackupError(f"psql failed: {_sanitize(result.stderr, cfg)}")
    return result.stdout.strip()


def _sanitize(text: str, cfg: dict) -> str:
    """Remove anything credential-shaped before the text reaches a log or evidence file."""

    if not text:
        return ""
    cleaned = text.replace(cfg["password"], "[REDACTED]")
    cleaned = re.sub(r"postgres(?:ql)?://[^\s\"']+", "[REDACTED-URL]", cleaned)
    cleaned = re.sub(r"PGPASSWORD=\S+", "PGPASSWORD=[REDACTED]", cleaned)
    return cleaned


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _paths(name: str) -> tuple[Path, Path, Path]:
    return (
        BACKUP_DIR / f"{name}.dump",
        BACKUP_DIR / f"{name}.dump.sha256",
        BACKUP_DIR / f"{name}.metadata.json",
    )


# ------------------------------------------------------------------------ backup


def cmd_backup(args: argparse.Namespace) -> int:
    cfg = config()
    name = args.name or f"{cfg['database']}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    dump_path, sum_path, meta_path = _paths(name)

    # Never silently overwrite: a backup that replaced an earlier one without saying so
    # destroys the only copy of an older state.
    for path in (dump_path, sum_path, meta_path):
        if path.exists():
            raise BackupError(f"refusing to overwrite existing artifact: {path.name}")

    server_version = _psql(cfg, cfg["database"], "SHOW server_version")
    revision = _psql(cfg, cfg["database"], "SELECT version_num FROM alembic_version")

    client_version = _run_client(cfg, ["pg_dump", "--version"], mount_backups=False)
    client = client_version.stdout.strip()

    started = time.perf_counter()
    result = _run_client(cfg, [
        "pg_dump", "-h", cfg["host"], "-U", cfg["user"], "-d", cfg["database"],
        "--format=custom", "--file", f"/backups/{name}.dump",
    ])
    duration = round(time.perf_counter() - started, 2)

    if result.returncode != 0:
        # A partial artifact must never be presented as a completed backup.
        dump_path.unlink(missing_ok=True)
        raise BackupError(f"pg_dump failed: {_sanitize(result.stderr, cfg)}")
    if not dump_path.exists() or dump_path.stat().st_size == 0:
        dump_path.unlink(missing_ok=True)
        raise BackupError("pg_dump reported success but produced no usable dump")

    checksum = _sha256(dump_path)
    sum_path.write_text(f"{checksum}  {name}.dump\n", encoding="utf-8")

    metadata = {
        "backup_name": name,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "database": cfg["database"],
        "server_version": server_version,
        "pg_dump_client": client,
        "dump_format": "custom",
        "dump_size_bytes": dump_path.stat().st_size,
        "checksum_algorithm": "sha256",
        "checksum": checksum,
        "migration_revision": revision,
        "repository_commit": _git_commit(),
        "environment": cfg["environment"],
        "result": "completed",
        "duration_seconds": duration,
        # Deliberately absent: password, connection URL, host credentials, secrets.
        "contains_personal_data": True,
        "storage": "local only; not scheduled, not offsite, not encrypted at rest",
    }
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    _restrict(dump_path, sum_path, meta_path)

    print(json.dumps({"backup": name, "size_bytes": metadata["dump_size_bytes"],
                      "sha256": checksum, "revision": revision,
                      "duration_seconds": duration}, indent=2))
    return 0


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True)
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def _restrict(*paths: Path) -> None:
    """Best-effort permission tightening. POSIX only; recorded honestly on Windows."""

    for path in paths:
        try:
            path.chmod(0o600)
        except (OSError, NotImplementedError):
            pass


# ------------------------------------------------------------------- verification


def cmd_verify(args: argparse.Namespace) -> int:
    cfg = config()
    dump_path, sum_path, meta_path = _paths(args.name)

    if not dump_path.exists():
        raise BackupError(f"backup dump is missing: {dump_path.name}")
    if not sum_path.exists():
        raise BackupError(f"checksum sidecar is missing: {sum_path.name}")

    recorded = sum_path.read_text(encoding="utf-8").split()[0].strip().lower()
    actual = _sha256(dump_path)
    if actual != recorded:
        raise BackupError(
            f"CHECKSUM MISMATCH for {dump_path.name}: recorded {recorded}, actual {actual}. "
            "The backup is corrupt or was modified; it must not be restored."
        )

    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BackupError(f"metadata is malformed: {exc}") from None
        if metadata.get("result") != "completed":
            raise BackupError("metadata does not record a completed backup")
        if metadata.get("checksum", "").lower() != actual:
            raise BackupError("metadata checksum disagrees with the sidecar")

    print(json.dumps({"verified": args.name, "sha256": actual}))
    return 0


# ----------------------------------------------------------------------- restore


def cmd_restore(args: argparse.Namespace) -> int:
    cfg = config()
    dump_path, _, meta_path = _paths(args.name)
    target = args.target or f"{cfg['database']}_rehearsal"

    if target == cfg["database"]:
        raise BackupError(
            f"refusing to restore over the source database {target!r}. "
            "A rehearsal must target a separate database."
        )

    cmd_verify(argparse.Namespace(name=args.name))     # checksum BEFORE restore

    exists = _psql(cfg, "postgres",
                   f"SELECT 1 FROM pg_database WHERE datname = '{target}'")
    if exists.strip() == "1":
        tables = _psql(cfg, target,
                       "SELECT count(*) FROM pg_tables WHERE schemaname='public'")
        if int(tables or 0) > 0 and not args.force:
            raise BackupError(
                f"target database {target!r} already contains {tables} tables. "
                "Refusing to restore into a non-empty target; pass --force to override."
            )
        _psql(cfg, "postgres", f'DROP DATABASE "{target}"')

    _psql(cfg, "postgres", f'CREATE DATABASE "{target}"')
    empty = _psql(cfg, target, "SELECT count(*) FROM pg_tables WHERE schemaname='public'")
    if int(empty or 0) != 0:
        raise BackupError(f"freshly created {target!r} is not empty ({empty} tables)")

    started = time.perf_counter()
    result = _run_client(cfg, [
        "pg_restore", "-h", cfg["host"], "-U", cfg["user"], "-d", target,
        "--exit-on-error", f"/backups/{args.name}.dump",
    ])
    duration = round(time.perf_counter() - started, 2)

    if result.returncode != 0:
        raise BackupError(
            f"pg_restore FAILED (exit {result.returncode}): "
            f"{_sanitize(result.stderr, cfg)[:500]}"
        )

    print(json.dumps({"restored_into": target, "duration_seconds": duration,
                      "from": args.name}, indent=2))
    return 0


# ------------------------------------------------------------------------ parity


def cmd_parity(args: argparse.Namespace) -> int:
    cfg = config()
    source = cfg["database"]
    target = args.target or f"{source}_rehearsal"
    failures: list[str] = []
    report: dict = {"source": source, "restored": target, "checks": {}}

    def compare(label: str, sql: str) -> None:
        left, right = _psql(cfg, source, sql), _psql(cfg, target, sql)
        report["checks"][label] = {"source": left, "restored": right,
                                   "match": left == right}
        if left != right:
            failures.append(f"{label}: source={left!r} restored={right!r}")

    compare("migration_revision", "SELECT version_num FROM alembic_version")
    compare("table_names",
            "SELECT string_agg(tablename, ',' ORDER BY tablename) FROM pg_tables "
            "WHERE schemaname='public'")
    compare("table_count",
            "SELECT count(*)::text FROM pg_tables WHERE schemaname='public'")
    compare("index_names",
            "SELECT string_agg(indexname, ',' ORDER BY indexname) FROM pg_indexes "
            "WHERE schemaname='public'")
    for kind, label in (("f", "foreign_keys"), ("c", "check_constraints"),
                        ("u", "unique_constraints"), ("p", "primary_keys")):
        compare(label,
                "SELECT string_agg(conname, ',' ORDER BY conname) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace "
                f"WHERE n.nspname='public' AND c.contype='{kind}'")

    row_counts: dict[str, dict] = {}
    for table in CRITICAL_TABLES:
        exists = _psql(cfg, source,
                       f"SELECT to_regclass('public.{table}') IS NOT NULL")
        if exists.strip() != "t":
            failures.append(f"{table}: absent from the SOURCE database")
            continue
        left = _psql(cfg, source, f'SELECT count(*) FROM "{table}"')
        right = _psql(cfg, target, f'SELECT count(*) FROM "{table}"')
        row_counts[table] = {"source": int(left), "restored": int(right),
                             "match": left == right}
        if left != right:
            failures.append(f"{table} rows: source={left} restored={right}")
    report["row_counts"] = row_counts

    statuses = "SELECT string_agg(status || '=' || c, ',' ORDER BY status) FROM " \
               "(SELECT status, count(*)::text c FROM notifications GROUP BY status) s"
    compare("notification_status_counts", statuses)

    report["result"] = "PASS" if not failures else "FAIL"
    report["failures"] = failures
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


# ----------------------------------------------------------------------- cleanup


def cmd_cleanup(args: argparse.Namespace) -> int:
    cfg = config()
    target = args.target or f"{cfg['database']}_rehearsal"

    # The single most important line in this file. Cleanup must never be able to drop
    # the database it exists to protect.
    if target == cfg["database"]:
        raise BackupError(
            f"refusing to drop the SOURCE database {target!r}. Cleanup only ever removes "
            "a rehearsal copy."
        )
    if not target.endswith("_rehearsal") and not args.force:
        raise BackupError(
            f"{target!r} does not look like a rehearsal database; pass --force if intended"
        )

    _psql(cfg, "postgres", f'DROP DATABASE IF EXISTS "{target}"')
    print(json.dumps({"dropped": target}))
    return 0


def cmd_rehearse(args: argparse.Namespace) -> int:
    cfg = config()
    name = args.name or f"{cfg['database']}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    cmd_backup(argparse.Namespace(name=name))
    cmd_verify(argparse.Namespace(name=name))
    cmd_restore(argparse.Namespace(name=name, target=None, force=False))
    return cmd_parity(argparse.Namespace(target=None))


COMMANDS = {
    "backup": cmd_backup, "verify": cmd_verify, "restore": cmd_restore,
    "parity": cmd_parity, "cleanup": cmd_cleanup, "rehearse": cmd_rehearse,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--name", default=None)
    parser.add_argument("--target", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        return COMMANDS[args.command](args)
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
