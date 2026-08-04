# Workstream D — Backup and Restore

| Control | Value |
|---|---|
| Artifact ID | EV-WSD-001 |
| Date | 2026-08-04 |
| Owner | Technical lead |
| Status | **`LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED`** |
| **Decision** | **`WORKSTREAM_D_VERIFIED`** |

Not `PRODUCTION_DISASTER_RECOVERY_VERIFIED`. One rehearsal on a developer machine is not a
recovery guarantee, and nothing here is presented as one.

## 1. Client / server compatibility

```text
server  : 16.14
pg_dump : pg_dump (PostgreSQL) 16.14
```

Both come from `postgres:16-alpine`, so the client major version matches the server by
construction rather than by coincidence. The API image gains no backup tooling — an
ephemeral client container runs `pg_dump`, `pg_restore` and `psql`.

## 2–4. Source database before backup

| Item | Value |
|---|---|
| Migration revision | `c2f8d1b40e77` |
| Tables | 18 |
| Row manifest | customers=2, products=1, variants=1, inventory_items=1, notifications=3, orders=0 |

Test data is deliberately labelled (`restore-test@dedunet.example`,
`restore-test-item`) — staging still runs `SEED_DEMO_DATA=0`, so this is purpose-created
rehearsal data, not the demo seed returning by the back door.

## 5–8. Backup

```json
{
  "backup": "dedunet_staging-20260804T124542Z",
  "size_bytes": 51315,
  "sha256": "9655c71895b4c8ff31d56092c292b66579df639c17ffa0b85d6f5d1f44c098ad",
  "revision": "c2f8d1b40e77",
  "duration_seconds": 1.42
}
```

Three artifacts: `.dump` (custom format), `.dump.sha256`, `.metadata.json`.

Metadata carries backup timestamp, database, server version, client version, format, size,
checksum algorithm and value, migration revision, repository commit, environment and
result. It carries **no** password, connection URL, secret or personal credential — a test
asserts no credential-shaped keys exist.

The dump is written **inside** the container to a mounted directory, never streamed through
the host shell: `docker compose exec` allocates a TTY and would corrupt a binary dump. The
password travels by environment, never in `argv`, because command lines are visible in `ps`.

## 9–11. Verification and isolated restore

```text
verify  -> {"verified": "...", "sha256": "9655c718...c098ad"}
restore -> {"restored_into": "dedunet_staging_rehearsal", "duration_seconds": 2.02}
```

The checksum is verified **before** the database is contacted at all. The target is created
fresh and asserted empty before `pg_restore` runs. Migrations were **not** run against the
restored database — the dump itself must carry the recorded migration state, and it did.

## 12–15. Parity — source versus restored

| Check | Match |
|---|---|
| migration revision (`c2f8d1b40e77`) | ✅ |
| table names | ✅ |
| table count (18) | ✅ |
| index names | ✅ |
| foreign keys | ✅ |
| check constraints | ✅ |
| unique constraints | ✅ |
| primary keys | ✅ |
| notification status counts | ✅ |

Row counts compared for **all 18 critical tables**, every one matching: customers,
addresses, products, variants, inventory_items, carts, cart_lines, orders, order_lines,
reservations, payments, shipments, return_requests, notifications, promotions,
analytics_events, audit_logs, alembic_version.

Tables are listed explicitly rather than discovered, so a table silently vanishing from the
dump is a failure rather than something the comparison quietly skips.

## 16. Functional validation against the restored database

| # | Check | Result |
|---|---|---|
| 1 | `/ready` connectivity | ok |
| 2 | Catalog read | 1 product |
| 3 | Customer authentication | **true** |
| 4 | Administrator authentication | **true** |
| 5 | Order reads | 0 orders (matches source) |
| 6 | Notification lease fields readable | `attempts`, `sent_at`, `claimed_at`, `claim_expires_at`, `claim_token` |
| 7 | Migration drift | none — `c2f8d1b40e77` |
| 8 | Temporary write rolled back | true |
| 9 | Foreign-key enforcement | `IntegrityError` — live |
| 10 | Invalid notification status | `IntegrityError` — CHECK live |
| 11 | Inventory constraint | `IntegrityError` — live |
| 12 | Clean disconnect | ok |

