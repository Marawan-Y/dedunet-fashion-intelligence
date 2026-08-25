/* Typed access to the generated brand seam.
 *
 * public/brand.generated.js is emitted by scripts/brand/build_brand_package.py from the
 * immutable Side A delivery and assigns window.DEDUNET_BRAND. It is loaded by a plain
 * script tag ahead of the bundle, which keeps it a GENERATED artefact rather than
 * something a developer hand-copies into source — the drift check in the generator
 * compares it across all three clients for exactly that reason.
 *
 * This module is the only place that reads the global, so the untyped seam stops here.
 */

export interface BrandAssets {
  logo_primary: string;
  logo_compact: string;
  logo_monochrome: string;
  logo_reversed: string;
  favicon: string;
  app_icon: string;
  pattern: string;
  hero: string;
  collection_cover: string;
  about: string;
  email_banner: string;
  app_splash: string;
  social_avatar: string;
}

export interface Brand {
  name: string;
  tagline: string;
  domain: string;
  legalStatus: string;
  publicLaunch: string;
  assets: BrandAssets;
}

declare global {
  interface Window {
    DEDUNET_BRAND?: Brand;
  }
}

/* A fallback that is deliberately EMPTY rather than plausible.
 *
 * If the seam has not loaded, every asset path is "" and the Media component renders its
 * labelled placeholder. Inventing a path here would produce a broken image instead, which
 * looks like a bug in the artwork rather than a missing build artefact. */
const MISSING: Brand = {
  name: "DEDUNET",
  tagline: "Worth, worn.",
  domain: "dedunet.com",
  legalStatus: "UNKNOWN",
  publicLaunch: "BLOCKED",
  assets: {
    logo_primary: "", logo_compact: "", logo_monochrome: "", logo_reversed: "",
    favicon: "", app_icon: "", pattern: "", hero: "", collection_cover: "",
    about: "", email_banner: "", app_splash: "", social_avatar: "",
  },
};

export const brand: Brand = (typeof window !== "undefined" && window.DEDUNET_BRAND) || MISSING;
