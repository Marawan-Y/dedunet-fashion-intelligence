# Side A G0 Structured Consistency Review

| Field | Value |
|---|---|
| Artifact ID / version | EV-A0-002 / 1.0 |
| Owner | Side A Business/Product Lead |
| Source inputs / dependencies | All Side A G0 artifacts version 1.0; EV-A0-001 |
| Acceptance criteria | CSVs parse; IDs/statuses/required files pass; product-price-claim-policy-factory-logistics-platform contracts do not contradict; false external completion is absent |
| Validation procedure / result | PowerShell checks and structured checklist below / PASS for internal consistency |
| Evidence path | evidence/side-a/bootstrap/SIDE_A_G0_CONSISTENCY_REVIEW.md |
| Status | SELF-VALIDATED |
| Downstream consumer | Controller G0 review and Side B handoff review |
| Remaining risks / next action | No human/external facts validated; re-run after HO-A-B-001 response and any human evidence |

## Exact commands and outputs

Working directory: `C:\Users\User\Desktop\Platform\Fashion_Commerce_Codex_Multi_Agent_Pack`

Command executed 2026-08-01:

```powershell
$allowed = @('DRAFT','SELF-VALIDATED','AUTOMATED-TESTED','HUMAN-VERIFIED','EXTERNALLY-VERIFIED','BLOCKED','REJECTED'); $deliverables = Import-Csv docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv; $facts = Import-Csv docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv; $assumptions = Import-Csv docs/side-a/ASSUMPTION_REGISTER.csv; $dependencies = Import-Csv docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv; $risks = Import-Csv docs/side-a/SIDE_A_RISK_REGISTER.csv; $evidence = Import-Csv docs/side-a/EVIDENCE_INDEX.csv; $contract = Import-Csv docs/side-a/SIDE_A_BUSINESS_PLATFORM_CONTRACT.csv; "deliverables=$($deliverables.Count) duplicate_ids=$((($deliverables.artifact_id | Group-Object | Where-Object Count -gt 1)).Count) invalid_statuses=$((@($deliverables.status + $facts.evidence_status + $assumptions.status + $dependencies.status + $risks.status + $evidence.status) | Where-Object { $_ -notin $allowed } | Sort-Object -Unique) -join '|')"; "facts=$($facts.Count) assumptions=$($assumptions.Count) dependencies=$($dependencies.Count) risks=$($risks.Count) evidence=$($evidence.Count) contract_fields=$($contract.Count) contract_duplicate_ids=$((($contract.contract_id | Group-Object | Where-Object Count -gt 1)).Count)"; "execplan_sections=$((Select-String -Path docs/side-a/SIDE_A_EXECPLAN_G0.md -Pattern '^## ([1-9]|1[0-7])\.' -AllMatches).Count) external_dossiers=$((Select-String -Path docs/side-a/work_packages/side_a/EXTERNAL_ACTION_DOSSIERS.md -Pattern '^## EXT-' -AllMatches).Count)"; $required = @('docs/side-a/SIDE_A_INTAKE_REPORT.md','docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv','docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv','docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv','docs/side-a/SIDE_A_RISK_REGISTER.csv','docs/side-a/SIDE_A_G0_ASSESSMENT.md','docs/side-a/SIDE_A_FIRST_2_WEEK_BACKLOG.md','handoffs/outgoing/side-a/HO-A-B-001_G0_VERTICAL_SLICE_INPUTS_v1.md'); "required_missing=$((@($required | Where-Object { -not (Test-Path $_) })) -join '|')"; "side_a_files=$((Get-ChildItem docs/side-a,evidence/side-a,handoffs/outgoing/side-a -Recurse -File).Count)"
```

Initial output before the self-register row was appended:

```text
deliverables=20 duplicate_ids=0 invalid_statuses=
facts=15 assumptions=5 dependencies=12 risks=8 evidence=6 contract_fields=35 contract_duplicate_ids=0
execplan_sections=17 external_dossiers=10
required_missing=
side_a_files=20
```

Review correction: the deliverable register did not list itself. Row `A0-DELIV-REG-001` was appended. The post-correction validation below is authoritative.

Post-correction command executed 2026-08-01:

