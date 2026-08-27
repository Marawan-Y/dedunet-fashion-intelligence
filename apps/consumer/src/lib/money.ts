/* Money formatting and the product price-presentation rule.
 *
 * `docs/side-b/SIDE_B_MONEY_CONTRACT.md` rule 6: display values are DERIVED, never
 * authoritative, and "clients format integer minor units with pure integer/string
 * arithmetic — no division, so no binary float ever touches an amount". The formatter
 * below is therefore a port of `apps/web/ds.js:money()` and keeps that property: it slices
 * a digit string rather than dividing by 100.
 *
 * WHY THIS MODULE EXISTS AT ALL.
 *
 * The consumer client shipped believing the DEDUNET catalogue had no prices. `types.ts`
 * said so in a comment — "The five DEDUNET products carry NO price" — and modelled
 * CatalogVariant without a price field, so the product page fell back to a product-level
 * `price_display` that /api/v1/catalog/products has never sent. Every product rendered
 * "Not priced".
 *
 * The premise was wrong. The catalogue carries an authoritative price on each VARIANT:
 * every Source Tee variant is 7200 EUR minor units, and `list_products` already sorts by
 * `min(v.price_minor_units)`. The price was in the payload the whole time; nothing read it.
 * Recorded as F-2 in `evidence/staging-cutover/STAGING_CUTOVER_EXECUTION.md`.
 *
 * The rule below is deliberately the one the classic client already used — cheapest across
 * variants for a product-level figure — rather than a new invention.
 */

/** Currencies whose minor-unit exponent this client knows. */
const MINOR_UNIT_EXPONENTS: Record<string, number> = { EUR: 2 };
const CURRENCY_SYMBOLS: Record<string, string> = { EUR: "€" };

/**
 * Format authoritative integer minor units for display.
 *
 * Degrades rather than throws, deliberately and exactly as the classic client did: an
 * unknown currency or a non-integer amount renders as "<value> <currency>". A formatter
 * that throws inside a render turns one bad price into a blank page, and this one sits on
 * the path that shows customers what things cost.
 */
export function formatMinorUnits(minorUnits: number, currency = "EUR"): string {
  const exponent = MINOR_UNIT_EXPONENTS[currency];
  if (exponent === undefined || !Number.isInteger(minorUnits)) {
    return `${minorUnits} ${currency}`;
  }
  const sign = minorUnits < 0 ? "-" : "";
  // String arithmetic, not division. 7200 -> "7200" -> "72" + "." + "00".
  const digits = String(Math.abs(minorUnits)).padStart(exponent + 1, "0");
  const major = digits.slice(0, digits.length - exponent);
  const minor = digits.slice(digits.length - exponent);
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
  return `${sign}${symbol}${major}.${minor}`;
}

/** Anything carrying an authoritative variant price. Structural, so callers stay free. */
export interface PricedVariant {
  price_minor_units?: number | null;
}

/**
 * What a product's price should read as, given its variants.
 *
 * A discriminated union rather than a string, so a caller cannot accidentally render a
 * range as an exact price, and so "no price" stays a distinct state that has to be handled
 * rather than an empty string that renders as a gap.
 */
export type ProductPrice =
  /** No variant carries an authoritative price. The ONLY case that may say "Not priced". */
  | { kind: "absent" }
  /** Exactly one distinct price across the priced variants. */
  | { kind: "exact"; minorUnits: number; currency: string; label: string }
  /** More than one. `label` is a "From …" figure built from the lowest. */
  | { kind: "from"; minorUnits: number; currency: string; label: string };

/**
 * Derive the product-level price presentation from variant prices.
 *
 *   no priced variant        -> absent      -> the unpriced state, and only then
 *   one distinct price       -> exact       -> "€72.00"
 *   several distinct prices  -> from        -> "From €72.00"
 *
 * A price of 0 or a negative is treated as *not* an authoritative price: the API models
 * `price_minor_units` as `gt=0`, so anything else is absent data wearing a number, and
 * rendering "€0.00" for it would be an invented claim about what something costs.
 *
 * NOTE ON SCOPE: this says what a product COSTS. It says nothing about whether it can be
 * bought. Purchasability is `sellable` plus the commerce mode, gated separately, and a
 * visible price must never be read as an offer — every DEDUNET prototype is priced and
 * none is purchasable.
 */
export function productPrice(
  variants: readonly PricedVariant[] | null | undefined,
  currency = "EUR",
): ProductPrice {
  const prices = (variants ?? [])
    .map((v) => v.price_minor_units)
    .filter((p): p is number => typeof p === "number" && Number.isInteger(p) && p > 0);

  if (prices.length === 0) return { kind: "absent" };

  const lowest = Math.min(...prices);
  const distinct = new Set(prices).size;

  if (distinct === 1) {
    return { kind: "exact", minorUnits: lowest, currency, label: formatMinorUnits(lowest, currency) };
  }
  return {
    kind: "from",
    minorUnits: lowest,
    currency,
    label: `From ${formatMinorUnits(lowest, currency)}`,
  };
}
