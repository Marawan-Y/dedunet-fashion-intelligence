# DEDUNET V1 — Phase reports

| Control | Value |
|---|---|
| Artifact ID | SOR-PHASE-001 |
| Version | 1.0 |
| Owner | Technical lead (successor agent) |
| Format | As mandated: implementation / tests / security / regression / human / documentation |
| Rule | A `NOT TESTED` item is reported as `NOT TESTED`. It is never satisfied by an automated result |

---

## PHASE 0 — Successor takeover and baseline preservation

**Starting HEAD:** `41cee4c72f629b190fa7e1ea4bab879d9c045220`

| Field | Result |
|---|---|
| Implementation | **PASS** — read-only. No file changed during takeover |
| Tests | **PASS** — 415 passed, 2 skipped, re-executed rather than read forward |
| Security | **PASS** — no guard touched |
| Regression | **PASS** — baseline matched the recorded state |
| Human Test | **NOT TESTED** — nothing to test; no behaviour changed |
| Documentation | **PASS** — findings folded into Phase 1 |

**Evidence:** this report §0.1; `SUCCESSOR_AGENT_TAKEOVER_REPORT.md` (prior cycle, `d8e2f04`)

**Commits:** none — Phase 0 changed nothing.

### 0.1 Baseline, re-derived

| Measure | Observed |
|---|---|
| Git root | ends exactly at `Fashion_Commerce_Codex_Multi_Agent_Pack` |
| Branch / HEAD | `dedunet/repository-restructure-and-workstreams-a-f` / `41cee4c` |
| Working tree | **clean**, including untracked |
| Backend suite | **415 passed, 2 skipped** |
| Guard mutations registered | **72** |
| API contract | 31 paths, 31 operations |
| ORM classes | 23 — 18 tables, 5 status enums |
| Alembic | 5 revisions, head `a7c31f9be402` |
| Tracked files | 405 |

**The working tree was already clean.** The brief warned that an accepted-but-uncommitted
LAN staging change might be present. It was not — `41cee4c` *is* that change, already
committed. No destructive git command was issued at any point.

**Remaining issues:** none.

**Decision: `PHASE_0_COMPLETE`**

---

## PHASE 0A — iPhone web hardening (mandate §58)

Executed inside Phase 0's window because both items were open defects from human acceptance,
independent of the repositioning, and blocking nothing else.

**Starting HEAD:** `41cee4c`

| Field | Result |
|---|---|
| Implementation | **PASS** — both items closed |
| Tests | **PASS** — 434 passed, 2 skipped (415 + 19) |
| Security | **PASS** — 8/8 mutations over the changed file detected, 0 survived |
| Regression | **PASS** — delta fully explained; no test weakened, one made stricter |
| Human Test | **NOT TESTED** — two screens a human reported; a human should confirm them |
| Documentation | **PASS** — evidence written, CONFLICT-011 opened |

**Evidence:** `evidence/team-acceptance/IPHONE_WEB_HARDENING_CLOSURE.md`

**Commits:** `2f50e11`

| Check | Observed |
|---|---|
| New suite | 19 passed |
| Full backend suite | **434 passed, 2 skipped** |
| Mutations over `apps/web/app.js` | **8 run, 8 detected, 0 survived** |
| Harness total | 72 → **77** registered |
| Validators | exit 0 / 0 / **1** with `ACTIVATION_BLOCKED` verified by reason |
| OpenAPI drift | **none**, byte-identical |

### 0A.1 Remaining issues

| ID | Item | Status |
|---|---|---|
| `NATIVE_MIRRORS_ONE_GATE` | `ProductScreen.tsx` mirrors the product gate only; web now mirrors both. Correct against today's seed, wrong for a sellable product in a preview catalogue | **OPEN** — separate surface, separate acceptance |
| **CONFLICT-011** | The iPhone acceptance that reported these defects had no record in this repository | **RESOLVED 2026-08-24** — `EV-TA-006` written from tester-supplied scope |
| Human confirmation | Neither corrected screen has been seen by a human since the fix | **NOT TESTED** |

### 0A.2 A discarded result, recorded

`apps/web/app.js` was edited while the mutation harness was running. The harness restores the
source it captured, so a concurrent write can be reverted or can land on mutated source.
**M78's result from that run was discarded** and all eight mutations targeting the file were
re-run cleanly — including the three pre-existing ones, whose anchors the edit could have
broken without breaking the suite.

