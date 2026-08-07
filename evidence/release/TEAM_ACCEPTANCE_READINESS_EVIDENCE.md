# Team acceptance readiness — execution evidence

**Artifact ID:** EV-REL-001 · **Version:** 1.0 · **Owner:** Orchestrator (controller)
**Status:** `AUTOMATED-TESTED` · **Date:** 2026-08-07
**Reviewed commit:** `fc7bdeb` → **final** `1e657bf` + this evidence commit
**Decision:** [`READY_FOR_TEAM_ACCEPTANCE_TESTING`](../../docs/system-of-record/TEAM_ACCEPTANCE_READINESS_DECISION.md)

Every number here was produced by executing a command in this repository during the review.
Nothing is carried forward from an earlier milestone without being re-run.

---

## 1. Starting state

| Check | Result |
|---|---|
| `git rev-parse --show-toplevel` | `C:/Users/User/Desktop/Claude/Fashion_Commerce_Codex_Multi_Agent_Pack` ✅ |
| `git branch --show-current` | `dedunet/repository-restructure-and-workstreams-a-f` |
| `git rev-parse HEAD` | `fc7bdeb` ✅ matches expected |
| `git status --short` | clean ✅ |
| Repository identity | ends `Fashion_Commerce_Codex_Multi_Agent_Pack` ✅ |

## 2. Milestone ledger

All 11 named commits exist and are ancestors of HEAD — verified with
`git cat-file -t` and `git merge-base --is-ancestor`.

| Milestone | Commit | Subject | Status token located |
|---|---|---|---|
| Restructuring | `f7af320` | *refactor: restructure repository without behavior changes* | `RESTRUCTURE_VERIFIED` |
| Workstream A | `d143c12` | *feat: workstream A — PostgreSQL runtime foundation* | `WORKSTREAM_A_VERIFIED` |
| Workstream C | `48cd58a` | *feat: workstream C — public request rate limiting* | `WORKSTREAM_C_VERIFIED` |
| Workstream E | `efe168f` | *feat: workstream E — standalone local staging configuration* | `WORKSTREAM_E_VERIFIED` |
| Workstream B | `4a2c548`, `054fd47`, `c1f0188` | outbox → claim leases → fencing | `WORKSTREAM_B_VERIFIED_WITH_LEASE_FENCING` |
| Workstream D | `d8e2f04` | *feat: workstream D — PostgreSQL backup and isolated restore rehearsal* | `WORKSTREAM_D_VERIFIED`, `LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED` |
| Workstream F | `02a5796` | *feat: workstream F — Expo mobile rebuild against the commerce contract* | ⚠️ `WORKSTREAM_F_CONDITIONALLY_VERIFIED` |
| DEDUNET integration | `66c3100` | *test: complete DEDUNET integration verification* | `DEDUNET_INTEGRATION_VERIFIED` |
| Branded vertical slice | `fc7bdeb` | *docs: close branded vertical-slice media gap* | `BRANDED_VERTICAL_SLICE_VERIFIED` |

**⚠️ One discrepancy.** The brief expected `WORKSTREAM_F_ACCEPTED_FOR_DEDUNET_INTEGRATION`.
A scan of every tracked `.md`/`.json` finds only `WORKSTREAM_F_CONDITIONALLY_VERIFIED` and
`WORKSTREAM_F_VERIFIED` (the latter only in prose explaining why it was *not* used). The
expected token does not exist. Reported, not retro-fitted — F is conditional solely on
`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`, and its output was consumed and re-verified by
both later verified milestones. No evidence file was edited to manufacture the token.

`EAS_PROJECT_CONFIGURATION_VERIFIED`, `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`,
`EXTERNAL_SMTP_DELIVERY_PENDING` and `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` were all located
in committed files and are unchanged.

## 3. Capability matrix

Blocking stage legend: **TA** team acceptance · **HS** hosted staging · **PL** public launch.

### Repository and governance

