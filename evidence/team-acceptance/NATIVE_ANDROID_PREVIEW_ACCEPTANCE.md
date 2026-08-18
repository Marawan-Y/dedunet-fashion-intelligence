# DEDUNET — Native Android preview acceptance

**Artifact ID:** EV-TA-004 · **Version:** 1.0 · **Owner:** Side B / platform
**Status:** `NATIVE_ANDROID_PREVIEW_ACCEPTANCE_PASSED` · **Date:** 2026-08-18
**Accepted baseline before native work:** `c0c8fac` (*docs: close local team acceptance*)
**Android acceptance commit:** `4cb8e50` (*feat: complete Android native preview acceptance*)
**Decided by:** human acceptance manager

> `PUBLIC_COMMERCIAL_LAUNCH_BLOCKED` remains fully in force. This records that a **preview**
> APK was built and exercised on an **Android emulator**. It is not production readiness, not
> a store release, and not a launch authorization. No Apple/App Store work was begun.

---

## 1. What was accepted

| | |
|---|---|
| EAS project | `@dedunet.com/dedunet` |
| EAS project ID | `72b0a18d-36dd-406f-a54b-ab481a95db88` |
| Emulator | Pixel 9 · Android 16 · API 36 |
| Successful build IDs | `098add84-f7f5-4acd-a68b-e49bfcf2e100`<br>`2c765b76-2377-496c-8129-6b3bacde0a0b` |
| Package | `com.dedunet.store` |

Emulator identity re-confirmed on the running device during this phase:

```text
ro.build.version.release  16
ro.build.version.sdk      36
ro.product.model          sdk_gphone64_x86_64
pm list packages          package:com.dedunet.store
```

### Gates passed

| Gate | Result |
|---|---|
| Native catalogue renders | **PASS** |
| Native SVG / brand media renders | **PASS** |
| Preview purchase blocking | **PASS** |
| Auth persistence | **PASS** |
| Laptop and emulator restart persistence | **PASS** |
| Expired-session recovery | **PASS** |
| Test customer cleanup | **PASS** |
| Final `BRAND_PREVIEW_MODE` restoration | **PASS** |

### Explicitly NOT tested

**Physical Android device acceptance is `NOT TESTED`.** Acceptance ran entirely on an
emulator. An emulator shares the host's network stack through `10.0.2.2` and its own
graphics and storage behaviour; none of that establishes how a real handset behaves on a
real network. It is recorded as untested rather than inferred from the emulator run.

`NATIVE_IOS_PREVIEW_BUILD` also remains outside this record. No Apple publisher identity
exists and no iOS work was begun.

## 2. Post-acceptance issue A — a saved endpoint outlived its build

Everything about the build was right and the app was still unusable:

```text
preview APK carried          http://10.0.2.2:18080
Android manifest allowed     local cleartext traffic
emulator Chrome reached      the API, fine
the app showed               "Cannot reach the store"
the backend received         no request at all
clearing app storage         fixed it instantly
```

That last line is the diagnosis: state outliving the build that created it.

Re-measured from **inside the running emulator** during this phase, with `toybox nc`:

```text
GET 10.0.2.2:18080/ready   ->  HTTP/1.1 200 OK
                               {"status":"ready","checks":{"database":"ok",
                                "catalog_fixture":"ok"}}

connect 10.0.2.2:18000     ->  nc: connect: Connection refused
```

So the network path was fine, the API was up, and the app was faithfully talking to a port
nothing listens on.

### Root cause

`useAppStore` boot applied the saved base unconditionally:

```ts
const [storedBase] = await Promise.all([storage.loadApiBase(), ...]);
if (storedBase) setApiBaseState(storedBase);
```

An override saved against an **older** build had permanent precedence over the endpoint
baked into the new APK, with no expiry and no way out but wiping app data — which also
destroyed the session and the cart.

It was invisible to the suite because the rule lived inside a `useEffect` that reads
AsyncStorage; there was nothing pure to assert on.

Reproduced before changing anything:

```text
bakedIntoApk                 http://10.0.2.2:18080
savedOverrideFromOlderBuild  http://10.0.2.2:18000
apiBaseTheAppActuallyUses    http://10.0.2.2:18000
reachesTheApi                false
```

### Correction — a versioned override policy

The build's endpoint is authoritative. An override has to **earn** precedence by proving it
is still current, which it does by recording the build default it was saved *against*:

```text
v1   "http://10.0.2.2:18000"                    bare string, no provenance
v2   { version, value, buildBase }              provenance
```

`resolveApiBase(override, buildDefault)` applies an override only when all of it holds:

* it is the current schema version,
* its value is a usable absolute origin,
* it records the build default it was saved against,
* and that build default is the one in force now.

The last clause is the fix. A newer build carrying a different endpoint means the saved
value was configured for a different application, so it is discarded and the build wins.