Recorded because "the result was obtained under conditions that could have corrupted it" is
exactly what a passing number hides.

**Decision: `PHASE_0A_COMPLETE`** — for the two defects, on automated evidence.
**Not** an iPhone acceptance pass.

---

## PHASE 1 — Product repositioning and target domain architecture

**Starting HEAD:** `2f50e11`

| Field | Result |
|---|---|
| Implementation | **PASS** — design and governance only; no code proposed here is written |
| Tests | **PASS** — 434 passed, 2 skipped, unchanged by this phase |
| Security | **PASS** — no guard touched |
| Regression | **PASS** — no behaviour changed |
| Human Test | **NOT TESTED** — `ADR-0002` is `PROPOSED` and awaits an owner decision |
| Documentation | **PASS** — CONFLICT-009 closed, CONFLICT-011 opened |

**Evidence:**

```text
docs/architecture/decisions/ADR-0002-repositioning-to-fashion-intelligence-platform.md
docs/architecture/DEDUNET_V1_TARGET_DOMAIN_ARCHITECTURE.md
docs/architecture/DEDUNET_V1_EXECUTION_PLAN.md
docs/system-of-record/CONFLICT_AND_RESOLUTION_REGISTER.md   (009 closed, 011 opened)
README.md · docs/KNOWN_LIMITATIONS.md                        (DISC-02, DISC-01)
```

**Commits:** `a9fa0f7`, `37c9be8`, `49125cb`

### 1.1 The finding that shaped the phase

Three properties of the existing domain, measured rather than assumed:

```text
no tenant column on any table
no brand entity -- Product belongs to a catalogue, not a seller
no styling domain -- ai_stylist.py is 68 lines its own docstring calls a demo
```

**The gap is a new domain, not a refactor.** Every entity in the target map is marked
`EXISTS` or `NEW`, because this phase's failure mode is a document that reads like an
inventory and is actually a wish list.

### 1.2 Errors found in this phase's own output

Found by re-reading, before commit. Recorded because the same discipline applies to my work.

| Error | Correction |
|---|---|
| "74 → 79 mutations" — counted from the highest id | **72 → 77**. M56 and M57 were never used |
| `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` listed among preserved states | **Removed.** The token exists in no tracked file and no commit on any ref |
| Same acceptance listed as an inherited pass in Rule 8 | **Excluded**, with the reason stated |
| "7 routes" | **8** |
| "482 lines" for the admin portal | **482 lines of `admin.js`** |

The first two matter most. A count taken from a label rather than the data, and a brief's
assertion promoted into a repository fact, are the two ways this programme's evidence chain
would degrade quietly.

### 1.3 Remaining issues

| Item | Status |
|---|---|
| `ADR-0002` | **PROPOSED** — not adopted. Owner decision required before Phase 2 |
| Phases 2–19 | **NOT STARTED** |
| Phase 15 (CI/CD) | **BLOCKED** — no Git remote; the workflow has never executed |
| CONFLICT-010 (Git remote) | **OPEN** — owner decision, needs a secret and personal-data review first |
| CONFLICT-011 (iPhone record) | **RESOLVED** — `EV-TA-006`, `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` |
| Risk-owner acceptance | **PENDING** — all four |
| Deliverables C, D, K, M–AD | **NOT AUTHORED** — they belong to their phases |

**Decision: `PHASE_1_COMPLETE`**

---

## PHASE 1B — Governance closure

**Starting HEAD:** `37cd6f6`

| Field | Result |
|---|---|
| Implementation | **PASS** — documentation and governance only. No application code touched |
| Tests | **PASS** — 434 passed, 2 skipped, unchanged (no code in scope) |
| Security | **PASS** — no guard touched |
| Regression | **PASS** — `controller_validate.py` **585 errors before, 585 after: zero introduced** |
| Human Test | **PASS** — this phase *records* a human acceptance the tester performed |
| Documentation | **PASS** — eight documents brought into agreement, 29 links, 0 broken |

**Evidence:** `evidence/team-acceptance/IPHONE_MOBILE_WEB_ACCEPTANCE.md` (`EV-TA-006`)

### 1B.1 CONFLICT-011 closed

