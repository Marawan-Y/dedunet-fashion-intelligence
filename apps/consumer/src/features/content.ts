/* The editorial content layer.
 *
 * READ THIS BEFORE ADDING ANYTHING HERE.
 *
 * Three different kinds of thing live in this file and they are not equally real:
 *
 *   REAL         Occasions and style categories. They are navigation and they genuinely
 *                filter the catalogue, so they are as real as the filter they drive.
 *
 *   COMPOSED     Looks. Each one is an editorial arrangement of PRODUCTS THAT EXIST in the
 *                DEDUNET catalogue. No look invents a garment, a price, a material or a
 *                brand. What is not real about them is the CURATION: there is no outfit
 *                engine and no recommendation model, so a look is a human arrangement and
 *                every surface that shows one says so.
 *
 *   SHAPE ONLY   The non-DEDUNET brand. It exists to demonstrate that the platform holds
 *                more than one brand, it is labelled as a demonstration everywhere it
 *                appears, and it is not a partner. DEDUNET has no commercial agreement
 *                with any brand and this file must never imply one.
 *
 * Section 47: nothing here may be added to make the platform look larger than it is.
 */

export interface Occasion {
  slug: string;
  name: string;
  hint: string;
  /** Catalogue categories this occasion draws from. This is what makes it real. */
  categories: string[];
  /**
   * Concept artwork for the occasion plate.
   *
   * An occasion has no photography of its own and none will be invented for it. Each one
   * borrows a delivered DEDUNET concept plate — the lifestyle or detail artwork of a piece
   * that genuinely suits that occasion — so every image on the surface is real brand media
   * doing honest work. Section 3: no fabricated product photography.
   */
  image: string;
}

/** What are you dressing for. The entry point into styling, and section 12's core module. */
export const OCCASIONS: Occasion[] = [
  { slug: "interview", name: "Interview", hint: "Considered, quiet, credible", categories: ["Trousers", "Shirts"], image: "assets/brand-prototype/products/ddn-sh01-detail.svg" },
  { slug: "work", name: "Work", hint: "Everyday professional", categories: ["Trousers", "Shirts", "Outerwear"], image: "assets/brand-prototype/media/ddn-tr01-lifestyle.svg" },
  { slug: "dinner", name: "Dinner", hint: "Evening, unfussy", categories: ["Shirts", "Trousers"], image: "assets/brand-prototype/products/ddn-tr01-detail.svg" },
  { slug: "date", name: "Date", hint: "Personal, not performative", categories: ["Shirts", "Knitwear"], image: "assets/brand-prototype/media/ddn-ts01-lifestyle.svg" },
  { slug: "wedding", name: "Wedding", hint: "Formal, with room to sit", categories: ["Shirts", "Trousers"], image: "assets/brand-prototype/media/collection-cover.svg" },
  { slug: "travel", name: "Travel", hint: "Layers that fold flat", categories: ["Outerwear", "Trousers", "Accessories"], image: "assets/brand-prototype/media/ddn-os01-lifestyle.svg" },
  { slug: "weekend", name: "Weekend", hint: "Off duty", categories: ["T-shirts", "Trousers"], image: "assets/brand-prototype/products/ddn-ts01-detail.svg" },
  { slug: "party", name: "Party", hint: "Late, warm rooms", categories: ["Shirts", "Outerwear"], image: "assets/brand-prototype/products/ddn-os01-detail.svg" },
  { slug: "everyday", name: "Everyday", hint: "The default that works", categories: ["T-shirts", "Trousers"], image: "assets/brand-prototype/media/about-image.svg" },
  { slug: "formal", name: "Formal", hint: "When the code is stated", categories: ["Shirts", "Trousers"], image: "assets/brand-prototype/products/ddn-sc01-detail.svg" },
];

export interface StyleCategory {
  slug: string;
  name: string;
  description: string;
}

/** How the catalogue is cut by style rather than by occasion. */
export const STYLE_CATEGORIES: StyleCategory[] = [
  { slug: "minimal", name: "Minimal", description: "Little detail, exact proportion" },
  { slug: "classic", name: "Classic", description: "Shapes that predate the season" },
  { slug: "smart-casual", name: "Smart Casual", description: "Structured, not formal" },
  { slug: "streetwear", name: "Streetwear", description: "Volume and ease" },
  { slug: "luxury", name: "Luxury", description: "Material first" },
  { slug: "modest", name: "Modest", description: "Full coverage, considered line" },
  { slug: "contemporary", name: "Contemporary", description: "Current without being loud" },
  { slug: "avant-garde", name: "Avant-Garde", description: "Proportion as the argument" },
];

