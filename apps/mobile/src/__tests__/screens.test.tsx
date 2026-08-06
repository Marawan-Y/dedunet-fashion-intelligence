/**
 * Screen-level state rendering.
 *
 * Uses react-test-renderer directly rather than adding @testing-library/react-native: the
 * assertions here are about which testID is present for a given state, and the extra
 * dependency was the one package that could not resolve against the SDK 56 react pin.
 */

import React from "react";
import TestRenderer, { act } from "react-test-renderer";

import { ApiError } from "../api/client";
import { CatalogScreen } from "../screens/CatalogScreen";
import type { AppState, CatalogState } from "../store";

function findByTestId(tree: TestRenderer.ReactTestRenderer, testID: string): boolean {
  return tree.root.findAll((node: TestRenderer.ReactTestInstance) => node.props?.testID === testID)
    .length > 0;
}

/** Minimal app-state stub. Only the fields CatalogScreen reads need to be real. */
function stubApp(catalog: CatalogState): AppState {
  return {
    catalog,
    loadCatalog: jest.fn(),
    navigate: jest.fn(),
  } as unknown as AppState;
}

function render(catalog: CatalogState): TestRenderer.ReactTestRenderer {
  let tree!: TestRenderer.ReactTestRenderer;
  act(() => {
    tree = TestRenderer.create(<CatalogScreen app={stubApp(catalog)} />);
  });
  return tree;
}

describe("CatalogScreen states", () => {
  it("shows the loading state and neither empty nor error", () => {
    const tree = render({ status: "loading" });
    expect(findByTestId(tree, "catalog-loading")).toBe(true);
    expect(findByTestId(tree, "catalog-empty")).toBe(false);
    expect(findByTestId(tree, "catalog-error")).toBe(false);
  });

  it("shows the empty state for a genuinely empty catalogue, not an error", () => {
    const tree = render({ status: "ready", products: [] });
    expect(findByTestId(tree, "catalog-empty")).toBe(true);
    expect(findByTestId(tree, "catalog-error")).toBe(false);
    expect(findByTestId(tree, "catalog-loading")).toBe(false);
  });

  it("shows the failed-fetch state with a retry, not an empty catalogue", () => {
    const tree = render({ status: "error", error: new ApiError("network", "unreachable") });
    expect(findByTestId(tree, "catalog-error")).toBe(true);
    expect(findByTestId(tree, "catalog-empty")).toBe(false);
  });

  it("renders rate-limit feedback with the retry delay", () => {
    const error = new ApiError("rate_limited", "rate limit exceeded", {
      status: 429,
      retryAfterSeconds: 12,
    });
    const tree = render({ status: "error", error });

    expect(findByTestId(tree, "catalog-error")).toBe(true);
    expect(JSON.stringify(tree.toJSON())).toContain("12 second");
  });

  it("always shows the sandbox notice", () => {
    // A prototype that looks like a shop must say so on screen, in every state.
    const states: CatalogState[] = [
      { status: "loading" },
      { status: "ready", products: [] },
      { status: "error", error: new ApiError("network", "x") },
    ];
    for (const state of states) {
      expect(findByTestId(render(state), "sandbox-notice")).toBe(true);
    }
  });

  it("renders a product with no variants without producing Infinity", () => {
    const tree = render({
      status: "ready",
      products: [
        {
          slug: "ghost",
          name: "No Variants",
          description: "",
          category: "tops",
          collection: "",
          material: "",
          care_instructions: "",
          country_of_origin: "XX",
          currency: "EUR",
          image_url: "",
          variants: [],
        },
      ],
    });

    const output = JSON.stringify(tree.toJSON());
    expect(output).toContain("Price unavailable");
    expect(output).not.toContain("Infinity");
    expect(output).not.toContain("€Infinity");
    expect(output).not.toContain("NaN");
  });

  it("never renders a 'Made in' claim for a product carrying an origin code", () => {
    const tree = render({
      status: "ready",
      products: [
        {
          slug: "tee",
          name: "Tee",
          description: "",
          category: "tops",
          collection: "Passage",
          material: "100% cotton",
          care_instructions: "",
          country_of_origin: "EG",
          currency: "EUR",
          image_url: "",
          variants: [
            { id: 1, sku: "T-M", size: "M", color: "Ink", price_minor_units: 5900, available: 2 },
          ],
        },
      ],
    });

    expect(JSON.stringify(tree.toJSON()).toLowerCase()).not.toContain("made in");
  });
});
