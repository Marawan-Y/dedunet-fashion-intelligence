"""Shared test safeguards.

The PoC catalog is a JSON file that the admin endpoint writes in place. A test that
reaches the write path would silently mutate the preserved sample fixture
(`backend/data/products.json`). This module snapshots the data fixtures before the
session, restores them afterwards, and FAILS the run if any test changed them, so a
fixture mutation can never pass unnoticed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROTECTED_FIXTURES = ("products.json", "candidate_products.json")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def protect_data_fixtures() -> object:
    snapshots = {
        name: (DATA_DIR / name).read_bytes()
        for name in PROTECTED_FIXTURES
        if (DATA_DIR / name).exists()
    }
    before = {name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()}

    yield

    mutated: list[str] = []
    for name, original in snapshots.items():
        path = DATA_DIR / name
        if _digest(path) != before[name]:
            mutated.append(f"{name} (sha256 {before[name]} -> {_digest(path)})")
            path.write_bytes(original)  # restore so the next run starts clean

    if mutated:
        raise AssertionError(
            "Test run mutated protected data fixtures and they were restored: "
            + "; ".join(mutated)
        )
