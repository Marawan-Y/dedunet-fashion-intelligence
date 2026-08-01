# Repository Inventory

| Control | Value |
|---|---|
| Artifact ID | SOR-G0-001 |
| Version | 1.0 |
| Owner | Controller / integration lead |
| Gate | G0 |
| Status | SELF-VALIDATED |
| Source inputs | `AGENTS.md`; `.agent/PLANS.md`; supplied filesystem at 2026-08-01 |
| Dependency IDs | None |
| Downstream consumers | Side A intake; Side B intake; Master Execution Plan; gate reviews |

## Purpose and acceptance criteria

This is the immutable-baseline inventory taken before controller reconciliation. It passes when every supplied directory and file is listed, source formats are readable at the level required by `AGENTS.md`, ownership is identified, and limitations are explicit.

## Baseline result

- 34 supplied directories and 59 supplied files were found.
- The workspace is not a Git repository; `git rev-parse --show-toplevel` and `git status --short` both returned `fatal: not a git repository`. Git history therefore cannot be used as integrity evidence.
- Both DOCX references opened as valid ZIP/OOXML containers (21 entries each).
- Both PDF references have valid `%PDF-` headers. They are human references only; their Markdown counterparts are authoritative for machine execution.
- All required Markdown sources and PoC text/code files were readable as UTF-8.
- The only zero-length file is the expected Python package marker `platform/poc/backend/app/__init__.py`.
- No pre-existing Side A, Side B, evidence, or outgoing-handoff artifacts were present.

## Directory inventory

