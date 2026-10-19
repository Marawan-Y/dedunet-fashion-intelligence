"""Run the mutation harness in a DISPOSABLE GIT WORKTREE, never in the active tree.

WHY THIS EXISTS.

The harness edits real source files in place and restores them afterwards. Run against the
checkout you are working in, that is a loaded gun: an interrupted run leaves a deliberately
broken line behind, and anything that stages files while it is mid-flight commits that line.

It happened. Commit `186891e` on the Dido branch carried

    "last_error": f"terminal: {exc}",  # MUTATED: claim retained

into the repository because `git add -A` ran while the harness was working. CI caught it,
which is the system behaving correctly, but a failed head is a hard stop and the cost was a
wasted acceptance cycle chasing nine test failures that were self-inflicted.

So the harness gets its own copy of the tree. `git worktree add --detach` gives it one at a
specific commit, in a directory nothing else touches, removed when the run ends. The active
branch cannot acquire a mutation marker no matter what the harness does, and an interrupted
run leaves a stray directory rather than a broken repository.

    python scripts/validation/run_mutation_isolated.py            # HEAD
    python scripts/validation/run_mutation_isolated.py --rev <sha>
    python scripts/validation/run_mutation_isolated.py -- --only M90_...

Everything after `--` is passed through to the harness.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Dependency stores the guarding tests need but a fresh checkout never has. Six backend
#: test modules gate themselves on `apps/mobile/node_modules/jsdom` and hand that directory
#: to node as NODE_PATH.
SHARED_NODE_MODULES = (Path("apps") / "mobile" / "node_modules",)


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, **kwargs)


def _share_node_modules(worktree: Path) -> list[tuple[Path, Path]]:
    """Point the worktree at the already-installed node modules.

    ISOLATION MUST NOT COST COVERAGE. A fresh worktree has no installed dependencies, and
    the six test modules that drive node skip themselves when jsdom is missing. pytest
    exits 0 when every selected test is skipped, so the harness reports those mutations
    INCONCLUSIVE -- correctly, and INCONCLUSIVE is a failure, not a pass. The first
    isolated run turned nine real verdicts into shrugs for exactly this reason.

    A link rather than a copy: the harness never writes inside node_modules, and copying it
    for every run would cost more than the run. A junction on Windows, which needs no
    elevation, unlike a directory symlink.
    """

    shared: list[tuple[Path, Path]] = []
    for rel in SHARED_NODE_MODULES:
        source = ROOT / rel
        if not source.is_dir():
            print(
                f"mutation harness: {rel.as_posix()} is not installed, so the guards that "
                "need node will report INCONCLUSIVE"
            )
            continue
        dest = worktree / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            made = _run(["cmd", "/c", "mklink", "/J", str(dest), str(source)])
            failed = made.returncode != 0
            detail = (made.stderr or made.stdout).strip()
        else:
            try:
                os.symlink(source, dest, target_is_directory=True)
                failed, detail = False, ""
            except OSError as exc:  # pragma: no cover - platform dependent
                failed, detail = True, str(exc)
        if failed:
            print(f"mutation harness: could not link {rel.as_posix()}: {detail}")
            continue
        shared.append((source, dest))
    return shared


def _unshare_node_modules(shared: list[tuple[Path, Path]]) -> None:
    """Drop the links BEFORE the worktree is deleted.

    This ordering is the whole safety argument. Deleting a tree that contains a junction
    can follow it, and on the other side is the real, installed node_modules. `os.rmdir`
    removes the reparse point itself and never touches what it points at.
    """

    for _source, dest in shared:
        try:
            os.rmdir(dest)
        except OSError as exc:
            print(
                f"mutation harness: WARNING: could not unlink {dest}: {exc}. Not deleting "
                "the worktree, because doing so could reach through the link.",
                file=sys.stderr,
            )
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rev",
        default="HEAD",
        help="commit to test (default HEAD). The worktree is detached at this revision.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="leave the worktree in place for inspection after the run",
    )
    parser.add_argument("passthrough", nargs="*", help="arguments for the harness")
    args = parser.parse_args()

    # A dirty tree means the thing being tested is not the thing committed. Refuse rather
    # than silently test a revision that does not include the work in progress.
    status = _run(["git", "status", "--porcelain"], cwd=ROOT)
    if status.stdout.strip():
        print("REFUSING: the working tree has uncommitted changes.", file=sys.stderr)
        print(
            "The worktree is created from a COMMIT, so uncommitted work would not be "
            "tested and the result would describe something else.",
            file=sys.stderr,
        )
        print(status.stdout, file=sys.stderr)
        return 2

    resolved = _run(["git", "rev-parse", args.rev], cwd=ROOT)
    if resolved.returncode != 0:
        print(f"REFUSING: cannot resolve {args.rev!r}", file=sys.stderr)
        return 2
    sha = resolved.stdout.strip()

    parent = Path(tempfile.mkdtemp(prefix="dedunet-mutation-"))
    worktree = parent / "tree"
    print(f"mutation harness: isolated worktree at {worktree}")
    print(f"mutation harness: testing {sha[:12]}")

    added = _run(["git", "worktree", "add", "--detach", str(worktree), sha], cwd=ROOT)
    if added.returncode != 0:
        print(added.stderr, file=sys.stderr)
        shutil.rmtree(parent, ignore_errors=True)
        return 2

    shared = _share_node_modules(worktree)

    try:
        harness = worktree / "scripts" / "validation" / "mutation_guard_check.py"
        result = subprocess.run(
            [sys.executable, str(harness), *args.passthrough],
            cwd=worktree,
            text=True,
        )
        exit_code = result.returncode
    finally:
        if args.keep:
            print(f"mutation harness: worktree kept at {worktree}")
        else:
            _unshare_node_modules(shared)
            # Remove the registration first, then the files. The reverse order leaves git
            # holding a record of a worktree that is no longer there.
            _run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT)
            shutil.rmtree(parent, ignore_errors=True)
            _run(["git", "worktree", "prune"], cwd=ROOT)

    # Insurance against the one way linking could go badly wrong. If cleanup had followed
    # a junction, the installed dependencies would be gone, and the next thing anyone would
    # see is unrelated tests skipping for a week.
    for source, _dest in shared:
        if not source.is_dir():
            print(
                f"ERROR: {source} disappeared during the run. Worktree cleanup followed a "
                "link into the real dependency store. Reinstall before trusting any result.",
                file=sys.stderr,
            )
            return 1

    # The active tree must be exactly as it was. This is the invariant the whole script
    # exists for, so it is checked rather than assumed.
    after = _run(["git", "status", "--porcelain"], cwd=ROOT)
    if after.stdout.strip():
        print(
            "WARNING: the active tree changed during an isolated run. That should be "
            "impossible; investigate before committing.",
            file=sys.stderr,
        )
        print(after.stdout, file=sys.stderr)
        return 1

    markers = _run(
        ["git", "grep", "-n", "# MUTATED", "--", "services", "apps", "scripts"], cwd=ROOT
    )
    leaked = [
        line
        for line in markers.stdout.splitlines()
        if "mutation_guard_check.py" not in line and "run_mutation_isolated.py" not in line
    ]
    if leaked:
        print("WARNING: a mutation marker is present in the active tree:", file=sys.stderr)
        print("\n".join(leaked), file=sys.stderr)
        return 1

    print("mutation harness: active tree verified clean")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
