import { useCallback } from "react";
import { fetchCatalog, fetchProduct } from "../api/endpoints";
import { useAsync } from "../lib/useAsync";
import type { CatalogProduct, ProductMedia } from "../api/types";

/** The whole DEDUNET catalogue. Five prototypes, none of them purchasable. */
export function useCatalog() {
  const run = useCallback((signal: AbortSignal) => fetchCatalog(signal), []);
  return useAsync<CatalogProduct[]>(run, []);
}

export function useProduct(slug: string | undefined) {
  const run = useCallback(
    (signal: AbortSignal) => {
      if (!slug) return Promise.reject(new Error("No product requested"));
      return fetchProduct(slug, signal);
    },
    [slug],
  );
  return useAsync<CatalogProduct>(run, [slug]);
}

/**
 * The image to lead with.
 *
 * Front, then whatever sorts first. Falling back rather than returning nothing matters:
 * the Media component renders a labelled placeholder for an empty src, and a placeholder
 * where a usable back view exists is a worse outcome than the back view.
 */
export function primaryImage(product: CatalogProduct): ProductMedia | undefined {
  const media = [...(product.media ?? [])].sort((a, b) => a.sort_order - b.sort_order);
  return media.find((m) => m.role === "front") ?? media[0];
}

/** Media in display order, front first. */
export function orderedMedia(product: CatalogProduct): ProductMedia[] {
  return [...(product.media ?? [])].sort((a, b) => a.sort_order - b.sort_order);
}

/** The lifestyle shot, where one exists. Used for editorial modules rather than grids. */
export function lifestyleImage(product: CatalogProduct): ProductMedia | undefined {
  return (product.media ?? []).find((m) => m.role === "lifestyle");
}

export function bySlug(
  products: CatalogProduct[] | null,
  slug: string,
): CatalogProduct | undefined {
  return products?.find((p) => p.slug === slug);
}

/**
 * The sizes a product is offered in, de-duplicated and in a sensible order.
 *
 * Variants carry a size and a colour, so a product with 12 variants may have 4 sizes across
 * 3 colours. Listing the raw variants would show every size four times.
 */
export function sizesOf(product: CatalogProduct): string[] {
  const order = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "ONE SIZE"];
  const sizes = [...new Set((product.variants ?? []).map((v) => v.size))];
  return sizes.sort((a, b) => {
    const ai = order.indexOf(a.toUpperCase());
    const bi = order.indexOf(b.toUpperCase());
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}

export function coloursOf(product: CatalogProduct): string[] {
  return [...new Set((product.variants ?? []).map((v) => v.color))];
}

/**
 * Pick a media role by rotation, so a rail of looks does not show four near-identical
 * plates.
 *
 * The capsule is small and looks deliberately share pieces — that is what a capsule is —
 * so three of four looks lead with the same garment. Rather than manufacture variety by
 * choosing a piece that is not the look's lead, each look shows its lead piece from a
 * DIFFERENT delivered view: front, detail, lifestyle, back. Every plate stays truthful to
 * the look it belongs to, and the rail stops looking like a printing error.
 *
 * Falls back to the primary image when a product has no artwork in the requested role.
 */
/* Front, detail and back only.
 *
 * NOT lifestyle. The lifestyle plates are composed differently from the product plates —
 * different geometry, and their baked type sits somewhere else — so the product crop lands
 * across it and the rail showed a look with stray lettering through the middle of it. The
 * three product views share one composition and therefore one crop. */
const VIEW_ROTATION = ["front", "detail", "back"] as const;

export function mediaByRotation(
  product: CatalogProduct,
  index: number,
): ProductMedia | undefined {
  const role = VIEW_ROTATION[index % VIEW_ROTATION.length]!;
  return (product.media ?? []).find((m) => m.role === role) ?? primaryImage(product);
}
