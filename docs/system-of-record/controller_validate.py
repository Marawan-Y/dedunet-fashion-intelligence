"""Controller integrity validator for the Fashion Commerce Codex pack.

Checks, per AGENTS.md and the Shared Interface Contract:
  1. every CSV register parses
  2. only allowed evidence statuses appear -- in the columns that actually use them
  2b. supersession state is valid, and independent of readiness
  3. no duplicate artifact IDs within a register
  4. every LIVE path reference exists on disk
  5. ExecPlan files carry all 17 required sections
  6. no unsupported completion / external-reality language

SCOPING (added 2026-08-24)
--------------------------
This validator previously reported 585 errors and every one was a false positive, produced
by inspecting things it does not govern. A validator that is permanently red governs
nothing: no one can distinguish a new error from the 585 already there, so the next real
finding arrives invisible.

The rules below narrow WHAT IS INSPECTED. None of them narrows WHAT IS ENFORCED. An invalid
evidence status in a register this validator governs still fails, and
`test_controller_validate.py` proves that in both directions -- valid vocabulary passes,
invalid vocabulary fails -- so the scoping cannot silently become a way of not checking.
"""
import csv
import io
import os
import re
import sys
from pathlib import Path

# Derived, not hard-coded. The previous absolute path meant this file only worked on one
# machine, and on any other would either crash or silently validate the wrong tree.
# docs/system-of-record/controller_validate.py -> repository root
ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- SCOPE 1: dependencies
#
# Dependency, build and cache trees are not repository content and this programme's rules
# have no authority over them. `apps/mobile/node_modules` alone produced an UNSUPPORTED
# CLAIM error for Expo's own README saying "Production-ready." -- a true statement, by a
# third party, about their software, which we can neither fix nor are asked to.
EXCLUDED_DIRS = {
    "node_modules", "__pycache__", ".git", ".pytest_cache", ".expo", ".next",
    "dist", "build", "coverage", "htmlcov", ".venv", "venv", "site-packages",
    ".mypy_cache", ".ruff_cache", "vendor", ".tox", ".gradle", "Pods",
}


def in_excluded_tree(path) -> bool:
    """True if any path segment names a dependency, build or cache directory."""

    return any(part in EXCLUDED_DIRS for part in Path(path).parts)


def walk(pattern):
    """`ROOT.rglob`, minus dependency, build and cache trees."""

    return [p for p in ROOT.rglob(pattern) if not in_excluded_tree(p)]


# ---------------------------------------------------------------- SCOPE 2: whose schema
#
# `handoffs/incoming/` holds immutable partner data packages. They carry their own schema
# and their own vocabulary -- `PROTOTYPE_CONCEPT`, `prototype_unavailable`,
# `ORIGINAL_PROTOTYPE_ASSET` -- and their own validator, `scripts/validation/
# verify_side_a_package.py`, plus a SHA-256 manifest that fails if a byte changes.
#
# Applying THIS programme's readiness vocabulary to THEIR files produced 93 errors that
# could never be fixed: the package is immutable by design, so the only way to satisfy the
# check would be to break the manifest.
PARTNER_DATA_PREFIX = "handoffs/incoming/"


def is_partner_data(rel_path: str) -> bool:
    return rel_path.startswith(PARTNER_DATA_PREFIX)


# ---------------------------------------------------------------- SCOPE 3: which columns
#
# The seven readiness statuses in AGENTS.md govern ARTIFACT READINESS. The previous rule
# -- `if "status" in header.lower()` -- applied them to every column whose name happened to
# contain the substring, which is how the validator came to insist that:
#
#     runtime_status   = build-time                240 errors
#     migration_status = DONE                       67 errors
#     inventory_status = prototype_unavailable      62 errors
#     ownership_status = ORIGINAL_PROTOTYPE_ASSET   31 errors
#
# were invalid evidence statuses. They are not evidence statuses at all. A column is not an
# evidence-status column because its name ends in `_status`; it is one because it carries
# the readiness vocabulary, which is a property of the register's schema.
#
# Derived empirically and then fixed here: across every non-partner register, these two
# columns carry the readiness vocabulary in 100% of populated rows (76 and 114 rows), and
# `status` carries it in every non-partner register that uses it.
EVIDENCE_STATUS_COLUMNS = {"artifact_status", "readiness_status", "status", "evidence_status"}

# DEC-009 declares risk state a SEPARATE axis from artifact readiness.
RISK_STATE_COLUMNS = {"current_status"}