```text
.
|-- .agent/
|-- .codex/
|   `-- agents/
|-- docs/
|   |-- side-a/
|   |-- side-b/
|   |-- source/
|   `-- system-of-record/
|-- evidence/
|   |-- side-a/
|   `-- side-b/
|-- handoffs/
|   |-- incoming/
|   |   |-- side-a/
|   |   `-- side-b/
|   `-- outgoing/
|       |-- side-a/
|       `-- side-b/
|-- platform/
|   `-- poc/
|       |-- .github/
|       |   `-- workflows/
|       |-- backend/
|       |   |-- app/
|       |   |-- data/
|       |   `-- tests/
|       |-- docs/
|       |-- mobile/
|       |-- scripts/
|       `-- storefront/
`-- prompts/
```

## File inventory and classification

| Path | Purpose | Owner | Format | Freshness signal | Parsing / integrity note |
|---|---|---|---|---|---|
| `AGENTS.md` | Repository operating rules | Controller policy | Markdown | Supplied baseline | Read completely; binding |
| `README_CODEX_SETUP.md` | Pack setup and operator guidance | Controller reference | Markdown | Supplied baseline | Readable |
| `.agent/PLANS.md` | ExecPlan standard | Controller policy | Markdown | Supplied baseline | Read completely; binding |
| `.codex/config.toml` | Enables two concurrent custom agents | Controller configuration | TOML | Supplied baseline | Parsed as text |
| `.codex/agents/side-a-business.toml` | Side A custom-agent definition | Side A configuration | TOML | Supplied baseline | Name resolves to `side_a_business` |
| `.codex/agents/side-b-platform.toml` | Side B custom-agent definition | Side B configuration | TOML | Supplied baseline | Name resolves to `side_b_platform` |
| `docs/source/Shared_Cross_Team_Agent_Interface_Contract.md` | Cross-side source-of-truth and handoff contract | Immutable shared source | Markdown | Version embedded in source pack | Read completely; SHA-256 `76C92888108F302CAB13975B336B35420FE9AB0E3EE61DA42AC3E7A917685C37` |
| `docs/source/Side_A_Business_Product_Brand_Marketing_Agent_Execution_Book.docx` | Side A human reference | Immutable source | DOCX | Version 1.0, 2026-08-01 | Valid OOXML, 21 entries; Markdown copy is machine authority |
| `docs/source/Side_A_Business_Product_Brand_Marketing_Agent_Execution_Book.pdf` | Side A human reference | Immutable source | PDF | Version 1.0, 2026-08-01 | Valid PDF header; Markdown copy is machine authority |
| `docs/source/Side_A_Business_Product_Brand_Marketing_Agent_System_Prompt.md` | Side A binding role prompt | Immutable source | Markdown | Supplied baseline | Read completely |
| `docs/source/Side_A_Execution_Book.md` | Side A A1-A18 execution authority | Immutable source | Markdown | Version 1.0, 2026-08-01 | Read completely; SHA-256 `1E00D077B472875D5CB18849C14F921BD2A109FA0B7BC1A3447B79F5350087FB` |
| `docs/source/Side_B_Execution_Book.md` | Side B B1-B22 execution authority | Immutable source | Markdown | Version 1.0, 2026-08-01 | Read completely; SHA-256 `9AA61BA11FFC382E772DDF9AC59F4DD1F63B91D32C048BE3CE2CBB3EFB0DE554` |
| `docs/source/Side_B_Platform_Software_AI_Apps_Agent_Execution_Book.docx` | Side B human reference | Immutable source | DOCX | Version 1.0, 2026-08-01 | Valid OOXML, 21 entries; Markdown copy is machine authority |
| `docs/source/Side_B_Platform_Software_AI_Apps_Agent_Execution_Book.pdf` | Side B human reference | Immutable source | PDF | Version 1.0, 2026-08-01 | Valid PDF header; Markdown copy is machine authority |
| `docs/source/Side_B_Platform_Software_AI_Apps_Agent_System_Prompt.md` | Side B binding role prompt | Immutable source | Markdown | Supplied baseline | Read completely |
| `docs/system-of-record/README.md` | Shared-write ownership marker | Controller | Markdown | Supplied baseline | Readable |
| `platform/poc/.env.example` | Local PoC configuration example | Side B | dotenv | Supplied baseline | Contains unsafe default token by design; not production configuration |
| `platform/poc/.gitignore` | PoC ignore rules | Side B | Git ignore text | Supplied baseline | Readable; no repository initialized |
| `platform/poc/docker-compose.yml` | Local API/storefront composition | Side B | YAML | Supplied baseline | Requires Docker; local-only |
| `platform/poc/Makefile` | Setup/test/validation commands | Side B | Makefile | Supplied baseline | Unix-oriented `cp`/`test` commands may not run natively in PowerShell |
| `platform/poc/README.md` | PoC runbook and limitations | Side B | Markdown | Supplied baseline | Read completely; explicitly non-production |
| `platform/poc/.github/workflows/ci.yml` | Backend CI definition | Side B | YAML | Supplied baseline | Python 3.12 + pytest only |
| `platform/poc/backend/Dockerfile` | FastAPI image build | Side B | Dockerfile | Supplied baseline | Requires Docker/network or cached layers |
| `platform/poc/backend/requirements.txt` | Pinned Python dependencies | Side B | Text | Supplied baseline | Six dependency lines; install may require network/cache |
| `platform/poc/backend/app/__init__.py` | Python package marker | Side B | Python | Supplied baseline | Intentionally zero length |
| `platform/poc/backend/app/ai_stylist.py` | Deterministic PoC recommender | Side B | Python | PoC v0.1.0 | Rule-based, not generative AI |
| `platform/poc/backend/app/catalog.py` | JSON catalog repository | Side B | Python | PoC v0.1.0 | File persistence; not transactional |
| `platform/poc/backend/app/config.py` | Environment-backed settings | Side B | Python | PoC v0.1.0 | Defaults are development-only |
| `platform/poc/backend/app/main.py` | API routes and quote logic | Side B | Python | PoC v0.1.0 | Quote excludes VAT/customs/payment/carrier truth |
| `platform/poc/backend/app/schemas.py` | Pydantic PoC schemas | Side B | Python | PoC v0.1.0 | Narrow sample schema |
| `platform/poc/backend/data/products.json` | Three synthetic/sample products and nine SKUs | Side A truth sample / Side B storage | JSON | Supplied PoC sample | Unsupported material/origin/stock/price claims; not business truth |
| `platform/poc/backend/tests/test_api.py` | Four backend tests | Side B | Python | Supplied PoC baseline | Health, catalog, budget, unknown-SKU paths only |
| `platform/poc/docs/brand_asset_manifest.csv` | Empty asset template | Side A input / Side B contract | CSV | Supplied template | Header only |
| `platform/poc/docs/cross_team_handoff_checklist.md` | Minimum cross-team checklist | Shared reference | Markdown | Supplied baseline | Not a formal handoff envelope by itself |
| `platform/poc/docs/decision_log.md` | Example decision-log row | Shared reference | Markdown | Placeholder date | Template, not an approved decision |
| `platform/poc/docs/product_master_template.csv` | Draft product import fields | Side A input / Side B schema | CSV | Supplied template | Header only; incomplete for launch truth |
| `platform/poc/docs/variant_master_template.csv` | Draft variant import fields | Side A input / Side B schema | CSV | Supplied template | Header only; incomplete for launch truth |
| `platform/poc/mobile/app.json` | Expo PoC app metadata | Side B | JSON | v0.1.0 | Example bundle IDs; not store-ready |
| `platform/poc/mobile/App.tsx` | Mobile catalog consumer | Side B | TypeScript/TSX | PoC v0.1.0 | Source only; no installed dependencies initially |
| `platform/poc/mobile/package.json` | Expo dependency snapshot | Side B | JSON | v0.1.0 | No lockfile or build/typecheck script supplied |
| `platform/poc/mobile/README.md` | Mobile local-run notes | Side B | Markdown | Supplied baseline | Requires environment-specific API URL |
| `platform/poc/scripts/validate_product_data.py` | Product-schema/SKU validator | Side B | Python | Supplied baseline | Requires Python dependencies |
| `platform/poc/storefront/app.js` | Static catalog/stylist client | Side B | JavaScript | PoC v0.1.0 | API port inferred from browser host |
| `platform/poc/storefront/Dockerfile` | Nginx static image | Side B | Dockerfile | Supplied baseline | Requires Docker/network or cached layer |
| `platform/poc/storefront/index.html` | Static PoC storefront | Side B | HTML | Supplied baseline | Contains unsupported customer-facing sample claims |
| `platform/poc/storefront/styles.css` | PoC styling | Side B | CSS | Supplied baseline | Cosmetic only; not design-system evidence |
| `prompts/00_MASTER_ORCHESTRATOR_BOOTSTRAP.md` | Controller bootstrap procedure | Controller | Markdown | Supplied baseline | Current execution request mirrors it |
| `prompts/01_CONTINUE_GATE_EXECUTION.md` | Gate continuation procedure | Controller | Markdown | Supplied baseline | Readable |
| `prompts/02_GATE_REVIEW_AND_RELEASE_DECISION.md` | Independent gate-review procedure | Controller | Markdown | Supplied baseline | Readable |
| `prompts/03_MANUAL_SIDE_A_START.md` | Manual Side A fallback prompt | Side A | Markdown | Supplied baseline | Readable |
| `prompts/04_MANUAL_SIDE_B_START.md` | Manual Side B fallback prompt | Side B | Markdown | Supplied baseline | Readable |

## Contradictions, duplicates, and stale signals

1. The DOCX/PDF books duplicate the authoritative Markdown books by design; no conflict is asserted without a semantic comparison. Execution uses Markdown as instructed.
2. The PoC presents “Egyptian cotton,” `100% cotton`, `Made in Egypt`, prices, and stock as sample values without evidence. These are rejected as business truth and may only be used as synthetic fixtures.
3. The PoC README says “real product data” in its demo language, but no product, supplier, factory, lab, QC, price, stock, or rights evidence exists. The safe interpretation is representative sample data.
4. The repository has no Git history even though setup instructions recommend initializing Git. This is an integrity and rollback limitation, not proof of corruption.

## Validation procedure and result

Commands run from the repository root:

```powershell
Get-ChildItem -Force -Recurse
Get-FileHash -Algorithm SHA256 docs/source/*
git rev-parse --show-toplevel
git status --short
```

DOCX containers were opened with `System.IO.Compression.ZipFile`; PDF first bytes were checked for `%PDF-`. Result: filesystem inventory and source readability passed; provenance/history validation is blocked by the absence of Git metadata.

## Remaining risks and next action

- Risk: no immutable VCS baseline or rollback point. Owner: human repository owner. Next action: initialize and protect a repository after reviewing generated files.
- Risk: source binary/Markdown semantic parity was not proven. Safe fallback: treat Markdown as authority exactly as `AGENTS.md` requires.
- Next action: reconcile both agent intakes and register all generated artifacts separately from this supplied baseline.
