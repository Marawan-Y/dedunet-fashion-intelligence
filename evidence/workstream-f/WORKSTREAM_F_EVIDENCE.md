# Workstream F — Mobile Application Rebuild

| Control | Value |
|---|---|
| Artifact ID | EV-WSF-001 |
| Version | 1.0 |
| Date | 2026-08-06 |
| Owner | Side B technical lead |
| Branch | `dedunet/repository-restructure-and-workstreams-a-f` |
| Status | `MOBILE_APPLICATION_REBUILT_AND_LOCALLY_VERIFIED` |
| EAS | `EAS_PROJECT_CONFIGURATION_VERIFIED` |
| Native build | `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING` |
| **Decision** | **`WORKSTREAM_F_CONDITIONALLY_VERIFIED`** |

Conditional, not full. Every check that can be executed on this machine passed, and the
application was driven end to end through a real browser against a real API. **No native
binary exists**, because no Expo account was available to authenticate. That is an external
dependency, not a defect, and it is the single reason this is not `WORKSTREAM_F_VERIFIED`.

Nothing here is production commerce. Payments run against a sandbox adapter; no card is
charged and nothing ships.

---

## 1. Original mobile audit

The pre-existing `apps/mobile/` was four files and had never been installed.

| Item | Finding |
|---|---|
| Files | `App.tsx`, `app.json`, `package.json`, `README.md` — 4 total |
| `node_modules` | absent; never installed |
| Lockfile | **none** — no reproducible install existed |
| `tsconfig.json` | **absent**, despite `.tsx` sources. TypeScript had never been run |
| `eas.json` | absent |
| Entry point | `main: node_modules/expo/AppEntry.js` — reaches inside a dependency; SDK-45-era |
| App identity | `"Origin Fashion PoC"`, slug `origin-fashion-poc` |
| Bundle identifiers | `com.example.originfashionpoc` on **both** platforms |
| EAS project | none configured |

### The peer-dependency conflict, identified precisely

`KNOWN_LIMITATIONS.md` recorded only "a peer-dependency conflict". The actual conflict is
that **every runtime pin disagreed with the Expo SDK 56 matrix**:

| Package | Was pinned | SDK 56 requires |
|---|---|---|
| `expo` | `56.0.12` | `~56.0.19` (latest patch) |
| `react` | `19.1.0` | **`19.2.3`** |
| `react-native` | `0.82.0` | **`0.85.3`** |
| `expo-status-bar` | `~3.0.8` | **`~56.0.4`** |

`expo-status-bar` is the clearest signal: `3.x` predates the package's realignment to SDK
versioning, so the manifest was assembled from versions that never shipped together.

### Two defects in the old `App.tsx`

1. **It called the wrong API.** `GET /api/v1/products` is the **legacy fixture-backed** PoC
   endpoint, not the commerce catalogue (`/api/v1/catalog/products`). It has a different
   payload and a different auth model.
2. **It rendered an unverified origin claim.** Line 67 read
   `Made in {item.made_in}` directly from the response. `KNOWN_LIMITATIONS.md` §1 and
   `CONFLICT-006` both forbid exactly this: `country_of_origin` is the deliberately invalid
   code `XX` precisely so it cannot be presented as substantiated.

The money formatter was the one part worth keeping — it already avoided float arithmetic —
and its approach is preserved and hardened in `src/money.ts`.

---

## 2. Dependency reconstruction

Rebuilt with Expo's own tooling. **No `--force`, no `--legacy-peer-deps`.**

```bash
npm install                       # expo only, to obtain the SDK resolver
npx expo install expo-status-bar react react-dom react-native react-native-web \
                 @react-native-async-storage/async-storage @expo/metro-runtime
npx expo install --fix
```

One genuine peer conflict arose and was **resolved rather than forced**:

```text
Found: react@19.2.3
Could not resolve dependency:
peer react@"^19.2.8" from react-test-renderer@19.2.8
```

