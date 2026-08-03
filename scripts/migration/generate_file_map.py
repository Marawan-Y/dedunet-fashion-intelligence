"""Generate the R0 repository audit file map and path migration map.

Both CSVs are derived from `git ls-files`, not hand-written, so they cannot drift from
reality. Re-running this after the moves must produce an empty "pending" set.

Mapping rules are declared once here and reused by the migration, so the documented plan
and the executed moves come from the same source.
"""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (prefix, target prefix, owning subsystem, risk)
# Order matters: the first matching prefix wins, so specific paths precede general ones.
RULES: list[tuple[str, str, str, str]] = [
    ("platform/poc/backend/",        "services/commerce-api/",     "commerce-api",   "medium"),
    ("platform/poc/storefront/",     "apps/web/",                  "web",            "medium"),
    ("platform/poc/admin/",          "apps/admin/",                "admin",          "medium"),
    ("platform/poc/mobile/",         "apps/mobile/",               "mobile",         "low"),
    ("platform/poc/scripts/",        "scripts/validation/",        "tooling",        "medium"),
    ("platform/poc/docs/api/",       "packages/contracts/openapi/", "contracts",     "medium"),
    ("platform/poc/docs/",           "docs/operations/",           "documentation",  "low"),
    ("platform/poc/.github/",        ".github/",                   "ci",             "high"),
]

# Individual files that move to the repository root or a specific place.
FILE_RULES: dict[str, tuple[str, str, str]] = {
    "platform/poc/docker-compose.yml":     ("docker-compose.yml",            "infrastructure", "high"),
    "platform/poc/Makefile":               ("Makefile",                      "tooling",        "medium"),
    "platform/poc/.env.example":           (".env.example",                  "infrastructure", "medium"),
    "platform/poc/.dockerignore":          (".dockerignore",                 "infrastructure", "high"),
    "platform/poc/README.md":              ("README.md",                     "documentation",  "low"),
    "platform/poc/KNOWN_LIMITATIONS.md":   ("docs/KNOWN_LIMITATIONS.md",     "documentation",  "low"),
    # Superseded by the root .gitignore restored during the Git-root normalisation.
    "platform/poc/.gitignore":             ("__DELETE__",                    "infrastructure", "low"),
}

# Paths that stay exactly where they are.
STATIONARY_PREFIXES = (
    "docs/", "evidence/", "handoffs/", "prompts/", ".codex/", ".agent/", "scripts/",
)

GENERATED = {"packages/contracts/openapi/openapi.json"}


def classify(path: str) -> tuple[str, str, str, str, str]:
    """Return (target, subsystem, generated_or_source, risk, validation)."""
    if path in FILE_RULES:
        target, subsystem, risk = FILE_RULES[path]
        return target, subsystem, "source", risk, "root command + docker + CI"

    for prefix, target_prefix, subsystem, risk in RULES:
        if path.startswith(prefix):
            target = target_prefix + path[len(prefix):]
            gen = "generated" if target in GENERATED else "source"
            validation = {
                "commerce-api": "pytest, alembic, manage.py",
                "web": "browser load + frontend security test",
                "admin": "browser load + frontend security test",
                "mobile": "tsc --noEmit (blocked)",
                "tooling": "validators + mutation harness",
                "contracts": "openapi export drift",
                "documentation": "link check",
                "ci": "workflow path resolution",
            }[subsystem]
            return target, subsystem, gen, risk, validation

    if path.startswith(STATIONARY_PREFIXES) or "/" not in path:
        return path, "governance" if path.startswith(("docs/", "evidence/", "handoffs/")) else "root", "source", "none", "unchanged"

    return path, "unclassified", "source", "review", "manual review"


def file_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "python", ".js": "javascript", ".tsx": "typescript", ".ts": "typescript",
        ".html": "html", ".css": "css", ".json": "json", ".csv": "csv", ".md": "markdown",
        ".yml": "yaml", ".yaml": "yaml", ".toml": "toml", ".txt": "text", ".pdf": "pdf",
        ".docx": "docx", ".svg": "svg", ".png": "image", ".zip": "archive",
        ".ini": "config", ".mako": "template", ".sh": "shell", ".example": "config",
    }.get(suffix, "other")


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()

    audit_rows, migration_rows = [], []
    for path in files:
        target, subsystem, gen, risk, validation = classify(path)
        runtime = "runtime" if path.startswith("platform/poc/backend/data/") else "build-time"
        audit_rows.append({
            "current_path": path,
            "file_type": file_type(path),
            "owning_subsystem": subsystem,
            "runtime_status": runtime,
            "generated_or_source": gen,
            "proposed_target_path": target,
            "migration_risk": risk,
            "required_validation": validation,
        })
        if target != path:
            migration_rows.append({
                "source_path": path,
                "target_path": target,
                "owning_subsystem": subsystem,
                "imports_affected": "yes" if file_type(path) in ("python", "javascript", "typescript") else "no",
                "docker_refs_affected": "yes" if subsystem in ("commerce-api", "web", "admin", "infrastructure") else "no",
                "ci_refs_affected": "yes" if subsystem in ("commerce-api", "tooling", "ci", "contracts") else "no",
                "doc_refs_affected": "yes" if subsystem in ("documentation", "commerce-api") else "no",
                "tests_required": validation,
                "migration_status": "PENDING",
            })

    (ROOT / "docs/architecture").mkdir(parents=True, exist_ok=True)
    with open(ROOT / "docs/architecture/CURRENT_REPOSITORY_FILE_MAP.csv", "w",
              newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(audit_rows[0]))
        w.writeheader(); w.writerows(audit_rows)

    with open(ROOT / "docs/architecture/REPOSITORY_PATH_MIGRATION_MAP.csv", "w",
              newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(migration_rows[0]))
        w.writeheader(); w.writerows(migration_rows)

    from collections import Counter
    print(f"tracked files      : {len(files)}")
    print(f"files that move    : {len(migration_rows)}")
    print(f"files that stay    : {len(files) - len(migration_rows)}")
    print("\nmoves by subsystem:")
    for k, v in sorted(Counter(r["owning_subsystem"] for r in migration_rows).items()):
        print(f"  {k:16s} {v}")
    unclassified = [r for r in audit_rows if r["owning_subsystem"] == "unclassified"]
    print(f"\nunclassified (must be 0): {len(unclassified)}")
    for r in unclassified[:10]:
        print("   ", r["current_path"])
    return 1 if unclassified else 0


if __name__ == "__main__":
    raise SystemExit(main())
