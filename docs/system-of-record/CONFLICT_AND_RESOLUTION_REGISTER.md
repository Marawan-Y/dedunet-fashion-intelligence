# Conflict and Resolution Register

| Control | Value |
|---|---|
| Artifact ID | SOR-CONF-001 |
| Version | 1.1 |
| Owner | Technical lead |
| Status | SELF-VALIDATED |
| Updated | 2026-08-24 — CONFLICT-009 and CONFLICT-011 both **RESOLVED**; CONFLICT-011 closed by `EV-TA-006`, the iPhone acceptance record supplied by the human tester. Earlier same day: CONFLICT-009 (honesty documents rewritten at `41cee4c`). Previously 2026-08-06: CONFLICT-001 marked superseded; CONFLICT-009 and CONFLICT-010 added by the successor agent takeover (`SUCCESSOR_AGENT_TAKEOVER_REPORT.md`) |
| Rule | No material contradiction is resolved silently. Each carries a proposed resolution and an approval state. |

Resolution follows the source-of-truth hierarchy in the human manager approval, §4.

---

## CONFLICT-001 — Git repository root sits above the active project boundary

**Files:** `C:\Users\User\Desktop\Claude\.git`, `Fashion_Commerce_Codex_Multi_Agent_Pack/`,
`Fashion_Commerce_Two_Agent_Execution_Pack/`

**Conflicting values:** §1 names `Fashion_Commerce_Codex_Multi_Agent_Pack` as the only active
project root and forbids executing against `Fashion_Commerce_Two_Agent_Execution_Pack`. §10's
target tree implies the active project *is* the repository root. In fact the Git root is the
**parent** directory and tracks both packs; all four existing commits span that wider root.

**Affected systems:** version control, history preservation, `git mv`, CI checkout paths, release
packaging.

**Proposed resolution:** Keep the existing Git root. Perform all restructuring with `git mv`
inside `Fashion_Commerce_Codex_Multi_Agent_Pack/` only. Treat the sibling pack as untouched
read-only legacy. Do **not** re-initialise a repository inside the active project.

**Reason:** §12 requires history preservation via `git mv`. Re-initialising would discard all four
commits, including the verified baseline this work depends on. Nothing in the sibling pack is read
or written by the active project.

**Risk:** Low. A future extraction to a standalone repository is a separate, clean operation
(`git subtree split`) and is not needed now. Residual risk is cosmetic: the repository contains a
directory the boundary rule says to ignore.

**Owner:** Marawan Younis (secrets and infrastructure)
**Approval status:** **SUPERSEDED 2026-08-06** — resolved by commit `e84cb09`, which normalised the
Git root to the active project via `git subtree split`. `git rev-parse --show-toplevel` now returns
`C:/Users/User/Desktop/Claude/Fashion_Commerce_Codex_Multi_Agent_Pack`, the sibling pack has 0
tracked files, and no remote exists. The description above is retained as the historical record of
why the migration was performed; it no longer describes the current state. See
`docs/architecture/GIT_ROOT_NORMALIZATION.md` and `SUCCESSOR_AGENT_TAKEOVER_REPORT.md` §1.

---

## CONFLICT-002 — Duplicate source archive inside the active project

**Files:** `platform/poc.zip` (untracked, 143,201 bytes, sha256 `c15c4985…f45a6b`)

**Conflicting values:** §21 requires duplicate source archives to be removed; §9.3 forbids
discarding files blindly.

**Affected systems:** repository hygiene, "no duplicate active source trees".

**Proposed resolution:** Delete. Verified first by content comparison: **71 of 71 files are
byte-identical to the live `platform/poc` tree; 0 differ; 0 exist only in the archive.** It
carries nothing unique.

**Reason:** It is a stale snapshot of the live tree, was never tracked by Git, and is exactly the
"duplicate source archive" §21 names.

**Risk:** None. Content is fully reproducible from the working tree and from Git history.

**Owner:** Technical lead
**Approval status:** RESOLVED — safe to delete, verified duplicate.

---

## CONFLICT-003 — Domain ownership evidence contains personal data

**Files:** the registrar certification letter is **held privately by the owner and is not in this repository** — removed from the tree and from all history before first publication, because it names a real registrant against a real registration. See `evidence/governance/domain/README.md`.

**Conflicting values:** §18 requires the file to be copied into the repository and checked for
"password, API token, recovery code or payment secret" — it contains none, and that check passes.
It does contain the registrant's residential address, personal phone number and personal email,
repeated four times.

