# Phase 6 — Style DNA: the explicit customer style profile

| | |
|---|---|
| Artifact ID | `EV-P6-STYLE-001` · **Version** 1.0 |
| Owner | Side B / platform |
| Status | `SELF-VALIDATED` + `AUTOMATED-TESTED` — the human gate is outstanding |
| Branch | `feat/style-dna-explicit-profile` from `main` at `752989d` |
| Migration | `a9f3e26b104c` |
| Consumer | Physical-iPhone Style DNA acceptance, then PR review |

## 1. What this phase built, and what it deliberately did not

Style DNA is **the structured set of style information a customer has deliberately told
DEDUNET about themselves.** In this phase that is the whole definition.

It is **not** an AI personality score, a recommendation score, an embedding, a Saved-item
inference, a browsing or purchase inference, a demographic or body-shape inference, or an
LLM-generated profile. None of those exists, none is stubbed, and nothing in the schema is
shaped to receive one without a migration someone reviews.

## 2. The rule the domain hangs from

> Every row exists because a person chose it.

Enforced in three places, each doing a different job:

| Layer | Mechanism | What it catches |
|---|---|---|
| Database | `CHECK (source = 'USER_EXPLICIT')` on all six preference tables | any code path at all, including a future migration, fixture or bulk import |
| Service | `ALLOWED_SOURCES` allow-list | gives a readable error instead of an `IntegrityError` |
| Client | `StyleSource = "USER_EXPLICIT"` as a literal type, not `string` | a future inferred value must be added before it can be rendered — which is when somebody decides how to label it |

`source` is a `VARCHAR`, not a PostgreSQL `ENUM`, so a later phase adds values in code
rather than with an `ALTER TYPE` on every table. The point of the column existing now, with
one legal value, is that **"you told us" and "we guessed" are distinguishable from the
start** — an inference phase cannot quietly reuse rows that were never explicit.

`M84_style_dna_source_is_pinned_by_the_database` mutates that constraint to `1 = 1`, and
`test_inferred_source_is_refused_by_the_database` fails when it does.

## 3. Schema — seven tables, normalized, no JSON blob and no EAV

```
style_profiles                 one per customer (UNIQUE customer_id)
├── style_direction_preferences   (profile, style_slug)          UNIQUE
├── style_colour_preferences      (profile, colour_slug)         UNIQUE
├── style_material_preferences    (profile, material_slug)       UNIQUE
├── style_fit_preferences         (profile, garment_category)    UNIQUE
├── style_sizes                   (profile, category, system)    UNIQUE
└── style_brand_preferences       (profile, brand_id FK brands)  UNIQUE
```

Scalars on the profile: `personalization_enabled`, `revision`, `colour_approach`,
`care_effort`, `seasonality`, `fit_notes`, and the two budgets with their currency.

**Why these are tables and not a JSON column.** A blob makes validation a code concern
rather than a schema one, makes "show me everything you hold about me" a parse instead of a
query, and makes a uniqueness guarantee impossible. **Why not EAV.** It would buy generality
this domain does not need and lose the ability to say, in the schema, that a stance belongs
to a colour and a size belongs to a category and a system.

**Uniqueness on `(profile, value)` rather than `(profile, value, stance)`** is a deliberate
choice: a customer cannot both prefer and avoid the same thing, and this makes the
contradiction *unrepresentable* rather than merely discouraged.

**Absence is not a third stance.** An unset preference is a missing row. Storing "neutral"
would be inventing an opinion the customer never expressed.

## 4. Section by section

### Style direction
Preferred and avoided across the existing DEDUNET vocabulary. **One source of truth:** the
server owns the list, serves it from `GET /style-dna/options`, and the consumer ships no
copy — so it cannot offer a choice the server rejects. The one list that legitimately
pre-existed on the client, `STYLE_CATEGORIES` in `content.ts`, is guarded by
`test_style_taxonomy_drift.py`, which parses that file and requires slugs, labels,
descriptions **and order** to match. A duplication with a guard is survivable; without one
it is a trap.

