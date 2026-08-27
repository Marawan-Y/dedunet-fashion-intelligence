# Staging cutover — physical iPhone Safari human acceptance

| Field | Value |
|---|---|
| Artifact ID | EV-ACC-005 · **Version** 1.0 |
| Status | **`HUMAN-VERIFIED`** |
| Result | **`PHYSICAL_IPHONE_STAGING_SMOKE_PASSED`** · **`STAGING_CUTOVER_ACCEPTED`** |
| Date | 2026-08-27 |
| Reviewer | Repository owner, in person |
| Device | **Physical iPhone, Safari**, over the LAN |
| Target | `http://10.0.0.2:13080/` — **normal staging**, not a candidate port |
| Application baseline | `be1d1e2` |
| Owner | Side B / platform |

> This records a **human** acceptance. It was performed by a person on real hardware. No
> automated result in this repository substitutes for it, and none is cited as if it did.

---

## 1. What was tested, and what passed

Against the **normal** staging deployment on port 13080 — the deployment the cutover
produced, not the additive candidate on 13081 that carried the earlier foundation
acceptance.

| # | Surface | Verdict |
|---|---|---|
| 1 | Home | **PASS** |
| 2 | Dido | **PASS** |
| 3 | Shop | **PASS** |
| 4 | Source Tee — displays **€72.00** and **NOT AVAILABLE TO BUY** | **PASS** |
| 5 | Account | **PASS** |
| 6 | Mobile navigation | **PASS** |
| 7 | Preview safety | **PASS** |

Item 4 is the one that matters most for this cycle. It is the surface that changed in the
F-2 repair, and it is the reason this smoke could not lean on byte-equivalence with the
previously accepted candidate: the repair deliberately changed the application, so the
product page had to be looked at rather than inferred.

## 2. What this acceptance means

**The staging cutover is accepted.** The enterprise consumer application is the normal
staging web application, served over a same-origin `/api` proxy, and a person has confirmed
on real hardware that it works.

**The enterprise consumer foundation is LOCKED.** The foundation accepted on 2026-08-26
against the candidate, plus the two post-cutover repairs, is now settled. It is the baseline
that later phases build on and is not reopened by them.

```
PHYSICAL_IPHONE_STAGING_SMOKE_PASSED
STAGING_CUTOVER_ACCEPTED
ENTERPRISE_CONSUMER_FOUNDATION_LOCKED
```

## 3. What this acceptance does NOT mean

Stated explicitly, because the failure mode this programme keeps closing is a narrow
acceptance being read as a wide one.

**This is not `NATIVE_IOS_ACCEPTANCE`.** What was tested is a **web application in Safari on
an iPhone**. No native iOS application was built, submitted, installed or run. Native iOS
remains a **separate, untested state**. Testing a website on an iPhone is not testing an
iPhone app, and this record may never be cited as if it were.

**This is not `PUBLIC_COMMERCIAL_LAUNCH_READY`.** `PUBLIC_COMMERCIAL_LAUNCH` remains
**BLOCKED**, unchanged and fully in force. Nothing here activates public commerce, changes
the commerce mode, enables payments or makes anything purchasable. The deployment tested was
in `BRAND_PREVIEW_MODE` with `purchasable: false` throughout, which is part of what item 7
confirmed.

**No product capability is accepted by this.** Not Dido intelligence, Style DNA, the
recommendation engine, the outfit engine, Saved persistence, real multi-brand integrations,
merchant SaaS, or native iOS. Item 2 above accepts the Dido **shell** as it stood at the
foundation acceptance — it does not accept a styling intelligence, because none is built.

## 4. Provenance

| | |
|---|---|
| Application baseline at the smoke | `be1d1e2` |
| Served bundle | `/assets/index-CogdTLIy.js` |
| Commerce mode during the smoke | `BRAND_PREVIEW_MODE`, `purchasable: false` |
| Document security headers | all four present on every document |
| Server-side purchase refusal | `409` on cart add |
| API / database / worker | untouched — start times unchanged since 2026-08-24 |

The engineering verification behind this baseline is in
`evidence/staging-cutover/STAGING_CUTOVER_EXECUTION.md`: 429 browser tests across three
engines against the deployed URL, 594 backend tests, 13 consumer unit tests, and every
governance, brand-drift and data validator passing.

## 5. History this record does not erase

The cutover did not go cleanly, and the record says so rather than presenting a single
success:

1. The first switch **restart-looped** — the consumer image renders its nginx config at
   container start and the service's read-only root filesystem refused the write. Corrected
   with a tmpfs, and the reason the candidate never caught it is recorded: it had been run
   without `read_only`.
2. Post-cutover verification found **two defects** — absent document security headers (F-1)
   and every product rendering "Not priced" (F-2).
3. The cutover was then **wrongly reported as ready for this human smoke** while both were
   open. The owner rejected that conclusion. Recording a defect does not satisfy the gate
   the defect fails.
4. Both were repaired, guarded by tests, and verified on real HTTP responses from the
   deployed application.
5. **This** smoke is the one that followed the repair.

## 6. Carried forward — unchanged by this acceptance

| Item | State |
|---|---|
| **Native iOS** | **NOT BUILT, NOT TESTED** — a separate state, not implied by this record |
| **Public commerce** | **BLOCKED** |
| **Saved persistence** | required before production exposure; no store, no endpoint, no model |
| **Looks as a real outfit object** | reasoning, pricing and modification actions — later phase |
| **Multi-brand domain** | not implemented; the second brand entry is a labelled demonstration |
| **Dido intelligence** | not built |
| About / Privacy / Terms routes | **do not exist**; required for public launch |
| Firefox | **BLOCKED** — cannot launch in this environment |
| LCP / INP / CLS on device | **NOT MEASURED** |
| Physical Android hardware | **NOT TESTED** |
| Media delivery separation | open platform action |
| Trusted proxy / client identity | open; not acceptable as final hosted production |
| Distributed rate limiting | open; single replica only |
