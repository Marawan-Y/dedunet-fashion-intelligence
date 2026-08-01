# Side A G1 M1 Consistency Validation

| Field | Value |
|---|---|
| Artifact ID / version | EV-A1-001 / 1.0 |
| Owner | Side A Business/Product Lead |
| Sources / dependencies | A1-DISP-001; A1-PAYLOAD-001; HO-A-B-002; current Side A registers/status |
| Acceptance criteria | Atomic matrix and JSON parse; every contract field is covered once; only allowed dispositions/statuses appear; lifecycle correction, blocked-null discipline, zero sellable stock, dependencies and no reused PoC truth are proven |
| Validation procedure / result | PowerShell checks below / PASS |
| Evidence path | evidence/side-a/g1/EV_A1_001_M1_CONSISTENCY_VALIDATION.md |
| Status | SELF-VALIDATED |
| Downstream consumer | Controller M1 reconciliation and Side B |
| Remaining risk / next action | Side B schema/runtime validation and all human/external evidence remain pending; re-run after receiver response |

## Validation command 1 — atomic coverage, payload discipline and registers

Executed from repository root on 2026-08-01. The expected-field array below is the controller-corrected atomic expansion of every SB-AR-B3-001 request.

```powershell
$allowedStatuses=@('DRAFT','SELF-VALIDATED','AUTOMATED-TESTED','HUMAN-VERIFIED','EXTERNALLY-VERIFIED','BLOCKED','REJECTED'); $allowedDispositions=@('ACCEPT','CONDITIONALLY_ACCEPT','REJECT'); $m=Import-Csv docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv; $p=Get-Content -Raw docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json|ConvertFrom-Json; $expected=@('product.product_id','product.style_code','product.name','product.slug','product.category','product.collection.id','product.collection.display_name','product.lifecycle_status','product.short_description','product.long_description','product.fit','material.fibre_composition','material.country_of_origin','material.care_instructions','compliance.approved_claims','compliance.responsible_operator.legal_name','compliance.responsible_operator.address','compliance.responsible_operator.contact','compliance.responsible_operator.role','compliance.responsible_operator.evidence_id','variant.sku','variant.barcode','variant.size','variant.size_system','variant.color','variant.color_code','variant.measurements','variant.weight_g','package.length_cm','package.width_cm','package.height_cm','package.weight_g','inventory.location_id','inventory.opening_stock','batch.supplier_id','batch.production_batch_id','batch.qc_release_id','price.market','price.currency','price.gross_minor_units','price.tax_class','price.net_gross_basis','price.valid_from','price.valid_to','economics.cost_stack','economics.margin_approval_id','market.language','market.locales','market.eligibility','policy.delivery_promise','policy.returns','policy.warranty','policy.support','fulfilment.warehouse','fulfilment.carrier','fulfilment.return_address','fulfilment.cutoff','content.media_assets','brand.tokens','analytics.business_questions','analytics.kpis','operations.roles','operations.approval_limits','operations.support_hours','operations.severity_contacts'); $matrixFields=@($m.atomic_field|Sort-Object -Unique); $missingExpected=@($expected|Where-Object {$_ -notin $matrixFields}); $unexpected=@($matrixFields|Where-Object {$_ -notin $expected}); $matrixMetaMissing=@($m|Where-Object {-not $_.side_a_owner -or -not $_.evidence_or_dependency_ids -or -not $_.reason -or -not $_.gate_impact -or -not $_.replacement_action}); $entries=@($p.candidate_values)+@($p.blocked_or_unknown_fields); $entryMetaMissing=@($entries|Where-Object {-not $_.field -or -not $_.source_artifact_id -or -not $_.approval_owner -or -not $_.approval_status -or -not $_.effective_version}); $payloadFields=@(($p.candidate_values|Where-Object {$_.field -notin @('scope.channel','activation.sellable_stock_cap')}|ForEach-Object {$_.field -replace 'variants\[\d+\]','variant'})+$p.blocked_or_unknown_fields.field|Sort-Object -Unique); $payloadMissing=@($expected|Where-Object {$_ -notin $payloadFields}); $payloadUnexpected=@($payloadFields|Where-Object {$_ -notin $expected}); $skus=@($p.candidate_values|Where-Object {$_.field -match '^variants\[\d+\]\.sku$'}|ForEach-Object value); $candidateText=$p.candidate_values|ConvertTo-Json -Depth 8; $banned=@('Origin 01','100% cotton','Made in Egypt','placehold.co','Nile Calligraphy','Desert Line','Cairo Grid'); $bannedHits=@($banned|Where-Object {$candidateText -match [regex]::Escape($_)}); $d=Import-Csv docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv; $f=Import-Csv docs/side-a/SIDE_A_FACT_ASSUMPTION_MATRIX.csv; $a=Import-Csv docs/side-a/ASSUMPTION_REGISTER.csv; $dep=Import-Csv docs/side-a/SIDE_A_DEPENDENCY_REGISTER.csv; $risk=Import-Csv docs/side-a/SIDE_A_RISK_REGISTER.csv; $ev=Import-Csv docs/side-a/EVIDENCE_INDEX.csv; $invalidStatuses=@($d.status+$f.evidence_status+$a.status+$dep.status+$risk.status+$ev.status+$m.candidate_value_state+$entries.approval_status|Where-Object {$_ -notin $allowedStatuses}|Sort-Object -Unique); $invalidDispositions=@($m.disposition|Where-Object {$_ -notin $allowedDispositions}|Sort-Object -Unique); $missingEvidence=@($d.evidence_uri|Where-Object {$_ -and -not (Test-Path $_)}|Sort-Object -Unique); $lifecycle=$m|Where-Object atomic_field -eq 'product.lifecycle_status'; $blockedNonNull=@($p.blocked_or_unknown_fields|Where-Object {$null -ne $_.value}); $nonDraftCandidate=@($p.candidate_values|Where-Object approval_status -ne 'DRAFT'); $nonBlockedUnknown=@($p.blocked_or_unknown_fields|Where-Object approval_status -ne 'BLOCKED'); "MATRIX rows=$($m.Count) unique_fields=$($matrixFields.Count) conditionally_accept=$((@($m|Where-Object disposition -eq 'CONDITIONALLY_ACCEPT')).Count) reject=$((@($m|Where-Object disposition -eq 'REJECT')).Count) accept=$((@($m|Where-Object disposition -eq 'ACCEPT')).Count) missing_expected=$($missingExpected -join '|') unexpected=$($unexpected -join '|') metadata_missing=$($matrixMetaMissing.Count) invalid_dispositions=$($invalidDispositions -join '|')"; "LIFECYCLE disposition=$($lifecycle.disposition) requested_value_state=$($lifecycle.candidate_value_state) replacement_present=$([bool]($lifecycle.replacement_action -match 'fixture\|candidate\|sample\|approved\|sellable\|retired')) payload_current=$($p.activation_controls.current_business_lifecycle) canonical=$($p.activation_controls.canonical_business_lifecycle -join '|') technical_implies_sellable=$($p.activation_controls.technical_active_or_published_implies_sellable)"; "PAYLOAD candidate_entries=$($p.candidate_values.Count) blocked_entries=$($p.blocked_or_unknown_fields.Count) covered_fields=$($payloadFields.Count) missing=$($payloadMissing -join '|') unexpected=$($payloadUnexpected -join '|') metadata_missing=$($entryMetaMissing.Count) blocked_non_null=$($blockedNonNull.Count) non_draft_candidate=$($nonDraftCandidate.Count) non_blocked_unknown=$($nonBlockedUnknown.Count)"; "INTEGRITY candidate_skus=$($skus.Count) unique_candidate_skus=$(($skus|Sort-Object -Unique).Count) sellable_stock_cap=$(($p.candidate_values|Where-Object field -eq 'activation.sellable_stock_cap').value) opening_stock_is_null=$($null -eq ($p.blocked_or_unknown_fields|Where-Object field -eq 'inventory.opening_stock').value) gross_minor_units_is_null=$($null -eq ($p.blocked_or_unknown_fields|Where-Object field -eq 'price.gross_minor_units').value) banned_candidate_hits=$($bannedHits -join '|')"; "REGISTERS deliverables=$($d.Count) duplicate_artifact_ids=$((@($d.artifact_id|Group-Object|Where-Object Count -gt 1)).Count) invalid_statuses=$($invalidStatuses -join '|') missing_evidence_paths=$($missingEvidence -join '|') evidence_rows=$($ev.Count) risks=$($risk.Count) facts=$($f.Count) dependencies=$($dep.Count)"
```

