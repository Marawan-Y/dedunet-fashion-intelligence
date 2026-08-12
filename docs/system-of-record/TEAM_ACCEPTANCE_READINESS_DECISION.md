# DEDUNET — Team acceptance readiness decision

**Artifact ID:** SOR-TAR-001 · **Version:** 1.1 · **Owner:** Orchestrator (controller)
**Original decision:** 2026-08-07 at `fc7bdeb` · **Status updated:** 2026-08-12
**Evidence:** [`evidence/release/TEAM_ACCEPTANCE_READINESS_EVIDENCE.md`](../../evidence/release/TEAM_ACCEPTANCE_READINESS_EVIDENCE.md)
· [`TEAM_ACCEPTANCE_READINESS_MATRIX.json`](../../evidence/release/TEAM_ACCEPTANCE_READINESS_MATRIX.json)
· [`evidence/team-acceptance/LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md`](../../evidence/team-acceptance/LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md)

---

## 0. Current status — supersedes §1

# `LOCAL_TEAM_ACCEPTANCE_PASSED`

**Date:** 2026-08-12 · **Decided by:** human acceptance manager

The acceptance testing that §1 authorized has now been **performed and passed**. A human
tester executed the script in `docs/operations/TEAM_ACCEPTANCE_TEST_SCRIPT.md` end to end:
environment, preview-mode storefront, admin portal, Expo web preview, and the full
commerce-test journey — synthetic inventory, fictional customer, sandbox decline, sandbox
success, backend and admin test-order provenance, fulfilment, the notification worker,
customer shipped/tracking visibility, synthetic inventory cleanup, return to preview mode,
preview purchase blocking, and the `PUBLIC_COMMERCE_MODE` activation guard.

Gate-by-gate results, the retained acceptance orders, the two post-acceptance defects found
and corrected, and the exact regression counts are in
[`evidence/team-acceptance/LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md`](../../evidence/team-acceptance/LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md).

### What this status does NOT mean

`PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` is **unchanged and fully in force**. This is not
`READY_FOR_PUBLIC_LAUNCH`, not production readiness, and not a launch authorization. It
records one thing: the *local, internal* acceptance script was run by a human against
fictional data, synthetic stock and a sandbox payment adapter, and it passed.

Every blocker in §11 remains open, and none was attempted. In particular the
`PUBLIC_COMMERCE_MODE` guard was tested during acceptance and **refused**, as designed:

```text
CommerceModeError: PUBLIC_COMMERCE_MODE cannot be enabled by configuration.
Public commercial launch is BLOCKED.
```

The runtime was returned to `BRAND_PREVIEW_MODE` afterwards, which is the state the
deployment is in now.

### Status history

| Date | Status | Commit |
|---|---|---|
| 2026-08-07 | `READY_FOR_TEAM_ACCEPTANCE_TESTING` | `fc7bdeb` |
| 2026-08-12 | `LOCAL_TEAM_ACCEPTANCE_PASSED` | this commit |

---

## 1. Executive decision *(as decided 2026-08-07; superseded by §0)*

# `READY_FOR_TEAM_ACCEPTANCE_TESTING`

A team member can exercise the complete internal system — local staging, preview mode,
commerce-test mode, web, mobile, admin, PostgreSQL, sandbox payment, synthetic inventory,
the notification worker, and backup and restore — using only what is in this repository and
Docker. No public DNS, real payment, real stock, live SMTP, Apple or Google publishing, or
trademark clearance is required to complete the acceptance script in §10.

**This is not production readiness and not a launch authorization.**
`PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` is unchanged. The public-launch gate (§11) is a
separate, longer list dominated by human and external evidence that no amount of
engineering in this repository can close.

Two corrections were made during the review, both permitted by the review brief and each in
its own commit:

* **`1e657bf` — a blocking defect.** `COMMERCE_MODE` was undeclared in both compose files,
  so local staging **could not be switched into `BRAND_PREVIEW_MODE` at all**. Steps 6, 7,
  8, 17 and 18 of the acceptance script were unperformable, silently. Found by executing
  the script's own commands rather than trusting them. Fixed, regression-tested (§7/L11).
* **Runbook R11** — stale documentation claiming no notification dispatcher exists (§7/L6).

No other implementation was changed.

---

## 2. Verified baseline

Re-executed at `fc7bdeb` during this review, not copied forward:

| Measure | Expected | Observed |
|---|---|---|
| Side A immutable package | 54/54 | **54/54**, 0 missing, 0 mismatched |
| DEDUNET products | 5 | **5** |
| DEDUNET variants | 62 | **62** (12+2+18+12+18) |
| Unique DEDUNET SKUs | 62 | **62** |
| Product-media relations | 18 | **18** |
| Registered brand assets | 31 | **31** |
| Container brand assets | 31/31 | **31/31**, bytes match manifest SHA-256 |
| Container product media | 18/18 | **18/18** |
| Customer-facing MERET/MERYT | 0 | **0** |
| Brand normalization | NO_DRIFT | **NORMALIZATION_VERIFIED** |
| SQLite suite | 301 / 2 skipped | **307 passed, 2 skipped** — see delta |
| PostgreSQL suite | 303 | **309 passed** — see delta |
| Backend mutations | 68/68, 0 survived | **68/68, 0 survived** |
| Proxy-boundary tests | 18 | **18 passed** |
| Mobile suite | 117 | **117 passed** |
| Mobile mutations | 18/18 | **18/18, 0 survived** |
| Git | clean | **clean** |

### Test-count delta, explained

`301 → 307` and `303 → 309`: **+6**, all from
`services/commerce-api/tests/test_compose_mode_switch.py`, the regression guard added with
the blocking-defect fix `1e657bf`. Four are parametrised static assertions over the two
compose files, two are in-process assertions on `modes.current_mode()`.

**No test was weakened, skipped or relaxed to meet a historic count.** The two skips are
the same two PostgreSQL-only tests as before. Every other count in the table is identical
to the branded vertical slice, which is the expected result for a review.

---

## 3. Milestone ledger

Every named commit exists and is an ancestor of `fc7bdeb`.

| Milestone | Commit | Recorded status | Reconciled |
|---|---|---|---|
| Repository restructuring | `f7af320` | `RESTRUCTURE_VERIFIED` | ✅ |
| Workstream A — PostgreSQL | `d143c12` | `WORKSTREAM_A_VERIFIED` | ✅ |
| Workstream C — rate limiting | `48cd58a` | `WORKSTREAM_C_VERIFIED` | ✅ |
| Workstream E — local staging | `efe168f` | `WORKSTREAM_E_VERIFIED` | ✅ |
| Workstream B — notifications | `4a2c548` → `054fd47` → `c1f0188` | `WORKSTREAM_B_VERIFIED_WITH_LEASE_FENCING` | ✅ |
| Workstream D — backup/restore | `d8e2f04` | `WORKSTREAM_D_VERIFIED`, `LOCAL_BACKUP_AND_RESTORE_REHEARSAL_VERIFIED` | ✅ |
| Workstream F — mobile | `02a5796` | `WORKSTREAM_F_CONDITIONALLY_VERIFIED` | ⚠️ **see below** |
| DEDUNET integration | `66c3100` | `DEDUNET_INTEGRATION_VERIFIED` | ✅ |
| Branded vertical slice | `fc7bdeb` | `BRANDED_VERTICAL_SLICE_VERIFIED` | ✅ |

### ⚠️ Discrepancy — Workstream F status token

The review brief expected `WORKSTREAM_F_ACCEPTED_FOR_DEDUNET_INTEGRATION`. **That token does
not exist anywhere in this repository.** The recorded status is
`WORKSTREAM_F_CONDITIONALLY_VERIFIED` (`evidence/workstream-f/WORKSTREAM_F_EVIDENCE.md`).

This is a naming discrepancy, not a substantive one, and it is reported rather than
retro-fitted. The two are reconcilable: F is conditional for exactly one reason —
`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`, because no Expo account exists in this
environment to produce a native binary. Every executable check passed, and F's output was
subsequently consumed and re-verified by both `DEDUNET_INTEGRATION_VERIFIED` and
`BRANDED_VERTICAL_SLICE_VERIFIED`, which is what "accepted for DEDUNET integration"
describes.

**No evidence file was edited to create the expected token.** Rewriting a verified
milestone's recorded status to match a later brief would destroy the very audit trail this
ledger exists to provide.

---

## 4. Architecture status

| Layer | State |
|---|---|
| API | FastAPI, single Uvicorn process via `app.server` (explicit ASGI proxy boundary) |
| Database | PostgreSQL 16 runtime; SQLite for development and the fast test path; Alembic head `a7c31f9be402` |
| Brand assets | Normalized package baked into the API image at `/app/brand-assets`, served by an allow-listed media route |
| Web | Static storefront + admin behind nginx; API base injected at image build time |
| Mobile | Expo/React Native, same commerce contract, web export verified |
| Notifications | Transactional outbox + separate worker container with claim leases and fencing |
| Backup | PostgreSQL custom-format dump, SHA-256 verified, restored into an isolated database |
| Modes | `BRAND_PREVIEW_MODE`, `COMMERCE_TEST_MODE`; `PUBLIC_COMMERCE_MODE` unreachable by configuration |