The human tester supplied the authoritative scope; the record was written from it and
**not** reconstructed from the brief. `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED` over 25 gates:
connectivity and LAN CORS, brand media, five preview products, the Source Tee at €72, preview
disclosure and purchase blocking, cart safety, registration, signed-in Account and Orders,
Safari persistence, server-side invalidation → authoritative 401 → client clearing stale
state, backend restoration leaving Safari signed out, disposable-customer deletion, and a
final `/ready` 200 in `BRAND_PREVIEW_MODE`.

**Ten claims independently corroborated** against repository data rather than transcribed —
€72 from `variant-master.csv`, five products from `product-master.json`, non-purchasability
from `prototype_unavailable` / `stock_quantity=0`, the mode gate from `assert_purchasable`,
the caution language from `origin_claim_status=UNVERIFIED`, and stale-token clearing from
mutation M74.

**Residual, recorded not hidden:** iPhone model, iOS version and the acceptance commit were
not supplied. The commit is an *inference* (`41cee4c`), bounded to a two-commit window because
LAN access is what that commit added and the reported defects were fixed in `2f50e11`.

### 1B.2 What this phase refused to do

`NATIVE_IOS_ACCEPTANCE` remains **`NOT TESTED`**. Apple signing, TestFlight and App Store
submission remain `NOT TESTED`. Apple Developer Program membership remains
**`DEFERRED — FUNDING`**.

Mobile web in Safari and the native application share a commerce contract and nothing else.
The Android emulator preview, the iPhone mobile-web acceptance and native iOS are three
distinct states, and no two of them may be aggregated into "mobile is accepted".

### 1B.3 Remaining issues

| Item | Status |
|---|---|
| Corrected screens re-checked on the reporting device | **NOT TESTED** — readiness action 8 |
| iPhone model / iOS version / acceptance commit | **NOT SUPPLIED** — `EV-TA-006` §7 |
| `controller_validate.py` | **FAILING AT BASELINE** — 585 errors, pre-existing. 442 are `BAD STATUS` from applying the evidence vocabulary to any `*_status` column (`runtime_status=build-time`, `inventory_status=prototype_unavailable`), and one `UNSUPPORTED CLAIM` is inside `apps/mobile/node_modules/`. A validator scoping defect, not a data defect. **Not fixed here** — out of scope for a governance closure, and recorded so it is not rediscovered as new |
| `ADR-0002` | **PROPOSED**, unmodified. Decision brief delivered separately |

**Decision: `PHASE_1B_COMPLETE`**

---

## PHASE 1C — ADR revision and governance validator closure

**Starting HEAD:** `be80411`

| Field | Result |
|---|---|
| Implementation | **PASS** — ADR §2.0 issued; validator scoped. No application code touched |
| Tests | **PASS** — backend 434 passed / 2 skipped; **26 new validator tests** |
| Security | **PASS** — no guard touched; mutation harness intact at 77, no target file changed |
| Regression | **PASS** — controller validator **585 → 8**, all 8 genuine; 0 false positives |
| Human Test | **N/A** — governance and documentation only |
| Documentation | **PASS** — 11 markdown files, 29 links, 0 broken; secret scan 0 |

**Commits:** `15f1851`, and the validator commit below.

### 1C.1 Validator — root causes and correction

| Class | Count | Root cause | Fix |
|---|---|---|---|
| `BAD STATUS` on domain columns | **442** | `if "status" in header` applied the seven readiness statuses to any column whose *name* contained the substring — `runtime_status=build-time`, `migration_status=DONE`, `inventory_status=prototype_unavailable`, `ownership_status=ORIGINAL_PROTOTYPE_ASSET` | explicit `EVIDENCE_STATUS_COLUMNS` set, derived empirically from which columns actually carry the vocabulary |
| `BAD STATUS` on partner data | (within the 442) | this programme's vocabulary applied to an immutable, checksum-sealed partner package with its own schema and its own validator | `handoffs/incoming/` exempt from *our* vocabulary; its uniqueness and structure are still checked |
| `MISSING PATH` | **140** | every column's prose scanned for path existence, and historical columns treated as live. All 140 were pre-restructure `platform/poc/…` paths — `source_path` records where a file *used* to be, and a `risk` cell mentioning a path is a sentence | check only live reference columns; exempt `HISTORICAL_PATH_COLUMNS` |
| `UNSUPPORTED CLAIM` in `node_modules` | **1** | Expo's own README saying "Production-ready." — true, third-party, unfixable by us | `EXCLUDED_DIRS` |
| `UNSUPPORTED CLAIM`, quoted phrase | **1** | a document headed *"False positive recorded and resolved"* was flagged for the phrase it quotes in backticks while explaining it is not a claim | mask fenced blocks and inline code before matching — the same fix that document records Side A applying to its own scanner |
| `UNSUPPORTED CLAIM`, wrapped negation | **1** | `"Nothing here is
production-ready."` put the negation on the previous physical line | negation window spans the sentence, read from masked text so a `not` inside code cannot launder a claim |

