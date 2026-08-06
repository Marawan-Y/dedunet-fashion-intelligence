/**
 * Money formatting. Integer minor units only.
 *
 * Money contract (docs/side-b/SIDE_B_MONEY_CONTRACT.md): the authoritative amount is an
 * integer number of minor units. EUR 59.00 is 5900. This module NEVER divides and never
 * produces a float from an amount, because binary floating point cannot represent 0.10
 * exactly and 0.70 * 3 is the standard demonstration.
 *
 * Formatting is string manipulation on the integer, matching what the browser clients do.
 */

/** Currencies whose minor-unit exponent has actually been reviewed. */
const MINOR_UNIT_EXPONENTS: Readonly<Record<string, number>> = { EUR: 2 };

const CURRENCY_SYMBOLS: Readonly<Record<string, string>> = { EUR: "€" };

export class MoneyError extends Error {}

/**
 * True only for a genuine, safe integer. Rejects `1.5`, `NaN`, `Infinity` and booleans.
 *
 * `Infinity` matters specifically: `Math.min()` of an empty list returns `Infinity`, so a
 * product with zero variants can produce an "amount" that is not a number at all. Guarding
 * here means such a value can never be rendered as a price.
 */
export function isMinorUnits(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value);
}

/**
 * Format integer minor units for display.
 *
 * Returns `null` when the amount is not a safe integer or the currency has no reviewed
 * exponent. Callers must render a non-price fallback rather than guessing — showing a
 * wrong price is worse than showing no price.
 */
export function formatMinorUnits(minorUnits: unknown, currency: string): string | null {
  if (!isMinorUnits(minorUnits)) return null;

  const exponent = MINOR_UNIT_EXPONENTS[currency];
  if (exponent === undefined) return null;

  const negative = minorUnits < 0;
  const digits = String(Math.abs(minorUnits)).padStart(exponent + 1, "0");
  const major = digits.slice(0, digits.length - exponent);
  const minor = digits.slice(digits.length - exponent);
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;

  return `${negative ? "-" : ""}${symbol}${major}.${minor}`;
}

/**
 * Lowest variant price of a product, or `null` when there are no priced variants.
 *
 * Deliberately NOT `Math.min(...prices)`. Spreading an empty array yields `Infinity`,
 * which would then be formatted and shown to a customer as a price. A product with no
 * variants has no price, and `null` is the honest answer.
 */
export function lowestPriceMinorUnits(
  variants: ReadonlyArray<{ price_minor_units: unknown }>
): number | null {
  let lowest: number | null = null;
  for (const variant of variants) {
    const price = variant.price_minor_units;
    if (!isMinorUnits(price)) continue;
    if (lowest === null || price < lowest) lowest = price;
  }
  return lowest;
}

/**
 * Multiply an integer unit price by an integer quantity.
 *
 * Throws rather than returning a wrong number: a silently incorrect line total is a
 * financial defect, and the server's total is authoritative anyway.
 */
export function lineTotalMinorUnits(unitPrice: unknown, quantity: unknown): number {
  if (!isMinorUnits(unitPrice)) throw new MoneyError("unit price is not integer minor units");
  if (!isMinorUnits(quantity)) throw new MoneyError("quantity is not an integer");
  const total = unitPrice * quantity;
  if (!Number.isSafeInteger(total)) throw new MoneyError("line total exceeds safe integer range");
  return total;
}