### Colour
Sixteen ordinary colour words, preferred or avoided, plus a **separate** explicit question
about how colour should work (`neutrals-only`, `tonal`, …). Separate on purpose: a customer
who likes black, white and grey has told us three colours, not that they want a neutral
palette. No colour-science model, no hex values, no computer vision, and nothing inferred
from Saved products.

### Fit and size
Fit per garment category from a four-term taxonomy. Sizes stated as
`(category, size_system, size_label)` and **never converted** — not between systems and not
between brands. `EU 50 = UK 40 = M` is approximately true across brands and exactly true
within none, and a profile that silently converted would be confidently wrong in the one
place nobody would check. Uniqueness is `(profile, category, system)`, so "tops: ALPHA M"
and "tops: EU 50" coexist with neither claiming to be the other. **No body measurements and
no body-shape inference.**

### Material
Preferred and avoided fibres, plus explicit care effort and climate. The page states, where
a customer will read it, that **a material preference is about them and not about any
garment** — composition stays "stated, not verified" until supplier documents and testing say
otherwise. Recording "I prefer cotton" authorizes no claim about any product.

### Brands and budget
Brand preferences by **foreign key** into the real Brand domain, never a name string that
would drift on a rename. **Development fixtures are refused** at the API and filtered from
the UI: offering `internal-development-fixtures` as something to follow would present a
scaffold as a fashion house. A preference implies **no partnership, endorsement or
commercial relationship**, and the page says so.

Budgets are **integer minor units with an explicit currency**. A float is rejected, never
coerced — `int(199.99 * 100)` is `19998` on this hardware, and money quietly one cent wrong
is worse than a refused request. The client formats and parses by slicing digits; it never
divides. A budget is what the customer said they want to spend, **not an estimate of what
they can afford**, and nothing infers income.

## 5. What was kept out of the persistent profile

Occasion, dress code, weather, destination and one-off event requirements are **session
context, not identity**, and none of them is stored. They belong to a future Dido styling
request. Turning a question asked once into a permanent attribute is how a profile starts
describing somebody who no longer exists.

## 6. Privacy

**No sensitive characteristic is stored or inferred** — not religion, ethnicity, sexual
orientation, health, politics, gender identity or financial condition.
`test_no_vocabulary_term_implies_a_sensitive_characteristic` fails if any vocabulary term
even *mentions* one. "Modest" is listed as a style direction because it is a cut of
clothing; the distinction is the point.

**One free-text field, capped at 280 characters.** An open box in a personal profile is
where sensitive disclosure arrives uninvited, and no placeholder text prevents it. A tight
bound at least keeps the field obviously a note about clothes.

**Events carry no profile content and no customer identifier.** `style_profile_created`,
`_updated`, `_enabled`, `_disabled`, `_deleted` are emitted with an empty payload. An
analytics table holding sizes and budgets would be a copy of the most personal data in the
system sitting outside every control built to protect the original — outside the delete
endpoint, outside erasure, and outside what the customer can inspect.
`test_events_carry_no_profile_content` greps real event rows for the actual values.

**No admin view of customer profiles was built.**

## 7. Two controls, never one

| Action | Effect |
|---|---|
| **Disable personalisation** | Profile preserved exactly. Future consumers must not treat it as active. |
| **Delete Style DNA** | Profile and all preference rows removed. **Saved items, orders, addresses and the account are untouched.** |

Conflating them would destroy data somebody meant to keep. Both directions are tested, and
`test_delete_removes_profile_and_every_child_row` plus
`test_deleting_style_dna_leaves_saved_items_alone` hold the boundary.

## 8. Account erasure — the lesson inherited, not rediscovered

`erase_customer` **pseudonymizes** the customer row so order history stays reconcilable,
which means the `ondelete=CASCADE` foreign keys **never fire**. Saved persistence paid for
that discovery; Style DNA gets it for free by deleting explicitly in the same function.

Both paths are tested separately: `test_hard_delete_of_the_customer_cascades` and
`test_erase_customer_removes_style_dna`. `M83` mutates the explicit deletion and the second
test catches it.