**Affected systems:** repository privacy posture, any future remote or release package.

**Proposed resolution:** Store as instructed and record the checksum. Do **not** redact
unilaterally. Flag for the owner with two options: keep in full while the repository stays
private, or substitute a redacted copy retaining domain, registrar, IANA number, dates,
registrant name and name servers, with the unredacted original held outside version control.

**Reason:** The instruction is explicit and the data is the owner's own. Altering evidence without
instruction would damage its evidentiary value. Silently committing personal data without saying
so would be worse.

**Risk:** Low today — no remote exists. Rises immediately if a remote is added or a release
package is published.

**Owner:** Marawan Younis (secrets and infrastructure)
**Approval status:** OPEN — awaiting owner decision. Not blocking.

---

## CONFLICT-004 — Side A prices are decimal major units; the platform is integer minor units

**Files:** `handoffs/incoming/side-a/.../data/brand-prototype/product-master.json`
(`prototype_price_eur: 72`), `variant-master.csv` (`price_eur: 72`),
`services/commerce-api/app/money.py`, DEC-010.

**Conflicting values:** `72` (EUR major) versus `7200` (integer minor units).

**Affected systems:** product import, pricing, checkout, order totals.

**Proposed resolution:** Convert during import via the existing `to_minor_units()`, which accepts
`int`/`str`/`Decimal` and **rejects binary floats**. Never parse a price through `float`. The
incoming package stays unmodified; conversion happens in the importer.

**Reason:** §16 mandates integer minor units; `money.py` already enforces exact conversion or
failure. `72 → 7200` is exact.

**Risk:** Low, provided no `float()` appears on the path. Guarded by existing money tests and a
new importer test.

**Owner:** Ahmed Younis (inventory and financial integrity)
**Approval status:** RESOLVED — deterministic conversion.

---

## CONFLICT-005 — Variants are not inline in the product master

**Files:** `product-master.json` (5 products, `variants: []` on every one),
`variant-master.csv` (62 rows).

**Conflicting values:** The JSON implies a nested model; the authoritative variant data is a
separate flat CSV keyed by `product_id`.

**Affected systems:** product import, SKU uniqueness, inventory seeding.

**Proposed resolution:** Treat `variant-master.csv` as authoritative for variants and join on
`product_id`. Verified: 62 rows, 62 unique SKUs, zero duplicates, zero orphans
(18/18/12/12/2 across the five products).

**Reason:** The CSV is complete and internally consistent; the empty JSON arrays are a
serialisation choice, not missing data.

**Risk:** Low. A naive importer reading only the JSON would silently create five products with no
purchasable variants — the importer must fail loudly if the join yields zero variants.

**Owner:** Technical lead
**Approval status:** RESOLVED.

---

## CONFLICT-006 — Side A origin wording versus the mandated origin state

**Files:** `product-master.json` (`origin: "Intended Egypt production; factory and
country-of-origin evidence pending."`), human approval §16.

**Conflicting values:** Prose intent versus the required typed state
`country_of_origin = XX`, `intended_origin = EG`, `origin_claim_status = UNVERIFIED`.

**Affected systems:** product schema, storefront display, AI grounding, claim gating.

**Proposed resolution:** Import Side A's prose into a non-authoritative descriptive field and set
the typed fields to the mandated values. `XX` is an intentionally invalid ISO code so it cannot be
mistaken for a substantiated origin. Never render "Made in Egypt" as verified.

**Reason:** §16 is higher in the hierarchy than the Side A delivery. Side A's own wording already
says evidence is pending, so the two are aligned in intent.

**Risk:** Low. Highest-consequence failure would be publishing an unverified origin claim; the
typed state plus display gating prevents it.

**Owner:** Aya Ashraf (brand claims and naming risk)
**Approval status:** RESOLVED.

---

## CONFLICT-007 — Single-image model versus multi-media delivery

**Files:** `product-master.json` (`imagery: [FRONT, BACK, DETAIL, LIFESTYLE]`),
`asset-register.csv` (31 assets), current `Product.image_url` single column.

**Conflicting values:** Four-plus media records per product versus one `image_url` string.

**Affected systems:** product schema, storefront PDP, mobile, admin, migrations.

**Proposed resolution:** Add a `product_media` table with `role` (front/back/detail/lifestyle/
campaign/collection) and ordering. Retain `image_url` temporarily as a derived primary-image
convenience, marked non-authoritative, then remove it once all consumers read `product_media`.