---

## 5. Capability matrix

The full matrix — every capability with its evidence path, verification method, status,
residual risk, human/external dependency and blocking stage — is in
[`evidence/release/TEAM_ACCEPTANCE_READINESS_EVIDENCE.md`](../../evidence/release/TEAM_ACCEPTANCE_READINESS_EVIDENCE.md) §3
and machine-readable in
[`TEAM_ACCEPTANCE_READINESS_MATRIX.json`](../../evidence/release/TEAM_ACCEPTANCE_READINESS_MATRIX.json).

Summary by group:

| Group | Capabilities | Blocking team acceptance |
|---|---|---|
| Repository and governance | 7 | 0 |
| Database | 11 | 0 |
| Security | 12 | 0 |
| Rate limiting | 7 | 0 |
| Notifications | 12 | 0 |
| Backup and recovery | 13 | 0 |
| Local staging | 12 | 0 |
| Web | 15 | 0 |
| Mobile | 14 | 0 |
| Admin | 8 | 0 |
| Brand integration | 11 | 0 |
| Commerce modes | 3 | 0 |

---

## 6. Regression results

Full battery re-executed at `fc7bdeb` — see evidence §4. Headlines:

`Side A 54/54` · `NO_DRIFT` · `container 29/29` · `31/31 assets` · `18/18 media` ·
`SQLite 301+2s` · `PostgreSQL 303` · `mutations 68/68` · `proxy 18` · `web 23` ·
`mobile 117` · `mobile mutations 18/18` · `OpenAPI NO_DRIFT` · `journeys 137/137` ·
`backup+restore PASS / 20/20 / 20/20` · `secrets clean` · `personal data clean` ·
`legacy 0` · `git clean`

---

## 7. Known limitations

| ID | Limitation | Classification |
|---|---|---|
| **L4** | `load-test-inventory` in `PUBLIC_COMMERCE_MODE` prints an uncaught `CommerceModeError` traceback instead of the `{"result": "refused"}` JSON the other two refusals return | **NON_BLOCKING_TECH_DEBT** — operator ergonomics only |
| **L5** | `orders.status` is `varchar(15)` with no DB `CHECK`; validity is application-enforced | **NON_BLOCKING_TECH_DEBT** for team acceptance; **BLOCKS_PUBLIC_LAUNCH** as a defence-in-depth item |
| **L6** | Runbook R11 claimed no notification dispatcher exists | **RESOLVED during this review** |
| **L7** | Rate-limit buckets are process-local | **BLOCKS_HOSTED_STAGING** / **BLOCKS_PUBLIC_LAUNCH** at >1 replica; not blocking team acceptance |
| **L8** | No Git remote | **NON_BLOCKING_TECH_DEBT** for local acceptance; **BLOCKS_PUBLIC_LAUNCH** for governance and CI |
| **L9** | Catalogue-grid lazy thumbnails not observed loading under automation | **NOT A DEFECT** — automation artifact, proven |
| **L10** | In `PUBLIC_COMMERCE_MODE` the API starts, `/ready` returns 200, and every commerce request returns 500 | **NON_BLOCKING_TECH_DEBT** for team acceptance; **BLOCKS_PUBLIC_LAUNCH** |
| **L11** | `COMMERCE_MODE` was undeclared in both compose files, so the mode could not be switched in any deployed stack | **RESOLVED during this review** (`1e657bf`) |

### L4 — ergonomics, not a functional or security problem

The refusal is correct and complete: non-zero exit, nothing written, and the message names
the reason. Verified during the vertical slice with an explicit assertion that a refused
command writes no stock. Only the *presentation* differs from the other two refusals. It
does not prevent controlled team testing, so it is recorded and not fixed.

### L5 — reachable risk is nil through the application

Assessed rather than asserted. Every write to `orders.status` is a Python `OrderStatus`
enum constant, at six call sites, all in `services.py`:

```
services.py:639  status=OrderStatus.PENDING_PAYMENT     services.py:771  order.status = OrderStatus.SHIPPED
services.py:707  order.status = OrderStatus.CANCELLED   services.py:803  order.status = OrderStatus.CANCELLED
services.py:724  order.status = OrderStatus.PAID        services.py:850  order.status = OrderStatus.REFUNDED
```

The only client-supplied `order_status` in the API is a **read-side filter**
(`api.py:695–700`, `[o for o in orders if o.status.value == order_status]`) — it never
writes. No endpoint accepts a status for writing, and the admin transitions go through
guarded service functions whose refusal was verified after restore (an illegal transition
returned 409).

