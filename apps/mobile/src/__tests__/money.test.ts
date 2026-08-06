/**
 * Money and zero-variant guards.
 *
 * These are the two defects the brief names explicitly: a float reaching an authoritative
 * price, and `Math.min(...[])` producing `Infinity` for a product with no variants.
 */

import {
  MoneyError,
  formatMinorUnits,
  isMinorUnits,
  lineTotalMinorUnits,
  lowestPriceMinorUnits,
} from "../money";

describe("formatMinorUnits", () => {
  it("formats integer minor units without dividing", () => {
    expect(formatMinorUnits(5900, "EUR")).toBe("€59.00");
    expect(formatMinorUnits(13900, "EUR")).toBe("€139.00");
    expect(formatMinorUnits(890, "EUR")).toBe("€8.90");
  });

  it("pads amounts below one major unit", () => {
    expect(formatMinorUnits(5, "EUR")).toBe("€0.05");
    expect(formatMinorUnits(50, "EUR")).toBe("€0.50");
    expect(formatMinorUnits(0, "EUR")).toBe("€0.00");
  });

  it("formats negative amounts with the sign outside the symbol", () => {
    expect(formatMinorUnits(-250, "EUR")).toBe("-€2.50");
  });

  it("refuses a non-integer amount rather than rounding it", () => {
    // 0.70 * 3 is the canonical binary-float demonstration: 2.0999999999999996.
    expect(formatMinorUnits(0.7 * 3, "EUR")).toBeNull();
    expect(formatMinorUnits(59.5, "EUR")).toBeNull();
    // 59.0 is the integer 59 in JavaScript, so it is accepted -- and it means 59 MINOR
    // units, which is €0.59. Anyone reading `59.0` as "fifty-nine euros" has already made
    // the major/minor mistake the contract exists to prevent.
    expect(formatMinorUnits(59.0, "EUR")).toBe("€0.59");
  });

  it("refuses Infinity and NaN", () => {
    expect(formatMinorUnits(Infinity, "EUR")).toBeNull();
    expect(formatMinorUnits(-Infinity, "EUR")).toBeNull();
    expect(formatMinorUnits(NaN, "EUR")).toBeNull();
  });

  it("refuses a currency whose minor-unit exponent has not been reviewed", () => {
    // Only EUR has a reviewed exponent. Guessing 2 for every currency is wrong for JPY
    // (0) and for KWD (3), and a wrong exponent misprices by a factor of 100.
    expect(formatMinorUnits(5900, "JPY")).toBeNull();
    expect(formatMinorUnits(5900, "KWD")).toBeNull();
    expect(formatMinorUnits(5900, "USD")).toBeNull();
  });

  it("refuses non-numeric input", () => {
    expect(formatMinorUnits("5900", "EUR")).toBeNull();
    expect(formatMinorUnits(null, "EUR")).toBeNull();
    expect(formatMinorUnits(undefined, "EUR")).toBeNull();
  });
});

describe("isMinorUnits", () => {
  it("accepts only safe integers", () => {
    expect(isMinorUnits(0)).toBe(true);
    expect(isMinorUnits(-1)).toBe(true);
    expect(isMinorUnits(1.5)).toBe(false);
    expect(isMinorUnits(Number.MAX_SAFE_INTEGER + 2)).toBe(false);
    expect(isMinorUnits(true)).toBe(false);
  });
});

describe("lowestPriceMinorUnits — the zero-variant guard", () => {
  it("returns null for a product with no variants, never Infinity", () => {
    const result = lowestPriceMinorUnits([]);

    expect(result).toBeNull();
    // The specific failure the brief calls out: Math.min(...[]) === Infinity.
    expect(result).not.toBe(Infinity);
    // And nothing formattable can come out of it.
    expect(formatMinorUnits(result as unknown as number, "EUR")).toBeNull();
  });

  it("matches Math.min for a normal product", () => {
    const variants = [
      { price_minor_units: 8900 },
      { price_minor_units: 5900 },
      { price_minor_units: 13900 },
    ];
    expect(lowestPriceMinorUnits(variants)).toBe(5900);
  });

  it("skips variants whose price is not integer minor units", () => {
    expect(lowestPriceMinorUnits([{ price_minor_units: 59.5 }, { price_minor_units: 8900 }])).toBe(
      8900
    );
    expect(lowestPriceMinorUnits([{ price_minor_units: null }])).toBeNull();
    expect(lowestPriceMinorUnits([{ price_minor_units: Infinity }])).toBeNull();
  });
});

describe("lineTotalMinorUnits", () => {
  it("multiplies integers exactly", () => {
    expect(lineTotalMinorUnits(5900, 3)).toBe(17700);
    expect(formatMinorUnits(lineTotalMinorUnits(2333, 3), "EUR")).toBe("€69.99");
  });

  it("throws rather than returning a wrong number", () => {
    expect(() => lineTotalMinorUnits(59.5, 2)).toThrow(MoneyError);
    expect(() => lineTotalMinorUnits(5900, 1.5)).toThrow(MoneyError);
    expect(() => lineTotalMinorUnits(Number.MAX_SAFE_INTEGER, 2)).toThrow(MoneyError);
  });
});
