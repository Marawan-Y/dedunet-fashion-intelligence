# Saved persistence — physical iPhone Safari human acceptance

| Field | Value |
|---|---|
| Artifact ID | EV-ACC-007 · **Version** 1.0 |
| Status | **`HUMAN-VERIFIED`** |
| Result | **`SAVED_PERSISTENCE_ACCEPTED`** |
| Date | 2026-10-07 |
| Reviewer | Repository owner, in person |
| Device | **Physical iPhone, Safari**, over the LAN |
| Target | `http://10.0.0.2:13080/` — normal staging |
| Application baseline | `2fcf968` (PR #1 head at acceptance) |
| Owner | Side B / platform |

> A **human** acceptance, performed by a person on real hardware. No automated result in this
> repository substitutes for it, and none was offered as doing so.

## 1. What is accepted

The real, server-backed Saved feature delivered in Phase 5: Saved Looks, Favorite Products and
Favorite Brands, persisted to the customer's account in PostgreSQL and read back on any device
that signs in.

## 2. Gates observed by the human

| # | Gate | Result |
|---|---|---|
| 1 | Current Source Tee Saved UI (the real control, not the old disclosure) | **PASS** |
| 2 | Sign in | **PASS** |
| 3 | Save the Source Tee | **PASS** |
| 4 | Save the DEDUNET brand | **PASS** |
| 5 | Save a curated Look | **PASS** |
| 6 | Saved counts read **1 / 1 / 1** | **PASS** |
| 7 | **Persistence across a Safari restart** | **PASS** |
| 8 | Unsave all | **PASS** |
| 9 | Cross-page / cross-surface consistency | **PASS** |
| 10 | Final counts read **0 / 0 / 0** | **PASS** |
| 11 | Signed-out Save behaviour | **PASS** |

Gate 7 is the one that distinguishes this feature from what preceded it. A list that survives
a full Safari restart on the device, under an account, is server persistence; a list that does
not is browser state wearing its clothes. This phase deliberately refused to write Saved state
to `localStorage` precisely so that this gate could mean something, and the device is where
that refusal is cashed in.

Gate 9 is what a single shared fetch buys: the same item reads as saved on Shop, Product
detail, Brands, Brand detail, Looks, Look detail and Saved, with no surface disagreeing.

## 3. The first acceptance attempt FAILED, and that is part of this record

**This is the second attempt. The first one failed, and it is not rewritten here.**

On 2026-10-07 a physical iPhone acceptance was attempted and **failed before functional
testing**: the Source Tee page rendered *"Saving is not built. There is nowhere to store it
yet."* — stale pre-Saved-Persistence copy.

The failure was genuine and was correctly reported as a hard failure. It was **not** a defect
in the Saved feature:

- Port `13080` was serving `dedunet-consumer-candidate:e29e019`, a cutover rehearsal container
  roughly six weeks old, instead of `dedunet-staging-web-1`.
- A host restart on 2026-10-04 had crossed the Docker port map.
- The staging web container had logged **no request at all** since it started.
- The code, the database (`c7a41d9e8b52`), the API (10/10 Saved endpoints) and CI were all
  correct and current the whole time.

Full account: `evidence/phase-5/SAVED_ACCEPTANCE_DEPLOYMENT_INCIDENT.md`. Risk `R-019`.

> Recording this matters more than recording the pass. An acceptance log that showed only the
> successful attempt would imply the deployment had always been correct, and would quietly
> delete the one finding worth keeping: that **code provenance and deployment provenance are
> separate facts**, and this programme had been verifying only the first.

## 4. Deployment provenance was verified BEFORE the human was asked to test

The precondition that the failed attempt lacked. Established by observable artifact evidence,
not by `docker ps` looking right and not by CI being green:

| Link in the chain | Evidence |
|---|---|
| Host URL → container | Uniquely-named probe path sent to `http://10.0.0.2:13080` **appeared in `dedunet-staging-web-1`'s access log** |
| Container → image | `dedunet-staging-web` `sha256:33d0975fa7d3` |
| Artifact identity | `ETag "6abd9488-7af"`, entry chunk `index-BW2pDhkZ.js` — host response **matches the container's own file** |
| Image → source | Rebuilt from `2fcf968`; layers cached, so image content equals current source |
| Exclusivity | Exactly **one** container publishes `13080` |

Counter-evidence that the stale artifact is gone: `/assets/index-B-2mQdH-.js` — the stale entry
chunk — returns **404**.

## 5. Safety at acceptance time — unchanged

| Check | Result |
|---|---|
| Commerce mode | `BRAND_PREVIEW_MODE`, `purchasable: false`, `public_commerce_enabled: false` |
| Source Tee | **€72.00** (7200 minor units × 18 variants), `NON_PURCHASABLE`, **NOT AVAILABLE TO BUY** |
| Cart add | refused **409** |
| Document security headers | all four, every location |
| `/api/` | keeps its stricter `Referrer-Policy: no-referrer` |
| Same-origin `/api` | intact |
| Multi-brand | intact |

A save changes no commerce state. Saving a `NON_PURCHASABLE` item remains a record of
intention, not a step toward a purchase that cannot happen.

## 6. What this acceptance does NOT cover

Stated explicitly, because a feature acceptance is easy to read as a product one:

- **`STYLE_DNA_ACCEPTED`** — not started, no schema, no UI.
- **`DIDO_INTELLIGENCE_ACCEPTED`** — not started.
- **`RECOMMENDATION_ENGINE_ACCEPTED`** — not started; no scoring exists.
- **`OUTFIT_ENGINE_ACCEPTED`** — not started; Looks remain human-composed, with no total price
  and no column for one.
- **`NATIVE_IOS_ACCEPTED`** — iOS native has never been built. Safari is not the native app.
- **`PUBLIC_COMMERCIAL_LAUNCH_READY`** — **`PUBLIC_COMMERCIAL_LAUNCH` remains `BLOCKED`**;
  `LEGAL_CLEARANCE_PENDING` is unchanged.

Also still true from the phase's own limitations: resume-after-login is **not** implemented, a
signed-out save sends the visitor to sign in without replaying the save; Look copy remains
duplicated between `content.ts` and the database with the database authoritative; the
saved-state fetch is whole-set.

## 7. Locked behaviour

`SAVED_PERSISTENCE = ACCEPTED`. A future phase may extend Saved deliberately, but the
following are now accepted behaviour and must not be rewritten casually:

1. **Customer ownership** — saved rows belong to a customer, and no endpoint accepts a customer
   id in a path, query or body.
2. **Server persistence** — the account is the store. **No `localStorage` fake persistence.**
3. **Uniqueness at the database** — `UNIQUE(customer_id, target_id)`, not an application check.
4. **Idempotent save and unsave** — unsaving something not saved succeeds.
5. **Privacy deletion by two mechanisms** — FK cascade on hard delete, and explicit deletion in
   `erase_customer`, which pseudonymizes and so would never fire the cascade.
6. **Visibility rules** — you may only save what you can see; a hidden target answers **404,
   not 403**; something already saved that later becomes unpublished stays in your list,
   flagged and unlinked.
7. **Cross-surface consistency** — one shared state fetch, settled-version refetch.

## 8. Remaining risks and next action

- Deployment provenance has no automated gate; the §4 chain was executed by hand. `R-019`.
- Saved has no reordering, no collections and no admin view — the last deliberately.
- Next executable work is **closure only**: merge PR #1, sync `main`, verify post-merge CI.
  **Style DNA is not authorized by this acceptance.**