**Reason:** §16 states the single-image model must not remain the only authoritative
representation. All 31 registered assets exist on disk and all imagery references resolve.

**Risk:** Medium — a schema change touching web, mobile and admin. Mitigated by keeping the legacy
column during transition and migrating consumers one at a time.

**Owner:** Technical lead
**Approval status:** PROPOSED — scheduled for M7, not R0.

---

## CONFLICT-008 — Legacy MERET brand references in live platform source

**Files:** 19 files, of which 12 are live source; the remainder are runtime artefacts
(`__pycache__`, `commerce.sqlite3`) that are not version-controlled.

**Conflicting values:** Customer-facing MERET identity versus the selected DEDUNET brand.

**Affected systems:** storefront, admin, seed data, tests, docs.

**Proposed resolution:** Controlled migration per §17 via
`docs/side-b/DEDUNET_REBRAND_MIGRATION_REGISTER.md`, classifying every reference before changing
it. **No repository-wide find-and-replace.** Customer-facing values change first; technical
identifiers migrate separately with rollback. Explicitly **not** part of R0, which must be
behaviour-preserving.

**Reason:** §13 forbids brand changes in the restructuring commit; §17 forbids uncontrolled
replacement.

**Risk:** Medium if done carelessly — `MERET` appears in test fixtures and seed constants where a
blind replace would break assertions and demo credentials simultaneously.

**Owner:** Aya Ashraf (brand claims), with technical lead executing
**Approval status:** PROPOSED — scheduled for M7.

---

## CONFLICT-009 — The honesty documents contradict five delivered workstreams — **RESOLVED**

**Files:** `docs/KNOWN_LIMITATIONS.md`, `README.md`

**Conflicting values:** `KNOWN_LIMITATIONS.md` states "No rate limiting" (L86), "Backup and
restore — NOT_STARTED" (L50), "Nothing dispatches them … No message has ever been sent" (L63),
"PostgreSQL has **not** been exercised here" (L81), "Staging / production deployment —
NOT_STARTED" (L47), "81 tests pass" (L99) and "None of these has a **named human risk owner**"
(L38). `README.md` claims "81 tests" twice (L135, L152) and describes a MERET-era platform with no
PostgreSQL, rate limiting, notifications, staging or backup.

Against these: Workstreams A, B, C, D and E are all committed, evidenced and independently
re-verified — 167 SQLite / 168 PostgreSQL tests, 48/48 mutations, live 429 responses, a rehearsed
restore, and four named risk owners in `RISK_OWNER_REGISTER.md` v2.0.

`README.md` additionally links three files that do not exist: `docs/RUNBOOKS.md`,
`docs/EXTERNAL_SERVICE_ACTIVATION.md` and `KNOWN_LIMITATIONS.md`. The real paths are
`docs/operations/RUNBOOKS.md`, `docs/operations/EXTERNAL_SERVICE_ACTIVATION.md` and
`docs/KNOWN_LIMITATIONS.md`.

**Affected systems:** onboarding of any new agent or human, readiness review, gate decisions,
external communication about platform state.

**Proposed resolution:** A documentation-only commit updating both files to the verified state,
before Workstream F. Each corrected line must cite the evidence file that supports it. Do **not**
delete the historical entries wholesale — convert each `NOT_STARTED` to its verified status with a
pointer to `evidence/workstream-*/`, so the record shows the progression rather than erasing it.

**Reason:** The source-of-truth order places current Git implementation and executed tests above
documentation. `KNOWN_LIMITATIONS.md` is the file the repository designates as its honest
inventory — a stale honesty document is worse than none, because it is trusted. The direction of
the error is unusual and worth naming: these documents **understate** what was delivered. That is
the safe direction for a launch claim, but it is still false, and a readiness review conducted
over it would reject work that is in fact complete.

**Risk:** Medium. No runtime impact. The failure mode is decision-level: a reviewer, manager or
successor agent concluding that rate limiting, backups, notifications or PostgreSQL are missing
and either re-implementing them or blocking a gate that should pass.

**Owner:** Technical lead
**Approval status:** **RESOLVED 2026-08-24 at `41cee4c`.** Both files rewritten against the
executed state. Recorded by the successor agent 2026-08-06; not resolved silently and not fixed
during the read-only takeover, as intended.

**What was done, and what it cost.** Every corrected line is marked `**[was: …]**` in place, so
the drift is visible rather than erased — the resolution above required showing the progression,
and a clean rewrite would have destroyed exactly the record this register exists to keep. The
three dead `README.md` links now resolve, and a link check over both files plus the four new
architecture documents reports **0 broken**.