Constraints are not merely present in the schema dump — they were **exercised** and
rejected bad writes. A restore that recreates constraint definitions but not their
enforcement would pass a schema diff and fail in production.

## 17–20. Failure modes — 23/23

| Case | Exit | Behaviour |
|---|---|---|
| Corrupted dump, verify | 1 | `CHECKSUM MISMATCH` naming both digests |
| Corrupted dump, restore | 1 | Refused; **`pg_restore` never ran** |
| Missing checksum sidecar | 1 | Clear message |
| Malformed metadata | 1 | Fails safely |
| Missing dump | 1 | Clear message |
| Restore targeting the source database | 1 | Refused |
| Cleanup targeting the source database | 1 | Refused |
| Cleanup of a non-rehearsal name | 1 | Refused |
| Non-empty target without `--force` | 1 | Refused, override named |
| Overwriting an existing backup name | 1 | Refused |
| Credentials in output | — | Password absent; no connection URL |
| Partial artifact | — | Metadata records an explicit `completed` result |

### The measurement bug worth recording

The first attempt at these checks used `cmd 2>&1 | tail -1; echo "exit=$?"` — which reports
**`tail`'s** exit status, not the command's. Every case printed `exit=0`, including the ones
that had correctly failed. The guards appeared unverified and verified at the same time, and
reporting them as working would have rested on a measurement that measured nothing.

Rewritten as a Python harness capturing `returncode` directly and asserting both the exit
code and the message. This is the third measurement-level false pass in this project, after
the R0 fail-closed check that was actually crashing and the CORS test that only checked
header presence.

## 21. Cleanup

```text
{"dropped": "dedunet_staging_rehearsal"}
rehearsal database present after cleanup : 0
SOURCE database present after cleanup    : 1
source row counts intact                 : customers=2
```

Cleanup is explicit and separate. It refuses the source database and refuses any name that
does not look like a rehearsal copy.

## 22–24. Suites and mutations

| Check | Result |
|---|---|
| SQLite full suite | **167 passed**, 1 skipped (PostgreSQL-only) |
| PostgreSQL full suite | **168 passed** |
| Mutation guards | **48 run, 48 detected, 0 survived** |

Seven new (M42–M48): checksum verified before restore; checksum mismatch fatal; restore
target differs from source; non-empty target rejected; failed `pg_restore` cannot report
success; parity reports failure; cleanup cannot drop the source.

## 25–26. Secret scan and Git status

- `backups/` git-ignored and **0 tracked files**.
- The staging password appears in no tracked file.
- Evidence contains no customer address, phone number, token or password hash.
- Working tree clean.

## 27. Known limitations

- **`LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED` only.** Not scheduled, not offsite, no
  geographic redundancy, no encryption at rest, no automatic disaster recovery.
- **RPO = time since someone last ran a backup by hand.** Nothing schedules them.
- **RTO evidence is the measured 2.02s rehearsal on a 51 KB dump.** It scales with data
  volume and excludes detection, decision, redeploy and verification time. It is not a
  production RTO.
- **Recovering over a live database is unrehearsed** and deliberately unsupported by this
  tooling. The manual path is sketched in the runbook and explicitly marked unverified.
- **`chmod 0600` is a no-op on Windows**, so on this machine artifacts inherit directory
  ACLs rather than restrictive permissions.
- **Deletion is not secure erasure.** Unlinking a dump leaves the blocks until overwritten;
  on SSDs wear levelling defeats overwriting too. Any machine that has held a dump should
  be treated as still holding the data.
- A single rehearsal proves the mechanism, not reliability over time. Repeat it whenever
  the schema changes.

## 28. Rollback

Nothing in this workstream changes application behaviour: it adds tooling, tests and
documentation. `git revert` removes them. Backup artifacts live outside version control and
are unaffected by a revert; delete them manually if required, noting the erasure limitation
above.

## 29–30. Commit and decision

**`WORKSTREAM_D_VERIFIED`** · **`LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED`**
