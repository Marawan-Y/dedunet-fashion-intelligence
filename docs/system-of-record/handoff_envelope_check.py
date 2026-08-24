"""Controller handoff-envelope validator.

Shared_Cross_Team_Agent_Interface_Contract.md requires every handoff to carry:
  stable ID, sender/receiver, work-package and artifact IDs, purpose, files/data,
  schema/version, confirmed facts, assumptions, questions, acceptance criteria,
  validation steps, need-by gate/date, impact, fallback, change-control statement.

SCOPING (added 2026-08-24)
--------------------------
`REQUIRED` below is UNCHANGED. All eighteen envelope fields are still demanded of every
document this validator governs. What changed is WHICH DOCUMENTS it governs.

`rglob("handoffs/**/*.md")` matched 20 paths (19 unique), of which only 8 were handoff
envelopes. The other 11 were the contents of a delivered partner package -- brand-prototype
documents, a README and a VALIDATION_REPORT -- which are not envelopes and never were.
Demanding "sender", "need-by gate" and "fallback" of a brand identity document is a
category error, and the package is sealed by `CHECKSUMS_SHA256.txt` (54/54), so the only
way to satisfy the check would have been to break its own manifest.

A handoff envelope is a document a side SENT or RECEIVED: it lives directly in
`handoffs/{incoming,outgoing}/<side>/`. Anything deeper is the content of a package, not
an envelope for it. That rule also removes the duplicate count -- the partner package
contains its own nested `handoffs/` directory, which `handoffs/**` matched twice.
"""
import re
import sys
from pathlib import Path

# Derived, not hard-coded: this file only worked on one machine before.
# docs/system-of-record/handoff_envelope_check.py -> repository root
ROOT = Path(__file__).resolve().parents[2]

# A handoff envelope sits directly in a side directory. Exactly four segments:
#   handoffs / {incoming|outgoing} / <side> / <document>.md
ENVELOPE_DEPTH = 4


def is_envelope(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return False
    return (
        len(parts) == ENVELOPE_DEPTH
        and parts[0] == "handoffs"
        and parts[1] in {"incoming", "outgoing"}
        and path.suffix == ".md"
    )

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

files = sorted({p for p in (ROOT / "handoffs").rglob("*.md") if is_envelope(p)})
skipped = sorted({p for p in (ROOT / "handoffs").rglob("*.md") if not is_envelope(p)})

print("=" * 70)
print("HANDOFF ENVELOPE VALIDATION")
print("=" * 70)
if not files:
    print("no handoff envelopes found")
    sys.exit(1)

if skipped:
    print(f"\nNot envelopes -- package contents, not documents a side sent ({len(skipped)}):")
    for p in skipped:
        print(f"  - {str(p.relative_to(ROOT)).replace(chr(92), '/')}")

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
print(f"CHECKED: {len(files)}   PASSED: {len(files) - fail}   FAILED: {fail}")
print(f"RESULT: {'PASS' if not fail else 'FAIL'} "
      f"({len(files) - fail}/{len(files)} handoff envelopes)")
sys.exit(1 if fail else 0)
