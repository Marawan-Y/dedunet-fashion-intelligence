# HANDOFF — SIDE A TO SIDE B — DEDUNET v1

**Handoff ID:** H-A-B-DEDUNET-v1.0  
**Status:** READY FOR DEDUNET PLATFORM INTEGRATION  
**Legal launch status:** BLOCKED PENDING PROFESSIONAL CLEARANCE

## 1. Brand display truth

- Display name: **DEDUNET**
- Status label in admin/config: `PROVISIONAL_NOT_LEGALLY_CLEARED`
- Identity territory: **Material Worth**
- Primary tagline: **Worth, worn.**
- Collection: **First Passage**
- Internal assistant label: **DEDUNET Guide**
- Do not expose DEDU as a public sub-brand.

## 2. Authoritative files

1. `data/brand-prototype/brand-tokens.json`
2. `data/brand-prototype/brand-tokens.css`
3. `data/brand-prototype/font-manifest.json`
4. `data/brand-prototype/navigation.json`
5. `data/brand-prototype/content-copy.json`
6. `data/brand-prototype/product-master.json`
7. `data/brand-prototype/variant-master.csv`
8. `data/brand-prototype/collection-master.csv`
9. `data/brand-prototype/asset-register.csv`
10. `docs/brand-prototype/06_OPEN_RISKS_AND_EXTERNAL_ACTIONS.md`

Where prose and structured data differ, the machine-readable files above are authoritative for platform implementation.

## 3. Assets

- Header/default logo: `assets/brand-prototype/logos/logo-primary.svg`
- Compact navigation/social mark: `assets/brand-prototype/logos/logo-compact.svg`
- Browser icon: `assets/brand-prototype/logos/favicon.svg`
- App icon: `assets/brand-prototype/logos/app-icon.png`
- Dark-field logo: `assets/brand-prototype/logos/logo-reversed.svg`
- Pattern: `assets/brand-prototype/patterns/passage-lines.svg`

## 4. Fonts

- Display: Bodoni Moda 500/600.
- Body/UI: Manrope 400/500/600/700.
- Arabic: IBM Plex Sans Arabic 400/500/600.
- Self-host production subsets; use `font-display: swap`.

## 5. Routes and collection

- `/collections/first-passage`
- `/shop`
- `/about`
- `/journal`
- `/size-guide`
- `/delivery`
- `/returns`
- `/care`
- `/accessibility`
- `/privacy`
- `/terms`
- `/imprint`

## 6. Product seed

Seed exactly five products and 62 variants from the supplied masters. Set:

- `inventory_status = prototype_unavailable`
- `stock_quantity = 0`
- checkout mode = prototype/no-charge
- evidence badge visible on every PDP

## 7. Legal and evidence-safe controls

- Keep the prototype checkout notice visible.
- Never render intended composition or origin as a verified badge.
- Do not publish “Egyptian cotton,” sustainability, ethical-production or certification claims.
- Do not state that DEDUNET is a historically verified weaving goddess.
- Footer/admin should retain `PROVISIONAL_NOT_LEGALLY_CLEARED` outside customer-facing production builds.

## 8. Media behaviour

- Use 4:5 product cards.
- Front-to-back hover allowed only where both assets exist.
- All included media is concept media; retain alt text from `asset-register.csv`.
- Respect reduced-motion settings.

## 9. Acceptance response required from Side B

Return one:

- `ACCEPT`
- `CONDITIONALLY ACCEPT`
- `REJECT`

Include validation results for JSON parsing, asset paths, product/variant counts, unique SKUs, routes, token loading and prototype checkout blocking.