Exact output:

```text
MATRIX rows=65 unique_fields=65 conditionally_accept=64 reject=1 accept=0 missing_expected= unexpected= metadata_missing=0 invalid_dispositions=
LIFECYCLE disposition=REJECT requested_value_state=REJECTED replacement_present=True payload_current=candidate canonical=fixture|candidate|sample|approved|sellable|retired technical_implies_sellable=False
PAYLOAD candidate_entries=21 blocked_entries=52 covered_fields=65 missing= unexpected= metadata_missing=0 blocked_non_null=0 non_draft_candidate=0 non_blocked_unknown=0
INTEGRITY candidate_skus=3 unique_candidate_skus=3 sellable_stock_cap=0 opening_stock_is_null=True gross_minor_units_is_null=True banned_candidate_hits=
REGISTERS deliverables=26 duplicate_artifact_ids=0 invalid_statuses= missing_evidence_paths= evidence_rows=7 risks=9 facts=17 dependencies=12
```

## Validation command 2 — handoff envelope, report and required paths

```powershell
$h=Get-Content -Raw handoffs/outgoing/side-a/HO-A-B-002_SB_B0_INPUT_RESPONSE_v1.md; $patterns=@('HANDOFF-ID','Sender / receiver / date','Work package / artifact IDs','Purpose / consuming workflow','Files / payload / schema','Confirmed facts','Assumptions','Questions to Side B','Acceptance criteria for Side B processing','Validation procedure and Side A result','Impact if late and safe fallback','Change control and supersession','Receiver result'); $missing=@($patterns|Where-Object {$h -notmatch [regex]::Escape($_)}); $statusSections=(Select-String docs/side-a/STATUS_REPORT.md -Pattern '^## [1-9]\.' -AllMatches).Count; "ENVELOPE required_patterns=$($patterns.Count) missing=$($missing -join '|') status_report_sections=$statusSections"; "FILES matrix=$((Test-Path docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv)) payload=$((Test-Path docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json)) handoff=$((Test-Path handoffs/outgoing/side-a/HO-A-B-002_SB_B0_INPUT_RESPONSE_v1.md)) evidence=$((Test-Path evidence/side-a/g1/EV_A1_001_M1_CONSISTENCY_VALIDATION.md)) status=$((Test-Path docs/side-a/STATUS_REPORT.md)) g0_archive=$((Test-Path docs/side-a/STATUS_REPORT_G0_v1.md))"
```

