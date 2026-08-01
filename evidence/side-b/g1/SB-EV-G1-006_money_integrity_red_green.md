# Money Integrity — float path found, RED test written, then fixed (GREEN)

- Artifact ID: SB-EV-G1-006
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: SB-AR-B3-003 money contract; DEC-006; HO-A-B-001 BPC-A-020..023; controller M1 task E
- Acceptance criteria: state honestly whether a float money path existed; if it did, preserve a failing test written *before* the fix, then preserve the passing result after; prove the fix is load-bearing by mutation.
- Validation procedure/result: a float money path **did** exist across the catalog, quote, stylist and configuration paths. Failing tests were written first (exit 2, then exit 1), the path was removed, and the suite is now green. Mutations M14–M19 prove the guards.
- Evidence path: this file
- Readiness status: AUTOMATED-TESTED
- Downstream consumer: Side A Finance; controller M1 review; B11 checkout
- Remaining risks/next action: no approved business amount, tax class, price validity or finance approval exists. The candidate `price` is still `null` and checkout remains disabled. EUR 59 in the sample fixture is a **synthetic fixture value**, not an approved price.

## 1. Finding: a float money path existed

Contrary to the state implied by SB-AR-B3-003 v1.0.0 (which covered only the *candidate* record), the PoC carried binary floats through the entire legacy catalog and quoting path:

| Location | Before | Problem |
|---|---|---|
| `app/schemas.py` `Product.price_eur` | `float = Field(gt=0)` | authoritative price stored as IEEE-754 |
| `app/schemas.py` `OrderQuote.subtotal/shipping/total` | `float` | authoritative totals on the wire as float |
| `app/schemas.py` `StylistRequest.budget_eur` | `float` | client could push an inexact amount |
| `app/schemas.py` `StylistRecommendation.total_eur` | `float` | float total |
| `app/config.py` `default_shipping_eur` | `float(os.getenv(...))` | `float("8.90")` = 8.9000000000000003552713678800500929355621337890625 |
| `app/config.py` `free_shipping_threshold_eur` | `float(...)` | float threshold comparison |
| `app/main.py` quote | `subtotal += product.price_eur * item.quantity` then `round(x, 2)` | float accumulation |
| `app/ai_stylist.py` | `running_total += product.price_eur` | float accumulation |
| `app/catalog.py` | `json.load(handle)` | fixture `59.0` became a binary float at ingestion |
| `storefront/app.js`, `mobile/App.tsx` | `money(product.price_eur)` / `.toFixed(2)` | float on the display path |

So the honest answer to "confirm money handling is integer minor units end to end" was **no** for everything except the candidate `PriceRecord`.

## 2. RED — failing test written before the fix

`platform/poc/backend/tests/test_money_integrity.py` was authored first. Initial run:

```text
WORKING DIRECTORY: ...\platform\poc\backend
COMMAND: python -m pytest -q tests/test_money_integrity.py

=================================== ERRORS ====================================
_______________ ERROR collecting tests/test_money_integrity.py ________________
ImportError while importing test module
'C:\Users\User\Desktop\Claude\Fashion_Commerce_Codex_Multi_Agent_Pack\platform\poc\backend\tests\test_money_integrity.py'.
Traceback:
tests\test_money_integrity.py:30: in <module>
    from app.money import FloatMoneyRejected, from_minor_units, to_minor_units
E   ModuleNotFoundError: No module named 'app.money'
=========================== short test summary info ===========================
ERROR tests/test_money_integrity.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 warning, 1 error in 2.45s
EXIT_CODE: 2
```

Note the path: this RED evidence is attributable to **this** working tree, unlike SB-EV-G1-001.

Second RED stage, after the module existed but before the path was fully removed — four genuine failures, preserved verbatim:

```text
COMMAND: python -m pytest -q -p no:cacheprovider
..F....................F......F.F....                                    [100%]

FAILED tests/test_api.py::test_stylist_recommendation_respects_budget - KeyError: 'total_eur'
FAILED tests/test_money_integrity.py::test_product_schema_rejects_binary_float_price
FAILED tests/test_money_integrity.py::test_quote_totals_are_exact_in_minor_units - assert 0 == 890
FAILED tests/test_money_integrity.py::test_quote_repeated_small_quantities_do_not_accumulate_error - assert 409 == 200
4 failed, 33 passed, 1 warning in 2.86s
EXIT_CODE: 1
```

Two of those four were defects in the *tests*, not the code, and are recorded as such:
- `test_quote_totals_are_exact_in_minor_units` asserted 890 shipping on a 148.00 basket that legitimately crosses the 100.00 free-shipping threshold.
- `test_quote_repeated_small_quantities...` requested quantity 20 of a SKU whose fixture stock is 18, so the 409 was correct behaviour.

Both were corrected to assert the real contract; a new test `test_quote_rejects_quantity_above_fixture_stock` now pins the 409 case explicitly.

## 3. The fix

New module `platform/poc/backend/app/money.py`:

- `FloatMoneyRejected(TypeError, ValueError)` — subclasses `ValueError` so a Pydantic validator turns it into a 422 rather than an unhandled 500.
- `to_minor_units(value, currency, *, already_minor=False)` — accepts `int` / `Decimal` / decimal `str`; **raises on `float` and on `bool`**; raises on unknown currency; raises on excess fractional precision instead of rounding it away (Python's `decimal` has no `ROUND_UNNECESSARY`, so the check is explicit).
- `from_minor_units` / `format_minor_units` — derived display values only.
- `sum_line_totals` — pure integer line arithmetic, rejecting any non-`int` unit price.

Changed:
- `app/catalog.py` parses the fixture with `json.load(handle, parse_float=Decimal)`, so `59.0` never becomes a binary float, and serializes `Decimal` exactly on write.
- `app/schemas.py` — `Product.price_minor_units: int = Field(strict=True, gt=0)` plus `currency`; `price_display` is a derived `Decimal` computed field. A `model_validator(mode="before")` accepts the legacy `price_eur` key **only** as an exact `Decimal`/string. `OrderQuote` and `StylistRecommendation` carry strict-int minor units with derived `*_display`.
- `app/config.py` — `default_shipping_minor_units` / `free_shipping_threshold_minor_units` as `int`, converted from the env **string** via `Decimal` (`"8.90"` -> `890`), never via `float()`.
- `app/main.py` — quote arithmetic via `sum_line_totals`; currency mismatch fails with 409.
- `app/ai_stylist.py` — budget comparison and accumulation in minor units.
- `scripts/validate_product_data.py` — `parse_float=Decimal`, duplicate-ID check, and an exact minor-unit round-trip assertion.
- `storefront/app.js` and `mobile/App.tsx` — render minor units with pure integer/string formatting; no division, no `toFixed`.

## 4. GREEN

```text
WORKING DIRECTORY: ...\platform\poc\backend
COMMAND: python -m pytest -q -p no:cacheprovider
53 passed, 1 warning in 2.21s
EXIT_CODE: 0
```

Money-specific results (from the `-rA` transcript in SB-EV-G1-002):

```text
PASSED tests/test_money_integrity.py::test_to_minor_units_rejects_binary_float
PASSED tests/test_money_integrity.py::test_to_minor_units_converts_decimal_and_string_exactly
PASSED tests/test_money_integrity.py::test_to_minor_units_rejects_excess_fractional_precision
PASSED tests/test_money_integrity.py::test_to_minor_units_rejects_unknown_currency
PASSED tests/test_money_integrity.py::test_from_minor_units_round_trips_exactly
PASSED tests/test_money_integrity.py::test_product_schema_stores_integer_minor_units
PASSED tests/test_money_integrity.py::test_product_schema_rejects_binary_float_price
PASSED tests/test_money_integrity.py::test_product_schema_accepts_exact_decimal_legacy_price
PASSED tests/test_money_integrity.py::test_product_schema_rejects_non_integer_minor_units
PASSED tests/test_money_integrity.py::test_product_display_price_is_derived_not_authoritative
PASSED tests/test_money_integrity.py::test_catalog_fixture_never_produces_binary_float
PASSED tests/test_money_integrity.py::test_preserved_fixture_prices_convert_exactly
PASSED tests/test_money_integrity.py::test_shipping_configuration_is_integer_minor_units
PASSED tests/test_money_integrity.py::test_quote_totals_are_exact_in_minor_units
PASSED tests/test_money_integrity.py::test_quote_free_shipping_threshold_uses_integer_comparison
PASSED tests/test_money_integrity.py::test_quote_repeated_small_quantities_do_not_accumulate_error
PASSED tests/test_money_integrity.py::test_quote_rejects_quantity_above_fixture_stock
PASSED tests/test_money_integrity.py::test_line_total_summation_is_exact_where_a_float_path_drifts
PASSED tests/test_money_integrity.py::test_line_total_summation_rejects_float_unit_price
PASSED tests/test_money_integrity.py::test_quote_wire_field_rejects_float_subtotal
PASSED tests/test_money_integrity.py::test_quote_display_values_are_derived_from_minor_units
PASSED tests/test_money_integrity.py::test_stylist_total_is_integer_minor_units_and_respects_budget
PASSED tests/test_money_integrity.py::test_stylist_rejects_excess_precision_budget
PASSED tests/test_money_integrity.py::test_no_float_money_symbols_remain_in_backend_source
```

Runtime confirmation over HTTP in the isolated container (SB-EV-G1-005 §4.6):

```text
GET /api/v1/products      -> "price_minor_units":5900,"currency":"EUR","price_display":"59.00"  (no price_eur)
POST /api/v1/orders/quote -> subtotal 5900 + shipping 890 = total 6790 minor units
POST /api/v1/orders/quote with a float quantity 1.5 -> HTTP 422
```

## 5. Proof the guards are load-bearing

Mutation results (SB-EV-G1-003): **M14, M15, M16, M17, M18, M19 all DETECTED.**

The most important of these is M17. Its first version *survived*: a reintroduced float round-trip was invisible at fixture magnitudes because the final rounding absorbed the error. The invariant was made structurally testable, and the adversarial case now pins it:

```text
EUR 0.70 x 3 = 210 minor units exactly.
int((70 / 100) * 3 * 100) == 209        <- the naive float path is off by one minor unit
sum_line_totals([(70, 3)]) == 210       <- integer arithmetic
```

## 6. Deliberate contract change

The API no longer emits `price_eur` / `total_eur`. Consumers read `price_minor_units` + `currency` (authoritative) and may read `*_display` (derived). This is a **breaking wire change**, accepted because the PoC is local and non-public, and because retaining a float field would have preserved the defect. `storefront/app.js` and `mobile/App.tsx` were updated in the same change. Recorded as decision SB-DEC-G1-003.

## 7. Not proven

Integer minor units are necessary but not sufficient. Rounding policy for VAT, discounts, partial refunds, multi-currency conversion and payout reconciliation is **not** designed, implemented or tested. `MINOR_UNIT_EXPONENTS` currently contains only EUR by design: an unknown currency fails rather than defaulting to two digits.
