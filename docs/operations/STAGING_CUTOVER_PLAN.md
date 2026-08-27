# Staging cutover plan — consumer candidate replaces `apps/web`

| Field | Value |
|---|---|
| Artifact ID | OPS-CUT-001 · **Version** 1.0 |
| Status | **EXECUTED AND ACCEPTED 2026-08-27** — option A, human iPhone smoke PASSED. Results in `evidence/staging-cutover/STAGING_CUTOVER_EXECUTION.md`; acceptance in `evidence/team-acceptance/STAGING_CUTOVER_IPHONE_ACCEPTANCE.md` |
| Owner | Side B / platform |
| Prerequisite met | `ENTERPRISE_CONSUMER_FOUNDATION = ACCEPTED WITH FOLLOW-UP ITEMS` |
| Authorization | **GRANTED** by explicit owner instruction, 2026-08-27, selecting option **A** |

> **This plan has been carried out.** Staging serves the enterprise consumer client on 13080
> over a same-origin `/api` proxy. The candidate remains on 13081 as the acceptance reference
> during the soak. One correction was needed during execution and is recorded in §8 below and
> in the execution evidence: the consumer image renders its nginx config at container start,
> which the service's read-only root filesystem forbade until a tmpfs was added for
> `/etc/nginx/conf.d`.
>
> The plan text below is preserved **as it was written before execution**. It is the record of
> what was intended; the execution evidence is the record of what happened.

---

## 1. What the cutover actually changes

One thing: **which image the `web` service in `docker-compose.staging.yml` builds and
serves.** It does not touch the API, the database, the notification worker, the commerce
mode, any security control, or any data.

| | Before | After |
|---|---|---|
| `:13080/storefront/` | `apps/web`, classic scripts, hash routing | — |
| `:13080/` | 302 to `/storefront/` | consumer client, real path routing |
| `:13080/admin/` | admin portal | admin portal, unchanged |
| API topology | client calls `:18080` cross-origin, CORS entry required | same-origin `/api` proxied by nginx |
| `:13081` | candidate | retired after the soak period |

## 2. Preconditions — every one verifiable before starting

| # | Precondition | How it is checked |
|---|---|---|
| 1 | Working tree clean, HEAD recorded | `git status --short` empty; `git rev-parse --short HEAD` |
| 2 | Backend regression green | `pytest -q` → **576 passed, 2 skipped** [was written as 570; stale on arrival, see execution evidence F-3] |
| 3 | Browser suite green on three engines | 130 each on Chromium, WebKit, Mobile Safari viewport |
| 4 | Suite run against the **deployed candidate**, not a dev server | `DEDUNET_BASE_URL=http://<LAN>:13081` |
| 5 | Governance validators pass | brand drift `NORMALIZATION_VERIFIED`; Side A `DEDUNET_HANDOFF_INTEGRITY_VERIFIED`; data validators exit 0/0/1 |
| 6 | Commerce mode confirmed | `/api/v1/commerce/mode` → `BRAND_PREVIEW_MODE`, `purchasable: false` |
| 7 | Image provenance | served bundle filenames identical to a local build from the same HEAD |
| 8 | A database backup exists | `infrastructure/backup` runbook, even though the cutover does not touch the database — because a rollback under pressure is not the moment to discover there isn't one |

**If any precondition fails, the cutover does not start.** There is no partial cutover.

## 3. Decision to make before starting: the API topology

The candidate proxies `/api` same-origin. Staging's classic client calls `:18080`
cross-origin and the API's `CORS_ORIGINS` is configured for that. Two options:

| | Option | Consequence |
|---|---|---|
| **A** *(recommended)* | Serve the consumer client with the same-origin proxy, as the candidate does | No CORS entry needed for the storefront at all. Production-like. The admin client still needs its own cross-origin config, which it already has |
| **B** | Keep the client cross-origin, baking `API_BASE_URL` as today | No nginx proxy; unchanged from the classic deployment's shape, but keeps a CORS list to maintain and a preflight on every call |

**A is recommended** and is what has been tested on the device. B is recorded so the choice
is visible rather than assumed.

Under A, one thing must be checked and is easy to miss: the API's rate limiter will key on
the **proxy container's address** rather than each client's, because the API correctly
ignores `X-Forwarded-For` unless told how many proxies to trust. On a single-user staging
LAN that is immaterial. It is **not** immaterial for a hosted multi-user deployment, and it
interacts with `PLAT-ACT-001` — see `docs/architecture/MEDIA_DELIVERY_SEPARATION.md`.

## 4. Procedure

Each step is reversible up to step 5.

1. **Record the baseline.** `git rev-parse --short HEAD`, `docker ps`, and the current
   `web` image id. Write them into the cutover evidence file before changing anything.

2. **Point the `web` service at the consumer Dockerfile** in
   `docker-compose.staging.yml` — `dockerfile: apps/consumer/Dockerfile`, build context
   unchanged at the repository root, and pass `DEDUNET_API_UPSTREAM` for the same-origin
   proxy under option A. **Do not delete the classic service definition**; comment it with
   a pointer to this document so the rollback is a one-line revert rather than an
   archaeology exercise.

