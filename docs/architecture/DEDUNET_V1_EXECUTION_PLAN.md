# DEDUNET V1 — Phased execution plan

| Control | Value |
|---|---|
| Artifact ID | ARCH-P1-002 |
| Version | 1.0 |
| Date | 2026-08-24 |
| Owner | Technical lead (successor agent) |
| Status | **PROPOSED** |
| Baseline | `41cee4c` |
| Related | `ADR-0002`, `DEDUNET_V1_TARGET_DOMAIN_ARCHITECTURE.md` |

---

## 0. Standing rules for every phase

A phase is complete when **all** of these hold, and not before.

```
1. acceptance criteria written BEFORE implementation
2. implemented
3. new tests, each demonstrated to fail without the change
4. guard mutations added for every new safety guard, each DETECTED
5. full backend suite green, count reconciled against the previous phase
6. mobile suite + tsc green where the phase touches mobile
7. security regression: tenant isolation, validation, rate limiting, XSS discipline
8. every previously passed acceptance state still passes
9. documentation updated in the same commit as the behaviour
10. evidence written to evidence/<phase>/
11. focused commits, one concern each
12. phase report in the mandated format, with NOT TESTED stated as NOT TESTED
```

**Rule 5 exists because a growing test count is not evidence.** Every phase must state its
delta and explain it, the way the team-acceptance review explained `301 → 307`. A count that
moves without an explanation is a weakened test until proven otherwise.

**Rule 8 is the one that protects the inheritance.** Local team acceptance and Android native
preview acceptance are passed states with records in `evidence/team-acceptance/`. A phase that
would invalidate either is blocked, not permitted to proceed with a note.

**iPhone mobile web is *not* on that list**, deliberately. A brief asserts it passed; the
repository records no such acceptance (**CONFLICT-011**). Rule 8 protects states that can be
pointed at, and this one cannot — so it must be re-established by a human, not carried forward
as though it had been. Treating an assertion as an inherited pass is how a readiness matrix
ends up with an entry nobody can reconstruct.

---

## 1. Phase ledger

| # | Phase | Depends on | Primary risk |
|---|---|---|---|
| 0 | Successor takeover + baseline preservation | — | agent acts before understanding state |
| 1 | Product repositioning + target domain architecture | 0 | architecture written as a wish list |
| 2 | Design system + website foundation | 1 | a redesign that regresses the mode disclosures |
| 3 | Consumer fashion platform (pages, discover, saved) | 2 | catalogue re-emerges as the product |
| 4 | Multi-brand marketplace domain | 1 | `Brand` retrofit over an unbranded `Product` |
| 5 | Merchant SaaS + multi-tenancy | 4 | **cross-tenant read. The programme's worst credible defect** |
| 6 | Style DNA | 1 | collecting personal data with no consent basis |
| 7 | Dido conversational experience | 6 | a chat bubble instead of a product |
| 8 | Recommendation engine | 6, 4 | LLM ranking creeping in through the back door |
| 9 | Outfit engine | 8 | looks that are lists, not outfits |
| 10 | AI orchestration + fashion knowledge | 9 | the model originating facts |
| 11 | Events, automation, notifications | 5 | double-send, double-charge |
| 12 | Security hardening | 5, 11 | hardening that breaks local staging |
| 13 | Performance + caching | 12 | caching private data publicly |
| 14 | Observability | 12 | logging personal data |
| 15 | CI/CD + deployment architecture | 12 | **blocked: no Git remote (L8)** |
| 16 | Privacy + governance | 6, 14 | style data treated as non-personal |
| 17 | Full regression | 2–16 | — |
| 18 | Human acceptance | 17 | automated green reported as human-tested |
| 19 | Production-readiness closure | 18 | claiming readiness for unevidenced items |

---

## 2. Acceptance criteria per phase

Abbreviated to the criteria that decide pass or fail. Each phase expands these before it
starts.

### Phase 2 — Design system + website foundation
- A component library with explicit states: loading, empty, success, partial, offline,
  error, unauthorized, forbidden, rate-limited.
- The mode disclosure, the purchase refusal and the mode-derived orders copy survive the
  redesign **with their tests unchanged**. If a test needs rewriting to accommodate the new
  markup, the rewrite is reviewed as a potential weakening.
- Keyboard navigation, focus indication, contrast and reduced-motion verified.
- `NOT a regression`: no `innerHTML` anywhere; the existing assertion still passes.

### Phase 3 — Consumer fashion platform
- Home, Discover, Looks, Look detail, Brands, Brand detail, Shop, Search, Product detail,
  Saved, Account, My Style, Orders, plus the legal set.
- Dido is the primary route. The catalogue is reachable, not dominant.
- Every page has a defined empty and error state. No "Load failed".