`react-test-renderer@*` resolved to a version demanding a newer React than SDK 56 pins.
Fixed by pinning `react-test-renderer` to `19.2.3` to match React exactly. Forcing it would
have installed a renderer built against a different React than the app runs.

This is also why `@testing-library/react-native` was **not** adopted — it was the package
that could not resolve cleanly. The screen tests use `react-test-renderer` directly.

### Final SDK matrix

```text
expo                                     ~56.0.19
react                                     19.2.3
react-dom                                 19.2.3
react-native                              0.85.3
react-native-web                          ^0.21.2
expo-status-bar                          ~56.0.4
@expo/metro-runtime                      ~56.0.19
@react-native-async-storage/async-storage 2.2.0

devDependencies
typescript                               ~6.0.3
jest                                     ~29.7.0
jest-expo                                ~56.0.0
@types/jest                               29.5.14
@types/react                             ~19.2.0
react-test-renderer                      ^19.2.3
@types/react-test-renderer               ^19.1.0
```

```text
$ npx expo install --check
Dependencies are up to date          exit 0
```

### Lockfile and clean install

`package-lock.json` is committed. Verified from a genuinely empty state:

```bash
rm -rf node_modules dist .expo
npm ci
```

```text
added 744 packages in 50s          exit 0
```

**A drift worth stating plainly.** Immediately after the clean install, `expo install --check`
reported `expo@56.0.18 - expected version: ~56.0.19`: a new patch had been published between
the first install and the re-check. `npm ci` was correct — it installed exactly what the
lockfile pinned. The project was then moved to `~56.0.19` and re-verified. `--check` compares
against the matrix *as published today*, so it will report an update again whenever Expo ships
a patch. That is not a broken lockfile and must not be treated as one.

---

## 3. TypeScript

`tsconfig.json` created, extending `expo/tsconfig.base`, with `strict` plus
`noUncheckedIndexedAccess`, `noImplicitOverride` and `noFallthroughCasesInSwitch`.

```text
$ npx tsc --noEmit
exit 0
```

No `any` escape hatches and no `@ts-ignore` were added to reach this.

---

## 4. App identifiers and EAS

```text
$ npx expo config --type public --json
name                : DEDUNET
slug                : dedunet
owner               : Dedunet
scheme              : dedunet
version             : 0.2.0
ios.bundleIdentifier: com.dedunet.store
android.package     : com.dedunet.store
extra.eas.projectId : 72b0a18d-36dd-406f-a54b-ab481a95db88
web.output          : single
```

**Identifier conflict investigated before changing.** The previous identifiers were
`com.example.originfashionpoc` on both platforms. `com.example.*` is the reserved
documentation namespace and can never be published to either store, so these were
placeholders with no claim attached and no migration consideration. Replacing them
displaces nothing.

`eas.json` created with `development`, `preview` and `production` profiles.

### EAS link — attempted, and blocked on authentication

```text
$ eas whoami
Not logged in

$ eas project:info
An Expo user account is required to proceed.
```

eas-cli 21.6.0 was installed cleanly and ran; there is no Expo session and no `EXPO_TOKEN`
in this environment. Therefore:

- **`EAS_PROJECT_CONFIGURATION_VERIFIED`** — the configuration resolves locally and carries
  the **existing** project ID `72b0a18d-36dd-406f-a54b-ab481a95db88`.
- **`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`** — no build was queued, no binary exists.

**No replacement Expo or EAS project was created.** Creating one would have required
authenticating, which was neither possible nor permitted. `M17` in the mutation harness fails
the build if the project ID is ever changed.

`app.json` also declares `"web": { "output": "single" }`. `"static"` pre-renders routes
through `expo-router`, which this app deliberately does not use, and the export fails on the
missing import — recorded because the failure message points at `expo-router` rather than at
the setting that caused it.

---

## 5. API-contract mapping

The OpenAPI contract is authoritative. One property of it materially shaped this work:

> **The commerce routes carry no `response_model`.** The contract types every REQUEST body
> and `TokenResponse`, but declares each commerce `200` as a bare `{}`.

