# Backup and Restore Runbook

| Control | Value |
|---|---|
| Artifact ID | OPS-BR-001 |
| Owner | Marawan Younis (secrets and infrastructure risk owner) |
| Status | **`LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED`** |
| Applies to | The locally verified staging topology only |

This is **not** `PRODUCTION_DISASTER_RECOVERY_VERIFIED`. One rehearsal on a developer
machine is not a recovery guarantee.

---

## Four operations that are frequently confused

Naming these apart matters more than any script here: three of them are routine and one
destroys data.

| Operation | Command | Destroys data? |
|---|---|---|
| **Normal shutdown** | `docker compose -f docker-compose.staging.yml stop` | No. Containers stop; the volume survives |
| **Destructive reset** | `docker compose -f docker-compose.staging.yml down -v` | **YES — deletes the database volume permanently** |
| **Backup** | `python infrastructure/backup/backup_manager.py backup` | No. Read-only against the source |
| **Restore rehearsal** | `python infrastructure/backup/backup_manager.py rehearse` | No. Restores into a *separate* database |

`down -v` is the only one that loses data. It is a deliberate reset, **never** a normal
shutdown, and it must not appear in routine instructions.

---

## Taking a backup

```bash
python infrastructure/backup/backup_manager.py backup
```

Produces three artifacts in `backups/` (git-ignored):

```text
<db>-<UTC timestamp>.dump            custom format
<db>-<UTC timestamp>.dump.sha256     checksum sidecar
<db>-<UTC timestamp>.metadata.json   safe metadata
```

An existing name is never overwritten — a backup that silently replaced an earlier one
destroys the only copy of an older state. A failed `pg_dump` removes its partial file, so
a partial artifact is never presented as a completed backup.

Runs `pg_dump` in an ephemeral `postgres:16-alpine` container, matching the server's major
version. The API image gains no backup tooling. The password is passed by environment,
never in `argv`, because command lines appear in `ps`.

## Verifying a backup

```bash
python infrastructure/backup/backup_manager.py verify --name <backup-name>
```

Non-zero on a modified dump, a missing sidecar, malformed metadata, or metadata whose
checksum disagrees with the sidecar.

## Rehearsing a restore

```bash
python infrastructure/backup/backup_manager.py rehearse     # backup + verify + restore + parity
```

Or step by step:

```bash
python infrastructure/backup/backup_manager.py restore --name <backup-name>
python infrastructure/backup/backup_manager.py parity
python infrastructure/backup/backup_manager.py cleanup      # explicit; never automatic
```

The restore always targets `<database>_rehearsal`. It refuses the source database
outright, refuses a populated target without `--force`, and verifies the checksum **before**
contacting the database at all.

Cleanup is a separate, explicit action. It refuses to drop the source database and refuses
any target that does not look like a rehearsal copy.

## Recovering for real

Not yet rehearsed and therefore not documented as a procedure. Restoring **over** a live
database is deliberately unsupported by this tooling. A real recovery would be: stop the
API, rename or drop the damaged database by hand, restore into a fresh one, point
`DATABASE_URL` at it, and restart. **That path has not been executed and must not be
treated as verified.**

---

## Honest recovery objectives

```text
Current RPO: time since the last successfully completed backup.
             Backups are OPERATOR-TRIGGERED. Nothing schedules them.
             If nobody ran one today, the RPO is "since whenever someone last did".

Current RTO evidence: measured isolated restore rehearsal duration ONLY.
             Observed: ~2.0s restore for a ~51 KB dump of a small staging dataset.
             This is NOT a production RTO. It scales with data volume, and it excludes
             detection time, decision time, DNS, redeploy and verification.
```

Explicitly **not** claimed: scheduled backups, offsite copies, geographic redundancy,
encrypted remote storage, production RPO/RTO, automatic disaster recovery.

## Personal data and storage

Database dumps contain customer records, password hashes and order history.

- `backups/` is git-ignored and verified untracked.
- Artifacts must never be committed, uploaded, pasted into chat or attached to an issue.
- Metadata carries no password, connection URL or secret — a test asserts no
  credential-shaped keys exist.
- File permissions are tightened to `0600` where the platform supports it. **On Windows
  `chmod` is a no-op**, so on this machine the artifacts inherit directory ACLs.
- **Deletion is not secure erasure.** Removing a dump unlinks it; the blocks remain on disk
  until overwritten. On an SSD, wear levelling means even overwriting does not guarantee
  destruction. Treat any machine that has held a dump as having held the data.
- Encryption at rest for offsite or hosted backups is a future external requirement.

## Failure modes and what they mean

| Symptom | Meaning | Action |
|---|---|---|
| `CHECKSUM MISMATCH` | The dump changed since it was written | Do **not** restore it. Take a fresh backup; investigate the storage |
| `checksum sidecar is missing` | Incomplete artifact set | Treat the backup as unusable |
| `metadata is malformed` | Interrupted write or manual edit | Re-verify; prefer a fresh backup |
| `refusing to restore over the source database` | Working as designed | Target `<db>_rehearsal` |
| `Refusing to restore into a non-empty target` | Target holds data | Confirm it is disposable, then `--force` |
| `pg_restore FAILED` | The dump did not restore | The backup is **not** usable. Do not report success |
| parity `FAIL` | Restored content differs from source | Investigate before trusting any backup from that period |

## Verification history

| Date | Result | Detail |
|---|---|---|
| 2026-08-04 | PASS | 18/18 tables row-count parity; schema, index, FK, CHECK, unique and PK parity; migration revision `c2f8d1b40e77` matched; 12/12 functional checks on the restored database; 23/23 failure-mode checks |
