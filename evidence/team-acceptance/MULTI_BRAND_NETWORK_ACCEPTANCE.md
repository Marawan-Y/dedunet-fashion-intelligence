# Multi-brand fashion network — physical iPhone Safari human acceptance

| Field | Value |
|---|---|
| Artifact ID | EV-ACC-006 · **Version** 1.0 |
| Status | **`HUMAN-VERIFIED`** |
| Result | **`MULTI_BRAND_FASHION_NETWORK_ACCEPTED`** |
| Date | 2026-09-30 |
| Reviewer | Repository owner, in person |
| Device | **Physical iPhone, Safari**, over the LAN |
| Target | `http://10.0.0.2:13080/` — normal staging |
| Application baseline | `a1abed3` |
| Owner | Side B / platform |

> A **human** acceptance, performed by a person on real hardware.

## 1. What is accepted

The multi-brand domain as delivered in Phase 4: products belong to brands, brands carry
explicit ownership, commerce routing is a separate axis from ownership, and provenance is
modelled rather than assumed.

Human-verified surfaces: Brands, Brand detail, Shop brand attribution and filter,
Product → Brand navigation, the DEDUNET first-party brand, and the development fixture's
labelling.

## 2. What is NOT accepted, and was not claimed

- **No real external brand integration exists.** `EXTERNAL` and `REFERRAL` are implemented
  and tested; **no data uses them**. Nothing here is a partnership, agreement or integration.
- **`HOSTED` checkout is unreachable** — refused until merchant commerce exists.
- **`MerchantOrganization` is a stub** tenant root. Merchant SaaS is not started.
- **Brand sync is not built.** `last_checked_at` / `last_synced_at` are null, not stale.
- A **Look** remains curated editorial content. It is not an engine-generated outfit with
  reasoning, pricing and modification actions.

`PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**. `LEGAL_CLEARANCE_PENDING` is unchanged.
A web application accepted in Safari on an iPhone is **not** native iOS acceptance.

## 3. Provenance

Engineering verification behind this baseline: 657 backend tests, 462 browser tests across
Chromium, WebKit and the Mobile Safari viewport against the deployed URL, 13 consumer unit
tests, and migration integrity proven byte-identical before and after — see
`evidence/phase-4/MULTI_BRAND_NETWORK_EVIDENCE.md`.

Source Tee remained **€72.00**, `NON_PURCHASABLE`, preview throughout.