So response field names cannot come from the contract. They were taken from
`services/commerce-api/app/commerce/api.py` and are pinned two ways: `contract.test.ts`
asserts the request shapes and endpoint existence against the committed contract, and
`commerce.test.ts` asserts that a renamed response field is **rejected** rather than rendered.

| Flow | Endpoint | Source of response shape |
|---|---|---|
| Catalogue | `GET /api/v1/catalog/products` | `api.py:191 _product_payload` |
| Product | `GET /api/v1/catalog/products/{slug}` | same |
| Register | `POST /api/v1/auth/register` | contract `TokenResponse` |
| Sign in | `POST /api/v1/auth/login` | contract `TokenResponse` |
| Cart | `GET /api/v1/cart` | `api.py:264 _cart_payload` |
| Add line | `POST /api/v1/cart/items` | same |
| Remove line | `DELETE /api/v1/cart/items/{variant_id}` | same |
| Quote | `GET /api/v1/cart/quote` | `pricing.py:57 PriceBreakdown.as_dict` |
| Checkout | `POST /api/v1/checkout` | `api.py:337` → `{order, replayed}` |
| Orders | `GET /api/v1/me/orders` | `api.py:340 _order_payload` |
| Order | `GET /api/v1/me/orders/{order_number}` | same |

### The missing endpoint

**There is no update-quantity endpoint.** `POST /cart/items` is *additive*
(`desired = existing.quantity + quantity`, `services.py:501`) and the only other verb is
DELETE. `setCartItemQuantity` therefore:

- increase → POST the **difference**;
- decrease → DELETE, then POST the **absolute** new quantity;
- zero → DELETE.

The decrease path is two calls and **is not atomic**. If the second fails the line is gone
rather than merely unchanged, so the caller is handed the real server cart and the customer
sees the true state. Presenting this as atomic would be a lie about a server that offers no
such guarantee. `PATCH /cart/items/{variant_id}` would remove the problem entirely and is
recommended as backend follow-up.

`GET /cart/quote` returns **HTTP 400** for an empty cart (`services.py:546`). That is a
normal state, mapped to `null`, not an error banner.

---

## 6. Implemented screens and flows

`index.ts` → `App.tsx` (typed-union routing, tab bar) → seven screens.

All 25 flows from the brief:

| # | Flow | Verified |
|---|---|---|
| 1 | App boot | boot gate restores session/cart/API base before first fetch |
| 2 | Runtime API configuration | Settings screen; **refuses to save an unreachable base** |
| 3 | Catalogue loading | 4 products rendered from the live API |
| 4 | Loading state | `catalog-loading` |
| 5 | Empty catalogue | `catalog-empty`, distinct from error |
| 6 | Failed fetch | live: "Cannot reach the store", with retry |
| 7 | Product detail | fetched by slug |
| 8 | Variant selection | radio group, stock shown, sold-out disabled |
| 9 | Login | live, session persisted |
| 10 | Registration | implemented; server validation mirrored client-side |
| 11 | Logout | live; cart deliberately survives |
| 12 | Session persistence | survived full page reload |
| 13 | Session expired | forged token → 401 → signed out + notice |
| 14 | Cart creation | token minted and stored |
| 15 | Cart-token persistence | bag survived reload |
| 16 | Add line | live |
| 17 | Update quantity | live increase **and** decrease |
| 18 | Remove line | implemented |
| 19 | Checkout quote | server-priced |
| 20 | Sandbox checkout | live, all three outcomes |
| 21 | Order confirmation | live |
| 22 | Order history | 4 orders, correct statuses |
| 23 | Order detail | live |
| 24 | Rate-limit feedback | live: "wait 662 seconds" |
| 25 | Network recovery | retry actions on every failure banner |

### Live end-to-end transcript

Expo web (`http://localhost:8081`) against a real API (`http://127.0.0.1:18200`), driven
through a real browser:

```text
catalogue      4 products, "From €45.00 / €189.00 / €59.00 / €129.00"
product        Oversized Crew Tee, 3 variants, stock 12/18/7
add to bag     "Added to your bag."   badge -> Bag (1)
quantity +     €59.00 x 2 = €118.00, shipping €0.00 (free-shipping threshold)
quantity -     €59.00 x 1 = €59.00,  shipping €8.90 restored
sign in        customer@meret.example -> tab flips to "Account"
checkout       Declined  -> "The sandbox payment was declined. No charge was made."
checkout       Succeeds  -> Order FC-6130D368, status paid, €248.00
bag after      empty
orders         FC-6130D368 paid €248.00 | FC-ACB36894 paid €67.90
               FC-B4202A89 cancelled    | FC-AA85C07B cancelled
session expiry forged token -> "Your session expired. Please sign in again."
settings       http://127.0.0.1:19999 -> "Not saved — Cannot reach the store"
API stopped    -> "Cannot reach the store. Check your connection and try again." + Try again
```

Order totals reconcile: subtotal €248.00, shipping €0.00, total €248.00, **including**
€39.60 VAT — VAT as a component of the gross, never added on top.

---

## 7. Two real defects found by driving the API, not by unit tests

Both were invisible to the test suite and only appeared when the application was operated
against a live server. Both are now fixed and guarded.

### 7.1 A declined order was replayed and presented as a successful purchase

`services.checkout` returns **any** existing order whose `idempotency_key` matches, with
`replayed=true`, *regardless of that order's status* (`services.py:580`).

The first implementation generated one idempotency key per mounted checkout screen. So:

```text
choose "Declined", pay   -> order created, then cancelled
choose "Succeeds", pay   -> SAME key -> replayed the CANCELLED order
                            screen showed: "Order FC-AA85C07B"
```

No order was placed, and the customer was not told. Two fixes:

1. The key is now `<per-mount nonce>-<outcome>`. Retrying the *same* outcome still replays,
   which is the entire point of idempotency; changing the outcome is a **new intent** and
   gets a new key.
2. `replayed` is now surfaced. The order screen shows an explicit
   `order-replayed` banner, and a settled-but-unsuccessful status renders in the warning
   tone rather than the success tone.

Re-verified live: decline, then succeed → **new** order `FC-ACB36894`, status `paid`.

### 7.2 The bag kept the items the customer had just bought

`services.checkout` sets `cart.status = "converted"` but **leaves the cart lines in place**
(`services.py:678`). `GET /cart` with the same token therefore keeps returning them, and the
bag badge kept counting them after a completed purchase.

Fixed by dropping the stored cart token on a successful checkout, so the next cart call mints
a fresh, empty cart. Re-verified live: bag badge cleared after `FC-6130D368`.

---

## 8. Money behaviour

`src/money.ts` never divides and never produces a float from an amount.

| Property | Behaviour |
|---|---|
| `5900` EUR | `€59.00` |
| `5` EUR | `€0.05` |
| `-250` EUR | `-€2.50` |
| `0.7 * 3` | **`null`** — not a safe integer |
| `Infinity` / `NaN` | **`null`** |
| `JPY` / `KWD` / `USD` | **`null`** — exponent not reviewed |
| zero variants | **`null`**, never `Infinity` |

`lowestPriceMinorUnits` iterates instead of `Math.min(...prices)` specifically because
spreading an empty array yields `Infinity`, which would then be formatted and shown to a
customer as a price. A `screens` test asserts the rendered output for a zero-variant product
contains `"Price unavailable"` and contains neither `Infinity` nor `NaN`.

Only EUR has a reviewed minor-unit exponent. Defaulting to 2 would misprice JPY by 100×.

Client-side line totals are **display only**; the payable amount is always the server's.

---

## 9. Origin and claim gating

`src/origin.ts` is the only module permitted to turn `country_of_origin` into text.

| Input | Output |
|---|---|
| `XX`, `xx`, `""` | **nothing rendered** |
| `Egypt`, `EGY`, `E1` | nothing — not a 2-letter code |
| `EG` | `Declared origin EG — not independently verified` |