So there is **no reachable path** for an invalid status through the API or admin. The
missing `CHECK` matters only for direct SQL — a `psql` session, or a future service that
bypasses the ORM. It is therefore defence-in-depth debt, correctly described as
**application-enforced**, never as DB-enforced. Adding the constraint is a migration and
belongs to hardening, not to this review.

### L7 — a deployment constraint, not a solved problem

`MULTI_REPLICA_DEPLOYMENT_BLOCKED_PENDING_SHARED_OR_GATEWAY_RATE_LIMITING` stands. Buckets
live in one process's memory; N workers means N times the effective limit. Local staging
runs exactly one API process and one worker, which is the configuration that was verified.
Multi-replica rate limiting is a **hosted-scaling and public-launch requirement** and is
explicitly *not* claimed as solved.

### L8 — classification

* **Local team acceptance:** not blocking. Everything needed is in the working copy.
* **Collaboration and CI:** blocking. There is nowhere to push, so `.github/workflows/ci.yml`
  has never executed and no second person can obtain the work.
* **Production governance:** blocking. A single working copy on one machine is the only
  existing copy of every verified result.

No remote was invented. CONFLICT-010 remains an owner decision, because publishing this
repository requires a deliberate secret and personal-data review first.

### L9 — proven to be an automation artifact

The prior milestone recorded this as unresolved. It is now settled with direct evidence.
In the automation pane, at a 1280×720 viewport with three cards geometrically inside it:

| Probe | Result |
|---|---|
| `requestAnimationFrame` frames in 2 s | **0** — the renderer produces no frames |
| `document.visibilityState` | `hidden` |
| `IntersectionObserver` on an in-viewport card | **never fired** |
| `fetch()` of the same image URL | **200 `image/svg+xml`** |
| fresh `new Image()` with the same `src` | **loads, 1200 px** |
| eager images on the product page, same pane | **load normally** |

Chrome drives `loading="lazy"` from intersection logic that requires a rendering tab. In a
hidden, non-compositing tab that logic never runs, so a lazy image never loads however
in-viewport its geometry says it is — the earlier `inView: true` came from
`getBoundingClientRect`, which the renderer does not share. Everything the lazy path
depends on is verified working.

**No product code was changed for this.** Changing implementation to satisfy a measurement
artifact would be the wrong repair. A human tester with a visible browser confirms it in
step 7 of §10.

### L10 — public commerce is blocked, but the refusal is a 500 and readiness still lies

Measured on the staging container with `COMMERCE_MODE=PUBLIC_COMMERCE_MODE`:

| Observation | Value |
|---|---|
| container | starts, reports `(healthy)` |
| `/ready` | **200** |
| `GET /api/v1/catalog/products` | **500** |
| log | `CommerceModeError: PUBLIC_COMMERCE_MODE cannot be enabled by configuration …` |

The security property is intact and fail-closed: nothing can be browsed, carted or bought,
and the mode is unreachable by configuration by design. Two things are nonetheless wrong
for operations. `modes.current_mode()` raises per request rather than refusing at boot, so
the refusal surfaces as an unhandled 500; and `/ready` reports healthy while the
application cannot serve a single commerce request, so an orchestrator would keep the
container in rotation.

Not blocking team acceptance — step 18 is a *negative* test whose purpose is to show public
commerce is blocked, and it demonstrably is. It is recorded rather than fixed because
changing startup or readiness semantics is a hardening change, not a review correction.
Before public launch, readiness must not report healthy when the configured mode makes the
application unable to serve.

### L11 — the mode switch did not work in any deployed stack *(resolved)*

`COMMERCE_MODE` was declared in neither compose file, and Compose forwards no arbitrary
shell variable, so `COMMERCE_MODE=BRAND_PREVIEW_MODE docker compose up -d api` set it in the
operator's shell and nowhere else. Before the fix, after issuing exactly that command:
`COMMERCE_MODE=[]` inside the container, 6 products including a legacy fixture item, and
`POST /api/v1/cart/items` → **HTTP 200**, the item in a bag. After: `[BRAND_PREVIEW_MODE]`,
5 products all carrying an external product id, and **409** naming brand preview.

This is the same shape as the proxy-header defect closed earlier in this programme — the
application was correct and every in-process test passed, because pytest can set the
variable freely and the deployed stack could not. Fixed in `1e657bf` with
`tests/test_compose_mode_switch.py`, demonstrated to fail without the fix.

---

## 8. Human prerequisites

