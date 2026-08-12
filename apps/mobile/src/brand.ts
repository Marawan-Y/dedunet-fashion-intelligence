/**
 * The single brand-configuration seam.
 *
 * Every customer-visible brand string and colour in the application comes from here.
 * No screen hard-codes a brand name. This exists so that adopting the Side A DEDUNET
 * identity package is a change to ONE file plus a token import, rather than a
 * repository-wide find-and-replace across screens -- which is exactly what
 * CONFLICT-008 forbids.
 *
 * IMPORTANT: this is a technical placeholder palette, not the Side A brand token set.
 * Importing `data/brand-prototype/brand-tokens.json` and the fonts is still outstanding.
 *
 * Status note, 2026-08-12: this comment used to say the media and campaign copy were
 * outstanding too, and that the whole import was "the NEXT milestone (DEDUNET platform
 * integration)". That milestone has since landed. The client renders the DEDUNET catalogue
 * and DDN-TS01's four ordered media through `components/Gallery.tsx`, and human acceptance
 * confirmed it (Test 3B). Only the tokens and fonts remain.
 */

export type BrandPalette = {
  background: string;
  surface: string;
  border: string;
  text: string;
  textMuted: string;
  accent: string;
  accentText: string;
  danger: string;
  warning: string;
  success: string;
};

export type Brand = {
  /** Technical application name. Not a legal or trademark assertion. */
  name: string;
  /** Short line shown under the wordmark. Deliberately makes no product claim. */
  tagline: string;
  palette: BrandPalette;
};

export const BRAND: Brand = {
  name: "DEDUNET",
  tagline: "Prototype storefront",
  palette: {
    background: "#f6f3ee",
    surface: "#ffffff",
    border: "#e2dcd2",
    text: "#1c1a17",
    textMuted: "#5f594f",
    accent: "#1d3557",
    accentText: "#ffffff",
    danger: "#8b1e1e",
    warning: "#8a5a00",
    success: "#1f5f3f",
  },
};

/**
 * Shown wherever the build could be mistaken for a real shop, BEFORE the deployment has
 * said which commerce mode it is in — and afterwards if it could not be reached.
 *
 * Deliberately says only what is true in every permitted mode. It used to assert that
 * "payments run against a sandbox adapter", which overstates BRAND_PREVIEW_MODE, where no
 * payment call is reachable at all. The mode-specific wording is served by
 * `/api/v1/commerce/mode` so that this client and the web storefront cannot disagree about
 * what a mode means; see `commerceNotice`.
 */
export const SANDBOX_NOTICE =
  "Prototype build. No real card is charged and no real order is fulfilled.";

/**
 * The disclosure to show for a resolved commerce mode, or the mode-independent fallback.
 *
 * The server supplies both the mode and its wording; this only chooses between "we know"
 * and "we do not". Composing the sentences here would put a second author in charge of what
 * COMMERCE_TEST_MODE means to a customer.
 */
export function commerceNotice(
  disclosure: { headline?: string; detail?: string[] } | null | undefined
): string {
  const headline = typeof disclosure?.headline === "string" ? disclosure.headline.trim() : "";
  const detail = Array.isArray(disclosure?.detail)
    ? disclosure.detail.filter((line) => typeof line === "string" && line.trim())
    : [];
  if (!headline || detail.length === 0) return SANDBOX_NOTICE;
  return [headline, ...detail].join(" ");
}