## 9. The Saved boundary

`SavedProduct`, `FavoriteBrand` and `SavedLook` **do not create or modify Style DNA**. Not
by omission — by test: `test_saving_items_does_not_create_or_change_style_dna` saves a brand
and asserts no profile exists at all, and the E2E does the same through a real browser.

It would be a few lines to turn "saved three black pieces" into "prefers black". Those few
lines are the moment Style DNA stops being true: **a save is an act of interest, not a
statement of preference**, and people save things to decide against them. Inference needs
its own source, confidence, explanation, correction path, consent and decay. None exists, so
nothing infers.

The page says so out loud, because every other platform does infer and an assumption we know
people will make is one we are responsible for correcting.

## 10. Concurrency

`revision` with `expected_revision` on PATCH; mismatch returns **409** carrying the current
revision so the client can offer a reload without a second request. A style profile is
edited from a phone and a laptop by the same person, which is precisely the shape that loses
updates. Last-write-wins is not simpler — it moves the loss somewhere nobody sees it.

Validation is **whole-patch**: a rejected patch changes nothing
(`test_a_rejected_patch_changes_nothing`). A half-applied update would leave a profile the
customer never asked for.

`M82` mutates the conflict raise; `test_stale_revision_is_409_and_does_not_overwrite`
catches it.

## 11. API

| Route | Notes |
|---|---|
| `GET /api/v1/style-dna/options` | public — the platform's words, not anyone's data |
| `GET /api/v1/me/style-dna` | **200 with `exists: false`** when there is no profile |
| `PATCH /api/v1/me/style-dna` | partial; absent ≠ null ≠ `[]`; 409 on stale revision |
| `DELETE /api/v1/me/style-dna` | idempotent; returns the empty representation |

**Empty is 200, not 404.** A client forced to read absence out of an error cannot tell "no
profile yet" from "session expired", and those need opposite responses. 401 keeps one
meaning.

**No route accepts a customer id** — not in a path, query or body.
`test_no_route_accepts_a_customer_id` walks the route table and asserts it, because this is
exactly the resource where an unverified id gets overlooked and the consequence here is
somebody's measurements.

OpenAPI regenerated: **2 new paths, no existing path changed**.

## 12. My Style page

The accepted five-section structure is preserved; the `NotBuiltState` is gone because it is
now false. No router, design system, navigation, footer, Home, Brands, Shop or Saved change.

- **One request round on load** — options, profile and brands in parallel. Not one request
  per preference, and no catalogue fetch.
- **A three-state chip**: unset → like → avoid → unset. Returning to unset matters as much
  as the other two; "no opinion" is not "I avoid it". `aria-pressed` plus a spoken label, and
  "avoided" is marked by a dashed border **and** a strikethrough so it survives greyscale.
- **"Set by you"** on every value, true today by database constraint.
- **Completeness is a count** — "3 of 5 sections contain preferences". An E2E test greps the
  rendered page for any digit followed by `%` and for the words "strength" and "confidence".

## 13. Dido

Capability copy only. Four lines read "Not built" and were true until a customer could
record those things; they now read **"Stored, not yet applied"**, which is the other true
thing — Dido uses none of it. The disclosure rule cuts both ways: an unbuilt feature must say
so, and a built one must stop saying so. No conversation-engine change, no recommendation,
no scoring.

## 14. Migration — `a9f3e26b104c`

Additive only; no existing table, column, constraint or row touched. The migration verifies
its own claim **inside the transaction**: the seven tables must exist, must be **empty**
(a non-empty new table would mean it fabricated customer preferences), and the accepted
domain tables must still be present.

Round trip verified on a scratch database: `upgrade → 7 tables`, `downgrade → 0 tables`,
`upgrade` again, each with the exit code checked.

### Applied to staging on PostgreSQL

