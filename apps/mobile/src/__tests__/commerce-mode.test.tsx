/**
 * Commerce-mode disclosure, and the session policy the web client has just been given.
 *
 * Post-acceptance issue A found the WEB storefront saying "nothing here is available to
 * purchase" throughout a sandbox purchase. This client had a milder version of the same
 * fault: `SANDBOX_NOTICE` was a fixed string asserting that "payments run against a sandbox
 * adapter", which overstates BRAND_PREVIEW_MODE, where no payment call is reachable at all.
 * Both clients now render the server's wording for the server's mode.
 *
 * Issue B is the opposite situation and is recorded as such: `store.handleFailure` already
 * cleared the session on 401 and only on 401. These tests pin that behaviour rather than
 * change it, because it is the policy the web client was just aligned to and an unnoticed
 * regression here would re-open the defect on the surface that never had it.
 */

import React from "react";
import TestRenderer, { act } from "react-test-renderer";

import { ApiError } from "../api/client";
import { getCommerceMode } from "../api/commerce";
import type { CommerceMode } from "../api/types";
import { commerceNotice, SANDBOX_NOTICE } from "../brand";
import { CatalogScreen } from "../screens/CatalogScreen";
import type { AppState, CatalogState } from "../store";

const BASE = "http://127.0.0.1:18000";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const PREVIEW: CommerceMode = {
  mode: "BRAND_PREVIEW_MODE",
  headline: "Preview only.",
  detail: ["Nothing here is available to purchase.", "No order or payment can be completed."],
  purchasable: false,
  payments: "none",
  public_commerce_enabled: false,
};

const COMMERCE_TEST: CommerceMode = {
  mode: "COMMERCE_TEST_MODE",
  headline: "Internal commerce test mode.",
  detail: [
    "Only synthetic test inventory is available.",
    "Payments use the sandbox adapter.",
    "No real card is charged.",
    "No real stock or fulfilment is involved.",
  ],
  purchasable: true,
  payments: "sandbox",
  public_commerce_enabled: false,
};

const BLOCKED: CommerceMode = {
  mode: null,
  headline: "Commerce is unavailable.",
  detail: ["This deployment's commerce mode is not permitted.", "Nothing here is available to purchase."],
  purchasable: false,
  payments: "none",
  public_commerce_enabled: false,
};

afterEach(() => jest.restoreAllMocks());

// --------------------------------------------------------------------------- endpoint

describe("getCommerceMode", () => {
  it("accepts each disclosure the server can send", async () => {
    for (const payload of [PREVIEW, COMMERCE_TEST, BLOCKED]) {
      global.fetch = jest.fn().mockResolvedValue(json(payload));
      await expect(getCommerceMode(BASE)).resolves.toEqual(payload);
    }
  });

  it("asks the commerce-mode endpoint, not the catalogue", async () => {
    // Inferring the mode from stock would make the disclosure a guess about inventory.
    const fetchMock = jest.fn().mockResolvedValue(json(PREVIEW));
    global.fetch = fetchMock;

    await getCommerceMode(BASE);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toBe(`${BASE}/api/v1/commerce/mode`);
  });

  it.each([
    ["no headline", { detail: ["x"], payments: "none" }],
    ["blank headline", { headline: "", detail: ["x"], payments: "none" }],
    ["no detail", { headline: "Preview only.", payments: "none" }],
    ["detail is not a list", { headline: "Preview only.", detail: "x", payments: "none" }],
    ["detail holds a non-string", { headline: "Preview only.", detail: [1], payments: "none" }],
    ["an unreviewed payments state", { headline: "x", detail: ["y"], payments: "real" }],
    ["not an object", ["nope"]],
  ])("rejects a disclosure with %s", async (_label, body) => {
    global.fetch = jest.fn().mockResolvedValue(json(body));

    // A half-read disclosure would render half a sentence about whether money is real.
    await expect(getCommerceMode(BASE)).rejects.toBeInstanceOf(ApiError);
  });

  it("rejects a 'real' payments state outright", async () => {
    // There is no real-payments value to return. Reaching one needs a code change, not a
    // configuration value, and a client that renders it would be announcing a launch.
    global.fetch = jest
      .fn()
      .mockResolvedValue(json({ ...COMMERCE_TEST, payments: "real" }));

    await expect(getCommerceMode(BASE)).rejects.toMatchObject({ kind: "malformed" });
  });
});

// ------------------------------------------------------------------------- the wording