| Capability | Evidence | Verification | Status | Residual risk | Human/external dep. | Blocks |
|---|---|---|---|---|---|---|
| Repository root normalized | `docs/architecture/RESTRUCTURE_COMPLETION_REPORT.md` | `git rev-parse --show-toplevel` | ✅ | none | — | — |
| Branch and history intact | this document §2 | 11 commits confirmed ancestors | ✅ | none | — | — |
| Working tree clean | §7 | `git status --porcelain` empty | ✅ | none | — | — |
| Source-of-truth docs current | `docs/system-of-record/` | reviewed | ⚠️ | CONFLICT-009 open (README, KNOWN_LIMITATIONS stale) | — | PL |
| Conflict register current | `CONFLICT_AND_RESOLUTION_REGISTER.md` | CONFLICT-012 closed this review | ✅ | 009, 010 open | owner | PL |
| Rollback instructions | decision §12 | present per milestone | ✅ | none | — | — |
| Evidence packages committed | `evidence/` | 40+ files tracked | ✅ | none | — | — |

### Database

| Capability | Verification | Status | Blocks |
|---|---|---|---|
| PostgreSQL runtime | full suite on PostgreSQL 16 | ✅ 309 passed | — |
| SQLite dev/test support | full suite on SQLite | ✅ 307 passed, 2 skipped | — |
| Alembic revision | `alembic current` | ✅ `a7c31f9be402 (head)` | — |
| Clean migration upgrade | fresh DB → head | ✅ | — |
| Populated migration upgrade | seed + DEDUNET import, then cycle | ✅ | — |
| Downgrade | `downgrade base` on populated DB | ✅ reached base | — |
| Re-upgrade | `upgrade head` again | ✅ back to `a7c31f9be402` | — |
| Constraints | restore parity | ✅ check/unique/PK/FK identical | — |
| Indexes | restore parity | ✅ identical | — |
| Inventory integrity | journeys + suite | ✅ 25→23 exact, no overselling | — |
| Concurrency integrity | `-k "concurren or oversell or reserve"` | ✅ 9 passed, 1 PostgreSQL-only skip | — |

### Security

| Capability | Verification | Status | Blocks |
|---|---|---|---|
| Strong session secret required | refuses placeholder/short secrets outside dev | ✅ | — |
| Administrator authentication | journeys, admin phase | ✅ 26/26 | — |
| Customer authentication | journeys | ✅ | — |
| Erased-customer handling | mutation M28 | ✅ detected | — |
| Stored-XSS controls | `test_frontend_security.py` | ✅ 6 passed, no `innerHTML` | — |
| Input validation | suite | ✅ | — |
| CORS origin-scoped | rate-limit phase | ✅ | — |
| Correlation IDs | phases + proxy tests | ✅ present on 429s | — |
| Proxy-header boundary | `test_proxy_boundary.py`, real servers | ✅ 18 passed | — |
| Secret scan | history + tracked files | ✅ no `.env` anywhere | — |
| Personal-data scan | tracked text | ✅ only `.example` domains | — |
| Read-only API filesystem | `touch /app/__probe` in container | ✅ refused | — |

### Rate limiting

| Capability | Verification | Status | Blocks |
|---|---|---|---|
| Login limit | staging smoke | ✅ `401`×10 → `429` | — |
| Registration limit | proxy suite | ✅ own bucket | — |
| Cart/default limit | suite | ✅ | — |
| Browser-readable `Retry-After` | proxy suite + phases | ✅ exposed via CORS | — |
| Spoofed XFF resistance | staging smoke | ✅ 16/16 → 429, `bypass_present false` | — |
| Real-server boundary test | `test_proxy_boundary.py` | ✅ 18 passed | — |
| One-process/one-replica limit documented | `rate_limit.py`, staging compose | ✅ documented, **not solved** | HS, PL |

### Notifications

| Capability | Verification | Status | Blocks |
|---|---|---|---|
| Console adapter | worker log | ✅ `"sender": "console"` | — |
| SMTP adapter (protocol-level) | suite | ✅ implemented, unused | — |
| Outbox persistence | restore parity | ✅ preserved | — |
| Separate worker | container + mutation M31 | ✅ | — |
| Retries | suite | ✅ | — |
| Maximum attempts | mutation M30 | ✅ detected | — |
| Abandoned-claim recovery | mutations M32–M34 | ✅ detected | — |
| Claim leases | migration `c2f8d1b40e77` | ✅ persisted expiry | — |
| Stale-worker fencing | mutations M38–M41 | ✅ detected | — |
| DEDUNET identity | admin phase | ✅ subject carries `DEDUNET` | — |
| Test-order indication | mutation M61 | ✅ `[TEST ORDER]` | — |
| Erased-customer suppression | mutation M28 | ✅ detected | — |
| Real delivery | — | ⛔ `EXTERNAL_SMTP_DELIVERY_PENDING` | PL |

