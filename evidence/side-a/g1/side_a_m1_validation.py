"""Side A G1 M1 business consistency and controller-condition-closure validator.

Artifact ID : A1-VAL-001 v1.0
Owner       : Side A Business/Product Lead
Scope       : docs/side-a/, evidence/side-a/, handoffs/outgoing/side-a/ only.
Limitation  : Validates document and data consistency. It validates no external
              reality: no factory, sample, laboratory, customer, legal, tax,
              customs, registration, contract, payment, carrier or production fact.
Run         : python evidence/side-a/g1/side_a_m1_validation.py   (from repo root)
Exit code   : 0 = PASS, 1 = FAIL
"""
import csv, io, json, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(ROOT)

ALLOWED_STATUS = {"DRAFT", "SELF-VALIDATED", "AUTOMATED-TESTED", "HUMAN-VERIFIED",
                  "EXTERNALLY-VERIFIED", "BLOCKED", "REJECTED"}
ALLOWED_DISP = {"ACCEPT", "CONDITIONALLY_ACCEPT", "REJECT"}
CANONICAL_LIFECYCLE = ["fixture", "candidate", "sample", "approved", "sellable", "retired"]
fail = []


def rd(p):
    with io.open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def chk(cond, tag):
    if not cond:
        fail.append(tag)


# ---------------------------------------------------------------- C1 CSV parse
CSVS = ["docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv",
        "docs/side-a/SB_HO_B0_001_VARIANT_INSTANCE_DISPOSITIONS.csv",
        "docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv",
        "docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv",
        "docs/side-a/SIDE_A_RISK_REGISTER.csv",
        "docs/side-a/EVIDENCE_INDEX.csv",
        "docs/side-a/ASSUMPTION_REGISTER.csv",
        "docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv",
        "docs/side-a/SIDE_A_BUSINESS_PLATFORM_CONTRACT.csv"]
data = {}
for p in CSVS:
    rows = rd(p)
    data[p] = rows
    ragged = [i + 2 for i, r in enumerate(rows) if None in r or None in r.values()]
    print("C1 PARSE %-48s rows=%-4d cols=%-3d ragged=%s"
          % (os.path.basename(p), len(rows), len(rows[0]) if rows else 0, ragged or "none"))
    chk(not ragged, "ragged " + p)

# ---------------------------------------------------------------- C2 JSON parse
payload = json.load(io.open("docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json", encoding="utf-8"))
cv, bl = payload["candidate_values"], payload["blocked_or_unknown_fields"]
ac = payload["activation_controls"]
print("C2 JSON  parse=OK version=%s candidate=%d blocked=%d"
      % (payload["artifact_metadata"]["version"], len(cv), len(bl)))

# ------------------------------------------------------------- C3 status vocab
STATUS_COLS = {"docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv": ["status"],
               "docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv": ["status"],
               "docs/side-a/SIDE_A_RISK_REGISTER.csv": ["status"],
               "docs/side-a/EVIDENCE_INDEX.csv": ["status"],
               "docs/side-a/ASSUMPTION_REGISTER.csv": ["status"],
               "docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv": ["evidence_status"],
               "docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv": ["candidate_value_state"],
               "docs/side-a/SB_HO_B0_001_VARIANT_INSTANCE_DISPOSITIONS.csv": ["candidate_value_state"]}
bad = set()
for p, cols in STATUS_COLS.items():
    for c in cols:
        for r in data[p]:
            v = (r.get(c) or "").strip()
            if v and v not in ALLOWED_STATUS:
                bad.add("%s:%s=%s" % (os.path.basename(p), c, v))
for e in cv + bl:
    if e["approval_status"] not in ALLOWED_STATUS:
        bad.add("payload:%s=%s" % (e["field"], e["approval_status"]))
print("C3 STATUS_VOCAB invalid=%s" % (sorted(bad) or "none"))
chk(not bad, "status vocab")

