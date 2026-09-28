# Contributing

Thank you for looking. Please read this first — it will save you time.

## This is an evidence repository

It records one programme's engineering, including its mistakes, and its value depends on that
record staying accurate. It is **not** looking for feature contributions, and a pull request
that adds a capability will most likely be declined — not because it is unwelcome, but
because an unbuilt capability here is usually unbuilt on purpose and documented as such.

**Genuinely welcome:**

- a defect, especially in a safety control or a claim this repository makes about itself;
- a place where the documentation and the code disagree — that is the failure mode this
  project cares most about;
- a security issue (see [`SECURITY.md`](SECURITY.md));
- a correction where something is overclaimed.

## The house rules

If you do open a pull request, these are the standards the existing code is held to:

1. **Do not describe a mock, sandbox, fixture or prototype as production-ready.** Every
   surface that depends on something unbuilt must say so — on screen, in the payload, and in
   the docs. Deleting the disclosure instead of building the feature is the one change that
   will always be rejected. See
   [`docs/architecture/PRODUCTION_DISCLOSURE_RULE.md`](docs/architecture/PRODUCTION_DISCLOSURE_RULE.md).
2. **Money is integer minor units.** €72.00 is `7200`. Never a float, never a rounded decimal,
   and clients format with integer and string arithmetic.
3. **Safety guards fail closed**, and a new guard needs a test that fails when the guard is
   removed. A guard whose removal nobody notices is not a guard.
4. **Never loosen the purchase gate.** `PUBLIC_COMMERCIAL_LAUNCH` is blocked.
5. **Say what you did not do.** A change that reports itself as complete while a required
   condition is failing is worse than one that reports itself as blocked.

## Running the checks

```bash
# backend suite
cd services/commerce-api && PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider

# data and governance validators
python scripts/validation/validate_product_data.py
python scripts/validation/validate_candidate_data.py --assess-sellable   # MUST exit non-zero
python docs/system-of-record/controller_validate.py

# consumer unit tests, then the browser suite against a running deployment
cd apps/consumer && npx vitest run
DEDUNET_BASE_URL=http://localhost:13080 npx playwright test
```

CI runs the backend suite on Python 3.12, 3.13 and 3.14, proves migrations apply **and
reverse** on both SQLite and PostgreSQL, asserts the exported OpenAPI contract has not
drifted, and fails if a `.env` file ever appears in history.

## Licence

This repository is source-available and **not** open source — see [`LICENSE`](LICENSE). By
opening a pull request you agree your contribution may be included under those terms.