### Backup and recovery

All ✅ — custom-format dump, SHA-256, metadata, checksum-before-restore, source protection,
isolated restore, schema/table/index/constraint parity, functional restore, DEDUNET
catalogue, order provenance and notification preservation. `LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED`.
**Production DR is not claimed** — no offsite copy, no schedule, no RPO/RTO. Blocks PL.

### Local staging

| Capability | Verification | Status | Blocks |
|---|---|---|---|
| Standalone Compose | own file, nothing inherited | ✅ | — |
| PostgreSQL not exposed | no `ports:` on `db` | ✅ | — |
| No automatic demo seed | `SEED_DEMO_DATA: "0"` | ✅ | — |
| Manual admin bootstrap | `manage.py create-admin` | ✅ | — |
| Strong secret requirement | entrypoint `check-config` | ✅ | — |
| Read-only root filesystem | write probe refused | ✅ | — |
| Resource limits | memory/cpu declared | ✅ | — |
| One Uvicorn worker | `--workers 1` | ✅ | — |
| Explicit proxy boundary | startup line | ✅ `proxy_headers: false` | — |
| DEDUNET assets in image | 31 files, SHA-256 match | ✅ | — |
| `/ready` | 200 | ✅ | — |
| `/health` | 200 | ✅ | — |

### Web / Mobile / Admin / Brand / Modes

All ✅ against the criteria in the brief, evidenced by: container acceptance 29/29, the
137/137 journey phases, `test_web_media_resolver.py` (11), `test_web_gallery.py` (12),
`test_frontend_security.py` (6), mobile 117 + 18/18 mutations + clean `npm ci` + `tsc` +
Expo export, and brand `NORMALIZATION_VERIFIED` with 0 customer-facing legacy references.
Mobile native binary: ⛔ `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` (blocks store launch only).

**Commerce modes.** `BRAND_PREVIEW_MODE`: 5 products visible with real media, checkout
blocked, no payment call, zero effective sellability — re-verified after the L11 fix
(catalogue 5, cart-add 409). `COMMERCE_TEST_MODE`: synthetic inventory explicitly loaded
onto one SKU, sandbox payments only, orders stamped `COMMERCE_TEST_MODE`, notifications
labelled, cleanup available. `PUBLIC_COMMERCE_MODE`: refused — see L10 for exactly how.

## 4. Regression battery

| Check | Result |
|---|---|
| Side A checksum verification | **54/54**, 0 missing, 0 mismatched → `DEDUNET_HANDOFF_INTEGRITY_VERIFIED` |
| Brand normalization drift | `NORMALIZATION_VERIFIED` — 5 / 62 / 62 / 31 / 18 / 1 |
| Container build (no cache) | succeeds; `PACKAGED_BRAND_ASSETS_VERIFIED` in the build log |
| Container asset verification | **31/31** files, bytes match manifest SHA-256 |
| Container security scan | no `.git`, `.env`, evidence, dumps, handoffs, docs, tests, `node_modules`; no real secret values; read-only rootfs enforced; 73.7 MB |
| Container media acceptance | **29/29** — 31/31 assets, 18/18 media, DDN-TS01 `[200×4]`, 9/9 hostile refused |
| SQLite full suite | **307 passed, 2 skipped** |
| PostgreSQL full suite | **309 passed** |
| Backend mutation harness | **68 run, 68 detected, 0 survived** |
| Proxy-boundary tests | **18 passed** |
| SQLite + PostgreSQL concurrency | **9 passed, 1 skipped** (PostgreSQL-only) |
| Web media resolver tests | **11 passed** |
| Web gallery tests | **12 passed** |
| Admin / frontend security tests | **6 passed** |
| Mobile clean install | `npm ci` from committed lockfile ✅ |
| Mobile Expo dependency matrix | `Dependencies are up to date` |
| Mobile TypeScript | `tsc --noEmit` clean |
| Mobile complete tests | **117 passed**, 9 suites |
| Mobile mutations | **18/18 detected, 0 survived** |
| Expo web export | `Exported: dist` |
| OpenAPI drift | 30 paths, **NO_DRIFT** |
| Staging readiness | `/ready` 200, `/health` 200, storefront 200 |
| Preview-mode journey | Phase B **14/14**, C.10 **5/5** |
| Commerce-test journey | Phase C **28/28**, D **38/38**, E **26/26** |
| Notification-worker smoke | starts, 0 failed cycles, graceful SIGTERM after 66 cycles, bounded dispatch OK |
| Rate-limit smoke | control `429`×6, spoofed `429`×16, `bypass_present false` |
| Backup | `dedunet_slice-20260807T190328Z`, 61226 bytes, custom format |
| Checksum | `fe215cf0ae5fea329dade0a3f9d654d93fd33e3e8d3b25dbd3f967a6eeb7f304`, verified **before** restore |
| Isolated restore | into `dedunet_slice_rehearsal`, schema parity **PASS** |
| Restored functional checks | value parity **20/20**, functional **20/20** |
| Secret scan | no `.env` in history; none tracked |
| Personal-data scan | no real emails, phone numbers or IBANs |
| Active customer-facing legacy scan | **0** |
| Preserved fixture checksums | both match the values CI asserts |
| Git cleanliness | clean |