3. **Build without switching traffic.** `docker compose -f docker-compose.staging.yml build web`.
   A failed build at this point has changed nothing that is serving.

4. **Verify the built image on the spare port first**, exactly as the candidate was
   verified: run it on 13081, run the browser suite against it, confirm the served bundle
   matches a local build from the same HEAD.

5. **Switch.** `docker compose -f docker-compose.staging.yml up -d web`.
   **`docker compose down -v` must never be used** — it destroys the database volume, and
   nothing about a frontend cutover requires touching data.

6. **Verify the switched service** — see §5.

7. **Soak.** Leave `:13081` running until the owner confirms. Retire it only afterwards, so
   there is a known-good reference during the soak rather than only a rollback.

## 5. Post-cutover verification

| Check | Expected |
|---|---|
| `:13080/` | 200, consumer client, bundled `/assets/index-*.js`, **no `app.js`** |
| `:13080/discover` direct load | 200 — history fallback present |
| `:13080/discover` after refresh | 200 — this is the check that only fails on reload |
| `:13080/api/v1/commerce/mode` | 200, `BRAND_PREVIEW_MODE`, `purchasable: false` |
| `:13080/admin/` | 200, portal reachable and configured |
| Browser suite vs `:13080` | 130 × 3 engines |
| Product page | "Not available to buy", disabled, reason bound via `aria-describedby` |
| API, DB, worker uptime | **unchanged** — none should have restarted |
| Physical iPhone | one pass over Home, Dido, Looks, Shop, Account |

## 6. Rollback

**Trigger:** any post-cutover check failing, or the owner saying so. No further diagnosis is
required before rolling back — diagnosis happens afterwards, on the candidate port.

**Procedure:** revert the one `dockerfile:` line in `docker-compose.staging.yml`, then
`docker compose -f docker-compose.staging.yml up -d web`.

**Time:** one rebuild of a static image, in the low minutes.

**Data risk: none.** No migration, no schema change, no volume touched. The rollback target
is a commit that is already tagged and whose image has been running for weeks.

## 7. What this cutover explicitly does not do

- It does **not** enable public commerce. `PUBLIC_COMMERCIAL_LAUNCH` stays **BLOCKED**.
- It does **not** change the commerce mode, payments, inventory or fulfilment.
- It does **not** migrate `apps/admin`.
- It does **not** retire `apps/web` from the repository. The classic client, its six jsdom
  harnesses and its eight guard mutations remain in the tree and keep passing. Retiring
  them is a separate decision with its own evidence, and doing it in the same change as a
  cutover would mean a rollback had nothing to roll back to.
- It does **not** resolve any accepted follow-up item — Saved persistence, Looks as a real
  outfit object, the multi-brand domain and Dido intelligence are all still outstanding, and
  the disclosure rule in `PRODUCTION_DISCLOSURE_RULE.md` still applies to every surface that
  names them.


---

## 8. Execution — what actually happened

Carried out 2026-08-27 from `e29e019`. Full record:
`evidence/staging-cutover/STAGING_CUTOVER_EXECUTION.md`.

| | Outcome |
|---|---|
| Tracked change | `docker-compose.staging.yml`, `web` service only |
| Deviation from §4 step 4 | pre-switch verification ran on **13082**, not 13081, so the accepted candidate on 13081 was left running as the reference |
| Unplanned correction | tmpfs on `/etc/nginx/conf.d` — the consumer image renders its nginx config at start and the read-only root filesystem refused the write, restart-looping the first attempt |
| Browser suite vs 13080 | 390 passed — 130 each on Chromium, WebKit, Mobile Safari viewport |
| Backend | 576 passed, 2 skipped |
| API / DB / worker | untouched, verified by unchanged container ids and start times |
| Served artifact | byte-identical to the accepted candidate, by SHA-256 on all six served files |
| New findings | F-1 security headers absent on every HTML document; F-2 every product rendering "Not priced". Both left open at the cutover, which was **wrongly** reported as ready for the human smoke. Owner rejected it; both **repaired and verified** — evidence §11. Post-repair: 429 browser, 594 backend |
| Rollback | rebuilt the classic image from committed source and served it, then removed the proof container |

**The physical-iPhone smoke PASSED on 2026-08-27** at `be1d1e2`, after the F-1 and F-2
repairs. `STAGING_CUTOVER = ACCEPTED`, `ENTERPRISE_CONSUMER_FOUNDATION = LOCKED`.

`PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**, and a web application accepted in Safari on
an iPhone is **not** native iOS acceptance.

**A note worth keeping.** This plan's §5 listed the post-cutover checks, and the security
headers were not among them — the plan checked that the app rendered, that routing survived
a refresh and that nothing was purchasable, but not that the response headers the previous
client served were still being served. A cutover that swaps the thing serving every response
should check the responses, not only the pages. F-1 reached staging through that gap.
