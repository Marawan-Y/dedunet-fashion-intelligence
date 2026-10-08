# Style DNA — physical iPhone Safari human acceptance

| Field | Value |
|---|---|
| Artifact ID | EV-ACC-008 · **Version** 1.0 |
| Status | **`HUMAN-VERIFIED`** |
| Result | **`STYLE_DNA_ACCEPTED`** |
| Date | 2026-10-08 |
| Reviewer | Repository owner, in person |
| Device | **Physical iPhone, Safari**, over the LAN |
| Target | `http://10.0.0.2:13080/` — normal staging |
| Application baseline | `93d044e` (PR #2 head at acceptance) |
| Owner | Side B / platform |

> A **human** acceptance, performed by a person on real hardware. No automated result in
> this repository substitutes for it, and none was offered as doing so.

## 1. What is accepted

**Style DNA as an explicit, customer-authored style profile**, and nothing beyond that.
Every value the human set, they set themselves. Nothing on the page was derived, inferred,
scored or guessed, and the acceptance confirms the page behaves that way on a real device.

## 2. The thirteen gates observed by the human

| # | Gate | Result |
|---|---|---|
| 1 | Sign in | **PASS** |
| 2 | My Style is the real editor, not the old shell | **PASS** |
| 3 | Set preferences in all five sections | **PASS** |
| 4 | Save | **PASS** |
| 5 | Persistence across a refresh | **PASS** |
| 6 | **Persistence across a Safari restart** | **PASS** |
| 7 | Edit and re-save | **PASS** |
| 8 | **Disabling personalisation preserves every value** | **PASS** |
| 9 | Re-enable personalisation | **PASS** |
| 10 | Dido's capability copy is truthful | **PASS** |
| 11 | Delete Style DNA | **PASS** |
| 12 | **A saved item survives Style DNA deletion** | **PASS** |
| 13 | Final profile is empty | **PASS** |

Gates 8 and 12 are the two that distinguish this feature from a plausible imitation of it.

**Gate 8** proves *disable* and *delete* are genuinely different actions. A control that
quietly did both would destroy data the customer meant to keep, and the only way to know it
does not is to switch it off and look.

**Gate 12** proves the delete is as narrow as it claims. "Forget what I told you about how I
dress" must not take the Saved list with it, and a customer would discover a breach of that
by noticing something gone rather than by being told.

**Gate 6** is what separates server persistence from browser state wearing its clothes — the
same gate the Saved phase turned on, applied to more intimate data.

## 3. Deployment provenance was verified BEFORE the human was asked to test

`docs/operations/DEPLOYMENT_PROVENANCE_GATE.md` was executed first, and **it caught a stale
deployment on its first real use.**

The staging web build failed on three TypeScript errors, `docker compose build` reported
success through a pipe that swallowed the exit code, `up -d` recreated from the six-week-old
image, and the deployed artifact contained **no Style DNA at all**. Healthy containers, a
correct API and green CI all agreed nothing was wrong. Only the artifact-identity checks
disagreed.

Without the gate this would have been the **second** phase running in a row in which a human
was asked to test a page that was not there. After the fix:

| Link in the chain | Evidence |
|---|---|
| Host URL → container | probe path sent to `http://10.0.0.2:13080` **appeared in `dedunet-staging-web-1`'s access log** |
| Container → image | `dedunet-staging-web`, rebuilt 2026-10-07 after the commit |
| Artifact identity | host `ETag` matched the container's own `index.html`, entry chunk identical |
| Artifact contains this phase | `MyStylePage-*.js` present; `style-dna` referenced |
| Exclusivity | exactly **one** container publishes 13080 |

## 4. Safety at acceptance time — unchanged

| Check | Result |
|---|---|
| Commerce mode | `BRAND_PREVIEW_MODE`, `purchasable: false`, `public_commerce_enabled: false` |
| Source Tee | **€72.00** (7200 minor units), `NON_PURCHASABLE`, NOT AVAILABLE TO BUY |
| Cart add | refused **409** |
| Document security headers | 4 of 4 on `/` and on `/my-style` |
| `/api/` | keeps its stricter `Referrer-Policy: no-referrer` |
| Multi-brand | DEDUNET 5 products, fixture 0 — unchanged |

Recording a style preference changes no commerce state.

## 5. What this acceptance does NOT cover

Stated explicitly, because a feature acceptance is easy to read as a capability one:

- **`DIDO_INTELLIGENCE_ACCEPTED`** — not started. Dido reads nothing from the profile.
- **`RECOMMENDATION_ENGINE_ACCEPTED`** — not started; no scoring exists.
- **`OUTFIT_ENGINE_ACCEPTED`** — not started.
- **`SAVED_INFERENCE_ACCEPTED`** — **deliberately not built.** Saved activity does not create
  or alter a Style DNA profile, and gate 10 confirms the product says so rather than leaving
  it to be assumed.
- **`FASHION_RAG_ACCEPTED`** — not started.
- **`NATIVE_IOS_ACCEPTED`** — iOS native has **never been built**. This acceptance was
  performed in **Safari**, which is not the native application. The automated **Mobile Safari
  viewport** project is a desktop browser emulating a viewport and is weaker evidence still;
  **neither is native-iOS acceptance** and neither may be reported as one.
- **`PUBLIC_COMMERCIAL_LAUNCH_READY`** — **`PUBLIC_COMMERCIAL_LAUNCH` remains `BLOCKED`**;
  `LEGAL_CLEARANCE_PENDING` is unchanged.

Also unchanged from the phase's own limitations: **nothing uses the profile**, there is no
cross-brand or cross-system size conversion, fit is per garment category rather than per
garment type, and Firefox remains `NOT RUN`.

## 6. Locked behaviour

`STYLE_DNA = ACCEPTED`, `STYLE_DNA = LOCKED`. A future phase may extend Style DNA
deliberately; the following are now accepted behaviour and **must not be silently weakened**:

1. **Customer-owned.** No `organization_id`, no merchant ownership, no tenancy, and no
   endpoint accepting a customer id.
2. **`USER_EXPLICIT` provenance**, pinned by a database CHECK on all six preference tables.
3. **No hidden inference.** Every value is visible to the customer who set it.
4. **One authoritative profile per customer**, by unique constraint.
5. **Normalized controlled vocabularies.** No opaque blob, no EAV, no free-text taxonomy.
6. **Brand preferences reference the Brand domain** by foreign key, never a name string.
7. **Integer minor-unit budgets** with an explicit currency. Float rejected, never coerced.
8. **No size conversion** — between systems or between brands.
9. **No body-shape inference.** No measurements are required or stored.
10. **Disable ≠ delete.** Disabling preserves everything.
11. **The customer may delete Style DNA independently** of their account.
12. **Account erasure removes Style DNA**, explicitly — because erasure pseudonymizes and the
    FK cascade never fires.
13. **Saved does not automatically modify Style DNA.**
14. **Dido does not apply Style DNA**, and says "Stored, not yet applied".
15. **No fabricated confidence or percentage scores.** Completion is a count of filled
    sections.

## 7. Remaining risks and next action

- **`R-019` remains OPEN.** The provenance gate passed manually, and passing manually is not
  the same as being automated — the gate is still a procedure a person has to remember to
  run. It stays open on the automation, not on this result.
- The next authorized phase is **Dido conversational intelligence**. It is **not started**.