# ---------------------------------------------------------------- SCOPE 6: two axes
#
# READINESS ("how well is this proven?") and SUPERSESSION ("is this still the current
# record?") are independent facts, and `docs/side-b/EVIDENCE_INDEX.csv` used to carry both
# in one `status` column. Writing SUPERSEDED there overwrote -- and destroyed -- the
# readiness the evidence document had declared, for four rows.
#
# They are now separate columns, so a superseded record keeps its historical readiness:
#
#     SB-EV-BOOT-002   readiness_status=AUTOMATED-TESTED   supersession_status=SUPERSEDED
#
# SUPERSEDED is deliberately NOT added to ALLOWED_STATUS. It was never a readiness value,
# and admitting it there would have re-legalised the overwrite that lost the data.
#
# Named for supersession rather than "lifecycle" on purpose: `lifecycle_status` is already
# taken in this repository for the PRODUCT business lifecycle
# (fixture|candidate|sample|approved|sellable|retired, BPC-A-003, and live in
# `app/candidate_activation.py` as `BusinessLifecycle`). Reusing the identifier for a second
# vocabulary would recreate exactly the one-name-two-meanings ambiguity this validator was
# just repaired to remove. "Supersession" is the repository's own term for this concept --
# `evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md`.
SUPERSESSION_COLUMNS = {"supersession_status"}
ALLOWED_SUPERSESSION = {"CURRENT", "SUPERSEDED"}

ALLOWED_STATUS = {
    "DRAFT", "SELF-VALIDATED", "AUTOMATED-TESTED", "HUMAN-VERIFIED",
    "EXTERNALLY-VERIFIED", "BLOCKED", "REJECTED",
}

# Phrases that would assert external reality we have no evidence for.
FORBIDDEN = [
    r"\bfactory (?:visit|audit) (?:was )?(?:completed|conducted|performed)\b",
    r"\blab(?:oratory)? (?:test|result)s? (?:were |was )?(?:completed|received|confirmed)\b",
    r"\bcustomers? (?:were |was )?interviewed\b",
    r"\bcontract (?:was |is )?signed\b",
    r"\b(?:company|trademark) (?:was |is )?registered\b",
    r"\bpayments? (?:are |is |were |was )?(?:activated|live)\b",
    r"\bapp[- ]store approval (?:was |is )?(?:granted|received)\b",
    r"\bproduction[- ]ready\b",
    r"\bshipped to (?:a )?real customer\b",
]

report = {"errors": [], "warnings": [], "info": []}


def err(m):
    report["errors"].append(m)


def warn(m):
    report["warnings"].append(m)


def info(m):
    report["info"].append(m)