### Phase 4 — Multi-brand marketplace
- `Brand` first-class; `Product.brand_id` `NOT NULL` after backfill.
- Three brand models supported: connected, hosted, curated.
- `CommerceRoute` typed and enforced server-side.
- Availability on external/referral routes carries `last_checked_at` and a confidence, and
  **no client renders it as a fact**.

### Phase 5 — Merchant SaaS + multi-tenancy
- `organization_id` on every merchant-owned table, `NOT NULL`, FK'd, after the four-step
  migration in the architecture §6.
- **Tenant isolation test category exists** and every merchant endpoint has a
  two-organization test asserting 404.
- A tenant id supplied by a client is never trusted. A test proves it is ignored.
- Entitlements enforced server-side; a client-side flag grants nothing.

### Phase 6 — Style DNA
- Consent recorded before any style data is stored.
- `MY STYLE` exposes view, edit, delete, reset and opt-out. All five work.
- Deleting personalization deletes it — a test asserts the rows are gone, not flagged.

### Phase 7 — Dido
- A distinct character surface, not a chat bubble.
- Ten animation states with a reduced-motion fallback that is not "no animation and no
  status" — screen-reader status text is required.
- Degradation path verified with the provider disabled.

### Phase 8 — Recommendation engine
- Explicit weighted scoring, configurable, **versioned onto every `Recommendation` row**.
- A test asserts that no ranking decision reads an LLM response.
- Reproducibility: the same request and the same version produce the same ranking.

### Phase 9 — Outfit engine
- `Look` + `LookItem`; compatibility validation before presentation.
- Each of the six conversational modifications has a test proving it changes *only* what it
  should: "not the jacket" replaces one slot and holds the other slots identical.

### Phase 10 — AI orchestration + fashion knowledge
- Structured output schema-validated; an invalid model response is rejected, not repaired.
- Claim class enforced: no heuristic rendered as fact.
- A test asserts the model cannot cause a write.

### Phase 11 — Events + automation
- Idempotency keys on every automation and webhook.
- Replay of the same event produces one effect. A test proves it.
- Dead-letter path exists and is observable.

### Phase 12 — Security hardening
- Full §57 case list: injection, IDOR, cross-tenant, XSS, SSRF, path traversal, oversized
  payload, malformed JSON, forged/expired token, duplicate checkout, forged webhook,
  malicious redirect and product URLs.
- Security headers added **without breaking local staging** — the acceptance script still
  runs end to end afterwards.

### Phase 13–14 — Performance, caching, observability
- No private data in a public cache. Cache keys include tenant and user where applicable.
- Structured logs with correlation IDs; a test asserts no password, token, card or
  unnecessary personal data is logged.

### Phase 15 — CI/CD
- **BLOCKED on L8.** There is no Git remote, so `.github/workflows/ci.yml` has never
  executed. CI can be authored and validated locally; a green pipeline may not be claimed.
  Closing this is CONFLICT-010, an owner decision requiring a secret and personal-data
  review first.

### Phase 16 — Privacy + governance
- Style profile treated as personal data throughout.
- Export, deletion, opt-out, retention and cookie consent all implemented and tested.

### Phase 17–19 — Regression, human acceptance, closure
- Full battery re-executed and reconciled.
- Human acceptance on Chrome, Edge, physical iPhone Safari, Android emulator.
- **iOS native remains NOT TESTED** — Apple Developer membership is deferred for budget.
  This must be reported as `NOT TESTED`, never inferred from the Android result.

---

## 3. Standing blockers

Carried from the readiness decision and the takeover report. None is closed by engineering
in this repository.

| Blocker | Blocks | Owner |
|---|---|---|
| No Git remote (L8) | CI, collaboration, off-machine copy of all verified work | owner — CONFLICT-010 |
| Apple Developer membership | iOS native build and acceptance | owner — budget |
| Brand legal clearance | public launch; **enlarged** by becoming a marketplace | external counsel |
| Risk-owner acceptance | formal residual-risk acceptance | four named humans, all `PENDING` |
| Process-local rate limiting (L7) | multi-replica hosted deployment | engineering, Phase 12+ |
| No hosted infrastructure | hosted staging, production | owner — budget |
| No LLM provider | Dido's language surface; the pipeline is testable without it | owner — budget |
| Real inventory, fulfilment, payment credentials | public commerce | owner |

---

## 4. Two decisions, kept separate

```
DEDUNET_PLATFORM_V1_PRODUCTION_READY   /  _BLOCKED
PUBLIC_COMMERCIAL_LAUNCH_READY         /  _BLOCKED
```

The first is an engineering judgement about the codebase and its evidence. The second is a
business and legal judgement dominated by items no amount of engineering here can close.

**Both are `BLOCKED` at `41cee4c`** and nothing in Phases 0–1 changes either.
