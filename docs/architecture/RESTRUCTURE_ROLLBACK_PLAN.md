# Restructure Rollback Plan

| Control | Value |
|---|---|
| Artifact ID | ARCH-R0-005 |
| Version | 1.0 |
| Owner | Technical lead |
| Status | SELF-VALIDATED |

Rollback is cheap here by construction: the restructure is one commit containing only renames and
reference updates, on a branch, with no remote and no schema or data change.

## Restore points, cheapest first

| # | Restore point | Recovers | Cost |
|---|---|---|---|
| 1 | `git revert <restructure-commit>` | Every path, on the same branch | seconds |
| 2 | `git reset --hard e84cb09` | Pre-restructure branch state | seconds |
| 3 | Branch delete | Everything back to the last accepted state | seconds |
| 4 | Backup bundle | The entire pre-normalisation workspace | minutes |

```bash
# 1 — preferred: reverses the moves, keeps the history of having tried
git revert --no-edit <restructure-commit-sha>

# 2 — discard uncommitted or unwanted work on the branch
git reset --hard e84cb09

# 4 — full workspace reconstruction, including the old parent repository layout
git clone "C:\Users\User\Desktop\dedunet_private_evidence\git_backup\
           claude-workspace-full-20260803-203833.bundle" restored
#    sha256 c0a4b527dfb773a407896d202de8e822de7a7f96c9b2de6293f8e6016a777332
```

## Why rollback is low-risk

**No data changes.** No migration runs, no schema alters, no seed executes. The SQLite database
is untracked and untouched. Reverting file paths cannot corrupt data that was never written.

**No behaviour changes.** Only renames plus the reference updates those renames force. If the
83 tests pass after the restructure and passed before it, the two trees are behaviourally
equivalent by the only measure available.

**History survives either way.** `git mv` records renames; revert restores paths without losing
the record.

**The container is decoupled.** A running stack keeps serving from its built image regardless of
host paths. A rollback needs at most `docker compose up --build` again.

## What rollback does NOT undo

| Item | Why it persists | Recovery |
|---|---|---|
| Git-root normalisation | A separate, already-accepted correction | Restore `OLD_PARENT_REPO.git` — see `GIT_ROOT_NORMALIZATION.md` |
| Unredacted PDF purge | Deliberately irreversible in the active repo | Only via the backup bundle, which reintroduces the personal data |
| Deleted `platform/poc.zip` | Verified duplicate, 0 unique files | Reproducible from any commit |
| Purged `__pycache__` | Regenerated on next run | None needed |

**The purge is intentionally hard to undo.** That is the point of a personal-data removal. Anyone
rolling back far enough to recover it is reintroducing the founder's home address into version
control and must treat that as a deliberate act.

## Triggers — roll back rather than fix forward if

1. Test count is not exactly 83, or any test fails.
2. Mutation harness is not 19/19 with 0 survivors.
3. A fixture checksum changed.
4. `--assess-sellable` starts exiting 0 — a fail-open regression is worse than a broken build.
5. Docker cannot build or reach healthy.
6. The Side A manifest stops verifying at 54/54.
7. Any secret or runtime artefact becomes tracked.

Triggers 3, 4 and 7 are non-negotiable: they are correctness and safety regressions, not
inconvenience, and must not be "fixed forward" under time pressure.

## Procedure

1. Stop. Do not layer a fix onto a failed restructure.
2. Capture the failure: exact command, output, exit code, into `evidence/restructuring/`.
3. Roll back with restore point 1 or 2.
4. Re-run the baseline and confirm it matches `BASELINE_BEFORE_RESTRUCTURE.md` exactly.
5. Record the failure and cause in `RESTRUCTURE_COMPLETION_REPORT.md` with status
   `RESTRUCTURE_FAILED`.
6. Only then plan a corrected attempt.

A rollback is not a failure of process — it is the process working. Reporting
`RESTRUCTURE_VERIFIED` over a partially broken tree would be.