# --------------------------------------------------------------- C4 dispositions
m = data["docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv"]
mi = data["docs/side-a/SB_HO_B0_001_VARIANT_INSTANCE_DISPOSITIONS.csv"]
badd = sorted(({r["disposition"] for r in m} | {r["disposition"] for r in mi}) - ALLOWED_DISP)
print("C4 DISPOSITION atomic=%d %s | instance=%d %s | invalid=%s"
      % (len(m), dict(Counter(r["disposition"] for r in m)),
         len(mi), dict(Counter(r["disposition"] for r in mi)), badd or "none"))
chk(not badd, "disposition vocab")

# ------------------------------------------------------------ C5 duplicate IDs
d = data["docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv"]
dups = {
    "deliverable.artifact_id": [k for k, v in Counter(r["artifact_id"] for r in d).items() if v > 1],
    "matrix.atomic_field": [k for k, v in Counter(r["atomic_field"] for r in m).items() if v > 1],
    "instance.atomic_instance_field": [k for k, v in Counter(r["atomic_instance_field"] for r in mi).items() if v > 1],
    "evidence.evidence_id": [k for k, v in Counter(r["evidence_id"] for r in data["docs/side-a/EVIDENCE_INDEX.csv"]).items() if v > 1],
    "dependency.dependency_id": [k for k, v in Counter(r["dependency_id"] for r in data["docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv"]).items() if v > 1],
    "payload.field": [k for k, v in Counter(e["field"] for e in cv + bl).items() if v > 1],
}
for k, v in dups.items():
    print("C5 DUPLICATE %-32s %s" % (k, v or "none"))
    chk(not v, "duplicate " + k)

# ---------------------------------------------------- C6 evidence paths on disk
miss = []
for r in d:
    u = (r.get("evidence_uri") or "").strip()
    if u and not u.startswith("http") and not os.path.exists(u):
        miss.append(("DELIVERABLE", r["artifact_id"], u))
for r in data["docs/side-a/EVIDENCE_INDEX.csv"]:
    u = (r.get("source_uri_or_path") or "").strip()
    if u and not u.startswith("http") and not os.path.exists(u):
        miss.append(("EVIDENCE_INDEX", r["evidence_id"], u))
for r in data["docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv"]:
    u = (r.get("evidence_uri") or "").strip()
    if u and not u.startswith("http") and not os.path.exists(u):
        miss.append(("DEPENDENCY", r["dependency_id"], u))
for k in ("evidence_path", "prior_evidence_path"):
    u = payload["artifact_metadata"].get(k)
    if u and not os.path.exists(u):
        miss.append(("PAYLOAD", k, u))
for u in payload["contract_reference"].values():
    if isinstance(u, str) and "/" in u and not os.path.exists(u):
        miss.append(("PAYLOAD_CONTRACT_REF", u, u))
print("C6 EVIDENCE_PATHS_ON_DISK checked_and_missing=%s" % (miss or "none"))
chk(not miss, "missing evidence path")

# ------------------------------------------------------- C7 payload discipline
nonnull = [e["field"] for e in bl if e["value"] is not None]
nondraft = [e["field"] for e in cv if e["approval_status"] != "DRAFT"]
nonblocked = [e["field"] for e in bl if e["approval_status"] != "BLOCKED"]
nodep = [e["field"] for e in bl if not e["dependency_ids"]]
nometa = [e["field"] for e in cv + bl
          if not e.get("source_artifact_id") or not e.get("approval_owner") or not e.get("effective_version")]
skus = [e["value"] for e in cv if re.match(r"^variants\[\d+\]\.sku$", e["field"])]
cap = [e["value"] for e in cv if e["field"] == "activation.sellable_stock_cap"]
print("C7 PAYLOAD blocked_nonnull=%s non_draft_candidate=%s non_blocked_unknown=%s blocked_without_dependency=%s missing_metadata=%s"
      % (nonnull or "none", nondraft or "none", nonblocked or "none", nodep or "none", nometa or "none"))
