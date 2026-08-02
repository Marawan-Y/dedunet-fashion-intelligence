"""Every third-party import must be declared in requirements.txt.

Why this exists
---------------
SQLAlchemy and Alembic were added to the application and installed into the developer's
environment, but never recorded in `requirements.txt`. Tests passed locally because the
packages were present; the Docker image, which installs only from `requirements.txt`,
crashed on startup with `ModuleNotFoundError: No module named 'sqlalchemy'`.

A local test run cannot catch that class of defect, because the local environment is
exactly what makes it invisible. This test compares the imports in the source against
the declared dependencies, so the gap is caught without needing to build an image.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
REQUIREMENTS = BACKEND / "requirements.txt"

# Import name -> distribution name, where they differ.
IMPORT_TO_DISTRIBUTION = {
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic",
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "uvicorn": "uvicorn",
    "httpx": "httpx",
    "dotenv": "python-dotenv",
    "pytest": "pytest",
    "starlette": "fastapi",      # transitive, guaranteed by fastapi
    "pydantic_core": "pydantic",  # transitive, guaranteed by pydantic
}


def declared_distributions() -> set[str]:
    names: set[str] = set()
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Strip version pins and extras: "uvicorn[standard]==0.35.0" -> "uvicorn"
        name = line.split("==")[0].split(">=")[0].split("[")[0].strip()
        names.add(name.lower())
    return names


def top_level_imports(root: Path) -> set[str]:
    modules: set[str] = set()
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                # level > 0 is a relative import within this package.
                if node.level == 0 and node.module:
                    modules.add(node.module.split(".")[0])
    return modules


def test_every_third_party_import_is_declared() -> None:
    declared = declared_distributions()
    stdlib = sys.stdlib_module_names

    undeclared: list[str] = []
    for module in sorted(top_level_imports(APP)):
        if module in stdlib or module == "app":
            continue
        distribution = IMPORT_TO_DISTRIBUTION.get(module, module).lower()
        if distribution not in declared:
            undeclared.append(f"{module} (needs '{distribution}' in requirements.txt)")

    assert not undeclared, (
        "Imports not declared in requirements.txt — the container build will fail:\n  "
        + "\n  ".join(undeclared)
    )


def test_runtime_dependencies_are_pinned() -> None:
    """An unpinned dependency makes a build non-deterministic."""

    unpinned = [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#") and "==" not in line
    ]
    assert not unpinned, f"unpinned dependencies: {unpinned}"