| File | Change |
|---|---|
| `src/config.ts` | `resolveApiBase` as a **pure** function, plus `buildDefaultApiBase`, `describeApiBaseSource`, `describeOverrideRejection` |
| `src/storage.ts` | v2 record; v1 retired on read and its key removed |
| `src/store.ts` | boot resolves instead of assuming; a refused override is discarded and explained |
| `src/screens/SettingsScreen.tsx` | shows the source and the build default; a reset that actually resets |
| `src/ui.tsx` | `Body` accepts a `testID` so a line of copy can be asserted on |

### Migration and reset behaviour

* **A stale v2 record** (saved against a different build default) is discarded, reported as
  `stale`, and removed so the next launch is not asked the same question.
* **A legacy v1 record** cannot prove anything about itself, so it is discarded and reported
  as `legacy`. "Cannot be shown to be current" has to mean discarded; the opposite default
  is the defect. The cost is one re-entry for a developer who had saved a LAN address — a
  one-time inconvenience against an endpoint that could otherwise never be dislodged.
* **A malformed or blank record** is discarded and reported as `malformed`, not silently
  treated as "no override", which would hide a corrupted store.
* **A valid current override** is applied unchanged. This is the case the feature exists
  for: one build reached from an emulator and from a handset.
* **The discard is visible.** The settings screen explains it, so the endpoint does not
  appear to change by itself between launches.
* **Nothing else is touched.** Session and cart are separate records. The old workaround —
  clearing app storage — destroyed both, and reproducing that inside the fix would be that
  workaround wearing a nicer hat. Three tests hold it, including one asserting that exactly
  the two API keys are removed and the session and cart keys remain.

### Production must not inherit a local endpoint

`10.0.2.2` was the unconditional Android fallback, so a release build with no
`EXPO_PUBLIC_API_BASE` would have carried a hidden emulator endpoint and failed like a
network fault. It is now **development-only**; an unconfigured release build reports
`unconfigured` rather than substituting an address, and the settings screen's address table
is behind a `__DEV__` guard. Three tests pin the literal inside that one dev-only function
and out of every other source file.

## 3. Post-acceptance issue B — the orders empty state promised a purchase

In `BRAND_PREVIEW_MODE` the empty order history read:

> "Sandbox orders you place will appear here."

Nothing can be placed in preview mode — re-confirmed from inside the emulator in §5. The
screen was inviting the customer to do something the server would refuse, which is the same
class of untruth as the storefront banner closed in `1a90c10`, one screen further in.

```text
BRAND_PREVIEW_MODE   No orders yet.
                     Purchasing is unavailable while this catalogue is in preview.

COMMERCE_TEST_MODE   No orders yet.
                     Sandbox test orders you place will appear here.

unresolved/blocked   No orders yet.
                     Orders you place will appear here once this deployment allows
                     purchasing.
```

The third case is deliberate: before the deployment has said what it allows, and when it
reports a refused mode, the honest answer is that we do not know. Derived from the mode,
never from stock — a test holds the copy still while `purchasable` flips.

## 4. Tests added

| Suite | Count | Covers |
|---|---|---|
| `api-base-lifecycle.test.ts` | **20** | the acceptance failure verbatim, legacy/stale/malformed refusal, a valid current override, the production fallback, the emulator address staying inside its dev-only path |
| `api-base-storage.test.ts` | **15** | v2 round-trip, v1 retirement, unreadable records, and that the migration and reset leave session and cart untouched |
| `api-base-screens.test.tsx` | **8** | the source shown on screen, the discard banner, and a reset that clears the saved record |
| `orders-copy.test.tsx` | **12** | both modes, the neutral fallback, no inference from stock, and the preserved signed-out path |

**55 new tests.** Mobile suite `151 → 206` across 14 suites.

The first assertion is the acceptance failure verbatim: an old `:18000` override plus a new
`:18080` build must not stay pinned to `:18000`.

### Mutations

| Mutation | Attack | Outcome |
|---|---|---|
| `M19` | make the staleness check unconditional, so a saved endpoint from an older build outranks this build | **DETECTED** |
| `M20` | give preview mode the sandbox wording | **DETECTED** |

Mobile harness: **20 run, 20 detected, 0 survived, 0 errors.**

## 5. Verification

### Expo configuration

```text
npx expo config --type public
  owner                          dedunet.com
  slug / eas projectId           dedunet / 72b0a18d-36dd-406f-a54b-ab481a95db88
  plugins                        ["expo-image"]
  expo-image                     1 occurrence
  expo-build-properties          0 occurrences
  10.0.2.2                       absent
  DEDUNET_ALLOW_LOCAL_HTTP       absent
  usesCleartextTraffic           absent

DEDUNET_ALLOW_LOCAL_HTTP=true npx expo config --type prebuild
  plugins                        ["expo-image","expo-build-properties"]
  expo-image                     1 occurrence
  expo-build-properties          1 occurrence
  usesCleartextTraffic           {"android":{"usesCleartextTraffic":true}}

eas.json production profile      {"autoIncrement":true}
  10.0.2.2                       absent
  DEDUNET_ALLOW_LOCAL_HTTP       absent
  EXPO_PUBLIC_API_BASE           absent
```