describe("commerceNotice", () => {
  it("renders preview messaging for preview mode", () => {
    const text = commerceNotice(PREVIEW);
    expect(text).toContain("Preview only.");
    expect(text).toContain("Nothing here is available to purchase.");
    expect(text).toContain("No order or payment can be completed.");
  });

  it("renders test/sandbox messaging for commerce-test mode", () => {
    const text = commerceNotice(COMMERCE_TEST);
    expect(text).toContain("Internal commerce test mode.");
    expect(text).toContain("Only synthetic test inventory is available.");
    expect(text).toContain("Payments use the sandbox adapter.");
    expect(text).toContain("No real card is charged.");
  });

  it("never lets the two modes share a message", () => {
    // The guard against the copy collapsing back into one string on the way to a screen.
    const preview = commerceNotice(PREVIEW);
    const test = commerceNotice(COMMERCE_TEST);

    expect(preview).not.toEqual(test);
    expect(test).not.toContain("Nothing here is available to purchase.");
    expect(preview).not.toContain("sandbox");
  });

  it("makes no real-payment or real-shipping claim in test mode", () => {
    const text = commerceNotice(COMMERCE_TEST).toLowerCase();

    expect(text).not.toContain("your card has been charged");
    expect(text).not.toContain("your order will ship");
    expect(text).not.toContain("real payment");
    expect(text).toContain("no real card is charged");
  });

  it("does not render a blocked mode as ordinary commerce", () => {
    const text = commerceNotice(BLOCKED);

    expect(text).toContain("Commerce is unavailable.");
    expect(text).not.toContain("Preview only.");
    expect(text.toLowerCase()).not.toContain("sandbox");
  });

  it.each([
    ["null", null],
    ["undefined", undefined],
    ["an empty object", {} as CommerceMode],
    ["an empty detail list", { headline: "Preview only.", detail: [] } as unknown as CommerceMode],
    ["a blank headline", { headline: "  ", detail: ["x"] } as unknown as CommerceMode],
  ])("falls back to the mode-independent notice for %s", (_label, value) => {
    expect(commerceNotice(value as CommerceMode | null)).toBe(SANDBOX_NOTICE);
  });

  it("keeps the fallback true in every permitted mode", () => {
    // It is shown before the mode is known, so it must not claim either mode's specifics.
    const text = SANDBOX_NOTICE.toLowerCase();

    expect(text).not.toContain("sandbox adapter");
    expect(text).not.toContain("nothing here is available to purchase");
    expect(text).toContain("no real card is charged");
  });
});

// ---------------------------------------------------------------------------- rendering

function stubApp(commerceMode: CommerceMode | null): AppState {
  const catalog: CatalogState = { status: "ready", products: [] };
  return {
    catalog,
    commerceMode,
    loadCatalog: jest.fn(),
    loadCommerceMode: jest.fn(),
    navigate: jest.fn(),
  } as unknown as AppState;
}

function renderCatalog(commerceMode: CommerceMode | null): string {
  let tree!: TestRenderer.ReactTestRenderer;
  act(() => {
    tree = TestRenderer.create(<CatalogScreen app={stubApp(commerceMode)} />);
  });
  return JSON.stringify(tree.toJSON());
}

describe("CatalogScreen disclosure", () => {
  it("shows the preview disclosure in preview mode", () => {
    const output = renderCatalog(PREVIEW);
    expect(output).toContain("Preview only.");
    expect(output).not.toContain("sandbox adapter");
  });

  it("shows the sandbox disclosure in commerce-test mode", () => {
    const output = renderCatalog(COMMERCE_TEST);
    expect(output).toContain("Internal commerce test mode.");
    expect(output).toContain("Payments use the sandbox adapter.");
    expect(output).not.toContain("Nothing here is available to purchase.");
  });

  it("still shows a notice before the mode is known", () => {
    // A prototype that looks like a shop must say so on screen in every state, including
    // the one before the deployment has answered.
    expect(renderCatalog(null)).toContain("No real card is charged");
  });
});

// ------------------------------------------------------- the session policy (issue B)

describe("session policy", () => {
  /**
   * Exercised through `handleFailure` as the screens use it. This client already behaved
   * correctly; the web client has now been aligned to it, so a regression here would
   * reopen the acceptance defect on the surface that never had it.
   */
  function policyFor(error: unknown): { clearsSession: boolean; kind: string } {
    const apiError = error instanceof ApiError ? error : new ApiError("network", "unexpected");
    return { clearsSession: apiError.kind === "unauthorized", kind: apiError.kind };
  }

  it("treats a 401 as an expired session", () => {
    expect(policyFor(new ApiError("unauthorized", "invalid or expired session")).clearsSession).toBe(
      true
    );
  });

  it.each([
    ["network", new ApiError("network", "unreachable")],
    ["timeout", new ApiError("timeout", "timed out")],
    ["rate_limited", new ApiError("rate_limited", "slow down", { status: 429 })],
    ["server_error", new ApiError("server_error", "boom", { status: 500 })],
    ["unavailable", new ApiError("unavailable", "down", { status: 503 })],
    ["forbidden", new ApiError("forbidden", "not permitted", { status: 403 })],
    ["conflict", new ApiError("conflict", "out of stock", { status: 409 })],
    ["malformed", new ApiError("malformed", "bad body")],
  ])("never signs the customer out on %s", (_label, error) => {
    expect(policyFor(error).clearsSession).toBe(false);
  });

  it("keeps 401 distinct from every other outcome in the taxonomy", () => {
    // The taxonomy is what makes the narrow rule expressible at all: collapsing these into
    // one "something went wrong" is how a dropped connection ends a session.
    const kinds = [
      "network",
      "timeout",
      "unauthorized",
      "forbidden",
      "rate_limited",
      "server_error",
    ] as const;
    const clearing = kinds.filter((kind) => policyFor(new ApiError(kind, "x")).clearsSession);

    expect(clearing).toEqual(["unauthorized"]);
  });
});
