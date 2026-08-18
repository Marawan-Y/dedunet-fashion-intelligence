/**
 * What an empty order history says, and whether the mode can support the claim.
 *
 * Native Android preview acceptance, issue B. In `BRAND_PREVIEW_MODE` the screen read:
 *
 *     "Sandbox orders you place will appear here."
 *
 * Nothing can be placed in preview mode. `modes.assert_purchasable` refuses every purchase
 * before a payment call is reached, and a cart add answers 409 "this catalogue is in brand
 * preview". So the screen was inviting the customer to do something the server would refuse
 * -- the same class of untruth as the storefront banner, one screen further in.
 *
 * Derived from the authoritative commerce mode, never from stock.
 */

import React from "react";
import TestRenderer, { act } from "react-test-renderer";

import type { CommerceMode } from "../api/types";
import { ordersEmptyDetail } from "../brand";
import { OrdersScreen } from "../screens/OrdersScreen";
import type { AppState } from "../store";

const API_BASE = "http://10.0.2.2:18080";

// ------------------------------------------------------------------------ the wording

describe("orders empty state copy", () => {
  it("does not promise sandbox orders in preview mode", () => {
    const text = ordersEmptyDetail({ mode: "BRAND_PREVIEW_MODE" });

    expect(text).toBe("Purchasing is unavailable while this catalogue is in preview.");
    expect(text.toLowerCase()).not.toContain("sandbox");
  });

  it("offers sandbox wording in commerce-test mode", () => {
    const text = ordersEmptyDetail({ mode: "COMMERCE_TEST_MODE" });

    expect(text).toContain("Sandbox test orders");
    expect(text.toLowerCase()).not.toContain("preview");
  });

  it("keeps the two modes from sharing a message", () => {
    // A shared string is how the preview promise came back in the first place.
    expect(ordersEmptyDetail({ mode: "BRAND_PREVIEW_MODE" })).not.toBe(
      ordersEmptyDetail({ mode: "COMMERCE_TEST_MODE" })
    );
  });

  it.each([
    ["an unresolved mode", null],
    ["a blocked mode", { mode: null }],
    ["an unknown mode", { mode: "SOMETHING_ELSE" }],
    ["undefined", undefined],
  ])("promises nothing for %s", (_label, disclosure) => {
    // The honest answer before the deployment has said what it allows.
    const text = ordersEmptyDetail(disclosure as { mode?: string | null } | null);

    expect(text.toLowerCase()).not.toContain("sandbox");
    expect(text).toContain("once this deployment allows purchasing");
  });

  it("never infers the wording from stock", () => {
    // Same mode, opposite inventory: the copy must not move. A client reasoning "there is
    // stock, so orders must be placeable" would be right today and wrong the first time a
    // preview catalogue carries a non-zero count.
    const preview = { mode: "BRAND_PREVIEW_MODE" as const, purchasable: true };
    expect(ordersEmptyDetail(preview)).toBe(ordersEmptyDetail({ mode: "BRAND_PREVIEW_MODE" }));
  });
});

// ------------------------------------------------------------------------- the screen

function ordersApp(commerceMode: CommerceMode | null): AppState {
  return {
    apiBase: API_BASE,
    session: { accessToken: "tok-not-a-credential", role: "customer", email: "a@b.example" },
    commerceMode,
    navigate: jest.fn(),
    handleFailure: jest.fn(),
  } as unknown as AppState;
}

function mode(name: CommerceMode["mode"]): CommerceMode {
  return {
    mode: name,
    headline: "x",
    detail: ["y"],
    purchasable: name === "COMMERCE_TEST_MODE",
    payments: name === "COMMERCE_TEST_MODE" ? "sandbox" : "none",
    public_commerce_enabled: false,
  };
}

/** Render the orders list with an empty history, with the network stubbed to return none. */
async function renderEmptyOrders(commerceMode: CommerceMode | null): Promise<string> {
  global.fetch = jest.fn().mockImplementation(() =>
    Promise.resolve(
      new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } })
    )
  );
  let tree!: TestRenderer.ReactTestRenderer;
  await act(async () => {
    tree = TestRenderer.create(<OrdersScreen app={ordersApp(commerceMode)} />);
  });
  return JSON.stringify(tree.toJSON());
}

afterEach(() => jest.restoreAllMocks());

describe("the empty order history on screen", () => {
  it("does not promise sandbox orders in preview mode", async () => {
    const output = await renderEmptyOrders(mode("BRAND_PREVIEW_MODE"));

    expect(output).toContain("Purchasing is unavailable while this catalogue is in preview.");
    expect(output.toLowerCase()).not.toContain("sandbox orders you place");
  });

  it("offers sandbox wording in commerce-test mode", async () => {
    const output = await renderEmptyOrders(mode("COMMERCE_TEST_MODE"));

    expect(output).toContain("Sandbox test orders you place will appear here.");
    expect(output).not.toContain("Purchasing is unavailable");
  });

  it("promises nothing before the mode is known", async () => {
    const output = await renderEmptyOrders(null);

    expect(output).toContain("once this deployment allows purchasing");
    expect(output.toLowerCase()).not.toContain("sandbox");
  });

  it("still asks a signed-out customer to sign in, whatever the mode", () => {
    // Preserved behaviour: the mode-aware copy must not have displaced the signed-out path.
    let tree!: TestRenderer.ReactTestRenderer;
    act(() => {
      tree = TestRenderer.create(
        <OrdersScreen
          app={{ ...ordersApp(mode("BRAND_PREVIEW_MODE")), session: null } as AppState}
        />
      );
    });

    expect(JSON.stringify(tree.toJSON())).toContain("Please sign in to see your orders.");
  });
});
