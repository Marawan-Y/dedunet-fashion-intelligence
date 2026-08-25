# Side-by-side acceptance deployment — consumer candidate

**Artifact ID:** EV-P3-002 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `AUTOMATED-TESTED` — deployed for physical-device acceptance, **not accepted**
**Date:** 2026-08-25 · **HEAD:** `608fc56` · **Working tree:** clean

> Deployed **beside** the accepted staging web client, not over it. Existing staging was
> not stopped, not recreated and not reconfigured. `docker compose down -v` was not run.

---

## 1. Topology

| Surface | URL | Serves | State |
|---|---|---|---|
| Accepted staging web | `http://10.0.0.2:13080/storefront/` | `apps/web` (classic) | **untouched**, container up 6h |
| Consumer candidate | `http://10.0.0.2:13081/` | `apps/consumer` (React, built) | new |
| Commerce API | `http://10.0.0.2:18080` | unchanged | untouched, up 30h, healthy |
| Admin portal | `http://10.0.0.2:13080/admin/` | unchanged | untouched |

The candidate container joins the existing `dedunet-staging_default` network as a client of
the API. It publishes one port and starts no database, no worker and no second API.

## 2. API connectivity — same-origin, as instructed

The browser calls `http://10.0.0.2:13081/api/...` and nginx forwards it to the commerce API
at `api:8000` over the Docker network.

**No new CORS origin was added.** The API's `CORS_ORIGINS` is unchanged, and no API
security control was weakened or relaxed.

Chosen over widening CORS because it is the topology a real deployment behind a gateway
would use: the browser sees one origin, so there is no preflight, no per-deployment CORS
entry to maintain, no cross-origin cookie or referrer difference, and the client needs no
absolute API base compiled into it.

**The upstream is a service name, never a host address.** `DEDUNET_API_UPSTREAM` defaults to
`api:8000` in the image and is overridable per deployment. No LAN address appears anywhere
in tracked source or in the image.

**One consequence, stated because it is real.** The API deliberately ignores
`X-Forwarded-For` unless told how many proxies to trust, which is correct and was left
alone. Rate limiting therefore keys on the proxy container's address, so every client behind
this candidate shares one 300-request-per-minute bucket. Irrelevant for one person on one
phone; it would matter if this topology were used for many concurrent users.

## 3. Build provenance

Built by Docker from committed source at `608fc56` — `npm ci` against the lockfile, then
`tsc -b && vite build`, so a type error fails the image rather than the browser.

**The served artefact is verified identical to a local build from the same HEAD:**

```
container : index-BfXCLgie.js   router-BIPeleUq.js
local dist: index-BfXCLgie.js   router-BIPeleUq.js
```

Content-hashed filenames, so identical names mean identical bytes. No stale image and no
stale container: the image is tagged and labelled `dedunet.head=608fc56`.

**The runtime posture is unchanged.** The container runs with a read-only root filesystem,
proven rather than asserted:

```
touch /usr/share/nginx/html/PROOF  ->  Read-only file system
```

Writable paths nginx genuinely needs are tmpfs. The nginx config is rendered from a template
at start by the entrypoint's envsubst, restricted by `NGINX_ENVSUBST_FILTER=DEDUNET_` so
nginx's own variables survive — verified in the rendered file: `try_files $uri` intact,
`proxy_pass http://api:8000` substituted.

## 4. Host verification

### The candidate serves the new client, not `apps/web`

```
/assets/index-BfXCLgie.js     bundled React build
app.js                        ABSENT
window.DEDUNET_API_BASE       undefined  (same-origin, no absolute base)
first image src               /api/v1/media/...   relative, through the proxy
```

### Commerce mode, read through the proxy

```
mode: BRAND_PREVIEW_MODE | purchasable: false | public_commerce_enabled: false
```

### Every route, client-side navigation

| Route | h1 | Route | h1 |
|---|---|---|---|
| `/` | DEDUNET | `/product/the-measure-trouser` | The Measure Trouser |
| `/discover` | Discover | `/saved` | Saved |
| `/dido` | Style with Dido | `/my-style` | My Style |
| `/looks` | Looks | `/account` | Sign in to DEDUNET |
| `/look/quiet-interview` | The Quiet Interview | `/orders` *(signed out)* | → Sign in to DEDUNET |
| `/brands` | Brands | `/for-brands` | Reach customers through styling… |
| `/brand/dedunet` | DEDUNET | `/cart` | Bag |
| `/shop` | Shop | `/nonsense` | This page does not exist |

### Direct load, refresh, back and forward

Deep links resolve as real document loads — the history fallback works:

```
/  /discover  /looks  /brand/dedunet  /product/the-measure-trouser  /account  /nonsense
                          all -> 200
```

Back/forward restore the right route and heading:

```
product -> brands -> looks -> back(brands) -> back(product) -> forward(brands)
```

### The purchase gate, on the deployed candidate

```
control : "Not available to buy"   disabled: true
reason  : "This catalogue is in preview. Nothing here is available to buy."
```

### Browser suite, against the deployed container at the LAN address

| Engine | Result |
|---|---|
| Chromium | **130 passed** |
| WebKit | **130 passed** |
| Mobile Safari (iPhone 13 viewport) | **130 passed** |

Run against `http://10.0.0.2:13081` — the actual artefact, at the actual URL the phone will
use, over the same proxy.

## 5. Known limitations of this deployment

| Item | State |
|---|---|
| **Physical iPhone** | **NOT TESTED.** Automated WebKit is not the device |
| Firefox | **BLOCKED** — cannot launch in this environment |
| `/admin` on port 13081 | Returns 200 but is **NOT CONFIGURED**: the classic admin resolves its own API base and cannot use the proxy, so it falls back to a port this origin does not publish. Out of scope. The accepted admin remains on 13080 |
| Brand display typeface | Not shipped; renders in fallback faces |
| HTTPS | None. Plain HTTP over the LAN, as staging already is |
| Restart policy | `unless-stopped`. It will come back after a Docker restart until explicitly stopped |

## 6. Reversal

The candidate is additive. To remove it entirely:

```
docker rm -f dedunet-consumer-candidate
```

Nothing else is affected. Staging keeps serving `apps/web` on 13080 throughout, and no
API, database, mode or security control was changed at any point.