Exact output:

```text
ENVELOPE required_patterns=13 missing= status_report_sections=9
FILES matrix=True payload=True handoff=True evidence=True status=True g0_archive=True
```

## Structured consistency review

| Control | Result | Evidence / limitation |
|---|---|---|
| Atomic request coverage | PASS | 65 expected atomic fields; none missing/unexpected/duplicated |
| Disposition discipline | PASS | 64 `CONDITIONALLY_ACCEPT`; lifecycle request only `REJECT`; no unsupported full `ACCEPT` |
| Lifecycle correction | PASS | Requested enum rejected; canonical lifecycle exact; technical active/published does not imply sellable |
| Candidate values | PASS | 21 entries, all `DRAFT`, all source/owner/version metadata present |
| External/unknown values | PASS | 52 entries, all `BLOCKED`, all values null, dependency linked |
| Variant test data | PASS | Three unique `CAND-` SKUs and DRAFT S/M/L + Black hypotheses only |
| Price/inventory | PASS | Gross minor units and opening stock null; sellable stock cap zero |
| Prohibited PoC truth | PASS | No banned PoC brand/copy/composition/origin/image identifiers in candidate values |
| Registers/evidence paths | PASS | 26 unique deliverables; allowed statuses; no missing evidence paths |
| Handoff/report | PASS | Full envelope patterns present; current cycle report has nine sections |

## Conclusion

Side A M1 inputs are `SELF-VALIDATED` for internal consistency. A1-PAYLOAD-001 and HO-A-B-002 remain `DRAFT` until Side B/controller processing. This evidence does not verify a real product, market, factory, material, price, legal/compliance, provider or operational event.

## Final recheck after register/catalog update

```powershell
$d=Import-Csv docs/side-a/SIDE_A_DELIVERABLE_REGISTER.csv; $m=Import-Csv docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv; $p=Get-Content -Raw docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json|ConvertFrom-Json; $e=Import-Csv docs/side-a/EVIDENCE_INDEX.csv; $required=@('docs/side-a/SB_HO_B0_001_ATOMIC_DISPOSITION_MATRIX.csv','docs/side-a/VS_TEE_001_CANDIDATE_PAYLOAD_v0_1.json','handoffs/outgoing/side-a/HO-A-B-002_SB_B0_INPUT_RESPONSE_v1.md','evidence/side-a/g1/EV_A1_001_M1_CONSISTENCY_VALIDATION.md','docs/side-a/STATUS_REPORT.md'); "FINAL_RECHECK deliverables=$($d.Count) duplicate_ids=$((@($d.artifact_id|Group-Object|Where-Object Count -gt 1)).Count) matrix_rows=$($m.Count) matrix_unique=$((@($m.atomic_field|Sort-Object -Unique)).Count) json_status=$($p.artifact_metadata.readiness_status) evidence_rows=$($e.Count) required_missing=$((@($required|Where-Object {-not (Test-Path $_)})) -join '|')"; "CURRENT_REPORT sections=$((Select-String docs/side-a/STATUS_REPORT.md -Pattern '^## [1-9]\.' -AllMatches).Count) validation_status=$((Select-String evidence/side-a/g1/EV_A1_001_M1_CONSISTENCY_VALIDATION.md -Pattern '^\| Status \| SELF-VALIDATED \|$').Count) owned_files=$((Get-ChildItem docs/side-a,evidence/side-a,handoffs/outgoing/side-a -Recurse -File).Count)"
```

```text
FINAL_RECHECK deliverables=26 duplicate_ids=0 matrix_rows=65 matrix_unique=65 json_status=DRAFT evidence_rows=7 required_missing=
CURRENT_REPORT sections=9 validation_status=1 owned_files=26
```