```powershell
$allowed = @('DRAFT','SELF-VALIDATED','AUTOMATED-TESTED','HUMAN-VERIFIED','EXTERNALLY-VERIFIED','BLOCKED','REJECTED'); $d=Import-Csv docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv; $f=Import-Csv docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv; $a=Import-Csv docs/side-a/ASSUMPTION_REGISTER.csv; $dep=Import-Csv docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv; $risk=Import-Csv docs/side-a/SIDE_A_RISK_REGISTER.csv; $ev=Import-Csv docs/side-a/EVIDENCE_INDEX.csv; $bpc=Import-Csv docs/side-a/SIDE_A_BUSINESS_PLATFORM_CONTRACT.csv; $invalid=@($d.status+$f.evidence_status+$a.status+$dep.status+$risk.status+$ev.status)|Where-Object {$_ -notin $allowed}|Sort-Object -Unique; $missingEvidence=@($d.evidence_uri|Where-Object {$_ -and -not (Test-Path $_)}|Sort-Object -Unique); $required=@('docs/side-a/SIDE_A_INTAKE_REPORT.md','docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv','docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv','docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv','docs/side-a/SIDE_A_RISK_REGISTER.csv','docs/side-a/SIDE_A_G0_ASSESSMENT.md','docs/side-a/SIDE_A_FIRST_2_WEEK_BACKLOG.md','handoffs/outgoing/side-a/HO-A-B-001_G0_VERTICAL_SLICE_INPUTS_v1.md','evidence/side-a/bootstrap/SIDE_A_G0_CONSISTENCY_REVIEW.md'); "POST_VALIDATION deliverables=$($d.Count) duplicate_deliverable_ids=$((@($d.artifact_id|Group-Object|Where-Object Count -gt 1)).Count) invalid_statuses=$($invalid -join '|') missing_evidence_paths=$($missingEvidence -join '|') required_missing=$((@($required|Where-Object {-not (Test-Path $_)})) -join '|')"; "MATRICES facts=$($f.Count) assumptions=$($a.Count) dependencies=$($dep.Count) risks=$($risk.Count) evidence=$($ev.Count) contract_fields=$($bpc.Count) duplicate_contract_ids=$((@($bpc.contract_id|Group-Object|Where-Object Count -gt 1)).Count) execplan_sections=$((Select-String docs/side-a/SIDE_A_EXECPLAN_G0.md -Pattern '^## ([1-9]|1[0-7])\.' -AllMatches).Count) dossiers=$((Select-String docs/side-a/work_packages/side_a/EXTERNAL_ACTION_DOSSIERS.md -Pattern '^## EXT-' -AllMatches).Count)"; "OWNED_FILES=$((Get-ChildItem docs/side-a,evidence/side-a,handoffs/outgoing/side-a -Recurse -File).Count)"
```

Authoritative output:

```text
POST_VALIDATION deliverables=21 duplicate_deliverable_ids=0 invalid_statuses= missing_evidence_paths= required_missing=
MATRICES facts=15 assumptions=5 dependencies=12 risks=8 evidence=6 contract_fields=35 duplicate_contract_ids=0 execplan_sections=17 dossiers=10
OWNED_FILES=21
```

False-completion scan command:

```powershell
rg -n -i "customer[- ]validated|factory (is|was) audited|sample (is|was) approved|lab (passed|verified)|legally compliant|tax compliant|customs cleared|registered|signed agreement|payment activated|production[- ]ready|100% Egyptian cotton|real campaign|real orders" docs/side-a evidence/side-a handoffs/outgoing/side-a
```

Output:

```text
docs/side-a\SIDE_A_EXECPLAN_G0.md:37:Dependencies are registered in `SIDE_A_DEPENDENCY_REGISTER.csv`. The first outgoing handoff is `HO-A-B-001`; it requests schema/validation feedback and explicitly prevents synthetic values from becoming sellable truth.
docs/side-a\SIDE_A_INTAKE_REPORT.md:25:- No signed agreement, legal entity, named accountable human, product specification, sample, supplier/factory record, material evidence, lab result, cost, price approval, inventory record, registration, carrier result, payment activation, customer interview or campaign result is present.
```

Disposition: both matches are boundary/absence statements, not claims of completion. A second scan for `HUMAN-VERIFIED|EXTERNALLY-VERIFIED|AUTOMATED-TESTED` returned no matches and `rg` exit code 1, which is expected when no such status is claimed.

## Structured business consistency checklist

| Control | Test | Result | Evidence / residual action |
|---|---|---|---|
| Product | One product/one color/three sizes only; all non-evidenced facts are candidate or unknown | PASS | A0-VS-001; human/product evidence still BLOCKED |
| Price | EUR 59 appears only as non-authoritative research test point; live gross price is unknown | PASS | A-A-004; BPC-A-020; DEP-A-005 |
| Claims | No material/origin/quality/sustainability claim is approved; claim rendering requires evidence/approver/expiry | PASS | BPC-A-007/008/010; EXT-04; R-A-004 |
| Policy/compliance | Germany is a hypothesis; legal/tax/customs/textile/GPSR/REACH/packaging outcomes require adviser evidence | PASS | DEP-A-006/007; EXT-06/07 |
| Factory/product truth | No factory/sample/tech pack/QC completion claimed; positive sellable stock is prohibited | PASS | DEP-A-003/004; BPC-A-019/029/030; EXT-03/04 |
| Logistics/customer promise | EU stock is only a hypothesis; no carrier rate, delivery promise, return result or test shipment is claimed | PASS | A-A-003; DEP-A-008; EXT-08 |
| Platform contract | 35 unique fields have owner, truth state, validation, evidence, missing-data behavior, acceptance and change control | PASS | A0-BPC-001; receiver implementation decision pending |
| Fixture boundary | PoC product/price/stock/cotton/origin/brand values are explicitly rejected as business/external evidence | PASS | A0-INTAKE-001; HO-A-B-001 |
| External dossier coverage | Governance, research, factory/sample, material/lab, cost, legal/tax/customs, product/packaging, fulfilment, rights and payment each have an execution dossier | PASS | 10 EXT sections; outcomes remain BLOCKED |
| Handoff completeness | Sender/receiver/date, WP/artifacts, purpose, payload/schema/version, facts, assumptions, questions, acceptance, validation, gate/impact/fallback and change control exist | PASS | HO-A-B-001; receiver result pending |
| Gate logic | Stricter G0 rule applied; failed governance criteria produce NO-GO and no material commitment | PASS | A0-GATE-001 |

## Validation conclusion

Internal artifact consistency is `SELF-VALIDATED`. This does not validate demand, product, factory, material, legal, tax, customs, registrations, fulfilment, payment or production reality. The current G0 recommendation remains `NO-GO`.