| | before | after |
|---|---|---|
| products / variants / brands / looks / look_items | 6 / 63 / 2 / 4 / 10 | **identical** |
| saved_looks / favorite_products / favorite_brands | 1 / 2 / 1 | **identical** |
| orders / customers | 2 / 14 | **identical** |
| catalogue md5 (sku + price, every variant) | `093e07688e9b342aa932c20192f974e2` | **identical** |
| brand md5 (slug + ownership + publication) | `540e23bcefb0d8902755f99c9b8bf438` | **identical** |
| base tables | 27 | 34 (+7) |
| rows in the seven new tables | — | **0** |

> **Rollback destroys customer style data and it is NOT reconstructible.** Unlike the brand
> association, which could be rebuilt from the registry, this was typed by people about
> themselves. There is no source to re-derive it from. Export the seven tables first if any
> customer has used the feature. Stated in the migration docstring rather than left to be
> discovered.

## 15. Verification

| Check | Result |
|---|---|
| Backend `pytest -q` | **770 passed, 2 skipped** (was 701) |
| Consumer unit tests | **54 passed** (was 26) |
| `npm run build` (`tsc -b && vite build`) | exit 0 |
| Mutation testing | **82 run, 82 detected, 0 survived, 0 inconclusive** |
| Browser E2E, Style DNA | **48 passed, 0 failed** — 16 tests × Chromium, WebKit, Mobile Safari |
| Browser E2E, Style DNA + rendering | **219 passed, 0 failed** after the signed-out fix |
| Browser E2E, **full suite** | **528 passed, 1 failed, 1 flaky** — see below |
| OpenAPI | regenerated, 2 new paths, no existing path changed |
| Governance (`controller_validate.py`) | PASS, 0 errors |
| Brand drift | `BRAND_PACKAGE_NO_DRIFT` |
| Packaged assets | `PACKAGED_BRAND_ASSETS_VERIFIED` |
| Firefox | **NOT RUN** — `browserType.launch: spawn UNKNOWN`. Not claimed |

### The one full-suite failure was the known media limiter, not this phase

The full browser run finished **528 passed, 1 failed, 1 flaky**. The failure was in the
**existing Saved suite** — `save a product and a brand, and they persist across a refresh`,
Chromium only — and it **passes 9 of 9 in isolation**.

Diagnosed from the API log rather than assumed: **109 rate-limit refusals**, of which the top
entries are all static product media under `/api/v1/media/assets/...`, with six
`/me/saved/state` refusals as collateral. That is the already-recorded architectural finding
that **product media shares the general API limiter**, which this phase was not scoped to fix
and did not.

**The limiter was not raised and no assertion was weakened.** The suite is simply larger now —
this phase added 16 tests across three engines — which brings the shared budget closer to its
edge. The flaky Style DNA test (`a chip cycles like, avoid, unset`, Chromium) passed on retry
and is reported as flaky rather than folded into the pass count.

### Three defects in my own tests, found and fixed

Worth recording because each one passed while proving nothing:

1. **`save()` waited for text containing `"saved"`** — and the pre-save status reads *"You
   have un**saved** changes."*, which contains it. The wait matched instantly and every test
   raced ahead of the request it was meant to wait for. It surfaced as an intermittent
   failure in the longest test and as silence everywhere else. A substring assertion on a
   status line is only as good as the other strings that line can hold.
2. **A page read before the route chunk rendered** — `innerText` straight after `goto`
   asserted against an empty shell.
3. **A case-sensitive assertion against uppercased CSS** — the Dido state column is
   `text-transform: uppercase` and `innerText` reports text **as rendered**. The assertion
   failed on all three engines while the copy was perfectly correct: it was testing the
   stylesheet, not the sentence.

### A regression the repository's own test caught

`rendering.spec.ts` asserts that `/my-style` renders at least 40 elements -- a floor
deliberately set to catch a stub rather than a thin page. The first version of this phase
failed it on all three engines, and the test was right.

The page it replaced listed all five sections and their signals **to everyone**, and that
was its value: you could see what DEDUNET would ask before deciding whether to tell it.
Replacing that with a bare sign-in panel was a real downgrade -- *"sign in to find out what
we want to know about you"* is a worse offer than the shell it replaced.

