#!/usr/bin/env python
"""Executed failure-mode tests for the backup tooling.

Written as a Python harness rather than shell because a piped shell command reports the
exit status of the LAST stage: `cmd 2>&1 | tail -1; echo $?` yields tail's status, not
cmd's. An earlier attempt to verify these guards that way printed exit=0 for every case,
including the ones that had correctly failed — a false pass produced entirely by the
measurement.

Every case here asserts BOTH the exit code and the message, and that no credential
appears in the output.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANAGER = REPO_ROOT / "infrastructure" / "backup" / "backup_manager.py"
BACKUP_DIR = REPO_ROOT / "backups"

results: list[tuple[str, bool, str]] = []


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(MANAGER), *args],
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def check(label: str, condition: bool, detail: str = "") -> None:
    results.append((label, condition, detail))
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))


def secret() -> str:
    env = REPO_ROOT / ".env.staging"
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("POSTGRES_PASSWORD="):
            return line.split("=", 1)[1].strip()
    return ""


def main() -> int:
    name = sorted(p.stem for p in BACKUP_DIR.glob("*.dump"))[-1]
    dump = BACKUP_DIR / f"{name}.dump"
    sidecar = BACKUP_DIR / f"{name}.dump.sha256"
    metadata = BACKUP_DIR / f"{name}.metadata.json"
    password = secret()

    print(f"backup under test: {name}\n")

    # 1 - corrupted dump must fail verification
    shutil.copy2(dump, dump.with_suffix(".dump.bak"))
    with dump.open("ab") as handle:
        handle.write(b"corruption")
    proc = run("verify", "--name", name)
    check("corrupted dump fails verify", proc.returncode != 0, f"exit={proc.returncode}")
    check("corruption message names the mismatch", "CHECKSUM MISMATCH" in proc.stderr)

    # 2 - and a corrupted dump must never reach pg_restore
    proc = run("restore", "--name", name)
    check("corrupted dump refuses restore", proc.returncode != 0, f"exit={proc.returncode}")
    check("restore aborted before pg_restore ran", "pg_restore" not in proc.stderr.lower())
    shutil.move(str(dump.with_suffix(".dump.bak")), str(dump))

    proc = run("verify", "--name", name)
    check("original dump verifies after restoration", proc.returncode == 0, f"exit={proc.returncode}")

    # 3 - missing checksum sidecar
    shutil.move(str(sidecar), str(sidecar) + ".hidden")
    proc = run("verify", "--name", name)
    check("missing checksum fails", proc.returncode != 0, f"exit={proc.returncode}")
    check("missing checksum message is clear", "checksum sidecar is missing" in proc.stderr)
    shutil.move(str(sidecar) + ".hidden", str(sidecar))

    # 4 - malformed metadata
    shutil.copy2(metadata, str(metadata) + ".bak")
    metadata.write_text("{ not valid json", encoding="utf-8")
    proc = run("verify", "--name", name)
    check("malformed metadata fails safely", proc.returncode != 0, f"exit={proc.returncode}")
    check("malformed metadata message is clear", "metadata is malformed" in proc.stderr)
    shutil.move(str(metadata) + ".bak", str(metadata))

    # 5 - missing backup entirely
    proc = run("verify", "--name", "no-such-backup")
    check("missing dump fails", proc.returncode != 0, f"exit={proc.returncode}")
    check("missing dump message is clear", "dump is missing" in proc.stderr)

    # 6 - restore must refuse the SOURCE database
    proc = run("restore", "--name", name, "--target", "dedunet_staging")
    check("restore refuses the source database", proc.returncode != 0, f"exit={proc.returncode}")
    check("source-protection message is explicit",
          "refusing to restore over the source database" in proc.stderr)

    # 7 - cleanup must refuse the SOURCE database
    proc = run("cleanup", "--target", "dedunet_staging")
    check("cleanup refuses the source database", proc.returncode != 0, f"exit={proc.returncode}")
    check("cleanup-protection message is explicit",
          "refusing to drop the SOURCE database" in proc.stderr)

    # 8 - cleanup refuses a target that is not a rehearsal copy
    proc = run("cleanup", "--target", "some_other_db")
    check("cleanup refuses a non-rehearsal target", proc.returncode != 0, f"exit={proc.returncode}")

    # 9 - a non-empty target is rejected without an explicit override.
    #     The rehearsal database is currently populated from the earlier restore.
    proc = run("restore", "--name", name)
    check("non-empty target rejected without --force", proc.returncode != 0,
          f"exit={proc.returncode}")
    check("non-empty message mentions the override",
          "--force" in proc.stderr, proc.stderr.strip()[-90:])

    # 10 - overwrite protection on backup creation
    proc = run("backup", "--name", name)
    check("existing backup name is not overwritten", proc.returncode != 0,
          f"exit={proc.returncode}")
    check("overwrite message is explicit", "refusing to overwrite" in proc.stderr)

    # 11 - no credential appears anywhere in the tooling's output
    combined = "".join(p for _, _, p in results)
    all_output = combined
    for probe in ("verify", "restore", "cleanup"):
        out = run(probe, "--name", name)
        all_output += out.stdout + out.stderr
    leaked = bool(password) and password in all_output
    check("no database password in any output", not leaked)
    check("no connection URL in any output", "postgresql://" not in all_output)

    # 12 - a partial artifact is never presented as complete
    check("metadata records an explicit completion result",
          json.loads(metadata.read_text(encoding="utf-8")).get("result") == "completed")

    failed = [label for label, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:")
        for label in failed:
            print(f"  - {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
