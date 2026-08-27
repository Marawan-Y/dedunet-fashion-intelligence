import { fetchBrand, fetchBrands } from "../api/endpoints";
import { useAsync } from "../lib/useAsync";
import { formatMinorUnits } from "../lib/money";
import type { BrandProductSummary, BrandSummary } from "../api/types";

/* Brand data, from the API.
 *
 * This replaces a hardcoded array in `content.ts` that held DEDUNET and one entry called
 * "Partner brand". That array was honest about being a demonstration, but it was still
 * frontend fiction: the page could not tell you how many products a brand had, and a brand
 * added to the database would not have appeared. Brands are now domain data.
 *
 * The FIXTURE RULE moved with it, and got stronger. The demonstration entry is no longer a
 * literal in this bundle; it is a row flagged `is_development_fixture`, which the database
 * forbids publishing and which the API hides entirely once public commerce is enabled. The
 * client's job is only to render `fixture_notice` wherever such a brand appears.
 */

export function useBrands() {
  return useAsync((signal) => fetchBrands(signal), []);
}

export function useBrand(slug: string | undefined) {
  return useAsync(
    (signal) => {
      if (!slug) return Promise.reject(new Error("no brand slug"));
      return fetchBrand(slug, signal);
    },
    [slug],
  );
}

/**
 * A brand's price range, formatted.
 *
 * Uses the same integer/string formatter as the product page, so a brand card and a product
 * page can never disagree about what something costs. Returns "" when a brand has no priced
 * product, which the caller renders as nothing rather than as a zero.
 */
export function brandPriceRange(products: BrandProductSummary[]): string {
  const lows = products
    .map((p) => p.price_minor_units_min)
    .filter((v): v is number => typeof v === "number" && v > 0);
  if (lows.length === 0) return "";

  const currency = products.find((p) => p.currency)?.currency ?? "EUR";
  const lowest = Math.min(...lows);
  const highest = Math.max(
    ...products
      .map((p) => p.price_minor_units_max ?? p.price_minor_units_min)
      .filter((v): v is number => typeof v === "number" && v > 0),
  );

  if (lowest === highest) return formatMinorUnits(lowest, currency);
  return `${formatMinorUnits(lowest, currency)} – ${formatMinorUnits(highest, currency)}`;
}

/** Real brands first. A development fixture must never displace one in a list. */
export function realBrandsFirst(brands: BrandSummary[]): BrandSummary[] {
  return [...brands].sort((a, b) => {
    if (a.is_development_fixture !== b.is_development_fixture) {
      return a.is_development_fixture ? 1 : -1;
    }
    return a.name.localeCompare(b.name);
  });
}