print("C7 PAYLOAD candidate_skus=%d unique=%d sellable_stock_cap=%s price.gross_minor_units=%s inventory.opening_stock=%s"
      % (len(skus), len(set(skus)), cap,
         [e["value"] for e in bl if e["field"] == "price.gross_minor_units"],
         [e["value"] for e in bl if e["field"] == "inventory.opening_stock"]))
chk(not (nonnull or nondraft or nonblocked or nodep or nometa), "payload discipline")
chk(len(skus) == 3 and len(set(skus)) == 3 and cap == [0], "payload sku/stock")

# -------------------------------------------------- C8 matrix/payload coverage
mf = {r["atomic_field"] for r in m}
pf = {re.sub(r"variants\[\d+\]", "variant", e["field"]) for e in cv + bl} - {"scope.channel", "activation.sellable_stock_cap"}
print("C8 COVERAGE matrix_fields=%d payload_fields=%d matrix_only=%s payload_only=%s"
      % (len(mf), len(pf), sorted(mf - pf) or "none", sorted(pf - mf) or "none"))
chk(not (mf - pf) and not (pf - mf), "coverage")

# -------------------------------------------- C9 prohibited PoC truth in values
BANNED = ["Origin 01", "Origin", "100% cotton", "Made in Egypt", "Egyptian cotton",
          "placehold.co", "Nile", "Cairo", "Desert Line", "59.00", "5900", "free shipping"]
blob = json.dumps(cv)
hits = [b for b in BANNED if b.lower() in blob.lower()]
print("C9 PROHIBITED_POC_TRUTH_IN_CANDIDATE_VALUES hits=%s" % (hits or "none"))
chk(not hits, "prohibited poc value")

# --------------------------------- C10 unsupported completion language (prose)
CLAIMS = [r"\bcompleted successfully\b", r"\bwe (?:visited|inspected|audited|interviewed)\b",
          r"\bfactory (?:visit|audit) (?:completed|passed)\b", r"\blab(?:oratory)? (?:report )?(?:confirms|confirmed|passed)\b",
          r"\bcontract (?:is |was )?signed\b", r"\bregistration (?:is |was )?(?:complete|completed|obtained)\b",
          r"\bcustomers? (?:said|told us)\b", r"\bproduction[- ]ready\b",
          r"\bapproved by (?:our |the )?(?:lawyer|counsel|adviser|accountant)\b",
          r"\bshipment (?:was )?delivered\b", r"\bpayment (?:is |was )?activated\b",
          r"\bgate G\d (?:has )?passed\b", r"\bexternally[- ]verified\b(?!.*status)"]
FENCE = re.compile(r"```.*?```", re.S)
TABLE_CODE = re.compile(r"`[^`]*`")
scan, lang_hits = [], []
for base in ("docs/side-a", "evidence/side-a", "handoffs/outgoing/side-a"):
    for rt, _, fs in os.walk(base):
        for fn in fs:
            scan.append(os.path.join(rt, fn).replace("\\", "/"))
for p in scan:
    if p.endswith((".py", ".json")):
        continue
    try:
        t = io.open(p, encoding="utf-8").read()
    except Exception:
        continue
    prose = TABLE_CODE.sub(" ", FENCE.sub(" ", t))   # strip fenced blocks and inline code
    for w in CLAIMS:
        for mm in re.finditer(w, prose, re.I):
            lang_hits.append("%s :: %s" % (p, mm.group(0)))
print("C10 UNSUPPORTED_COMPLETION_LANGUAGE files_scanned=%d prose_hits=%s" % (len(scan), lang_hits or "none"))
chk(not lang_hits, "completion language")

# ------------------------------------ C11 external-action dossier 8-element audit
txt = io.open("docs/side-a/work_packages/side_a/EXTERNAL_ACTION_DOSSIERS.md", encoding="utf-8").read()
ELEMENTS = {"1_responsible_party": "Owner:", "2_exact_action_required": "Action required:",
            "3_procedure": "Procedure:", "4_questions": "Questions:",
            "5_acceptance_criteria": "Acceptance:", "6_evidence_template": "Evidence template:",
            "7_impact_if_delayed": "Impact if delayed:", "8_safe_fallback": "Fallback:"}