A test asserts that **no input to `originLabel` can produce the substring "made in"**, and a
screen test asserts the same over fully rendered output for a product carrying `EG`. Live,
the seeded products carry `XX`, so no origin line appears at all — visible in the transcript
above. Material renders as `Stated material: …`, never as tested fact.

---

## 10. Failure taxonomy

Twelve distinct outcomes, each with its own customer-facing sentence:

`network`, `timeout`, `unauthorized`, `forbidden`, `not_found`, `conflict`,
`payment_declined`, `rate_limited`, `unavailable`, `client_error`, `server_error`,
`malformed`.

The distinctions that matter:

- **A dropped connection is not an expired session.** Collapsing them would sign a customer
  out because their Wi-Fi blipped. Asserted directly.
- **A timeout is not a plain network failure.** This gap was found by the mutation harness —
  see §12.
- **A FastAPI 422 validation array never reaches the customer.** Only a short string `detail`
  is used; the array form is a developer report.
- **No stack trace or provider payload is ever surfaced.**

Every endpoint validates the response shape before handing it to a screen. A renamed
`price_minor_units` produces `malformed`, not the string `"undefined"` beside a product.

---

## 11. Rate-limit handling and CORS

### Live rate-limit evidence

```text
$ 12 rapid logins        401 x10, then 429 x2
$ 429 headers            x-ratelimit-limit: 10
                         x-ratelimit-remaining: 0
                         retry-after: 5
                         access-control-expose-headers: X-Correlation-ID, Retry-After,
                           X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

$ registration bucket    201 x5, then 429 (5/hour)
                         retry-after: 718
```

In the running application, that produced:

```text
"Too many requests. Please wait 662 seconds and try again."
```

That single sentence exercises the whole chain: Workstream C's limiter emits `Retry-After`,
Workstream C's `expose_headers` fix makes it **readable by a browser**, and the mobile client
parses and renders it. Without `Access-Control-Expose-Headers` the header is sent but the
client is forbidden from reading it — the exact false guard recorded in the Workstream C
evidence.

### CORS

The Expo web origin was confirmed empirically as `http://localhost:8081` and added to
`CORS_ORIGINS` **explicitly**:

```bash
CORS_ORIGINS="http://localhost:8081,http://127.0.0.1:8081"
```

```text
preflight OPTIONS /api/v1/cart/items   (Origin: http://localhost:8081)
  HTTP/1.1 200 OK
  access-control-allow-origin: http://localhost:8081
  access-control-allow-methods: GET, POST, DELETE
  access-control-allow-headers: ... Authorization, X-Cart-Token, X-Correlation-ID

GET /api/v1/catalog/products           (Origin: http://localhost:8081)
  access-control-allow-origin: http://localhost:8081

GET /api/v1/catalog/products           (Origin: http://evil.example)
  no access-control-allow-origin header at all

wildcard check: no `access-control-allow-origin: *` on any response
```

**No CORS setting was weakened.** `allow_credentials` remains `False` and the allow-list
remains explicit; a disallowed origin receives no header and a browser blocks it.

---

## 12. Mobile guard mutations — 18/18

`apps/mobile/scripts/mutation_check.mjs`, same discipline as the backend harness: remove one
protected behaviour, require the guarding test to fail, **and require it to fail for the
stated reason**. A rotted anchor is an error, never a skip.

```text
MUTATIONS RUN: 18
DETECTED:      18
SURVIVED:      0
ERRORS:        0
RESULT: every guard removal was detected by its guarding test.
```

| ID | Behaviour removed |
|---|---|
| M1 | zero-variant guard → `Math.min(...[])` → `Infinity` |
| M2 | integer check on money |
| M3 | reviewed-currency check |
| M4 | origin gate → renders `Made in …` |
| M5 | `XX` treated as a real country |
| M6 | 429 classification, losing `Retry-After` |
| M7 | timeout vs network discrimination |
| M8 | malformed-JSON rejection |
| M9 | response validation of `price_minor_units` |
| M10 | cart decrease → POSTs absolute quantity |
| M11 | empty-cart 400 → hard error |
| M12 | sign-out discards the bag |
| M13 | corrupt stored session crashes boot |
| M14 | empty catalogue rendered as an error |
| M15 | sandbox notice removed |
| M16 | screen hard-codes the brand name |
| M17 | app points at a **new** EAS project |
| M18 | regression to the legacy `/api/v1/products` |