| Item | Status | Blocks |
|---|---|---|
| Risk-owner acceptance | `ASSIGNMENT_RECORDED — HUMAN ACCEPTANCE PENDING` | Public launch |
| Brand legal / trademark clearance | `LEGAL_CLEARANCE_PENDING` | Public launch |
| Verified product existence, origin, material | Not yet sufficient for real commercial claims | Public launch |
| Approved commercial pricing | Not approved | Public launch |
| Privacy / legal review | Not performed | Public launch |
| Publisher identity (Apple, Google) | `DEFERRED — PUBLISHER IDENTITY PENDING` | Native store launch |

None of these blocks team acceptance testing, which uses fictional data, synthetic stock
and a sandbox payment adapter.

## 9. External prerequisites

| Service | Status | Blocks |
|---|---|---|
| Expo — org `Dedunet`, project `72b0a18d-36dd-406f-a54b-ab481a95db88` | `EAS_PROJECT_CONFIGURATION_VERIFIED` · `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` | Native binary only; mobile web works |
| Apple Developer | `DEFERRED — PUBLISHER IDENTITY PENDING` | iOS store launch |
| Google Play | `DEFERRED — PUBLISHER IDENTITY PENDING` | Android store launch |
| SMTP | `EXTERNAL_SMTP_DELIVERY_PENDING` | Real mail delivery; console channel works |
| Hosted cloud | `DEFERRED — LOCAL STAGING ONLY` | Hosted staging and production |
| Live payment provider | Not activated | Public commerce |
| Real inventory | Not loaded | Public commerce |
| Real fulfilment | Not established | Public commerce |

**None of these has been transformed into a verified result.** Each remains exactly the
status the repository records.

---

## 10. Team acceptance instructions

See [`docs/operations/TEAM_ACCEPTANCE_TEST_SCRIPT.md`](../operations/TEAM_ACCEPTANCE_TEST_SCRIPT.md)
for the full 19-step script with copy-pasteable commands, expected output at each step, and
the shutdown warning about `docker compose down` versus the destructive `down -v`.

---

## 11. Public-launch blockers

Distinct from everything above. Public commercial launch remains **BLOCKED** until human
and external evidence resolves, at minimum:

1. Trademark and legal brand clearance (`LEGAL_CLEARANCE_PENDING`)
2. Verified product existence — no physical sample has been inspected
3. Verified origin — `origin_claim_status = UNVERIFIED`, `country_of_origin = XX`
4. Verified material composition — stated intention, not tested
5. Approved commercial pricing
6. Real inventory
7. Real fulfilment process and carrier integration
8. Live payment provider activation
9. External SMTP and deliverability
10. Hosted infrastructure
11. TLS and public networking
12. Multi-replica architecture with shared or gateway rate limiting (L7)
13. Monitoring and alerting
14. Offsite and scheduled backup
15. Production RPO/RTO definition and rehearsal
16. Apple and Google publisher identity, if native apps launch publicly
17. Risk-owner acceptance
18. Privacy and legal review
19. Database-level status constraints and similar hardening (L5)
20. A Git remote for governance and CI (L8)

None was attempted during this review.

---

## 12. Rollback references

| Scope | Reference |
|---|---|
| Media closure | `evidence/branded-vertical-slice/BRANDED_VERTICAL_SLICE_MEDIA_CLOSURE.md` §16 |
| Branded vertical slice | `evidence/branded-vertical-slice/BRANDED_VERTICAL_SLICE_EVIDENCE.md` §7 |
| Proxy-header correction | `git revert 3835aa0` (restores a bypassable configuration — not recommended) |
| This review | Documentation only; `git revert` of the readiness commit removes the documents and restores the stale R11 |
| Database | No schema change in this review; Alembic head `a7c31f9be402` |

---

## 13. Next human actions

> **Item 1 is complete.** The acceptance script was run and passed on 2026-08-12; see §0.
> Items 2–6 remain open.

1. ~~**Run the acceptance script**~~ — **DONE**, `LOCAL_TEAM_ACCEPTANCE_PASSED`. See
   [`evidence/team-acceptance/LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md`](../../evidence/team-acceptance/LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md).
2. **Decide CONFLICT-010** — whether this repository gets a private remote. That requires a
   secret and personal-data review first, and it unblocks CI and collaboration (L8).
3. **Accept or reassign risk owners** — `ASSIGNMENT_RECORDED — HUMAN ACCEPTANCE PENDING`.
4. **Authenticate Expo** if a native preview build is wanted
   (`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`).
5. **Close CONFLICT-009** — `docs/KNOWN_LIMITATIONS.md` and `README.md` still describe a
   pre-Workstream platform.
6. Do **not** begin hosted deployment on the strength of this decision. It authorizes
   internal acceptance testing only.
