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
}

/** What are you dressing for. The entry point into styling, and section 12's core module. */
export const OCCASIONS: Occasion[] = [
  { slug: "interview", name: "Interview", hint: "Considered, quiet, credible", categories: ["Trousers", "Shirts"] },
  { slug: "work", name: "Work", hint: "Everyday professional", categories: ["Trousers", "Shirts", "Outerwear"] },
  { slug: "dinner", name: "Dinner", hint: "Evening, unfussy", categories: ["Shirts", "Trousers"] },
  { slug: "date", name: "Date", hint: "Personal, not performative", categories: ["Shirts", "Knitwear"] },
  { slug: "wedding", name: "Wedding", hint: "Formal, with room to sit", categories: ["Shirts", "Trousers"] },
  { slug: "travel", name: "Travel", hint: "Layers that fold flat", categories: ["Outerwear", "Trousers", "Accessories"] },
  { slug: "weekend", name: "Weekend", hint: "Off duty", categories: ["T-shirts", "Trousers"] },
  { slug: "party", name: "Party", hint: "Late, warm rooms", categories: ["Shirts", "Outerwear"] },
  { slug: "everyday", name: "Everyday", hint: "The default that works", categories: ["T-shirts", "Trousers"] },
  { slug: "formal", name: "Formal", hint: "When the code is stated", categories: ["Shirts", "Trousers"] },
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

export type BrandOwnership = "PLATFORM_CURATED" | "MERCHANT_OWNED" | "EXTERNAL_CURATED";
export type CommerceRoute = "HOSTED" | "EXTERNAL" | "REFERRAL" | "NON_PURCHASABLE";

export interface BrandProfile {
  slug: string;
  name: string;
  /** Consumer-facing description of where the brand sits. Never the enum name. */
  positioning: string;
  story: string;
  origin: string;
  ownership: BrandOwnership;
  /** Ownership and commerce route are independent axes. Section 31. */
  commerceRoute: CommerceRoute;
  /** Real brands only. A demonstration is marked and says what it is. */
  demonstration?: boolean;
}

/**
 * Brands on the platform.
 *
 * DEDUNET is the only real one. The second entry exists so the multi-brand architecture is
 * visible rather than asserted, and it is labelled a demonstration on every surface that
 * renders it. Section 16: never invent partnerships. There are none.
 */
export const BRANDS: BrandProfile[] = [
  {
    slug: "dedunet",
    name: "DEDUNET",
    positioning: "Made and curated by DEDUNET",
    story:
      "DEDUNET designs in the language of Egyptian construction: a clear vertical line, weight that falls rather than drapes, and detail that rewards a second look instead of asking for the first. The first capsule is a prototype run built to test proportion, material and construction before anything is offered for sale.",
    origin: "Design in Egypt. Manufacturing partner not yet contracted.",
    ownership: "PLATFORM_CURATED",
    commerceRoute: "NON_PURCHASABLE",
  },
  {
    slug: "example-partner",
    name: "Partner brand",
    positioning: "Structure demonstration — not a real brand",
    story:
      "This entry is not a brand and not a partner. It exists to show that DEDUNET holds brands it does not own, and that where a brand sells is a separate question from who owns it. Nothing here is a commercial relationship: DEDUNET is not accepting brands and has no agreement with any.",
    origin: "Not applicable",
    ownership: "EXTERNAL_CURATED",
    commerceRoute: "EXTERNAL",
    demonstration: true,
  },
];

/** Consumer-facing language for the internal enums. Never show a customer an enum. */
export function ownershipLabel(ownership: BrandOwnership): string {
  switch (ownership) {
    case "PLATFORM_CURATED":
      return "Made by DEDUNET";
    case "MERCHANT_OWNED":
      return "Sold by the brand";
    case "EXTERNAL_CURATED":
      return "Curated by DEDUNET";
  }
}

export function commerceRouteLabel(route: CommerceRoute): string {
  switch (route) {
    case "HOSTED":
      return "Buy on DEDUNET";
    case "EXTERNAL":
      return "Buy on the brand's own site";
    case "REFERRAL":
      return "Available through a partner";
    case "NON_PURCHASABLE":
      return "Not available to buy";
  }
}

export function lookBySlug(slug: string): Look | undefined {
  return LOOKS.find((look) => look.slug === slug);
}

export function brandBySlug(slug: string): BrandProfile | undefined {
  return BRANDS.find((b) => b.slug === slug);
}

export function occasionBySlug(slug: string): Occasion | undefined {
  return OCCASIONS.find((o) => o.slug === slug);
}

export function styleCategoryBySlug(slug: string): StyleCategory | undefined {
  return STYLE_CATEGORIES.find((c) => c.slug === slug);
}
