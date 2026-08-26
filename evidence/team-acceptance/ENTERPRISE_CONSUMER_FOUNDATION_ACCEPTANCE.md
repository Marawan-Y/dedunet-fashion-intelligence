# Enterprise consumer foundation — physical iPhone Safari human acceptance

| Field | Value |
|---|---|
| Artifact ID | EV-ACC-004 · **Version** 1.0 |
| Status | **`HUMAN-VERIFIED`** |
| Result | **`ENTERPRISE_CONSUMER_FOUNDATION = ACCEPTED WITH FOLLOW-UP ITEMS`** |
| Date | 2026-08-26 |
| Reviewer | Repository owner, in person |
| Device | **Physical iPhone, Safari**, over the LAN |
| Candidate | `http://10.0.0.2:13081/` — consumer candidate, additive beside staging |
| Owner | Side B / platform |

> This records a **human** acceptance. It was performed by a person on real hardware, and
> nothing in it is inferred from an automated result.

---

## 1. What this acceptance covers

**Foundation only.** Named explicitly so it cannot be read wider than it is:

- deployed candidate rendering on the device
- routing — direct URL, refresh, back and forward
- Home
- Dido **shell**
- Looks **foundation**
- Brands **foundation**
- Shop
- Saved **foundation**
- Account
- mobile navigation
- responsive presentation
- preview safety behaviour

## 2. What this acceptance does NOT cover

Equally explicit. **None of the following is accepted, implied or claimed:**

- Dido AI intelligence
- Style DNA
- recommendation engine
- outfit engine
- **Saved persistence**
- real multi-brand integrations
- merchant SaaS
- public commerce
- native iOS

**This is not production-platform acceptance and must never be promoted into one.**
`PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**.

## 3. Findings, as given

| Surface | Verdict |
|---|---|
| **Home** | **PASS** — product positioning and information architecture are now correct |
| **Dido** | **PASS FOUNDATION / PRODUCT NOT BUILT** — the visual and conversation shell is accepted; real styling intelligence remains a future product phase |
| **Saved** | **PASS VISUAL FOUNDATION / FUNCTIONALITY NOT BUILT** — persistence must be implemented before production exposure |
| **Account** | **PASS** visual and design-system foundation |
| **Brands** | **PASS** visual and domain foundation — the real multi-brand domain is not yet implemented |
| **Looks** | **PASS** conceptual foundation — a Look must later become a real multi-item outfit object with reasoning, pricing and modification actions |
| **Shop** | **PASS** preview foundation and safety behaviour |

## 4. Follow-up item, closed in this cycle

**Reduce the mobile footer substantially.**

The persistent five-item tab bar already provides primary navigation, so the footer was
repeating the whole application hierarchy beneath it — ten redundant targets between the
reader and the one thing a footer is actually for.

**Done.** Below 900px the footer now carries identity, the destinations the tab bar does not
reach, and the disclosure in full. Desktop keeps the expanded columns. The columns are
removed with `display: none` rather than hidden visually, so they leave the accessibility
tree too and a screen reader on a phone is not read a duplicate of the navigation it has
just passed.

### What was deliberately NOT added

The brief named About, Privacy and Terms as footer essentials. They are correct essentials —
and **no such route exists**. Linking a customer to a 404 to look complete is the failure
mode this programme keeps closing, so they were omitted and recorded as a public-launch
requirement instead. See §6.

## 5. Verification of the follow-up

| Check | Result |
|---|---|
| Browser suite — Chromium | see `evidence/phase-3/` run log |
| Browser suite — WebKit | idem |
| Browser suite — Mobile Safari viewport | idem |
| Backend regression | 570 passed · 2 skipped |
| No horizontal overflow | 320 · 375 · 390 · 430 · 768 · 1024 · 1280 · 1440 |
| Footer captures | `evidence/phase-3/home-visual/footer-mobile.png`, `footer-desktop.png` |

## 6. Carried forward

| Item | State |
|---|---|
| **Saved persistence** | **Required before production exposure.** No store, no endpoint, no model |
| **Looks as a real outfit object** | reasoning, pricing and modification actions — future phase |
| **Multi-brand domain** | not implemented |
| **Dido intelligence** | not built |
| About / Privacy / Terms routes | **do not exist.** Required for public launch; omitted rather than linked to a 404 |
| Firefox | **BLOCKED** — cannot launch in this environment |
| LCP / INP / CLS on device | **NOT MEASURED** |
| Native iOS | **NOT TESTED** — never built |
| Physical Android hardware | **NOT TESTED** |

## 7. Provenance

The reviewer tested the deployed candidate on `http://10.0.0.2:13081/`, served from the
image labelled with its source commit, built by Docker from committed source, with its
served bundle verified byte-identical to a local build from the same HEAD.

Existing staging was untouched throughout — `apps/web` continued to serve on 13080, and no
API, database, commerce mode or security control was changed at any point in this cycle.
