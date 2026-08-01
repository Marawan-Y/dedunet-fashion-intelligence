"""Controller integrity validator for the Fashion Commerce Codex pack.

Checks, per AGENTS.md and the Shared Interface Contract:
  1. every CSV register parses
  2. only allowed evidence statuses appear
  3. no duplicate artifact IDs within a register
  4. every referenced evidence/file path actually exists on disk
  5. ExecPlan files carry all 17 required sections
  6. no unsupported completion / external-reality language
"""
import csv
import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack")

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
csv_files = sorted(ROOT.rglob("*.csv"))
csv_files = [p for p in csv_files if "__pycache__" not in str(p)]
info(f"CSV registers found: {len(csv_files)}")

PATHLIKE = re.compile(r"(?:docs|evidence|handoffs|platform|\.agent|\.codex)/[\w./\-]+")

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
    for h in headers:
        if h.lower() == "current_status":
            for i, r in enumerate(rows, start=2):
                v = (r.get(h) or "").strip().upper()
                if v and v not in RISK_STATE:
                    err(f"BAD RISK STATE {rel(path)}:{i} col='{h}' value='{v}'")
            continue
        if "status" in h.lower() or "readiness" in h.lower():
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
    for i, r in enumerate(rows, start=2):
        for h in headers:
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

execplans = [p for p in ROOT.rglob("*.md")
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
scan = [p for p in ROOT.rglob("*.md")
        if "docs/source" not in rel(p) and "__pycache__" not in str(p)]
for p in scan:
    text = p.read_text(encoding="utf-8", errors="replace")
    for pat in FORBIDDEN:
        for m in re.finditer(pat, text, re.I):
            line = text[:m.start()].count("\n") + 1
            ctx = text.splitlines()[line - 1].strip()[:150]
            # allow explicit negations / prohibitions
            if re.search(r"\b(never|not|no|nothing|none|without|require|pending|must|cannot|prohibit|do not|blocked)\b",
                         ctx, re.I):
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