### One mutation survived, and fixing it closed a real gap

**M7 survived the first run.** Replacing the `AbortError` check with `false` made every
timeout report as `network`, and **no test noticed** — there was no timeout test at all. Two
tests were added (timeout → `timeout`; externally cancelled → `network`). M7 is now detected.

### The harness misfired first, and that mattered

The first full run reported **18/18 "failed for the wrong reason"** — suspiciously uniform.
The cause was the runner, not the guards: `execFileSync` could not resolve `npx.cmd` on
Windows and threw with `stdout`/`stderr` **undefined**, so every reason-match compared against
an empty string. Rewritten with `spawnSync({ shell: true })`, joining both streams because
jest reports to stderr. Had the harness only checked "did it fail", this would have reported a
clean 18/18 while measuring nothing — the same class of measurement-level false pass recorded
three times previously in this project.

---

## 13. Test suite

```text
$ npx jest --ci
Test Suites: 8 passed, 8 total
Tests:       101 passed, 101 total
```

| File | Covers |
|---|---|
| `money.test.ts` | integer minor units, float rejection, zero variants |
| `origin.test.ts` | no "Made in" for any input |
| `client.test.ts` | full failure taxonomy, Retry-After, no payload leakage |
| `commerce.test.ts` | response validation, quantity workaround, empty-cart quote, idempotency keys |
| `storage.test.ts` | session/cart persistence, corrupt records, storage failure |
| `contract.test.ts` | endpoints + request schemas vs the committed contract |
| `screens.test.tsx` | loading / empty / failed / rate-limited, zero-variant, no "Made in" |
| `brand.test.ts` | brand seam, no legacy strings, EAS project id |

### Three of my own tests were wrong, and one was passing for the wrong reason

1. **`formatMinorUnits(59.0)`** — I asserted `€59.00`. `59.0` is the integer `59` in
   JavaScript, so it means 59 *minor* units: `€0.59`. The function was right; my expectation
   embodied the exact major/minor confusion the money contract exists to prevent.
2. **A leaked `AsyncStorage` spy** — a test that mocked `getItem` to reject leaked into the
   rest of the file, so every later assertion expecting `null` passed because the store was
   **broken**, not empty. That hid two genuine failures. `mockRestore()` then made it worse
   (returning `undefined`), because the mock's function is not a plain method. Fixed by
   swapping and restoring the property by hand, plus an assertion that the restore worked.
3. **A shared `Response` object** — `mockResolvedValue(json(...))` returns the *same*
   `Response` every call, and a body stream can only be read once. The two-call cart test
   failed as `malformed`; the client was correct and the test was wrong.
4. **An over-broad contract assertion** — I asserted `price_eur` appears nowhere in the
   contract. It does: in `Product-Input`/`Product-Output`, the **legacy** fixture surface the
   mobile app never calls. Rescoped to the commerce schemas, with the legacy fact recorded
   explicitly rather than asserted away.

---

## 14. Brand boundary

`src/brand.ts` is the single seam: every customer-visible brand string and every colour.
Enforced by tests:

- no source file references `MERET` or `MERYT`;
- the literal `"DEDUNET"` appears in **exactly one** module;
- no screen contains a hex colour literal;
- the file list is asserted non-empty and to contain known files, so an exclusion cannot
  silently empty the check;
- **no Side A `brand-prototype` asset is imported** — that is the next milestone.

Legacy `MRT-*` SKUs and product names still appear at runtime. Those are **server-side seed
values**, outside this workstream's scope, and are recorded as a limitation rather than
patched from the client.

---

## 15. Secret and bundle-configuration scan

```text
mobile source files scanned: 34
secret patterns (AWS keys, private keys, GitHub PATs, Slack tokens,
  Google API keys, bearer literals, JWTs, password literals): none
```

Built web bundle (`428,276` bytes):