Fixed on the product side rather than by lowering the floor: a signed-out visitor now sees
the five sections read-only, driven by the real server vocabulary. The options endpoint is
public precisely because these are the platform's words rather than anybody's data, which is
what makes it possible without a session. Re-run: **219 passed, 0 failed** across the three
engines.

### A mutation that survived, and what was done about it

`M84` was first registered against the explicit child-row deletion in `delete_profile`. It
**survived** — the ORM relationship cascade already removes those rows, so that line is
defence in depth for a database without FK enforcement, not a guard. Registering it as a
guard would have overstated what is tested, so it was **retargeted** at the explicit-only
CHECK constraint, which is load-bearing. The line itself was kept.

## 16. Deployment provenance — the gate, run before any human test

`OPS-GATE-001`, and it earned its place immediately: **the first run failed.**

`docker compose build` reported success through a `| tail` that swallowed the exit code, the
web image was in fact unchanged from 30 September, `up -d` recreated from that stale image,
and the deployed artifact contained no Style DNA at all. The build had failed on three real
TypeScript errors. **Nothing except the gate would have caught it** — the containers were
healthy, the API was correct, and a human would have been asked to test a six-week-old page
for the second time in two phases.

After the fix:

| Gate | Result |
|---|---|
| 1 — exclusive port ownership | 1 container, `dedunet-staging-web-1` |
| 2 — access-log probe via `http://10.0.0.2:13080` | **reached that container** |
| 3 — artifact identity | host `ETag "6ac6d720-7af"`, entry `index-BG8WaqiC.js`, **matching the container's own file** |
| 4 — image vs source | image built 2026-10-07T23:34Z, after commit `dc1713e` |
| 5 — the artifact contains this phase | `MyStylePage-BXkw0Rwy.js` present, `style-dna` referenced |

### Safety after deployment

| Check | Result |
|---|---|
| Commerce mode | `BRAND_PREVIEW_MODE`, `purchasable: false`, `public_commerce_enabled: false` |
| Source Tee | **7200 minor units = €72.00**, `sellable=false`, `NON_PURCHASABLE` |
| Cart add | refused **409** |
| Document security headers | 4 of 4 on `/` and on `/my-style` |
| `/api/` | keeps its stricter `Referrer-Policy: no-referrer` |
| Multi-brand | DEDUNET 5 products, fixture 0 — unchanged |

## 17. Known limitations

- **Nothing uses the profile.** Dido does not read it, the catalogue does not filter or rank
  on it, and no recommendation exists. Stored and applied are different states and only the
  first is true.
- **No cross-brand or cross-system size conversion**, deliberately. A customer who knows two
  systems must state both.
- **Fit is per garment category, not per garment type.** "Tops" is answerable reliably;
  "mid-weight knitwear" is answerable only guessingly.
- **The size editor shows one system at a time** per category. Both stored systems are
  listed beneath, but editing the second needs a switch. Twenty-four inputs on a phone was
  the alternative.
- **Brand preferences are limited to brands that exist**, which today means one real brand.
- **No reordering, no profile export beyond the existing account data export, no admin
  view** (the last deliberately).
- **Firefox is NOT RUN**, unchanged from previous phases.
- **Deployment provenance is still a manual gate** — `R-019` remains open on the automation.

## 18. Not started

Saved inference, browsing inference, LLM profile generation, Dido intelligence,
recommendation scoring, outfit generation, fashion RAG, weather integration, a dress-code
engine, cross-brand size recommendation, merchant SaaS, payments, public commerce. None of
these has a schema, an endpoint, a stub or a flag.

`PUBLIC_COMMERCIAL_LAUNCH` remains **BLOCKED**.

## 19. Outstanding

**Physical-iPhone Style DNA acceptance.** Sign in, open My Style, set explicit preferences,
save, refresh, confirm persistence, close and reopen Safari, confirm persistence again, edit
a preference, disable personalisation, confirm the values remain, re-enable, delete Style
DNA, confirm the profile is empty, and confirm Saved content is intact.

No automated result in this phase substitutes for it, and none is offered as doing so.