secs = re.findall(r"^## (EXT-\d+).*?$(.*?)(?=^## |\Z)", txt, re.M | re.S)
print("C11 DOSSIERS found=%d required_elements=%d" % (len(secs), len(ELEMENTS)))
for sid, body in secs:
    missing = [k for k, v in ELEMENTS.items() if v not in body]
    print("C11 %-7s missing_elements=%s" % (sid, missing or "none"))
    chk(not missing, "dossier " + sid)
dep = data["docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv"]
blocked = [r for r in dep if r["status"] == "BLOCKED"]
mapmiss = [r["dependency_id"] for r in blocked if not re.search(r"EXT-\d+", r["next_action"] or "")]
print("C11 BLOCKED_DEPENDENCIES=%d DOSSIERS=%d unmapped=%s"
      % (len(blocked), len(secs), mapmiss or "none"))
chk(len(secs) >= len(blocked) and not mapmiss, "dossier coverage")

print()
# ================= K1-K6 controller condition closure (SOR-G0-011) =============
mrow = {r["atomic_field"]: r for r in m}
pe = {e["field"]: e for e in cv + bl}

# K1 Germany + VS-TEE-001 only DRAFT
k1f = ["product.product_id", "price.market", "price.currency", "market.language",
       "market.locales", "market.eligibility"]
k1bad = [f for f in k1f if pe[f]["approval_status"] != "DRAFT" or mrow[f]["candidate_value_state"] != "DRAFT"]
k1acc = [r["atomic_field"] for r in m if r["disposition"] == "ACCEPT"]
print("K1 CONDITION_1 draft_only_violations=%s any_full_ACCEPT=%s -> %s"
      % (k1bad or "none", k1acc or "none", "CLOSED" if not k1bad and not k1acc else "OPEN"))
chk(not k1bad and not k1acc, "K1")

# K2 blocked fields carry dependency + status, no filler
k2bad = [e["field"] for e in bl if e["value"] is not None or e["approval_status"] != "BLOCKED" or not e["dependency_ids"]]
print("K2 CONDITION_2 blocked_entries=%d violations=%s -> %s"
      % (len(bl), k2bad or "none", "CLOSED" if not k2bad else "OPEN"))
chk(not k2bad, "K2")

# K3 lifecycle rejection + canonical enum + technical state separation
lc = mrow["product.lifecycle_status"]
k3 = (lc["disposition"] == "REJECT"
      and "|".join(CANONICAL_LIFECYCLE) in lc["replacement_action"]
      and ac["canonical_business_lifecycle"] == CANONICAL_LIFECYCLE
      and ac["technical_active_or_published_implies_sellable"] is False
      and ac["current_business_lifecycle"] == "candidate")
print("K3 CONDITION_3 disposition=%s canonical=%s technical_implies_sellable=%s -> %s"
      % (lc["disposition"], "|".join(ac["canonical_business_lifecycle"]),
         ac["technical_active_or_published_implies_sellable"], "CLOSED" if k3 else "OPEN"))
chk(k3, "K3")

# K4a nested fields enumerated to leaf level
NESTED = ["product.collection.id", "product.collection.display_name",
          "compliance.responsible_operator.legal_name", "compliance.responsible_operator.address",
          "compliance.responsible_operator.contact", "compliance.responsible_operator.role",
          "compliance.responsible_operator.evidence_id",
          "package.length_cm", "package.width_cm", "package.height_cm", "package.weight_g"]
k4a = [f for f in NESTED if f not in mf or f not in pe]
GROUP_PLACEHOLDERS = ["product.collection", "compliance.responsible_operator", "package"]
k4a += [g for g in GROUP_PLACEHOLDERS if g in mf]
print("K4a CONDITION_4_nested leaves_expected=%d missing_or_placeholder=%s -> %s"
      % (len(NESTED), k4a or "none", "CLOSED" if not k4a else "OPEN"))
