import { describe, expect, it } from "vitest";
import { formatMinorUnits, productPrice } from "./money";

/* The money rule, and the regression that made it necessary.
 *
 * Every product page rendered "Not priced" after the staging cutover because the client
 * read a product-level `price_display` that /api/v1/catalog/products does not send, while
 * the authoritative price sat on each variant. These tests pin the derivation so the same
 * class of defect — a price that exists in the payload and is not shown — fails here
 * instead of on a device.
 *
 * The cases are the ones the repair was specified against: one variant, several variants
 * agreeing, several disagreeing, none priced, and a preview product that is priced and
 * still not purchasable.
 */

describe("formatMinorUnits", () => {
  it("formats EUR minor units without ever dividing", () => {
    // SIDE_B_MONEY_CONTRACT rule 6: integer/string arithmetic only, no binary float.
    expect(formatMinorUnits(7200, "EUR")).toBe("€72.00");
    expect(formatMinorUnits(5900, "EUR")).toBe("€59.00");
    expect(formatMinorUnits(13900, "EUR")).toBe("€139.00");
  });

  it("pads amounts smaller than one major unit", () => {
    expect(formatMinorUnits(5, "EUR")).toBe("€0.05");
    expect(formatMinorUnits(50, "EUR")).toBe("€0.50");
    expect(formatMinorUnits(0, "EUR")).toBe("€0.00");
  });

  it("keeps the sign in front of the symbol", () => {
    expect(formatMinorUnits(-7200, "EUR")).toBe("-€72.00");
  });

  it("degrades instead of throwing on input it cannot format", () => {
    // A formatter that throws inside a render turns one bad price into a blank page.
    expect(formatMinorUnits(7200, "XYZ")).toBe("7200 XYZ");
    expect(formatMinorUnits(72.5, "EUR")).toBe("72.5 EUR");
  });

  it("does not accumulate binary float error the way division would", () => {
    // The reason the contract forbids division: 1999/100 is not exactly 19.99 in binary.
    expect(formatMinorUnits(1999, "EUR")).toBe("€19.99");
    expect(formatMinorUnits(70, "EUR")).toBe("€0.70");
  });
});

describe("productPrice", () => {
  it("shows the exact price when a single variant carries one", () => {
    const p = productPrice([{ price_minor_units: 7200 }], "EUR");
    expect(p.kind).toBe("exact");
    expect(p.kind !== "absent" && p.label).toBe("€72.00");
  });

  it("shows one exact price when every variant agrees — the Source Tee case", () => {
    // All 18 Source Tee variants are 7200. This is the case that regressed.
    const variants = Array.from({ length: 18 }, () => ({ price_minor_units: 7200 }));
    const p = productPrice(variants, "EUR");
    expect(p.kind).toBe("exact");
    expect(p.kind !== "absent" && p.label).toBe("€72.00");
  });

  it("shows a From figure built from the lowest when variants disagree", () => {
    const p = productPrice(
      [{ price_minor_units: 9900 }, { price_minor_units: 7200 }, { price_minor_units: 8500 }],
      "EUR",
    );
    expect(p.kind).toBe("from");
    expect(p.kind !== "absent" && p.label).toBe("From €72.00");
    expect(p.kind !== "absent" && p.minorUnits).toBe(7200);
  });

  it("reports absent only when no variant carries an authoritative price", () => {
    expect(productPrice([], "EUR").kind).toBe("absent");
    expect(productPrice(undefined, "EUR").kind).toBe("absent");
    expect(productPrice(null, "EUR").kind).toBe("absent");
    expect(productPrice([{ price_minor_units: undefined }], "EUR").kind).toBe("absent");
    expect(productPrice([{}, {}], "EUR").kind).toBe("absent");
  });

  it("treats a non-positive or non-integer price as absent, not as €0.00", () => {
    // The API models price_minor_units as gt=0. Anything else is missing data wearing a
    // number, and rendering it would be an invented claim about what something costs.
    expect(productPrice([{ price_minor_units: 0 }], "EUR").kind).toBe("absent");
    expect(productPrice([{ price_minor_units: -1 }], "EUR").kind).toBe("absent");
    expect(productPrice([{ price_minor_units: 72.5 }], "EUR").kind).toBe("absent");
  });

  it("ignores unpriced variants when some siblings are priced", () => {
    const p = productPrice(
      [{ price_minor_units: undefined }, { price_minor_units: 7200 }],
      "EUR",
    );
    expect(p.kind).toBe("exact");
    expect(p.kind !== "absent" && p.label).toBe("€72.00");
  });

  it("prices a preview, non-purchasable product exactly as any other", () => {
    /* THE POINT OF THIS TEST. Price and purchasability are independent, and the rule must
     * not quietly hide a price because nothing can be bought. Every DEDUNET prototype is
     * sellable:false and priced; the purchase gate refuses separately, and the product page
     * still renders "Not available to buy" beside the figure. A price is a statement about
     * cost, never an offer. */
    const previewVariants = [
      { price_minor_units: 7200, sellable: false },
      { price_minor_units: 7200, sellable: false },
    ];
    const p = productPrice(previewVariants, "EUR");
    expect(p.kind).toBe("exact");
    expect(p.kind !== "absent" && p.label).toBe("€72.00");
  });

  it("carries the product currency through rather than assuming EUR", () => {
    const p = productPrice([{ price_minor_units: 7200 }], "EUR");
    expect(p.kind !== "absent" && p.currency).toBe("EUR");
  });
});
