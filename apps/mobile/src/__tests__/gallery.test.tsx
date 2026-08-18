/**
 * Product media gallery.
 *
 * The single-image assumption is the thing under test: a product now carries an ordered
 * `media` array, and the gallery must render all of it, in order, without inventing a
 * fallback image when there is none.
 */

import React from "react";
import TestRenderer, { act } from "react-test-renderer";

import type { Product, ProductMedia } from "../api/types";
import { Gallery } from "../components/Gallery";

const BASE = "http://127.0.0.1:18000";

function media(role: ProductMedia["role"], order: number): ProductMedia {
  return {
    asset_id: `DDN-TS01-${role.toUpperCase()}`,
    role,
    sort_order: order,
    path: `assets/brand-prototype/products/ddn-ts01-${role}.svg`,
    url: `/api/v1/media/assets/brand-prototype/products/ddn-ts01-${role}.svg`,
    alt_text: `Concept ${role} view of The Source Tee`,
    status: "PROTOTYPE_CONCEPT",
  };
}

function product(over: Partial<Product> = {}): Product {
  return {
    slug: "the-source-tee",
    name: "The Source Tee",
    description: "",
    category: "T-Shirts",
    collection: "FIRST PASSAGE / 01",
    material: "",
    care_instructions: "",
    country_of_origin: "XX",
    currency: "EUR",
    image_url: "",
    variants: [],
    ...over,
  };
}

function render(p: Product): TestRenderer.ReactTestRenderer {
  let tree!: TestRenderer.ReactTestRenderer;
  act(() => {
    tree = TestRenderer.create(<Gallery product={p} apiBase={BASE} />);
  });
  return tree;
}

/**
 * Host elements carrying a testID with this prefix.
 *
 * `typeof type === "string"` restricts the match to HOST elements. Without it every hit is
 * counted twice — once for the composite component and once for the host it renders — and
 * the first version of these tests reported exactly double the real count.
 */
function all(tree: TestRenderer.ReactTestRenderer, prefix: string) {
  return tree.root.findAll(
    (n: TestRenderer.ReactTestInstance) =>
      typeof n.type === "string" &&
      typeof n.props?.testID === "string" &&
      n.props.testID.startsWith(prefix)
  );
}

describe("Gallery", () => {
  it("renders all four DDN-TS01 media roles", () => {
    const tree = render(
      product({
        media: [media("front", 0), media("back", 1), media("detail", 2), media("lifestyle", 3)],
      })
    );
    expect(all(tree, "gallery-image-")).toHaveLength(4);
  });

  it("preserves the server's order and does not re-sort", () => {
    // sort_order is assigned deterministically at build time. Re-sorting here would make
    // the gallery differ between platforms for the same product.
    const tree = render(
      product({
        media: [media("front", 0), media("back", 1), media("detail", 2), media("lifestyle", 3)],
      })
    );
    const ids = all(tree, "gallery-item-").map((n) => String(n.props.testID));
    expect(ids).toEqual([
      "gallery-item-DDN-TS01-FRONT",
      "gallery-item-DDN-TS01-BACK",
      "gallery-item-DDN-TS01-DETAIL",
      "gallery-item-DDN-TS01-LIFESTYLE",
    ]);
  });

  it("renders a single image without assuming a gallery", () => {
    const tree = render(product({ media: [media("front", 0)] }));
    expect(all(tree, "gallery-image-")).toHaveLength(1);
  });

  it("renders NOTHING when there is no media, rather than a broken image", () => {
    expect(render(product({ media: [] })).toJSON()).toBeNull();
    expect(render(product()).toJSON()).toBeNull();
  });

  it("builds an absolute URL from the API base and the server-supplied url", () => {
    const tree = render(product({ media: [media("front", 0)] }));
    const image = all(tree, "gallery-image-")[0];
    const expectedUri =
      `${BASE}/api/v1/media/assets/brand-prototype/products/ddn-ts01-front.svg`;

    const source = image?.props.source;
    const sources = Array.isArray(source) ? source : [source];

    expect(
      sources.some(
        (entry: unknown) =>
          typeof entry === "object" &&
          entry !== null &&
          "uri" in entry &&
          (entry as { uri?: string }).uri === expectedUri
      )
    ).toBe(true);
  });

  it("uses the Side A alt text for accessibility", () => {
    const tree = render(product({ media: [media("front", 0)] }));
    const image = all(tree, "gallery-image-")[0];
    expect(image?.props.accessibilityLabel).toBe("Concept front view of The Source Tee");
  });

  it("falls back to a generated label when alt text is empty", () => {
    const bare = { ...media("back", 0), alt_text: "" };
    const tree = render(product({ media: [bare] }));
    const image = all(tree, "gallery-image-")[0];
    expect(image?.props.accessibilityLabel).toBe("The Source Tee — back view");
  });

  it("replaces a failed image with a placeholder and keeps the rest", () => {
    const tree = render(product({ media: [media("front", 0), media("back", 1)] }));
    const first = all(tree, "gallery-image-")[0];

    act(() => {
      first?.props.onError({
        nativeEvent: {
          error: "synthetic image failure",
        },
      });
    });

    expect(all(tree, "gallery-failed-")).toHaveLength(1);
    // The second image is unaffected: one broken asset must not empty the gallery.
    expect(all(tree, "gallery-image-")).toHaveLength(1);
  });

  it("labels concept artwork rather than presenting it as photography", () => {
    const tree = render(product({ media: [media("front", 0)] }));
    expect(JSON.stringify(tree.toJSON())).toContain("Concept artwork");
    expect(JSON.stringify(tree.toJSON())).not.toContain("photograph of");
  });

  it("does not label non-concept media as concept artwork", () => {
    const real = { ...media("front", 0), status: "APPROVED_PHOTOGRAPHY" };
    const tree = render(product({ media: [real] }));
    expect(JSON.stringify(tree.toJSON())).not.toContain("Concept artwork");
  });

  it("never renders a 'Made in' claim from gallery text", () => {
    const tree = render(
      product({ media: [media("front", 0)], intended_origin: "EG", origin_claim_status: "UNVERIFIED" })
    );
    expect(JSON.stringify(tree.toJSON()).toLowerCase()).not.toContain("made in");
  });
});
