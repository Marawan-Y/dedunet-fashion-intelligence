# Saved physical acceptance — deployment provenance incident

| | |
|---|---|
| Artifact ID | `EV-P5-DEPLOY-001` |
| Version | 1.0 |
| Owner | Side B / platform |
| Date | 2026-10-07 |
| Status | `SELF-VALIDATED` — automated verification only; the human gate is unchanged |
| Inputs | PR #1 head `2fcf968`, CI runs #8/#9, running staging containers, staging PostgreSQL |
| Consumer | Physical-iPhone Saved acceptance |

## 1. What failed, and what did not

A physical iPhone Safari acceptance failed before functional testing: the Source Tee product
page rendered *"Saving is not built. There is nowhere to store it yet."*

**No application code was at fault, and none was changed.** The code, the database and the API
were all correct and current. What was wrong was *which container the acceptance port reached*.

> The report was right to treat this as a hard failure. A page that denies a feature the
> repository claims to have shipped is indistinguishable, from the device, from the feature not
> having shipped — and the correct first move was to doubt the deployment rather than the eyes.

## 2. Repository and PR state

| | |
|---|---|
| Branch | `feat/saved-persistence` |
| Local `HEAD` | `2fcf968c4ba96923b9c1f1ba699e5fed93970d19` |
| `origin/feat/saved-persistence` | identical |
| PR #1 head | identical — `2fcf968…`, OPEN, not draft, `MERGEABLE` |
| `git status --short` | clean, before and after |
| Latest CI | run **#9** `pull_request` and run **#8** `push`, both **success** on `2fcf968` |

Local checkout, origin and PR head agree. The investigation changed no tracked file.

## 3. The stale string, located exactly

| Location | Present? |
|---|---|
| Current source — rendered JSX | **No.** `ProductPage.tsx:332` holds the sentence only inside a comment recording its removal |
| Current source — docs/comments/tests | Yes, as history: `KNOWN_LIMITATIONS.md`, `PHASE_REPORTS.md`, `PRODUCTION_DISCLOSURE_RULE.md`, the E2E honesty test |
| Current build artifact (`dedunet-staging-web`) | **No.** Absent from every `.js` chunk |
| Artifact deployed on `:13080` at failure time | **YES** — `/assets/ProductPage-Ds90jgWP.js`, verbatim |
| Browser cache | **No.** Not involved — see §6 |

## 4. Image provenance — what `:13080` was actually serving

The two candidates answer with different, stable `ETag`s, which makes the comparison a
measurement rather than a visual judgement:

| Target | Container | ETag | `Last-Modified` | Entry chunk |
|---|---|---|---|---|
| `172.19.0.2` | `dedunet-staging-web-1` | `6abd9488-7af` | 2026-09-30 | `index-BW2pDhkZ.js` |
| `172.19.0.4` | `dedunet-consumer-candidate:e29e019` | `6a8ea862-7af` | **2026-08-26** | `index-B-2mQdH-.js` |
| **host `:13080`** | — | **`6a8ea862-7af`** | **2026-08-26** | **`index-B-2mQdH-.js`** |

`:13080` was byte-identical to the **candidate**, not to staging web. Verdict: **B — an older
enterprise consumer build**, from the cutover rehearsal, roughly six weeks stale.

Three independent confirmations, because one coincidence of hashes is not a proof:

1. **The access log.** A uniquely-named probe path sent to `:13080` never appeared in
   `dedunet-staging-web-1`'s log. That container had logged **no request at all** since it
   started on 2026-10-04 — the real staging web server was serving nobody.
2. **Stopping the candidate.** `docker stop dedunet-consumer-candidate` made `:13080` stop
   answering entirely. A port cannot go silent because an unrelated container stopped.
3. **The orphaned tag.** The candidate image is tagged `e29e019` — a commit that **no longer
   exists in this repository**, because the publication history rewrite replaced it. The image
   outlived the commit it was named after.

### How it happened

Both listeners belong to Docker Desktop (`com.docker.backend.exe` on `0.0.0.0`,
`wslrelay.exe` on `[::1]`). After the host restart on **2026-10-04 19:32** the port
assignments came back crossed: `13080` resolved to the candidate, and `13081` — the
candidate's own published port — answered nothing at all. Nothing in the repository caused
this and nothing in it could have prevented it. The rehearsal container simply outlived its
purpose and stayed running for six weeks, which is what made a crossed mapping possible.

### A trap worth naming

`curl http://localhost:13080` was not a safe probe here. `localhost` resolved to `::1` and
reached a different relay than the LAN address the iPhone uses. **Provenance was only settled
by querying each container's own IP inside the Docker network** and comparing ETags. A probe
against a name can answer about the wrong server while looking perfectly healthy.

## 5. Backend and migration provenance — already correct

Checked before assuming the fault was only in the frontend, and read-only throughout.

| Check | Result |
|---|---|
| Staging Alembic revision | **`c7a41d9e8b52`** — the Saved persistence migration |
| Code head revision | `c7a41d9e8b52` — **matches**, so no migration was applied |
| `looks`, `look_items`, `saved_looks`, `favorite_products`, `favorite_brands` | all **present** |
| `brands`, `brand_ownership`, `merchant_organizations` | all present |
| Base tables | **27** (26 + `alembic_version`) |
| Saved endpoints on the running API | **10 of 10** present |