Exactly one of each plugin under the flag, and neither the address nor the flag in the
production profile.

### Runtime, from inside the Android emulator

`BRAND_PREVIEW_MODE`, measured on the device with `toybox nc`:

| Check | Result |
|---|---|
| `GET :18080/ready` | **HTTP 200**, database and catalogue fixture ok |
| `GET :18080/api/v1/commerce/mode` | `BRAND_PREVIEW_MODE`, `purchasable=false`, `payments=none`, `public_commerce_enabled=false` |
| Catalogue | **5 products, 5 DEDUNET, none sellable** |
| `POST :18080/api/v1/cart/items` | **409** *"this catalogue is in brand preview; nothing is available to purchase"* |
| `connect :18000` | **Connection refused** — the stale override's target is genuinely dead |

Host-side, unchanged throughout this phase: `COMMERCE_MODE=BRAND_PREVIEW_MODE`, `/ready`
**200**. No order was created, no checkout replayed, and the runtime was never switched out
of preview mode.

### What native verification does NOT cover, and why

**The fixed application was not re-run natively.** Doing so needs a new APK, and none of the
three routes to one was available without crossing a gate:

| Route | Blocked by |
|---|---|
| EAS cloud build | Uploads the project to an external service. Not undertaken without an explicit instruction. |
| Local Gradle (`expo run:android`) | **No JDK installed** — `java` is not on PATH and `JAVA_HOME` is unset. |
| Expo Go | **Not installed** on the emulator (`pm list packages` shows only `com.dedunet.store` and Chrome). |
| Inspecting the installed app's storage | The preview APK is a release build — `run-as` reports *"package not debuggable"*. |

So the device-side evidence above is what the emulator can establish about the **defect and
its environment**, not about the corrected build. What changed is entirely JavaScript-level
endpoint selection and screen copy, covered by 55 tests and two mutations; but that is a
statement about coverage, not a substitute for running it, and it is recorded as such.

**Recommended next step:** rebuild the preview APK (EAS) and re-run the emulator pass —
catalogue loads, a stale override cannot hijack the build, the reset works, the orders copy
is preview-correct, purchase remains blocked.

## 6. Commits

| Commit | Scope |
|---|---|
| `4cb8e50` | *feat: complete Android native preview acceptance* — the accepted baseline for this phase |
| `1b2863b` | *fix: harden native API override lifecycle* |
| `4e4f8c0` | *fix: make native orders copy mode aware* |
| *this one* | *docs: close Android native acceptance* |

## 7. Remaining blockers

Unchanged by this phase, and none was attempted:

| Blocker | Status |
|---|---|
| Physical Android device acceptance | **NOT TESTED** — emulator only |
| Native iOS preview build | not begun; no Apple publisher identity |
| Apple publisher membership / identity | `DEFERRED — PUBLISHER IDENTITY PENDING` |
| Google Play publisher identity | `DEFERRED — PUBLISHER IDENTITY PENDING` |
| Re-verification of the fixed APK on the emulator | pending a new EAS build |
| External SMTP delivery | `EXTERNAL_SMTP_DELIVERY_PENDING` |
| Hosted production cloud | `DEFERRED — LOCAL STAGING ONLY` |
| Real payment provider activation | not activated |
| Real inventory activation | not loaded |
| Real fulfilment activation | not established |
| Product-origin substantiation | `origin_claim_status = UNVERIFIED`, `country_of_origin = XX` |
| Material / composition substantiation | stated intention, not tested |
| Product evidence approval | `evidence_status = DRAFT` |
| Legal / trademark clearance | `LEGAL_CLEARANCE_PENDING` |
| Human risk-owner approvals | `ASSIGNMENT_RECORDED — HUMAN ACCEPTANCE PENDING` |

Dependency vulnerabilities recorded in
[`LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md`](LOCAL_TEAM_ACCEPTANCE_CLOSEOUT.md) §6 are unchanged.
No dependency was upgraded and `npm audit fix` was not run.

## 8. Rollback

```bash
git revert 4e4f8c0 1b2863b
```

JavaScript only — no schema, migration, fixture, order, payment or inventory row is involved.
Reverting `1b2863b` restores the unconditional precedence, so a saved override will again
outrank the build endpoint permanently; reverting `4e4f8c0` restores the sandbox promise in
preview mode. A new APK would be needed for either revert to reach a device.

## 9. Position after this phase

```text
Local team acceptance                     PASSED   (human, 2026-08-12)
Native Android preview acceptance         PASSED   (human, emulator, 2026-08-18)
Native API override lifecycle             HARDENED
Native orders copy                        MODE AWARE
Physical Android device acceptance        NOT TESTED
Re-verification of the fixed APK          PENDING a new EAS build
Public commercial launch                  BLOCKED  (unchanged)
```