def rel(p):
    try:
        return str(Path(p).relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


# ---------- 1..4 CSV registers ----------
csv_files = sorted(walk("*.csv"))
info(f"CSV registers found: {len(csv_files)} (dependency/build trees excluded)")

PATHLIKE = re.compile(r"(?:docs|evidence|handoffs|platform|\.agent|\.codex)/[\w./\-]+")

# Columns that record where something USED to be. A path here that still exists would be
# the surprising outcome, not a missing one.
HISTORICAL_PATH_COLUMNS = {"source_path", "current_path", "source_or_basis"}

# Reference columns that do not end in `_path` but are still live pointers.
LIVE_REFERENCE_COLUMNS = {"evidence", "evidence_ref", "proving_evidence", "artifact_ref"}

for path in csv_files:
    try:
        raw = path.read_text(encoding="utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(raw)))
    except Exception as e:  # noqa: BLE001
        err(f"CSV PARSE FAIL {rel(path)}: {e}")
        continue
    if not rows:
        warn(f"CSV EMPTY {rel(path)}")
        continue

    headers = [h for h in (rows[0].keys()) if h]

    # status columns.
    # DEC-009 declares risk state a SEPARATE axis from artifact readiness:
    # OPEN / PARTIALLY MITIGATED / MITIGATED / FIXED / ACCEPTED / BLOCKED.
    # The seven readiness statuses govern artifacts, not risks, so risk-state
    # columns are checked against the risk vocabulary instead.
    RISK_STATE = {"OPEN", "PARTIALLY MITIGATED", "MITIGATED", "FIXED", "ACCEPTED", "BLOCKED"}

    # SCOPE 2: a partner data package carries its own schema and its own validator.
    partner = is_partner_data(rel(path))

    for h in headers:
        key = h.lower()

        if key in RISK_STATE_COLUMNS:
            for i, r in enumerate(rows, start=2):
                v = (r.get(h) or "").strip().upper()
                if v and v not in RISK_STATE:
                    err(f"BAD RISK STATE {rel(path)}:{i} col='{h}' value='{v}'")
            continue

        # Validated independently of readiness, and against its own vocabulary.
        if key in SUPERSESSION_COLUMNS:
            for i, r in enumerate(rows, start=2):
                v = (r.get(h) or "").strip().upper()
                if v and v not in ALLOWED_SUPERSESSION:
                    err(f"BAD SUPERSESSION {rel(path)}:{i} col='{h}' value='{v}'")
            continue

        # SCOPE 3: an evidence-status column is one that carries the readiness
        # vocabulary, not one whose name happens to contain "status". `runtime_status`,
        # `migration_status`, `inventory_status` and `ownership_status` are domain
        # classifications with their own value sets and are not governed here.
        if key not in EVIDENCE_STATUS_COLUMNS or partner:
            continue

        for i, r in enumerate(rows, start=2):
            v = (r.get(h) or "").strip()
            if not v:
                continue
            for token in re.split(r"[;,/|]", v):
                t = token.strip().upper()
                if not t:
                    continue
                if t in ALLOWED_STATUS:
                    continue
                # tolerate prose in narrative columns
                if len(t) > 24 or " " in t:
                    continue
                err(f"BAD STATUS {rel(path)}:{i} col='{h}' value='{token.strip()}'")

    # duplicate IDs -- primary key only.
    # These registers carry three kinds of id-shaped column:
    #   envelope tags (register_id, register_artifact_id) - constant across all rows
    #   foreign keys (dependency_ids, decision_or_dependency_id) - legitimately repeated
    #   the actual row key (artifact_id, record_id, risk_id, contract_id, atomic_field...)
    # Rather than hardcode names, pick the id-shaped column with the most distinct
    # values: that is the row key by construction. Only that column must be unique.
    id_cols = [h for h in headers
               if h.lower().endswith("_id") or h.lower() in ("id", "atomic_field")]
    best, best_n = None, 0
    for h in id_cols:
        n = len({(r.get(h) or "").strip() for r in rows if (r.get(h) or "").strip()})
        if n > best_n:
            best, best_n = h, n
    if best and best_n > 1:
        seen = {}
        for i, r in enumerate(rows, start=2):
            v = (r.get(best) or "").strip()
            if not v:
                continue
            if v in seen:
                err(f"DUPLICATE ID {rel(path)} col='{best}' value='{v}' rows {seen[v]} and {i}")
            else:
                seen[v] = i
        if best_n == len([r for r in rows if (r.get(best) or "").strip()]):
            info(f"PK unique ({best_n} rows) on '{best}': {rel(path)}")

    # path existence
    #
    # SCOPE 4: only LIVE reference columns are checked, and historical ones are not.
    # All 140 MISSING PATH errors this check used to report were `platform/poc/...`
    # paths, in two false-positive classes:
    #
    #   HISTORICAL   `source_path` in the migration map records where a file USED to
    #                live. It must not exist -- that is what "migrated" means. Likewise
    #                `current_path` in the dated pre-restructure file-map snapshot.
    #
    #   PROSE        a `risk` cell reading "secrets in platform/poc/.env" and an
    #                `acceptance_criteria` cell reading "evidence/gate ownership" are
    #                sentences that contain path-shaped text, not path references.
    #
    # Checking every column's prose for path existence made narrative columns unwritable
    # without tripping the validator. Checking reference columns keeps the property that
    # matters: a register pointing at evidence that is not there still fails.
    for i, r in enumerate(rows, start=2):
        for h in headers:
            key = h.lower()
            if key in HISTORICAL_PATH_COLUMNS:
                continue
            if not (key.endswith(("_path", "_paths")) or key in LIVE_REFERENCE_COLUMNS):
                continue
            v = (r.get(h) or "")
            for m in PATHLIKE.findall(v):
                cand = m.rstrip(".,;")
                # Prose like "evidence/gate" or "evidence/fallback" is an or-phrase,
                # not a path. Require either a file extension or >=2 path segments
                # below the root directory before treating it as a real path.
                segs = cand.split("/")
                if "." not in segs[-1] and len(segs) < 3:
                    continue
                if not (ROOT / cand).exists():
                    err(f"MISSING PATH {rel(path)}:{i} col='{h}' -> {cand}")

# ---------- 5. ExecPlan sections ----------
REQUIRED_SECTIONS = [
    "Title, owner, status and gate",
    "Purpose and observable outcome",
    "Context and source documents read",
    "Confirmed facts, assumptions and unresolved questions",
    "Scope and explicit non-scope",
    "Dependencies and required handoffs",
    "Artifact list with stable IDs and target paths",
    "Milestones in dependency order",
    "Detailed implementation or production steps",
    "Acceptance criteria",
    "Validation commands, review procedures and expected evidence",
    "Security, privacy, compliance and operational impact",
    "Migration, rollback and recovery plan",
    "Risks, mitigations and decision points",
    "Progress log with timestamps",
    "Decision log",
    "Completion summary and residual work",
]

execplans = [p for p in walk("*.md")
             if re.search(r"EXECPLAN|EXEC_PLAN|MASTER_EXECUTION_PLAN", p.name, re.I)]
info(f"ExecPlan files found: {len(execplans)}")
for p in execplans:
    text = p.read_text(encoding="utf-8", errors="replace")
    missing = []
    for n, sec in enumerate(REQUIRED_SECTIONS, start=1):
        key = sec.split(",")[0].split(" and ")[0][:18].lower()
        if re.search(rf"^#+\s*{n}\.", text, re.M) or key in text.lower():
            continue
        missing.append(f"{n}. {sec}")
    if missing:
        err(f"EXECPLAN MISSING SECTIONS {rel(p)}: {missing}")
    else:
        info(f"ExecPlan 17/17 sections OK: {rel(p)}")

# ---------- 6. unsupported language ----------
#
# SCOPE 5: two measured false-positive classes, both fixed by looking at the right text.
#
#   CODE SPANS   A phrase inside backticks or a fenced block is being NAMED, not claimed.
#                `EV_A1_002_M1_CONDITION_CLOSURE_VALIDATION.md` was flagged for a paragraph
#                headed "False positive recorded and resolved" which quotes the offending
#                phrase in backticks while explaining that it is not a claim. That document
#                also records the fix Side A applied to its own scanner -- strip fenced code
#                blocks and inline code before matching -- so this adopts it.
#
#   WRAPPED      "Nothing here is\nproduction-ready." puts the negation on the previous
#                physical line. Checking only the matched line missed it and reported the
#                strongest disclaimer in `CONTROLLER_VALIDATION_G1_M1.md` as a claim.
#
# Both are fixed by WIDENING what is examined, never by narrowing what is forbidden. The
# FORBIDDEN list is unchanged.

CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def mask_code(text: str) -> str:
    """Blank out code spans, preserving length so line numbers stay accurate."""

    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    return INLINE_CODE.sub(blank, CODE_FENCE.sub(blank, text))


# `docs/source` is immutable third-party input; dependency trees are not ours either.
scan = [p for p in walk("*.md") if "docs/source" not in rel(p)]
for p in scan:
    text = p.read_text(encoding="utf-8", errors="replace")
    masked = mask_code(text)
    for pat in FORBIDDEN:
        for m in re.finditer(pat, masked, re.I):
            line = masked[:m.start()].count("\n") + 1
            ctx = text.splitlines()[line - 1].strip()[:150]
            # Negation window spans the sentence, not the physical line, because a line
            # break between "Nothing here is" and "production-ready" does not make it a
            # claim. Read from the masked text so a negation inside code does not excuse
            # a claim outside it.
            window = " ".join(masked[max(0, m.start() - 200):m.end() + 60].split())
            if re.search(r"\b(never|not|no|nothing|none|without|require|pending|must|cannot|prohibit|do not|blocked)\b",
                         window, re.I):
                continue
            # a line that is itself a search command scanning FOR these phrases
            # (regex alternations, rg/grep invocations) is a control, not a claim
            if re.search(r"(^|\s)(rg|grep)\s", ctx) or ctx.count("|") >= 2:
                continue
            err(f"UNSUPPORTED CLAIM {rel(p)}:{line} :: {ctx}")

# ---------- output ----------
print("=" * 70)
print("CONTROLLER INTEGRITY VALIDATION")
print("=" * 70)
for k in ("info", "warnings", "errors"):
    print(f"\n--- {k.upper()} ({len(report[k])}) ---")
    for m in report[k]:
        print(f"  {m}")
print("\n" + "=" * 70)
print(f"RESULT: {'FAIL' if report['errors'] else 'PASS'} "
      f"({len(report['errors'])} errors, {len(report['warnings'])} warnings)")
sys.exit(1 if report["errors"] else 0)
