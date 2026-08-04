"""Guards on the backup tooling, as fast pure-logic tests.

The end-to-end rehearsal needs Docker, PostgreSQL and a running staging stack, so it lives
in `infrastructure/backup/test_backup_failure_modes.py` and is run deliberately. These
tests cover the same *decisions* with the database calls stubbed, so the mutation harness
can protect them and the main suite stays free of infrastructure dependencies.

What is verified here is the refusal logic — the code paths that decide NOT to do
something destructive. Those are the ones worth guarding permanently.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MANAGER_PATH = REPO_ROOT / "infrastructure" / "backup" / "backup_manager.py"


def _load_manager():
    spec = importlib.util.spec_from_file_location("backup_manager", MANAGER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    module = _load_manager()
    monkeypatch.setattr(module, "BACKUP_DIR", tmp_path)
    monkeypatch.setattr(module, "config", lambda: {
        "user": "u", "password": "secret-pw", "database": "src",
        "host": "db", "network": "net", "environment": "staging",
    })
    return module


def _make_backup(module, tmp_path, name="bk", *, body=b"DUMPBYTES", good_checksum=True):
    import hashlib

    dump = tmp_path / f"{name}.dump"
    dump.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest() if good_checksum else "0" * 64
    (tmp_path / f"{name}.dump.sha256").write_text(f"{digest}  {name}.dump\n", encoding="utf-8")
    (tmp_path / f"{name}.metadata.json").write_text(
        json.dumps({"result": "completed", "checksum": digest}), encoding="utf-8"
    )
    return name


# --------------------------------------------------------------------- checksum


def test_verify_accepts_an_intact_backup(manager, tmp_path):
    name = _make_backup(manager, tmp_path)
    assert manager.cmd_verify(argparse.Namespace(name=name)) == 0


def test_verify_rejects_a_modified_dump(manager, tmp_path):
    name = _make_backup(manager, tmp_path)
    (tmp_path / f"{name}.dump").write_bytes(b"TAMPERED")

    with pytest.raises(manager.BackupError, match="CHECKSUM MISMATCH"):
        manager.cmd_verify(argparse.Namespace(name=name))


def test_verify_rejects_a_missing_checksum_sidecar(manager, tmp_path):
    name = _make_backup(manager, tmp_path)
    (tmp_path / f"{name}.dump.sha256").unlink()

    with pytest.raises(manager.BackupError, match="checksum sidecar is missing"):
        manager.cmd_verify(argparse.Namespace(name=name))


def test_verify_rejects_malformed_metadata(manager, tmp_path):
    name = _make_backup(manager, tmp_path)
    (tmp_path / f"{name}.metadata.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(manager.BackupError, match="metadata is malformed"):
        manager.cmd_verify(argparse.Namespace(name=name))


def test_restore_verifies_the_checksum_before_touching_the_database(manager, tmp_path, monkeypatch):
    """A corrupt dump must never reach pg_restore."""

    name = _make_backup(manager, tmp_path)
    (tmp_path / f"{name}.dump").write_bytes(b"TAMPERED")

    touched: list[str] = []
    monkeypatch.setattr(manager, "_psql", lambda *a, **k: touched.append("psql") or "")
    monkeypatch.setattr(manager, "_run_client", lambda *a, **k: touched.append("client"))

    with pytest.raises(manager.BackupError, match="CHECKSUM MISMATCH"):
        manager.cmd_restore(argparse.Namespace(name=name, target="src_rehearsal", force=False))

    assert touched == [], "the database was contacted despite a failed checksum"


# ------------------------------------------------------------- source protection


def test_restore_refuses_to_target_the_source_database(manager, tmp_path, monkeypatch):
    name = _make_backup(manager, tmp_path)
    monkeypatch.setattr(manager, "_psql", lambda *a, **k: pytest.fail("database touched"))

    with pytest.raises(manager.BackupError, match="refusing to restore over the source"):
        manager.cmd_restore(argparse.Namespace(name=name, target="src", force=False))


def test_cleanup_refuses_to_drop_the_source_database(manager, monkeypatch):
    monkeypatch.setattr(manager, "_psql", lambda *a, **k: pytest.fail("DROP was issued"))

    with pytest.raises(manager.BackupError, match="refusing to drop the SOURCE database"):
        manager.cmd_cleanup(argparse.Namespace(target="src", force=False))


def test_cleanup_refuses_a_target_that_is_not_a_rehearsal_copy(manager, monkeypatch):
    monkeypatch.setattr(manager, "_psql", lambda *a, **k: pytest.fail("DROP was issued"))

    with pytest.raises(manager.BackupError, match="does not look like a rehearsal"):
        manager.cmd_cleanup(argparse.Namespace(target="production_data", force=False))


def test_cleanup_drops_only_the_rehearsal_database(manager, monkeypatch):
    issued: list[str] = []
    monkeypatch.setattr(manager, "_psql", lambda cfg, db, sql: issued.append(sql) or "")

    assert manager.cmd_cleanup(argparse.Namespace(target="src_rehearsal", force=False)) == 0
    assert any("src_rehearsal" in sql for sql in issued)
    assert not any('DROP DATABASE "src"' in sql for sql in issued)


# ------------------------------------------------------------ target protection


def test_restore_rejects_a_non_empty_target_without_force(manager, tmp_path, monkeypatch):
    name = _make_backup(manager, tmp_path)

    def fake_psql(cfg, database, sql):
        if "pg_database" in sql:
            return "1"          # the target already exists
        if "pg_tables" in sql:
            return "18"         # and it is populated
        return ""

    monkeypatch.setattr(manager, "_psql", fake_psql)
    monkeypatch.setattr(manager, "_run_client",
                        lambda *a, **k: pytest.fail("pg_restore ran against a non-empty target"))

    with pytest.raises(manager.BackupError, match="Refusing to restore into a non-empty target"):
        manager.cmd_restore(argparse.Namespace(name=name, target="src_rehearsal", force=False))


def test_backup_refuses_to_overwrite_an_existing_artifact(manager, tmp_path, monkeypatch):
    name = _make_backup(manager, tmp_path)
    monkeypatch.setattr(manager, "_psql", lambda *a, **k: pytest.fail("database touched"))

    with pytest.raises(manager.BackupError, match="refusing to overwrite"):
        manager.cmd_backup(argparse.Namespace(name=name))


# --------------------------------------------------------------- restore result


def test_a_failed_pg_restore_cannot_report_success(manager, tmp_path, monkeypatch):
    """The decisive property: a non-zero pg_restore must raise, never return 0."""

    name = _make_backup(manager, tmp_path)

    def fake_psql(cfg, database, sql):
        if "pg_database" in sql:
            return ""           # target does not exist
        if "pg_tables" in sql:
            return "0"          # freshly created and empty
        return ""

    class Failed:
        returncode = 1
        stdout = ""
        stderr = "pg_restore: error: could not read from input file"

    monkeypatch.setattr(manager, "_psql", fake_psql)
    monkeypatch.setattr(manager, "_run_client", lambda *a, **k: Failed())

    with pytest.raises(manager.BackupError, match="pg_restore FAILED"):
        manager.cmd_restore(argparse.Namespace(name=name, target="src_rehearsal", force=False))


# ---------------------------------------------------------------------- parity


def _parity_with(manager, monkeypatch, source_values: dict, restored_values: dict):
    def fake_psql(cfg, database, sql):
        table = source_values if database == "src" else restored_values
        for key, value in table.items():
            if key in sql:
                return value
        return "0"

    monkeypatch.setattr(manager, "_psql", fake_psql)
    return manager.cmd_parity(argparse.Namespace(target="src_rehearsal"))


def test_parity_fails_on_a_migration_revision_mismatch(manager, monkeypatch, capsys):
    code = _parity_with(
        manager, monkeypatch,
        {"version_num": "rev_A", "to_regclass": "t"},
        {"version_num": "rev_B", "to_regclass": "t"},
    )
    assert code == 1, "a differing migration revision was reported as parity"
    assert "migration_revision" in capsys.readouterr().out


def test_parity_fails_on_a_row_count_mismatch(manager, monkeypatch, capsys):
    code = _parity_with(
        manager, monkeypatch,
        {"version_num": "rev", "to_regclass": "t", "count(*) FROM \"customers\"": "7"},
        {"version_num": "rev", "to_regclass": "t", "count(*) FROM \"customers\"": "3"},
    )
    assert code == 1, "a differing row count was reported as parity"
    assert "customers" in capsys.readouterr().out


def test_parity_fails_when_a_critical_table_is_absent_from_the_source(manager, monkeypatch, capsys):
    def fake_psql(cfg, database, sql):
        if "to_regclass" in sql:
            return "f"          # every critical table reported missing
        if "version_num" in sql:
            return "rev"
        return "0"

    monkeypatch.setattr(manager, "_psql", fake_psql)
    assert manager.cmd_parity(argparse.Namespace(target="src_rehearsal")) == 1
    assert "absent from the SOURCE" in capsys.readouterr().out


def test_parity_passes_when_everything_matches(manager, monkeypatch):
    values = {"version_num": "rev", "to_regclass": "t"}
    assert _parity_with(manager, monkeypatch, values, dict(values)) == 0


# --------------------------------------------------------------- no credentials


def test_sanitize_removes_passwords_and_connection_urls(manager):
    cfg = {"password": "secret-pw"}
    text = "failed with PGPASSWORD=secret-pw for postgresql://u:secret-pw@db:5432/x"
    cleaned = manager._sanitize(text, cfg)

    assert "secret-pw" not in cleaned
    assert "postgresql://" not in cleaned
    assert "[REDACTED" in cleaned


def test_metadata_never_carries_credentials(manager, tmp_path):
    name = _make_backup(manager, tmp_path)
    metadata = json.loads((tmp_path / f"{name}.metadata.json").read_text(encoding="utf-8"))

    forbidden = {"password", "url", "dsn", "secret", "token", "connection"}
    present = {k for k in metadata if any(word in k.lower() for word in forbidden)}
    assert not present, f"metadata carries credential-shaped keys: {present}"
