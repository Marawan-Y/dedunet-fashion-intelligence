# Target Repository Architecture

| Control | Value |
|---|---|
| Artifact ID | ARCH-R0-003 |
| Version | 1.0 |
| Owner | Technical lead |
| Status | SELF-VALIDATED |
| Authority | Manager approval §10, adapted per §10's "document every deviation" |

## Structure

```
Fashion_Commerce_Codex_Multi_Agent_Pack/        <- Git root
├── README.md  Makefile  docker-compose.yml  .env.example
├── .gitignore  .gitattributes  .dockerignore
│
├── .agent/PLANS.md            .codex/{config.toml,agents/}
│
├── apps/
│   ├── web/                   customer storefront (no build step)
│   ├── admin/                 operations portal (no build step)
│   └── mobile/                Expo application — BLOCKED
│
├── services/
│   └── commerce-api/          FastAPI + SQLAlchemy
│       ├── app/{commerce/,...}  migrations/  tests/  data/
│       ├── manage.py  alembic.ini  requirements.txt
│       ├── Dockerfile  docker-entrypoint.sh
│
├── packages/
│   └── contracts/openapi/openapi.json     authoritative API contract
│
├── scripts/{validation/,migration/}
├── docs/{source/,system-of-record/,architecture/,operations/,side-a/,side-b/}
├── evidence/{baseline/,restructuring/,governance/,side-a/,side-b/}
├── handoffs/{incoming/,outgoing/}
└── .github/workflows/ci.yml
```

## Why each boundary exists

**`apps/` separates the three clients.** Web and admin currently share a stylesheet by reaching
across directories, which means neither can be built, deployed or owned independently. After the
split, `apps/admin` owns its own CSS. They may still ship in one nginx image — that is a
*packaging* decision, and packaging is allowed to combine things that source separates. The
reverse is not true.

**`services/commerce-api/` gives the backend a name that describes it.** `platform/poc/backend`
says "proof of concept", which is now false and actively misleading about how much verified
behaviour lives there. The service keeps its migrations, tests and management command together,
because they version with the code, not with the repository.

**`packages/contracts/` gives the API contract one authoritative home.** Today `openapi.json`
lives inside the backend's own docs, so web and mobile have nowhere natural to consume it. One
location plus the existing CI drift check is what stops three hand-maintained copies appearing.

**`scripts/` splits by purpose.** `validation/` holds the executable quality gates; `migration/`
holds one-shot tooling. Both are repository-level because they operate across subsystems.

**`evidence/` stays out of application directories.** Command transcripts are not source, do not
version with a service, and must not be importable.

## Deviations from the approved structure, and why

**1. `data/` is not created at the repository root yet.**
The approved tree lists `data/{seed,fixtures,imports,schemas}`. The only current data files are
`products.json` and `candidate_products.json`, which are the commerce-api's own test fixtures,
SHA-256-guarded by `conftest.py` and asserted by CI. They belong to the service that owns them,
so they stay at `services/commerce-api/data/`.

A root `data/` will be created in M7 for DEDUNET seed and import material, which genuinely is
cross-subsystem. Creating it now would mean an empty directory plus a fixture move that risks the
checksum gate for no benefit during a commit that is required to be behaviour-preserving.

**2. `packages/{brand,shared-types,shared-utils}` are not created yet.**
Empty directories cannot be committed by Git, and inventing placeholder files to hold them open
adds noise. `packages/brand/` is created in M7 when the DEDUNET transformation pipeline produces
its first artifact; `shared-types` and `shared-utils` when a second consumer actually exists.
Creating a shared package with one consumer is how premature abstraction starts.

**3. `tests/` at the root is not created yet.**
All 83 tests currently exercise the commerce-api and legitimately live with it. Root-level
`contract/`, `integration/`, `end-to-end/`, `performance/` and `security/` directories appear when
tests spanning more than one subsystem exist — which happens in M6 (mobile) and M8 (branded
vertical slice). A root `tests/` that only forwards to one service's suite is misdirection.

**4. `infrastructure/` is not populated yet.**
`docker-compose.yml` moves to the root because it composes the whole system and is invoked from
there. `infrastructure/{docker,staging,monitoring,backup}` is populated in M3 and M5 when
staging Compose, backup scripts and monitoring configuration exist. Moving one Compose file into
a four-directory tree today would be structure without content.

Every deviation defers creating a directory until it has real content. None blocks the target
shape; each is scheduled to a specific later milestone.

## Rules this structure enforces

1. An application never imports another application's source.
2. A service owns its own migrations, tests and data fixtures.
3. Contracts have exactly one authoritative copy; consumers read, never fork.
4. Infrastructure and deployment configuration is not application source.
5. Evidence is never written inside an application directory.
6. Runtime artefacts — databases, caches, build output, `.env` — are never tracked.
7. Incoming handoffs are immutable and byte-stable; transformation produces new files elsewhere.