The API image did need rebuilding — ten backend files changed after it was built, including
`catalog_scope.py` from `41f3d81` — but the endpoints it already exposed were correct.

## 6. Browser cache — NOT involved, and no device cleanup needed

Tested only after server provenance was settled, as the order of operations requires.

- `index.html` is served `Cache-Control: no-store, must-revalidate`, so the device **must**
  refetch the document; it cannot replay a cached one.
- Asset chunks are content-hashed and `immutable`, so a new build produces new filenames.
- The stale entry chunk `/assets/index-B-2mQdH-.js` now returns **404** on `:13080`.

**Verdict: browser cache involved = NO.** A normal page open or refresh is sufficient. The
human should not be asked to clear Safari website data — that would destroy their sign-in
state to fix a problem it was never causing.

## 7. Remediation

Only what the Saved phase requires:

| Action | Detail |
|---|---|
| Stopped `dedunet-consumer-candidate` | **Stop, not remove.** Container and image kept, so the cutover rollback material still exists |
| Rebuilt `web` | From `2fcf968`. Layers **cached** — the image content already equalled the current source |
| Rebuilt `api` | New image `6501cfeef5d6`, 2026-10-07 — ten backend files had changed since the old one |
| Recreated `web` + `api` | `up -d --no-deps --force-recreate web api` |
| **Not touched** | `db`, `notification-worker`, volumes, migrations, commerce gates, PR #1 |

No `down -v`, no database reset, no volume deletion, no merge.

## 8. Post-deployment verification

**Provenance now correct:** `:13080` returns ETag `6abd9488-7af` — the staging web container —
and a probe path appears in that container's access log. `http://10.0.0.2:13080`, the address
the iPhone uses, returns the same ETag.

### Safety — unchanged

| Check | Result |
|---|---|
| Commerce mode | `BRAND_PREVIEW_MODE`, `purchasable: false`, `public_commerce_enabled: false` |
| Source Tee price | **7200 minor units = €72.00**, all 18 variants, `EUR` |
| Sellable / route | `sellable=false`, **`NON_PURCHASABLE`** |
| Product page | shows **NOT AVAILABLE TO BUY** |
| Cart add | refused **409** — *"this catalogue is in brand preview; nothing is available to purchase"* |
| Document security headers | all four on `/`, `/assets/`, `/index.html` and a deep SPA route |
| `/api/` headers | keeps its stricter `Referrer-Policy: no-referrer` — the named exemption holds |
| Same-origin `/api` | intact; `/api/v1/commerce/mode` answers on the web origin |
| Multi-brand | `/api/v1/brands` returns DEDUNET (5 products) and the fixture brand (0, correctly hidden) |

### Product page — the failing surface

Read from the live DOM, not from source:

```
save button : aria-label="Save The Source Tee"  aria-pressed="false"
              data-saved="false"  disabled=false  44px
stale text  : "Saving is not built"      -> absent
              "nowhere to store it yet"  -> absent
price       : €72.00 shown      availability: NOT AVAILABLE TO BUY shown
```

The Saved page likewise now reads *"kept to your account … the same on every device you sign
in from"*, with a sign-in prompt — not *"Saving is not built yet"*.

### Automated Saved smoke on deployed `:13080`

Test customer created **out of band** via `manage.py create-test-customer`; password generated
at 24 characters, never printed, never committed. **25 checks, all PASS**:

- sign in; unauthenticated `saved/state` correctly **401**
- Source Tee: save → appears in `GET /me/saved/products` → re-save creates no duplicate →
  unsave → gone → unsave again still succeeds
- DEDUNET brand and the `quiet-interview` look: identical sequence, identical result
- final state for the test customer: `{"products": [], "brands": [], "looks": []}`

Pre-existing saved rows were **1/1/1 before and 1/1/1 after** — other test accounts' data was
read but never modified, and the smoke customer ends with zero rows.

> This is an API-level smoke on the deployed origin. **It does not substitute for the physical
> iPhone acceptance** and is not offered as doing so. It proves the server is reachable and
> correct; it proves nothing about the device, which is exactly what failed last time.

## 9. The lesson worth keeping

The build was right, the database was right, the API was right, CI was green on the exact
commit — and the acceptance still failed, because **nothing verified which artifact the
acceptance URL actually reached.** Every green signal in this repository described the code.
None of them described the deployment.

A long-lived rehearsal container is the specific hazard: `dedunet-consumer-candidate` had done
its job six weeks earlier and was never stopped, so when the port map came back crossed there
was something stale for it to land on. Tracked as **R-019**.

## 10. Residual risks and next action

- The crossed mapping was a host-level event with no repository cause; it can recur on the next
  restart. The check that catches it is cheap and is now written down: compare the `ETag` from
  the acceptance URL against the container's own, before starting an acceptance.
- No automated check asserts deployment provenance — the verification in §8 was performed by
  hand this once.
- **Physical-iPhone Saved acceptance remains outstanding and unclaimed.**
