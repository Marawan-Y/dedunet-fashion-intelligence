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
 * Importing `data/brand-prototype/brand-tokens.json`, the fonts, the media and the
 * campaign copy is the NEXT milestone (DEDUNET platform integration) and is explicitly
 * out of scope for Workstream F.
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
 * Shown wherever the build could be mistaken for a real shop.
 *
 * KNOWN_LIMITATIONS and the Side A validation report both state that checkout is
 * prototype-only and that payments run against a sandbox adapter. The application must
 * say so on screen, not only in documentation.
 */
export const SANDBOX_NOTICE =
  "Prototype build. Payments run against a sandbox adapter — no card is charged and nothing ships.";