export interface LookItem {
  /** The slug of a REAL product in the DEDUNET catalogue. */
  productSlug: string;
  /** What this piece is doing in the look. */
  role: string;
}

export interface Look {
  slug: string;
  name: string;
  occasion: string;
  /** The editorial argument for the arrangement. */
  story: string;
  descriptors: string[];
  items: LookItem[];
}

/**
 * Looks, composed from real catalogue products.
 *
 * There is no total price on a look and there is no field for one. Every DEDUNET product is
 * a prototype carrying no commercial price, so a total would be a number this platform
 * invented. Section 15 asks for total pricing and it is deliberately absent until the
 * catalogue carries prices; the look detail page says that in as many words rather than
 * showing a plausible figure.
 */
export const LOOKS: Look[] = [
  {
    slug: "quiet-interview",
    name: "The Quiet Interview",
    occasion: "interview",
    story:
      "An interview outfit should be the least interesting thing in the room. This one holds a clean vertical line and keeps every decision reversible: nothing here reads as a costume, and nothing distracts from what you say.",
    descriptors: ["Minimal", "Structured", "Neutral"],
    items: [
      { productSlug: "the-passage-shirt", role: "The clean upper line" },
      { productSlug: "the-measure-trouser", role: "Volume, held straight" },
    ],
  },
  {
    slug: "long-weekend",
    name: "The Long Weekend",
    occasion: "weekend",
    story:
      "Off duty without giving up on shape. The tee carries the ease and the trouser keeps the proportion honest, so the whole thing survives being photographed.",
    descriptors: ["Relaxed", "Contemporary", "Easy"],
    items: [
      { productSlug: "the-source-tee", role: "Ease, with a defined shoulder" },
      { productSlug: "the-measure-trouser", role: "The line that keeps it from slumping" },
    ],
  },
  {
    slug: "transitional-layer",
    name: "The Transitional Layer",
    occasion: "travel",
    story:
      "Built for the part of the year that cannot decide. The overshirt does the work of a jacket without the bulk, and the scarf is the adjustment you make at the door rather than a decoration.",
    descriptors: ["Layered", "Practical", "Considered"],
    items: [
      { productSlug: "the-structure-overshirt", role: "A jacket that folds flat" },
      { productSlug: "the-source-tee", role: "The base layer" },
      { productSlug: "the-measure-trouser", role: "Straight through the leg" },
      { productSlug: "the-trace-scarf", role: "The last adjustment" },
    ],
  },
  {
    slug: "evening-shirt",
    name: "Evening, Unfussy",
    occasion: "dinner",
    story:
      "Dinner does not need a suit. A shirt with an exact collar and a trouser that hangs properly reads as effort without announcing it.",
    descriptors: ["Classic", "Understated", "Evening"],
    items: [
      { productSlug: "the-passage-shirt", role: "The collar does the formality" },
      { productSlug: "the-measure-trouser", role: "Weight and fall" },
    ],
  },
];

/* THE HARDCODED BRAND LIST WAS REMOVED IN THE MULTI-BRAND PHASE.
 *
 * It held two literals -- DEDUNET and an entry called "Partner brand" -- plus
 * `ownershipLabel` and `commerceRouteLabel`, which translated internal enums into consumer
 * copy in the BROWSER. Three things were wrong with that once brands became real:
 *
 *   1. the list could not know how many products a brand had, and a brand added to the
 *      database would never have appeared;
 *   2. translating an ownership enum client-side means the enum has to be shipped to the
 *      client at all, and every surface is free to coin its own wording for it;
 *   3. `commerceRouteLabel("REFERRAL")` returned "Available through a partner" -- which
 *      claimed a partnership that has never existed. Exactly the class of invented
 *      relationship this programme forbids, sitting in a switch statement nobody read.
 *
 * Brands now come from `/api/v1/brands` and carry `relationship_label` decided by the
 * server, so there is one vocabulary and it is auditable in one place. See
 * `src/features/useBrands.ts` and `app/commerce/brand_api.py`.
 */

export function lookBySlug(slug: string): Look | undefined {
  return LOOKS.find((look) => look.slug === slug);
}

export function occasionBySlug(slug: string): Occasion | undefined {
  return OCCASIONS.find((o) => o.slug === slug);
}

export function styleCategoryBySlug(slug: string): StyleCategory | undefined {
  return STYLE_CATEGORIES.find((c) => c.slug === slug);
}
