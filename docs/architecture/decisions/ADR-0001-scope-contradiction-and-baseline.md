# ADR-0001 — Launch-candidate build mandate vs. repository gate state

| Field | Value |
|---|---|
| Status | DECIDED — Option A, gate override authorized by repository owner 2026-08-01 |
| Date | 2026-08-01 |
| Owner | Principal Engineering Lead / Delivery Controller |
| Supersedes | none |
| Related | `docs/system-of-record/GATE_REGISTER.md`, `ONE_PRODUCT_VERTICAL_SLICE.md`, `MASTER_EXECUTION_PLAN.md`, DEC-001..DEC-012 |

## Context

A master execution prompt directs the build of a complete launch-candidate Fashion Commerce
Platform: 34 subsystems, Android and iOS applications, an operations portal, infrastructure as
code, CI/CD, observability, a full layered test strategy and seeded brand data.

That prompt states the repository already contains authoritative product requirements, system
specifications, architecture documents, ADRs, API contracts, database and event schemas, UI/UX
specifications, infrastructure specifications, security requirements, AI and data specifications,
coding standards, testing strategies, deployment runbooks, operational runbooks, verification
procedures and acceptance criteria, and instructs that these be treated as the source of truth.

## Findings — measured, not assumed

A repository-wide search was executed before any implementation work.

| Claimed authoritative artifact | Instances found |
|---|---|
| Architecture decision records | 0 |
| OpenAPI / Swagger / protobuf contracts | 0 |
| Database schemas, migrations, event schemas | 0 |
| UI/UX specifications, wireframes, design system | 0 |
| Infrastructure as code (Terraform, k8s, Helm) | 0 |
| Deployment and operational runbooks | 0 |
| Coding standards | 0 |

Actual implemented surface: **1,261 lines total.** Eight HTTP endpoints, six of them read-only.
Persistence is two JSON files. The mobile application is an 87-line stub. The storefront is 83
lines of JavaScript. There is no database, authentication, customer identity, cart, order,
checkout, payment, shipping, tax, promotion, return, notification, search, wishlist, review,
support, analytics, CMS, infrastructure or observability layer.

What the repository *does* contain authoritatively is two execution books totalling 5,158 lines,
which specify requirements at the work-package level (A1–A18, B1–B22), plus the shared interface
contract, the governance registers and a proof-of-concept.

**Conclusion: the requirement corpus exists; the derived specification artifacts do not.** They
must be authored as part of the build. The prompt's premise that they can simply be followed is
not satisfied by this repository.

## The contradiction

Two authoritative sources conflict, and the prompt itself designates both as binding.

1. The master prompt orders immediate construction of mobile applications, broad AI features,
   catalog expansion, elaborate infrastructure and a public-capable storefront.
2. The repository's governance — which the prompt instructs be treated as source of truth —
   forbids exactly that scope at the current gate:
   - `GATE_REGISTER.md` records **G0 = NO_GO / BLOCKED** on three human-only criteria: founder/IP
     baseline, named accountable humans, and spending authority. All three remain unsatisfied.
   - `ONE_PRODUCT_VERTICAL_SLICE.md` places mobile, generative AI, additional styles, colours and
     markets, and public launch explicitly **out of scope**.
   - `MASTER_EXECUTION_PLAN.md` §5 lists storefront redesign, final branding, catalog expansion,
     live checkout, provider selection, microservices, Kubernetes and public deployment as
     non-scope until their evidence gates pass.
   - Three launch blockers are **OPEN and unowned**: stored XSS (SB-RISK-003), non-transactional
     inventory (SB-RISK-005) and secrets shipped in the pack (SB-RISK-011).

Under the master prompt §25, "two authoritative requirements irreconcilably conflict" is an
explicit condition for consulting the human owner. Under §19, work may not be marked verified
without executed evidence, and under §22 failures may not be hidden or disabled.

## Additional constraints of record

- The repository is **not under version control**. There is no rollback mechanism other than
  supersession against the pristine sibling pack. The master prompt requires a version-controlled
  repository as deliverable A.
- The executing account reached a **session limit** during the previous cycle, terminating a
  specialist agent mid-correction. Wide parallel delegation is therefore not currently reliable.
- Two field-level corrections issued to the platform lane remain **unapplied**.

## Decision

Deferred to the human owner. Three options were evaluated.

**Option A — Execute the master prompt literally.** Rejected as unsafe. It requires either
inventing the missing specifications as personal preference, which §6 forbids, or asserting
completion of 34 subsystems and two native applications without executable evidence, which §19 and
§22 forbid. It also overrides an unsatisfied gate on the authority of a calendar instruction, which
the shared interface contract prohibits: "No calendar deadline overrides a failed gate."

**Option B — Hold all build work until G0 clears.** Rejected as needlessly idle. G0 is blocked
solely on human governance evidence. Substantial technical work — schema, persistence, domain
services, contracts, tests — is genuinely independent of that evidence and is required under any
scope outcome.

**Option C — Author the missing specifications and build the first end-to-end vertical slice
against them, on fictional data, kept non-public. RECOMMENDED.** This satisfies master prompt §5,
which itself designates the complete admin-to-order-to-fulfilment journey as the first slice. It
respects the gate, because nothing becomes publicly sellable and no external provider is activated.
It produces the ADRs, API contract, database schema, migrations and test suites the repository
lacks, which every later milestone requires regardless of scope decisions. Mobile, broad AI and
production infrastructure remain deferred until their gates or an explicit owner override.

## Owner decision — recorded 2026-08-01

The repository owner was presented with the three options above and selected **Option A: override
the gate and build the full scope**. The owner also authorized initializing local version control.

Per the shared interface contract, a conditional decision taken over a failed gate must record the
authority, the impact and the compensating controls. They are:

- **Authority:** repository owner, via direct instruction in session, 2026-08-01. The owner is the
  same party who remains UNASSIGNED in the governance registers; no separate executive sponsor,
  legal, finance or security owner has been named.
- **Gate bypassed:** G0, which remains failed on founder/IP baseline, named accountable humans and
  spending authority. G1 through G6 remain unsatisfied and are not claimed.
- **Impact accepted by the owner:** work proceeds without named accountable humans, without spend
  authority, and with three launch blockers OPEN and unowned (stored XSS, non-transactional
  inventory, shipped secrets).
- **Compensating controls, applied unilaterally by the engineering lead and not negotiable under
  this override:** the system stays local and non-public; no real customer, payment, supplier or
  personal data is used; no external provider account is activated; every external integration runs
  as a sandbox or contract-compatible mock; no artifact is labelled `VERIFIED` without an executed
  command and preserved output; and no claim of legal, tax, customs, certification, origin,
  material or app-store status is made.

This override changes what is built. It does not change what may be claimed. Statements about
external reality still require external evidence, and none exists in this repository.

## Consequences

- The derived specification set becomes a first-class deliverable rather than an assumed input.
- Delivery claims will use `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `IMPLEMENTED_UNVERIFIED`,
  `VERIFIED` and `EXTERNALLY_PENDING`. No percentage completion will be reported without traceable
  evidence.
- A launch-candidate claim covering all 34 subsystems is not achievable or verifiable in the
  current session. Any such claim would be fabricated.
- If the owner overrides in favour of Option A, this ADR records that the gate was knowingly
  bypassed, who authorized it and on what basis, as the shared interface contract requires for a
  conditional decision.