Also fixed: `ROOT` was a **hard-coded absolute path to one machine**. Now derived from
`__file__`. Every new test depends on this — they run the validator against temporary trees
and would otherwise have silently validated the real repository.

**None of these narrows what is enforced.** All six widen or redirect *what is inspected*.
The `FORBIDDEN` list and `ALLOWED_STATUS` are unchanged.

### 1C.2 Tests — 26, each scoping rule in both directions

The easy way to make a validator green is to stop it checking, and that is invisible in an
error count. Every rule therefore has a paired test: *the false positive is gone* **and**
*the real violation still fails*. Notably `test_an_invalid_evidence_status_is_rejected_in_every_governed_column`
is parametrised over all four governed columns, because an explicit set is exactly the kind
of thing that loses a member unnoticed; and
`test_a_negation_inside_code_does_not_excuse_a_claim_outside_it` proves the code-masking
cannot be used to launder a real claim.

`test_the_repository_has_no_false_positive_classes_left` asserts by **class, not count** — a
total would move for legitimate reasons and then get edited to match, which is how a guard
stops guarding.

### 1C.3 Genuine findings that remain — reported, not fixed

| Finding | Count | Disposition |
|---|---|---|
| `SUPERSEDED` in `docs/side-b/EVIDENCE_INDEX.csv` and `EVIDENCE_INDEX_v2_0_0.csv` | **8** | **OPEN — owner decision.** `AGENTS.md` declares seven statuses and says "use only these". `SUPERSEDED` is an eighth. It is *not* a category error: the same column also holds `BLOCKED`, `SELF-VALIDATED` and `AUTOMATED-TESTED`, so it is genuinely a readiness column carrying an undeclared value. Resolving it means either adding `SUPERSEDED` to the declared vocabulary in `AGENTS.md` or moving supersession to its own column — both changes to a root governance file, and neither is mine to make unilaterally. **Deleting the data to reach green would destroy real lifecycle information** recorded in `evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md` |
| Stale `platform/poc/.github/workflows/ci.yml` in `SIDE_B_RISK_REGISTER.csv` | 1 | **FIXED** — corrected to `.github/workflows/ci.yml`, which exists. A live evidence reference left pointing at a pre-restructure path; within Side B's authorized scope and unambiguous |
| `handoff_envelope_check.py` — 6/20 handoffs pass | — | **PRE-EXISTING, OUT OF SCOPE.** Two Side B handoffs are missing `assumptions` and `questions` envelope fields. Neither the checker nor the handoffs were touched by this phase. Reported so it is not rediscovered as new |

**I considered and rejected a reading that would have reached zero.** Treating
`EVIDENCE_INDEX.status` as a lifecycle axis — like `current_status` for risk — would have
exempted all 8. The data refutes it: the column mixes `SUPERSEDED` with three readiness
values, so it is a readiness column with an undeclared member. Reasoning to green there
would have been the precise failure this phase exists to correct.

**Decision: `PHASE_1C_COMPLETE`**

---

## PHASE 1D — Final governance closure

**Starting HEAD:** `5ff75df` · **ADR-0002: APPROVED AS REVISED** by owner decision.