The counts were re-derived, not carried forward: **415 passed, 2 skipped** executed at `41cee4c`,
and **77 guard mutations** after this phase added five to the 72 that existed. The PostgreSQL
suite result is **carried
forward on prior evidence and explicitly labelled as such** in `KNOWN_LIMITATIONS.md` §7 rather
than restated as though re-run.

**One correction beyond the recorded scope.** `KNOWN_LIMITATIONS.md` §4 previously carried a
single "Android / iOS applications" row. That row cannot be true of both any more: Android has
passed native preview acceptance on an emulator and iOS has never been built. They are now
separate rows, and the iOS row says **do not infer iOS status from the Android result**. Merging
them was the shape of error that produces a false platform claim.

**Not closed by this.** The documents are now accurate about the *existing* platform. `ADR-0002`
proposes a repositioning whose entire domain is `NOT_STARTED`, and §4.1 of
`KNOWN_LIMITATIONS.md` records it as such. A future reader must not read that section as a
roadmap that is underway.

---

## CONFLICT-010 — No Git remote exists for the entire verified history

**Files:** repository configuration — `git remote` returns 0 entries

**Conflicting values:** Every verified artifact in this program — R0 and Workstreams A through E,
their evidence, and the immutable Side A package — exists on a single branch, in a single working
copy, on one developer machine. `GIT_ROOT_NORMALIZATION.md` §1 references a bundle at
`C:\Users\User\Desktop\dedunet_private_evidence\git_backup\`, which is outside the repository and
was not verified by the takeover.

**Affected systems:** continuity of all delivered work, disaster recovery, any future CI execution,
team acceptance testing, onboarding.

**Proposed resolution:** Owner decision, not an agent decision. Two viable paths: (a) a private
remote, which requires a deliberate secret and personal-data review first — the repository has
already carried an unredacted personal-data blob once (CONFLICT-003) and only a history purge
removed it; or (b) a scheduled, verified local bundle with a recorded checksum, which is weaker but
requires no third-party trust decision.

**Reason:** The repository's own backup runbook observes that RPO equals the time since someone
last ran a backup by hand. The same now applies to the source code and evidence themselves, and
unlike the database there is no rehearsal proving they can be recovered.

**Risk:** High in consequence, unknown in likelihood. Losing this machine loses every verified
result the program depends on. It does not block Workstream F.

**Owner:** Marawan Younis (secrets and infrastructure)
**Approval status:** OPEN — recorded by the successor agent 2026-08-06. Awaiting owner decision.
Explicitly **not** actioned: adding a remote would publish a repository whose personal-data and
secret posture the owner has not cleared for that purpose.

---

## CONFLICT-011 — Rate-limit documentation described a protection the deployment did not have

**Files:** `services/commerce-api/app/rate_limit.py` (docstring and `client_key`),
`docs/side-b/SIDE_B_LAUNCH_BLOCKER_AUDIT.md`, `evidence/workstream-c/WORKSTREAM_C_EVIDENCE.md`,
`README.md`, `docs/operations/RUNBOOKS.md`, `apps/mobile/README.md`,
`services/commerce-api/Dockerfile`, `docker-compose.staging.yml`

**Conflicting values:** `rate_limit.client_key` documents that `X-Forwarded-For` "is IGNORED by
default", and Workstream C's evidence recorded that property as verified. Both statements were
true of the function and false of the running system on one supported topology. uvicorn installs
`ProxyHeadersMiddleware` by default (`proxy_headers=True`, `forwarded_allow_ips` defaulting to
`127.0.0.1`) and rewrites `scope["client"]` from the header before any application code executes,
so on the documented development command — `python -m uvicorn app.main:app --port 18000` — the
limiter bucketed on an attacker-chosen value.

Measured on this repository at commit `d6c6973`, before any correction:

| burst | result |
|---|---|
| 16 logins, no `X-Forwarded-For` | `401` ×10 then `429` ×6 |
| 16 logins, a different `X-Forwarded-For` each | `401` ×16 — never limited |

The gap was not detectable by the existing suite: `fastapi.testclient.TestClient` builds the ASGI
scope directly and never installs that middleware, so `tests/test_rate_limit.py` — including
`test_spoofed_forwarded_for_does_not_mint_a_fresh_bucket` and mutation `M22` — passed throughout.

**Affected systems:** login and registration rate limiting on any directly-reached deployment;
the credential-stuffing and PBKDF2 CPU-exhaustion controls those buckets exist to provide.

**Proposed resolution:** Applied, not deferred. Two layers, each independently mutation-tested:
`app/server.py` states `proxy_headers=False` and an empty forwarder allowlist explicitly on every
committed launch path (`M62`); `rate_limit._peer_was_rewritten_upstream` quarantines a peer the
server rewrote anyway, which survives a bare `uvicorn app.main:app` (`M63`).
`tests/test_proxy_boundary.py` launches real server processes because the defect is unreachable
in-process. Documented in `RUNBOOKS.md` R12.

**Reason:** The correction is narrow and the defect was reproduced before and after. Recording it
here rather than only in the evidence file because the affected claim appears in Workstream C's
evidence, which is otherwise treated as settled by later work.

**Risk:** Was High on any loopback-reached deployment; Low after the correction. Docker staging
was **not** affected and this was re-verified, not assumed: its uvicorn binds `0.0.0.0` and traffic
arrives from the Docker bridge, which is not in `forwarded_allow_ips`. No evidence supports a claim
that staging was ever compromised, and none is made.

**Owner:** Technical lead
**Approval status:** RESOLVED — corrected and regression-tested by the successor agent 2026-08-07.
Workstream C's evidence file is left unedited; this entry is the correction of record.

---

## CONFLICT-012 — Runbook R11 states no notification dispatcher exists

**Files:** `docs/operations/RUNBOOKS.md` §R11

**Conflicting values:** R11 states "**There is currently no dispatcher.** Every notification ever
created is still queued … delivery was never implemented." Workstream B delivered
`services/commerce-api/notification_worker.py`, a separate worker container in
`docker-compose.staging.yml`, claim-lease fencing with a persisted expiry, and
`manage.py dispatch-notifications`. Evidence: `evidence/workstream-b/WORKSTREAM_B_EVIDENCE.md` and
`WORKSTREAM_B_LEASE_FENCING_EVIDENCE.md`.

**Affected systems:** incident response. An operator following R11 during a real backlog would
conclude the queue growing is expected and stop investigating.

**Proposed resolution:** Rewrite R11 against the delivered worker. Grouped with CONFLICT-009,
which is the same class of defect (honesty documents lagging delivered workstreams) and should be
corrected in one documentation commit rather than piecemeal.

**Reason:** Found while adding R12 during the branded vertical slice. Not corrected here: R11 is
outside this milestone's scope, and mixing an unrelated documentation rewrite into a security
correction would obscure both.

**Risk:** Medium. No runtime impact; misleads incident response.

**Owner:** Technical lead
**Approval status:** RESOLVED — corrected during the team-acceptance readiness review,
2026-08-07. R11 now documents the delivered worker: how to read its structured lifecycle
log, how to run one bounded cycle by hand, how claimed rows in `sending` expire against the
DATABASE clock rather than a worker-local timer, that `suppressed` counts erased customers and
is correct behaviour, and that a row at maximum attempts is never deleted. Every command in the
rewritten section was executed against the running staging stack before it was written down:
the compose `logs` invocation, `compose exec api python manage.py dispatch-notifications`
(returned `{"sent": 0, ...}`), and both SQL statements (returned `sent | 3` and zero rows in
`sending`). The section also records that a single `cycle_failed` naming *"the database system
is starting up"* immediately after a restart is the expected startup race, because that is
exactly what was observed when Docker restarted mid-review and it would otherwise read as an
incident.

CONFLICT-009 remains OPEN: it covers `docs/KNOWN_LIMITATIONS.md` and `README.md`, which are a
larger rewrite and were deliberately not pulled into a readiness review.

> **Update 2026-08-24 at `41cee4c`:** CONFLICT-009 is now **RESOLVED** — see its entry above.
> Both `docs/KNOWN_LIMITATIONS.md` and `README.md` were rewritten against the executed state,
> with every corrected line marked `**[was: …]**` so the drift stays visible.

---

## CONFLICT-011 — iPhone mobile-web acceptance is asserted but has no record in the repository — **RESOLVED**

**Files:** `evidence/team-acceptance/` — the directory that holds every other acceptance record

**Conflicting values:** A successor brief states that `IPHONE_MOBILE_WEB_ACCEPTANCE` "has
undergone successful human testing", listing eleven specific checks: physical iPhone Safari
access, LAN connectivity, CORS, catalogue, product images, product detail, preview safety,
account registration, session persistence, expired-session handling and stale-token clearing.

Against this, the repository records **nothing**. `evidence/team-acceptance/` holds
`LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md` and `NATIVE_ANDROID_PREVIEW_ACCEPTANCE.md` but no iPhone
equivalent. `git log --all -S "IPHONE_MOBILE_WEB"` returns **no commit in any ref**. The token
appears in zero tracked files predating this phase.

**What corroborates it.** The two UX defects that testing reported are real, specific and were
independently reproducible against the frozen client — an enabled "Add to cart" in
`BRAND_PREVIEW_MODE` and an empty order history reading "You have no orders yet." Both are now
closed (`evidence/team-acceptance/IPHONE_WEB_HARDENING_CLOSURE.md`). Commit `41cee4c`
(*support LAN staging storefront access*) is also consistent with someone having reached the
staging storefront from a phone on the LAN. **The testing almost certainly happened.**

**What does not follow.** A defect report is not an acceptance record. The Android closeout
names its emulator, API level, build id and gate-by-gate results; nothing comparable exists
for iPhone, so the *scope* of what passed cannot be reconstructed — which device, which iOS
version, which commit, which commerce mode, and whether the eleven checks were the whole
script or a subset.

**Affected systems:** readiness review, the acceptance matrix, any future claim about mobile
web support, and the credibility of the acceptance ledger as a whole — which depends on every
entry in it being reconstructible.

**Proposed resolution:** Either (a) the human tester writes the closeout, naming device, iOS
version, commit and mode, or (b) the acceptance is re-run and recorded. Until one of those
happens, every surface describing it must say **`HUMAN_ASSERTED_NOT_EVIDENCED`**, which
`README.md` and `docs/KNOWN_LIMITATIONS.md` §7 now do.

**Reason:** This is the same shape as DISC-07 in the takeover report, where the EAS project
id existed only in a brief and in zero tracked files. The rule applied there applies here: a
human-provided value is recorded **as stated** and is not converted into a verified result by
being written down again. Retro-fitting an acceptance record from a brief would manufacture
evidence, which is worse than the gap it closes.

**Risk:** Medium. No runtime impact. The failure mode is a readiness matrix that carries a
passed acceptance nobody can reconstruct, and a public claim of iPhone support resting on it.

**Owner:** Human acceptance manager
**Approval status:** **RESOLVED 2026-08-24 at `37cd6f6`** by resolution path (a): the human
tester supplied the authoritative scope and the record was written from it.

**Evidence:** [`evidence/team-acceptance/IPHONE_MOBILE_WEB_ACCEPTANCE.md`](../../evidence/team-acceptance/IPHONE_MOBILE_WEB_ACCEPTANCE.md)
— `EV-TA-006`, status `IPHONE_MOBILE_WEB_ACCEPTANCE_PASSED`, 25 gates across connectivity,
catalogue and brand, preview safety, identity, session invalidation and cleanup.

**Ten of the supplied claims were independently corroborated against the repository** rather
than transcribed: €72 confirmed from `variant-master.csv` (`DDN-TS01`, every variant
`price_eur=72`), five products from `product-master.json`, non-purchasability from
`inventory_status=prototype_unavailable` and `stock_quantity=0`, the mode gate from
`assert_purchasable`, the caution language from `origin_claim_status=UNVERIFIED`, and the
stale-token clearing from mutation M74. The record separates those from the observations only
a human could make, which are carried on the tester's authority.

**The residual gap is recorded rather than papered over.** This entry's proposed resolution
asked for device, iOS version, commit and mode. **Mode was supplied; iPhone model, iOS version
and the commit were not.** The commit is *inferred* as `41cee4c` and labelled an inference —
bounded because LAN storefront access is what that commit added, so the acceptance cannot
predate it, and the two defects it reported were fixed in `2f50e11`, so it cannot postdate
that. See `EV-TA-006` §7.

That residual is **not** re-raised as a new conflict. The substantive defect this entry
recorded was an acceptance with *no record at all*; that is closed. What remains is
reproducibility detail on a record the acceptance manager owns and has now written.

**One thing this resolution explicitly does not do.** It does not become native iOS
acceptance. `NATIVE_IOS_ACCEPTANCE` is `NOT TESTED`, Apple signing, TestFlight and App Store
are `NOT TESTED`, and Apple Developer Program membership remains `DEFERRED — FUNDING`. Mobile
web in Safari and the native application share a commerce contract and nothing else. `EV-TA-006`
§6 states this separately because it is the most likely misreading of the record.
