# DEDUNET mobile

Expo-managed React Native client for the commerce API. **Prototype only** — no real card is
charged and no real order is fulfilled. What the client can do depends on the deployment's
commerce mode: `BRAND_PREVIEW_MODE` reaches no payment call at all, `COMMERCE_TEST_MODE`
uses the sandbox adapter against synthetic stock. The catalogue screen states which, in the
server's own words, from `GET /api/v1/commerce/mode`.

Status: `LOCAL_TEAM_ACCEPTANCE_PASSED` · `EAS_PROJECT_CONFIGURATION_VERIFIED` ·
`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`. The Expo/React Native **web** preview was
exercised and passed in human acceptance (Test 3B); **no native binary has been produced**,
and that remains externally pending. See
`evidence/team-acceptance/LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md` for the acceptance result and
`evidence/workstream-f/WORKSTREAM_F_EVIDENCE.md` for the original workstream record.

`PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` is unchanged. Local acceptance is not a launch
authorization.

## Requirements

Node 24 (developed on 24.15.0) and npm 11. No Android/iOS toolchain is needed for the web
preview or for any check below.

## Install

```bash
cd apps/mobile
npm ci
```

`npm ci` installs exactly what `package-lock.json` pins. Use it rather than `npm install`
when reproducing a result.

## Run

Start the API first, from the repository root:

```bash
cd services/commerce-api && python -m app.server --port 18000
```

Then:

```bash
npm run web        # browser preview
npm start          # dev server for a device or emulator
```

**The API base URL differs per platform** and this is the usual reason a working API looks
unreachable:

| Target | Base URL |
|---|---|
| Android emulator | `http://10.0.2.2:18000` |
| iOS simulator / web | `http://127.0.0.1:18000` |
| Physical device | `http://<development machine LAN IP>:18000` |
| Local staging stack | port `18080` |

Set it three ways, in precedence order: the in-app **API settings** screen (persisted, and
verified before it is saved), `EXPO_PUBLIC_API_BASE` at build time, or the platform default.

### CORS

The API allows only the origins in `CORS_ORIGINS`. For the web preview, include the Expo
origin explicitly — never a wildcard:

```bash
CORS_ORIGINS="http://localhost:8081,http://127.0.0.1:8081" python -m app.server --port 18000
```

## Checks

```bash
npm run deps:check     # Expo SDK dependency matrix
npm run typecheck      # tsc --noEmit
npm test               # jest
npm run mutations      # guard-mutation harness
npm run export:web     # production web bundle
```

`npm run mutations` removes each protected behaviour in turn and requires the guarding test
to fail *for the stated reason*. A guard whose removal nobody notices is not a guard.

## Layout

```
index.ts                 entry (registerRootComponent)
App.tsx                  root, routing, tab bar
src/brand.ts             THE brand seam — every brand string and colour
src/config.ts            runtime API base resolution
src/money.ts             integer minor units; never divides
src/origin.ts            origin/material claim gating
src/storage.ts           session, cart token, API base persistence
src/store.ts             application state; central 401 handling
src/api/                 client (failure taxonomy) + endpoints + types
src/screens/             catalog, product, cart, checkout, orders, account, settings
scripts/mutation_check.mjs
```

## Rules this client enforces

**Money is integer minor units.** €59.00 is `5900`. Nothing divides, and a non-integer or
an unreviewed currency renders a non-price fallback rather than a guess.

**A product with no variants has no price.** `lowestPriceMinorUnits` returns `null`;
`Math.min(...[])` would return `Infinity` and render it as a price.

**No "Made in" claim.** `country_of_origin` is `XX` by design and carries no evidence of
substantiation, so `src/origin.ts` never renders a factual origin claim.

**The server prices the basket.** Line totals are display-only; the payable amount is always
the `/cart/quote` or order total, because VAT is a component of the gross, not an addend.

**Failures are distinct.** Network, timeout, 401, 402, 409, 429, 5xx and malformed each have
their own outcome and their own message. A dropped connection must never sign a customer out.
Only a 401 clears the session, once, in `store.handleFailure`; mutation `M7` proves it, and
the web storefront was aligned to this policy after human acceptance found it showing
"Signed in as customer" against an expired token.

**The deployment says what it is.** The catalogue notice is the server's wording for the
server's mode, never a fixed string and never inferred from stock — a client reasoning
"there is inventory, so this must be commerce-test" would be right today and wrong the first
time a preview catalogue carries a non-zero count.

## Known limitations

- No native build. `EAS_PROJECT_CONFIGURATION_VERIFIED` only; the app config carries the
  existing EAS project, but no Expo account was available to build or link.
- Routing is a typed union in `App.tsx`, not a navigation library. No deep links, no
  gesture-based back navigation.
- `AsyncStorage` is unencrypted. Session tokens are HMAC-signed, not encrypted, with no
  revocation list. A real deployment wants `expo-secure-store`.
- No update-quantity endpoint exists, so decreasing a line is DELETE followed by POST and is
  not atomic. See `setCartItemQuantity`.
- The Side A DEDUNET brand **tokens and fonts** are not imported. `src/brand.ts` still
  carries the technical placeholder palette, and adopting the Side A token set remains
  outstanding work.
  *Corrected 2026-08-12:* this entry previously also claimed the DEDUNET **media, catalogue
  and copy** were not imported. That is no longer true and had been superseded by the
  DEDUNET integration and branded vertical slice: the client renders the five-product
  DEDUNET catalogue and DDN-TS01's four ordered media through `components/Gallery.tsx`,
  re-confirmed in human acceptance Test 3B. Only the token/font half of the original
  statement still stands.
- The customer-facing catalogue is the DEDUNET catalogue. The legacy `MRT-*` fixture rows
  still exist server-side because existing orders reference them as financial records, and
  `BRAND_PREVIEW_MODE` filters them out of everything a customer can see.
- `npm run deps:check` compares against the SDK matrix *as published today*; a newly released
  Expo patch will make it report an update even though the lockfile is correct.
