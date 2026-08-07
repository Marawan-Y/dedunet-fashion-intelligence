# DEDUNET mobile

Expo-managed React Native client for the commerce API. **Prototype only** — payments run
against a sandbox adapter, no card is charged and nothing is fulfilled.

Status: `WORKSTREAM_F` · `EAS_PROJECT_CONFIGURATION_VERIFIED` ·
`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`. No native binary has been produced. See
`evidence/workstream-f/WORKSTREAM_F_EVIDENCE.md`.

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

## Known limitations

- No native build. `EAS_PROJECT_CONFIGURATION_VERIFIED` only; the app config carries the
  existing EAS project, but no Expo account was available to build or link.
- Routing is a typed union in `App.tsx`, not a navigation library. No deep links, no
  gesture-based back navigation.
- `AsyncStorage` is unencrypted. Session tokens are HMAC-signed, not encrypted, with no
  revocation list. A real deployment wants `expo-secure-store`.
- No update-quantity endpoint exists, so decreasing a line is DELETE followed by POST and is
  not atomic. See `setCartItemQuantity`.
- The Side A DEDUNET brand tokens, fonts, media, catalogue and copy are **not** imported.
  That is the next milestone.
- Seed data still carries legacy `MRT-*` SKUs and product names; those are server-side seed
  values, out of scope for this workstream.
- `npm run deps:check` compares against the SDK matrix *as published today*; a newly released
  Expo patch will make it report an update even though the lockfile is correct.
