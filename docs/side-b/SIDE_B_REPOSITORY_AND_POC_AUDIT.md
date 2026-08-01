# Side B Repository and PoC Audit

- Artifact ID: SB-AR-B2-001
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: complete repository inventory; all PoC source/manifests; SB-EV-BOOT-001 through SB-EV-BOOT-004
- Acceptance criteria: states what exists, what checks prove, what failed, what is absent, and security/privacy/runtime limitations without production overclaim.
- Validation procedure/result: full-file inspection plus configured check execution and code-risk review; SELF-VALIDATED.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-001_environment_and_setup.md` through `SB-EV-BOOT-004_docker_checks.md`
- Readiness status: SELF-VALIDATED
- Downstream consumer: controller G0 review; B1-B4/B19/B20 planning
- Remaining risks/next action: runtime attribution and mobile build remain blocked; address only in the next approved B2 increment.

## Repository integrity

The pack contains binding Markdown sources, controller prompts, two agent definitions, an empty controller-owned shared record, and a single PoC. The machine-readable Side B book is present and readable; PDF/DOCX copies were inventoried but not treated as machine sources. There was no Git repository/history, no existing Side B workspace, evidence, handoff, release, SBOM, lockfile for Python, or accepted incoming business contract.

## What the PoC actually proves

- Python modules compile.
- After pinned Python dependencies are installed, four configured API tests pass: health, minimum catalog count/origin fixture, budget ceiling, and unknown-SKU rejection.
- The validator accepts three JSON products containing nine globally unique SKUs.
- Docker can build the API and static Nginx images.
- Source inspection confirms web and Expo source target the same `/api/v1/products` contract.
- The stylist is deterministic local code and does not call an LLM/provider.

These are local/sample/software facts only. Docker runtime for this checkout was not proven because another checkout owns ports 8000/3000. Mobile dependencies do not install, so no mobile compile/build/device claim is valid.

## What the PoC does not prove

No real product, cotton composition, Egypt origin, stock, price, image rights, accessibility, tax, customs, merchant/importer, invoice, payment, order persistence, stock reservation, warehouse, carrier, return/refund, identity/RBAC/MFA, privacy rights, consent, analytics reconciliation, cloud, secrets, backup/restore, monitoring, incident response, load, vulnerability status, app-store eligibility, or production transaction has evidence.

## Test/build coverage gaps

The existing suite has no positive quote, insufficient-stock, duplicate request SKU, rounding, free-shipping boundary, country eligibility, product-detail, admin auth/upsert, duplicate product ID/slug, malformed JSON, zero-stock stylist, CORS, rate limit, XSS, accessibility, browser, mobile, integration, concurrency, performance, or security tests. CI only installs Python requirements and runs `pytest -q`; it omits the provided validator and every other component.

## Security/privacy/runtime findings

1. `ADMIN_API_TOKEN` defaults to `change-me`; there is no production startup guard, identity, RBAC, MFA, token rotation, or privileged audit.
2. Storefront catalog and rationale data are interpolated into `innerHTML`; product fields can therefore become a stored-XSS path. CSP/security headers are not configured.
3. `image_url` accepts `HttpUrl | str`, weakening URL validation.
4. JSON writes are not atomic database transactions; stock is a mutable number, with no ledger/reservation/idempotency/recovery model.
5. Money uses binary floating point and the quote explicitly omits VAT/customs/payment/carrier rules. Destination is only a two-character string.
6. The recommender filters active/budget but not actual variant availability; a zero-stock product may be recommended.
7. Logs, metrics, traces, alerting, backups, recovery, secret storage, dependency scanning, and incident workflows are absent.
8. Placeholder product content says `100% cotton`, `Made in Egypt`, and stock/price figures without linked evidence; public display could create false claims.
9. Mobile dependency resolution is broken and bundle identifiers remain `com.example.*`.
10. Local Python validation used user-installed Python 3.14 packages, whereas CI/Docker specify Python 3.12; an isolated reproducible developer environment was not established.

## Architecture disposition

Retain the PoC as a learning fixture. The next production-oriented design should be a modular monolith with PostgreSQL transactions, versioned contracts, admin approval/audit, server-authoritative minor-unit money, inventory ledger/reservations, hosted payment later, integration adapters, and observable failure recovery. Provider selection, live checkout, market rules, and broad UI work wait for accepted Side A inputs. Mobile and broad AI remain out of the first sellable slice.