### Environment interruption, recorded

Docker Desktop's engine stopped partway through this review (`docker-desktop` WSL distro
`Stopped`, named pipe absent, `com.docker.service` unstartable without elevation). It was
restored with `docker desktop start`, after which the staging stack auto-restarted healthy
and the entire Docker-dependent battery above was executed. The only visible consequence
was one `cycle_failed` in the notification worker naming *"the database system is starting
up"* — the expected startup race, which the next cycle cleared. That behaviour is now
documented in runbook R11 so it is not mistaken for an incident.

## 5. Limitation classification

| ID | Classification | Basis |
|---|---|---|
| L4 public-mode CLI traceback | `NON_BLOCKING_TECH_DEBT` | refusal correct: non-zero exit, nothing written; presentation only |
| L5 `orders.status` not DB-constrained | `NON_BLOCKING_TECH_DEBT` (TA) / `BLOCKS_PUBLIC_LAUNCH` | all 6 writes are enum constants; the only client-supplied status is a read filter; no reachable invalid write through API or admin |
| L6 stale runbook R11 | **RESOLVED** | rewritten against the delivered worker; every command executed first |
| L7 process-local rate limiter | `BLOCKS_HOSTED_STAGING` / `BLOCKS_PUBLIC_LAUNCH` | valid for one process/replica only; explicitly not solved |
| L8 no Git remote | `NON_BLOCKING_TECH_DEBT` (TA) / `BLOCKS_PUBLIC_LAUNCH` | local acceptance needs no remote; CI has never run; single-copy governance risk |
| L9 lazy thumbnails | **NOT A DEFECT** | 0 rAF frames, `visibilityState hidden`, IntersectionObserver never fired; `fetch` 200 and fresh `Image()` loads |
| L10 public-mode 500 + healthy `/ready` | `NON_BLOCKING_TECH_DEBT` (TA) / `BLOCKS_PUBLIC_LAUNCH` | block intact and fail-closed; readiness must not report healthy when unable to serve |
| L11 mode switch inert in compose | **RESOLVED** (`1e657bf`) | demonstrated, fixed, regression-tested |

## 6. Corrections made during the review

| Commit | Type | Justification |
|---|---|---|
| `1e657bf` | implementation | Blocking defect: acceptance steps 6, 7, 8, 17, 18 were unperformable. Demonstrated failure → narrow fix → regression test → evidence → separate commit, exactly as the brief requires. |
| this commit | documentation | Runbook R11 correction, CONFLICT-012 closure, readiness documents. |

## 7. Final state

| Check | Result |
|---|---|
| Final HEAD | see decision §1 |
| `git status --porcelain` | clean |
| Alembic head | `a7c31f9be402` |
| Verified milestone history | not rewritten |
| Scratch resources | rehearsal database dropped; source untouched |
