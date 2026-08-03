# Git Root Normalization and Personal-Data Purge

| Control | Value |
|---|---|
| Artifact ID | ARCH-R0-001 |
| Version | 1.0 |
| Date | 2026-08-03 |
| Owner | Technical lead |
| Status | VERIFIED |
| Authority | Manager decision — R0 paused for two corrections |

## Corrections executed

1. The active project became the actual Git repository root.
2. The unredacted domain letter was removed from the working tree **and from all history**.

---

## 1. Backup taken before any structural change

```text
Path   : C:\Users\User\Desktop\dedunet_private_evidence\git_backup\
         claude-workspace-full-20260803-203833.bundle
SHA-256: c0a4b527dfb773a407896d202de8e822de7a7f96c9b2de6293f8e6016a777332
Size   : 1,570,797 bytes
```

`git bundle verify` reported **"The bundle records a complete history."** It contains every
branch (`master`, `dedunet/repository-restructure-and-workstreams-a-f`) and all five commits that
existed at that moment, including the pre-purge blob.

The retired parent repository is additionally preserved in full at
`...\git_backup\OLD_PARENT_REPO.git`.

## 2. Method: history-preserving subtree extraction

`git filter-repo` is not installed. `git subtree` and `git filter-branch` are, so extraction used
`git subtree split`, which is history-preserving and required no new tooling.

```bash
# in the old parent repository
git subtree split -P Fashion_Commerce_Codex_Multi_Agent_Pack -b dedunet-extract

# in the active project
git init
git fetch <old-parent> dedunet-extract
git branch dedunet/repository-restructure-and-workstreams-a-f FETCH_HEAD
git symbolic-ref HEAD refs/heads/dedunet/repository-restructure-and-workstreams-a-f
git reset            # index from HEAD; working tree deliberately untouched
```

`git reset` (mixed) was chosen over `git checkout` so that not a single working file was
rewritten during the migration. The working tree that produced the verified baseline is the same
one that exists now.

A clean re-initialisation was **not** used. It was permitted as a fallback, but subtree split
preserved all six commits, so discarding history was unnecessary.

## 3. Commits preserved

All six, re-parented onto the new root. Hashes change because every tree is rewritten; the
content and messages do not.

| Original (old root) | Extracted | Final (post-purge) | Subject |
|---|---|---|---|
| `38219d1` | `1e94726` | `1e94726` | Baseline: governance pack + PoC before launch-candidate build |
| `a4f04ba` | `cdf5339` | `cdf5339` | Add commerce domain: auth, cart, checkout, orders, fulfilment, returns |
| `8fe83b6` | `4282dfc` | `4282dfc` | Add storefront, operations portal, migrations, docs and CI coverage |
| `9b7e256` | `e003411` | `e003411` | Fix Docker stack: declare SQLAlchemy/Alembic, bootstrap on start, serve admin |
| `e3f0118` | `faee4c1` | **`cd369b2`** | chore: checkpoint verified state and add immutable DEDUNET side-a handoff |
| `0517bff` | `4a52d5e` | **`333f2cb`** | security: replace domain evidence with a redacted copy |
| — | — | `dd4e9a2` | chore: restore `.gitignore` / `.gitattributes` at the new root |

Only the last two extracted commits changed hash during the purge. That is the expected and
verifiable signature of the operation: the unredacted blob first entered the tree at the
checkpoint commit, so that commit and every descendant had to be rewritten, while the four
commits preceding it were untouched. A purge that altered *all* hashes, or *none*, would indicate
something other than what was intended.

## 4. Exclusions verified

| Requirement | Check | Result |
|---|---|---|
| Sibling pack excluded | `git ls-files \| grep -c Two_Agent` | **0** |
| `.claude` excluded | `git ls-files \| grep -cE '^\.claude/'` | **0** |
| Nothing pushed | no remote configured | `git remote -v` empty |
| Root is the active project | `git rev-parse --show-toplevel` | `...\Fashion_Commerce_Codex_Multi_Agent_Pack` |
| Old parent no longer a repo | `git rev-parse` from parent | `fatal: not a git repository` |

## 5. Personal-data purge

```bash
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch "evidence/governance/domain/dedunet.com_ownership_letter.pdf"' \
  --prune-empty -- --all
rm -rf .git/refs/original .git/logs
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

Four independent proofs of removal:

1. Path appears in **0** commits across all refs (was 2).
2. `git rev-list --objects --all` returns only the **redacted** file.
3. `git ls-files` matches only the redacted file.
4. Blob `c060d63f3ac7af3aba1c08fdf11515ec624ee09a` is absent from the object database —
   `git cat-file -e` returns non-zero.

## 6. Two problems found and fixed during the migration

**`.gitignore` and `.gitattributes` did not survive the split.** Both lived one level *above* the
extracted prefix. Without them `.env`, `commerce.sqlite3*` and `__pycache__` would all have become
trackable at the next `git add -A`. Recreated at the new root and committed before any staging.
Verified: `git check-ignore` confirms `.env` is ignored, and `.env` appears in **0** commits.

**`.gitattributes` had to be re-scoped.** Its paths were written relative to the old root
(`Fashion_Commerce_Codex_Multi_Agent_Pack/handoffs/incoming/**`) and would have silently stopped
matching. Rewritten relative to the new root. This matters: without the `-text` rule Git would
normalise line endings inside the immutable Side A package, rewriting its bytes so it would fail
its own SHA-256 manifest on a fresh clone. Re-verified after migration: **54/54 checksums pass.**

## 7. Environment note

Git refused to operate in the project directory with `detected dubious ownership` — the directory
is owned by `Administrators` while the session runs as `User`. Resolved with git's documented
remedy, scoped to this single path:

```bash
git config --global --add safe.directory \
  "C:/Users/User/Desktop/Claude/Fashion_Commerce_Codex_Multi_Agent_Pack"
```

No filesystem ACL was modified. A fresh clone by a normal-ownership user will not need this.

## 8. Rollback

The migration is fully reversible while the backup exists.

```bash
# 1. restore the old parent repository
mv "C:\Users\User\Desktop\dedunet_private_evidence\git_backup\OLD_PARENT_REPO.git" \
   "C:\Users\User\Desktop\Claude\.git"

# 2. remove the new project-local repository
rm -rf "C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\.git"

# 3. or reconstruct everything from the bundle instead
git clone "C:\Users\User\Desktop\dedunet_private_evidence\git_backup\
           claude-workspace-full-20260803-203833.bundle" restored
```

Rolling back reinstates the unredacted PDF in history. That is the point of keeping the bundle,
and it is also why the bundle lives outside the repository and must never be committed or pushed.