```text
EXPO_PUBLIC_* inlined values : none
AKIA… / gh*_ / AIza… / PRIVATE KEY / JWT : 0
'demo-password' / 'change-me' / 'admin@' : 0
'SESSION_SECRET' / 'POSTGRES_PASSWORD'   : 0
```

Tracked-artifact check: `node_modules/`, `dist/` and `.expo/` are all git-ignored and
untracked. The committed set is source, config, tests and the lockfile only.

---

## 16. Expo export and web preview

```text
$ npx expo export --platform web --output-dir dist
Web Bundled 13377ms index.ts (225 modules)
_expo/static/js/web/index-*.js (428KB)
index.html (1.2KB)
Exported: dist                      exit 0
```

Web preview verified against the real API — see the transcript in §6.

---

## 17. Backend regression

Workstream F changed **no** backend file. Confirmed by re-running the full baseline:

| Check | Result |
|---|---|
| SQLite suite | **167 passed**, 1 skipped |
| PostgreSQL 16 suite | **168 passed** |
| Backend mutation harness | **48 run, 48 detected, 0 survived** |

PostgreSQL ran against an isolated throwaway `postgres:16-alpine` container on port 55433,
removed afterwards. No existing stack or volume was touched, and `down -v` was never issued.

---

## 18. Known limitations

- **`NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`.** No native binary exists. No Expo account
  was available, so no build was queued, no credentials generated, no store metadata created.
  Do not describe the mobile app as built.
- **Routing is a typed union, not a navigation library.** No deep links, no gesture back
  navigation, no URL-addressable screens on web.
- **`AsyncStorage` is unencrypted.** Session tokens are HMAC-signed, not encrypted, with no
  revocation list, so a token lifted from device storage is valid until it expires.
  `expo-secure-store` is the correct control and is not yet adopted.
- **Decreasing a cart quantity is not atomic** — two calls, because the API has no
  update-quantity endpoint.
- **No offline support, no caching, no optimistic updates.** Every screen reads live.
- **No automated accessibility audit.** Roles, labels, live regions and 46px touch targets
  are implemented; no axe run or screen-reader test was performed.
- **No device or emulator testing.** Verified on Expo **web** only. Android and iOS runtime
  behaviour is unexercised.
- **No performance measurement.** The 428KB bundle is a fact; no budget or load test exists.
- **Side A brand assets are not imported.** Deliberately out of scope.
- **Registration was exercised only against the rate limiter**, not through a full
  register-then-purchase journey.
- **The catalogue has no images.** `image_url` is empty in the seed and no image component is
  implemented.
- **`expo install --check` is a point-in-time statement**, not a stable invariant.

---

## 19. Rollback

Workstream F touches only `apps/mobile/` and adds `evidence/workstream-f/`. No backend file,
no migration, no schema change, no API change, no infrastructure change.

```bash
git revert --no-edit <workstream-f-commit>
```

That restores the previous four-file mobile stub, which had never been installed or run, so
nothing operational regresses. Build artifacts (`node_modules/`, `dist/`, `.expo/`) are
git-ignored and unaffected; delete them by hand if required.

The backend baseline is unchanged by this workstream, so no backend rollback is implied.

---

## 20. Decision

**`WORKSTREAM_F_CONDITIONALLY_VERIFIED`**

Every executable check passed: dependency matrix aligned by Expo's own tooling with no forced
resolution, clean install from a committed lockfile, TypeScript clean, 101 tests passing,
18/18 guard mutations detected with none surviving, a successful web export, and the complete
catalogue → cart → account → checkout → order journey driven through a real browser against a
real API — including the rate-limit, session-expiry, failed-fetch and empty states.

Two genuine defects that no unit test caught were found by operating the application against
a live server, fixed, and guarded.

It is **conditional** for one reason: `NATIVE_PREVIEW_BUILD_EXTERNALLY_PENDING`. No Expo
account exists in this environment, so no Android or iOS binary has been produced and none is
claimed. Nothing in the repository can close that; it needs a human with Expo credentials.