| Field | Result |
|---|---|
| Implementation | **PASS** — two genuine defects closed. No application code touched |
| Tests | **PASS** — backend 434/2 skipped; governance **43** (26 controller + 17 envelope) |
| Security | **PASS** — no guard touched; no mutation target changed; Side A package still `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| Regression | **PASS** — controller **8 → 0**; envelope **6/20 → 8/8** |
| Human Test | **N/A** — governance only |
| Documentation | **PASS** — links 0 broken; secret scan 0; `git diff --check` clean |

### 1D.1 Readiness and supersession separated

The `status` column in `docs/side-b/EVIDENCE_INDEX.csv` carried two independent facts.
Writing `SUPERSEDED` into it **destroyed** the readiness four evidence documents had
declared. Recovered from each document's own `- Readiness status:` line — never inferred:

| Evidence | Recovered readiness | Supersession | Superseded by |
|---|---|---|---|
| `SB-EV-BOOT-001` | **SELF-VALIDATED** | SUPERSEDED | `SB-EV-G1-005` |
| `SB-EV-BOOT-002` | **AUTOMATED-TESTED** | SUPERSEDED | `SB-EV-G1-005` |
| `SB-EV-BOOT-003` | **BLOCKED** *(control — never overwritten)* | SUPERSEDED | `SB-EV-G1-005` |
| `SB-EV-BOOT-004` | **BLOCKED** | SUPERSEDED | `SB-EV-G1-005` |
| `SB-EV-BOOT-005` | **SELF-VALIDATED** | SUPERSEDED | `SB-EV-G1-005` |
| `SB-EV-G1-001` | **SELF-VALIDATED** *(was already correct)* | SUPERSEDED | `SB-EV-G1-002` |

**`SB-EV-BOOT-003` is what makes this a recovery rather than a guess.** Its value was never
overwritten, and it matches its document exactly — so the method is validated against a
control before being trusted on the four rows that lost their data. Every non-overwritten
row was additionally cross-checked; the transform was written to **abort** on any mismatch,
and none occurred.

The supersession register named **six** superseded artifacts while the index marked four.
All six are now marked, so the two registers agree.

**Naming.** The column is `supersession_status`, not `lifecycle_status`, because
`lifecycle_status` is already taken in this repository for the **product** business
lifecycle (`fixture|candidate|sample|approved|sellable|retired`, BPC-A-003, live in
`app/candidate_activation.py` as `BusinessLifecycle`). Reusing the identifier for a second
vocabulary would have recreated the one-name-two-meanings ambiguity Phase 1C removed.
"Supersession" is the repository's own term for this concept —
`evidence/side-b/EVIDENCE_ATTRIBUTION_AND_SUPERSESSION.md`. **Deviation from the literal
instruction, taken deliberately and reported here.**

`SUPERSEDED` was **not** added to the readiness vocabulary. Admitting it there would
re-legalise the overwrite that lost the data.

### 1D.2 Handoff envelopes

`6/20` was two separate problems.

**Genuinely broken (2).** `SB-HO-B1-001` and its `_v1_0_0` twin lacked `assumptions` and
`questions`. The questions were **already in the document** — §9 asked three — so they were
named rather than invented, and §3a records assumptions restating what §1 and §3 already
established. **No claim, finding, disposition or acceptance criterion changed**, so the
version is deliberately not bumped; an envelope-completion note records this in §8.

**Never envelopes (11).** The checker scanned inside the delivered partner package —
brand-prototype documents, a README, a VALIDATION_REPORT. Demanding "sender" and "need-by
gate" of a brand identity document is a category error, and the package is sealed by
`CHECKSUMS_SHA256.txt` (54/54), so satisfying the check would have required breaking its own
manifest. It also **double-counted**: 20 reported against 19 unique, because the package
carries its own nested `handoffs/` directory.

A handoff envelope is now defined as a document a side sent — directly in
`handoffs/{incoming,outgoing}/<side>/`. `REQUIRED` is **unchanged**; all eighteen fields are
still demanded of all eight envelopes.

### 1D.3 Recorded, not fixed

| Item | Status |
|---|---|
| `handoffs/incoming/side-a/DEDUNET_Platform_Integration_v1/handoffs/outgoing/HANDOFF_SIDE_A_TO_SIDE_B_DEDUNET_v1.md` | **Excluded and would not pass.** It *is* a genuine handoff envelope, but it is Side A's, inside a checksum-sealed package, and covered by that package's own `VALIDATION_REPORT.md`. Repairing it would break the 54/54 manifest — a verified control. Reported rather than hidden by the exclusion |
| 3 `CSV EMPTY` warnings | Header-only templates in `docs/operations/`. Warnings, not errors; correct as templates |

**Decision: `PHASE_1D_COMPLETE`**

---

## Platform decisions

Re-stated at every phase boundary, deliberately separate.

# `DEDUNET_PLATFORM_V1_PRODUCTION_BLOCKED`

# `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED`

Nothing in Phases 0, 0A or 1 changes either, and neither could be changed by them. The first
is blocked because eighteen of twenty phases have not started. The second is blocked by the
twenty-item list in the readiness decision §11, dominated by human and external evidence no
amount of engineering in this repository can produce.