chk(not k4a, "K4a")

# K4b variant instances enumerated 1:1 with payload
inst_rows = {r["atomic_instance_field"] for r in mi}
inst_pay = {e["field"] for e in cv if re.match(r"^variants\[\d+\]\.", e["field"])}
k4b_multi = [r["atomic_instance_field"] for r in mi if "|" in r["candidate_value_or_null"]]
print("K4b CONDITION_4_instances rows=%d payload_instances=%d rows_only=%s payload_only=%s multivalue_rows=%s -> %s"
      % (len(inst_rows), len(inst_pay), sorted(inst_rows - inst_pay) or "none",
         sorted(inst_pay - inst_rows) or "none", k4b_multi or "none",
         "CLOSED" if inst_rows == inst_pay and not k4b_multi else "OPEN"))
chk(inst_rows == inst_pay and not k4b_multi, "K4b")

# K4c residual composite fields are single explicit BLOCKED nulls with dependency
COMPOSITE = ["variant.measurements", "economics.cost_stack", "content.media_assets",
             "analytics.business_questions", "analytics.kpis", "operations.roles",
             "policy.returns", "policy.warranty", "policy.support", "policy.delivery_promise"]
k4c = [f for f in COMPOSITE
       if f not in pe or pe[f]["value"] is not None or pe[f]["approval_status"] != "BLOCKED" or not pe[f]["dependency_ids"]]
print("K4c CONDITION_4_composites checked=%d not_explicit_blocked_null=%s -> %s"
      % (len(COMPOSITE), k4c or "none", "CLOSED" if not k4c else "OPEN"))
chk(not k4c, "K4c")

# K5 no rejected PoC truth returned as approved
k5vals = [e["field"] for e in cv + bl
          if any(b.lower() in json.dumps(e).lower() for b in ["100% cotton", "Made in Egypt", "Egyptian cotton", "placehold.co"])]
k5state = [f for f in ["price.gross_minor_units", "inventory.opening_stock", "content.media_assets",
                       "policy.delivery_promise", "material.country_of_origin",
                       "material.fibre_composition", "compliance.approved_claims"]
           if pe[f]["value"] is not None]
k5flags = (ac["public_product_eligible"] is False and ac["checkout_eligible"] is False
           and ac["claims_publishable"] is False and ac["positive_stock_permitted"] is False)
print("K5 CONDITION_5 poc_value_hits=%s must_be_null_but_set=%s activation_flags_all_false=%s -> %s"
      % (k5vals or "none", k5state or "none", k5flags,
         "CLOSED" if not k5vals and not k5state and k5flags else "OPEN"))
chk(not k5vals and not k5state and k5flags, "K5")

# K6 complete disposition + minimal explicit payload
REQ_COLS = ["disposition", "side_a_owner", "candidate_value_state",
            "evidence_or_dependency_ids", "reason", "gate_impact", "replacement_action"]
k6meta = [r["atomic_field"] for r in m if any(not (r.get(c) or "").strip() for c in REQ_COLS)]
k6meta += [r["atomic_instance_field"] for r in mi if any(not (r.get(c) or "").strip() for c in REQ_COLS)]
print("K6 CONDITION_6 atomic_rows=%d instance_rows=%d coverage_gap=%s rows_missing_required_metadata=%s candidate=%d blocked=%d -> %s"
      % (len(m), len(mi), sorted((mf - pf) | (pf - mf)) or "none", k6meta or "none",
         len(cv), len(bl), "CLOSED" if not k6meta and mf == pf else "OPEN"))
chk(not k6meta and mf == pf, "K6")

print()
print("OWNED_FILES docs/side-a+evidence/side-a+handoffs/outgoing/side-a = %d" % len(scan))
print("RESULT: %s  failures=%s" % ("FAIL" if fail else "PASS", fail or "none"))
sys.exit(1 if fail else 0)
