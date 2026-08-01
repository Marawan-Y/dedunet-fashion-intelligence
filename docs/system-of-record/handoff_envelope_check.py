"""Controller handoff-envelope validator.

Shared_Cross_Team_Agent_Interface_Contract.md requires every handoff to carry:
  stable ID, sender/receiver, work-package and artifact IDs, purpose, files/data,
  schema/version, confirmed facts, assumptions, questions, acceptance criteria,
  validation steps, need-by gate/date, impact, fallback, change-control statement.
"""
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack")

REQUIRED = {
    "stable ID":            r"handoff[_ ]?id|^\|\s*ID\b|\bHO-[A-Z]|\bSB-HO-",
    "sender":               r"\bsender\b|\bfrom\b:",
    "receiver":             r"\breceiver\b|\bto\b:",
    "work-package IDs":     r"work[- ]package",
    "artifact IDs":         r"artifact[_ ]?id",
    "purpose":              r"\bpurpose\b",
    "files/data":           r"\bfiles?\b|\bdata\b|\bpayload\b|\battach",
    "schema/version":       r"\bschema\b|\bversion\b",
    "confirmed facts":      r"confirmed fact",
    "assumptions":          r"\bassumption",
    "questions":            r"\bquestion",
    "acceptance criteria":  r"acceptance criteri",
    "validation steps":     r"\bvalidation\b",
    "need-by gate/date":    r"need[- ]by|\bneeded by\b",
    "impact":               r"\bimpact\b",
    "fallback":             r"\bfallback\b",
    "change control":       r"change[- ]control",
    "disposition":          r"accept|reject|conditional",
}

files = sorted(ROOT.rglob("handoffs/**/*.md"))
print("=" * 70)
print("HANDOFF ENVELOPE VALIDATION")
print("=" * 70)
if not files:
    print("no handoff files found")
    sys.exit(1)

fail = 0
for f in files:
    text = f.read_text(encoding="utf-8", errors="replace")
    missing = [k for k, pat in REQUIRED.items()
               if not re.search(pat, text, re.I | re.M)]
    rel = str(f.relative_to(ROOT)).replace("\\", "/")
    if missing:
        fail += 1
        print(f"\nFAIL {rel}\n     missing: {', '.join(missing)}")
    else:
        print(f"\nPASS {rel}  ({len(REQUIRED)}/{len(REQUIRED)} envelope fields)")

print("\n" + "=" * 70)
print(f"RESULT: {len(files) - fail}/{len(files)} handoffs pass envelope check")
sys.exit(1 if fail else 0)
