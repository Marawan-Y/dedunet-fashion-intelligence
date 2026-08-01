# Authoritative Money Representation Contract

- Artifact ID: SB-AR-B3-003
- Version: 2.0.0 (supersedes 1.0.0)
- Owner: Side B Platform Lead; the approved business amount remains Side A/Finance-owned
- Source inputs/dependencies: DEC-006; HO-A-B-001 BPC-A-020..023; controller M1 task E
- Acceptance criteria: authoritative monetary storage and calculation use integer minor units **everywhere**, not only in the candidate record; currency, validity, tax class, approval and evidence are explicit; binary float is rejected at every boundary; each rule is proven by a test that fails when its guard is removed.
- Validation procedure/result: 24 money tests passing; mutations M14–M19 all detected; runtime confirmation over HTTP in an attributed container. AUTOMATED-TESTED.
- Evidence path: `evidence/side-b/g1/SB-EV-G1-006_money_integrity_red_green.md`; `evidence/side-b/g1/SB-EV-G1-003_guard_mutation_matrix.md`
- Readiness status: AUTOMATED-TESTED
- Downstream consumer: Side A Finance; B3 schema; future B11 checkout and B16 reporting
- Remaining risks/next action: no real approved amount, tax treatment, price validity or finance approval exists; checkout stays disabled. Rounding policy for VAT, discounts, partial refunds, multi-currency and payouts is **not** designed (SB-RISK-015).

## Change from v1.0.0

v1.0.0 asserted the integer-minor-unit rule for the *candidate* `PriceRecord` only. A
re-audit found that the legacy catalog, quote, stylist, configuration and client paths
still carried binary floats end to end. v2.0.0 states and enforces the rule across the
whole system. v1.0.0 also cited an evidence file that did not exist; that is corrected.

## Rules

1. **Storage and calculation are integer minor units.** EUR 59.00 is `5900`. Every
   authoritative field is a strict integer: `PriceRecord.gross_minor_units`,
   `Product.price_minor_units`, `OrderQuote.{subtotal,shipping,total}_minor_units`,
   `StylistRecommendation.total_minor_units`,
   `Settings.{default_shipping,free_shipping_threshold}_minor_units`.
2. **Binary float is rejected, never coerced.** `money.to_minor_units` raises
   `FloatMoneyRejected` for any `float` (and for `bool`). It subclasses both `TypeError`
   and `ValueError` so a Pydantic validator returns HTTP 422 rather than a 500.
3. **Conversion is exact or it fails.** A value with more fractional digits than the
   currency permits raises. `59.005` in EUR is an error, not `5901` or `5900`.
   Python's `decimal` module has no `ROUND_UNNECESSARY`, so the check is explicit.
4. **Unknown currency fails closed.** `MINOR_UNIT_EXPONENTS` contains only `EUR` by
   deliberate choice. Adding a currency requires a reviewed exponent decision.
5. **Ingestion never creates a float.** `catalog.py` parses the JSON fixture with
   `json.load(handle, parse_float=Decimal)`, so a decimal literal in the fixture becomes
   a `Decimal` and then an exact integer. `scripts/validate_product_data.py` does the same
   and asserts an exact minor-unit round trip.
6. **Display values are derived, never authoritative.** `price_display`,
   `subtotal_display`, `shipping_display`, `total_display` and `total_display` are
   computed `Decimal` fields rendered from the integer. They are never an arithmetic input.
   Clients format integer minor units with pure integer/string arithmetic — no division,
   no `toFixed`.
7. **Clients never submit or override authoritative totals.** A customer-supplied
   *budget filter* is accepted as `budget_minor_units`, or via the legacy `budget_eur` key
   only as an exact `Decimal`/string/int. This is a discovery filter, not stored money.

## Mapping from a Side A approved amount

Side A may later provide a formally approved decimal amount. The ingestion boundary
converts it exactly to minor units only when the currency exponent is known and the value
carries no excess precision. Approved business `59.00` maps to `gross_minor_units = 5900`,
`currency = EUR`.

Authoritative price records contain:

- `gross_minor_units` — strict positive integer; floats including `59.0` fail validation.
- `currency` — uppercase ISO-4217-style three-letter code.
- `tax_class` — approved server-side reference, never inferred by the client.
- `valid_from` and optional `valid_to` — UTC ordered interval; `valid_from <= now < valid_to`.
- `approved` — must be true for sellable/public activation.
- `approval_evidence_id` — current, in-scope, human/external-verified, non-synthetic record.

## Current state

The candidate record has `price = null`. **EUR 59 remains a rejected, research-only test
point**, not an approved price. The `59.00` / `139.00` / `89.00` values in
`backend/data/products.json` are synthetic sample-fixture values. Live checkout and public
customer totals are disabled.

## Deliberate breaking change

The API no longer emits `price_eur` or `total_eur`. Consumers read `price_minor_units` +
`currency`, and may read the derived `*_display` values. `storefront/app.js` and
`mobile/App.tsx` were updated in the same change. Recorded as SB-DEC-G1-003.

## Proof that the guards are load-bearing

| Guard | Mutation | Result |
|---|---|---|
| `PriceRecord.gross_minor_units` strict integer | M14 | DETECTED |
| `to_minor_units` rejects binary float | M15 | DETECTED |
| catalog `parse_float=Decimal` | M16 | DETECTED |
| `sum_line_totals` integer arithmetic | M17 | DETECTED |
| `sum_line_totals` integer type check | M18 | DETECTED |
| `OrderQuote.subtotal_minor_units` strict integer | M19 | DETECTED |

M17's first version *survived* — a reintroduced float round-trip was invisible at fixture
magnitudes. It was closed by extracting the arithmetic into a pure function and pinning it
with an adversarial case: EUR 0.70 x 3 is exactly `210` minor units, while
`int((70/100) * 3 * 100)` evaluates to `209`. See SB-EV-G1-003.
