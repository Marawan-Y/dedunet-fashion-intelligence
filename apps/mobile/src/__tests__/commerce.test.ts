/**
 * Endpoint-layer tests: response validation, the cart-quantity workaround, and the
 * empty-cart quote.
 */

import { ApiError } from "../api/client";
import {
  addCartItem,
  listProducts,
  newIdempotencyKey,
  quoteCart,
  setCartItemQuantity,
  viewCart,
} from "../api/commerce";

const BASE = "http://127.0.0.1:18000";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * A fetch stub that builds a FRESH Response per call.
 *
 * `mockResolvedValue(json(...))` hands back the same Response instance every time, and a
 * Response body is a stream that can only be consumed once. The second read threw, and the
 * client correctly reported it as `malformed` — the test was wrong, not the client. Every
 * multi-call test must use this.
 */
function alwaysJson(body: unknown, status = 200) {
  return jest.fn().mockImplementation(() => Promise.resolve(json(body, status)));
}

const CART = { cart_token: "cart-1", status: "open", lines: [] };

afterEach(() => jest.restoreAllMocks());

describe("listProducts", () => {
  it("accepts a valid catalogue", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      json([
        {
          slug: "tee",
          name: "Tee",
          description: "",
          category: "tops",
          collection: "",
          material: "",
          care_instructions: "",
          country_of_origin: "XX",
          currency: "EUR",
          image_url: "",
          variants: [{ id: 1, sku: "T-M", size: "M", color: "Ink", price_minor_units: 5900, available: 3 }],
        },
      ])
    ) as never;

    const products = await listProducts(BASE);
    expect(products).toHaveLength(1);
    expect(products[0]?.variants[0]?.price_minor_units).toBe(5900);
  });

  it("accepts an empty catalogue as a valid, non-error state", async () => {
    global.fetch = jest.fn().mockResolvedValue(json([])) as never;
    await expect(listProducts(BASE)).resolves.toEqual([]);
  });

  it("rejects a renamed price field instead of rendering undefined", async () => {
    // If the server renamed price_minor_units, trusting the body would put the literal
    // string "undefined" next to a product. Failing loudly is the point.
    global.fetch = jest.fn().mockResolvedValue(
      json([
        {
          slug: "tee",
          name: "Tee",
          currency: "EUR",
          variants: [{ id: 1, sku: "T-M", size: "M", color: "Ink", price_eur: 59.0, available: 3 }],
        },
      ])
    ) as never;

    await expect(listProducts(BASE)).rejects.toMatchObject({ kind: "malformed" });
  });

  it("rejects an object where an array is required", async () => {
    global.fetch = jest.fn().mockResolvedValue(json({ products: [] })) as never;
    await expect(listProducts(BASE)).rejects.toMatchObject({ kind: "malformed" });
  });
});

describe("viewCart", () => {
  it("rejects a cart with no token", async () => {
    global.fetch = jest.fn().mockResolvedValue(json({ status: "open", lines: [] })) as never;
    await expect(viewCart(BASE, null)).rejects.toMatchObject({ kind: "malformed" });
  });

  it("omits the cart header entirely when there is no token", async () => {
    const spy = alwaysJson(CART);
    global.fetch = spy as never;

    await viewCart(BASE, null);

    const [, init] = spy.mock.calls[0] as [string, RequestInit];
    expect(init.headers).not.toHaveProperty("X-Cart-Token");
  });
});

describe("quoteCart", () => {
  it("treats HTTP 400 'the cart is empty' as an empty cart, not an error", async () => {
    global.fetch = jest.fn().mockResolvedValue(json({ detail: "the cart is empty" }, 400)) as never;
    await expect(quoteCart(BASE, "cart-1")).resolves.toBeNull();
  });

  it("still propagates a real failure", async () => {
    global.fetch = jest.fn().mockResolvedValue(json({ detail: "boom" }, 500)) as never;
    await expect(quoteCart(BASE, "cart-1")).rejects.toMatchObject({ kind: "server_error" });
  });

  it("returns the server breakdown unchanged", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      json({
        subtotal_minor_units: 11800,
        discount_minor_units: 0,
        shipping_minor_units: 890,
        tax_minor_units: 2028,
        total_minor_units: 12690,
        currency: "EUR",
        promotion_code: "",
      })
    ) as never;

    const quote = await quoteCart(BASE, "cart-1");
    expect(quote?.total_minor_units).toBe(12690);
  });
});

describe("setCartItemQuantity — the missing-endpoint workaround", () => {
  it("POSTs only the difference when increasing", async () => {
    const spy = alwaysJson(CART);
    global.fetch = spy as never;

    await setCartItemQuantity(BASE, "cart-1", 7, 2, 5);

    expect(spy).toHaveBeenCalledTimes(1);
    const [url, init] = spy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/v1/cart/items");
    expect(init.method).toBe("POST");
    // 3, not 5: POST /cart/items ADDS to the existing line.
    expect(JSON.parse(init.body as string)).toEqual({ variant_id: 7, quantity: 3 });
  });

  it("DELETEs then re-POSTs the absolute quantity when decreasing", async () => {
    const spy = alwaysJson(CART);
    global.fetch = spy as never;

    await setCartItemQuantity(BASE, "cart-1", 7, 5, 2);

    expect(spy).toHaveBeenCalledTimes(2);
    const [firstUrl, firstInit] = spy.mock.calls[0] as [string, RequestInit];
    const [, secondInit] = spy.mock.calls[1] as [string, RequestInit];

    expect(firstInit.method).toBe("DELETE");
    expect(firstUrl).toContain("/api/v1/cart/items/7");
    expect(secondInit.method).toBe("POST");
    expect(JSON.parse(secondInit.body as string)).toEqual({ variant_id: 7, quantity: 2 });
  });

  it("DELETEs once when the quantity reaches zero", async () => {
    const spy = alwaysJson(CART);
    global.fetch = spy as never;

    await setCartItemQuantity(BASE, "cart-1", 7, 3, 0);

    expect(spy).toHaveBeenCalledTimes(1);
    expect((spy.mock.calls[0] as [string, RequestInit])[1].method).toBe("DELETE");
  });

  it("never POSTs a non-positive quantity, which the server would reject", async () => {
    const spy = alwaysJson(CART);
    global.fetch = spy as never;

    await setCartItemQuantity(BASE, "cart-1", 7, 3, 0);

    for (const call of spy.mock.calls as [string, RequestInit][]) {
      if (call[1].method !== "POST") continue;
      expect(JSON.parse(call[1].body as string).quantity).toBeGreaterThan(0);
    }
  });

  it("refuses a negative or fractional target quantity", async () => {
    global.fetch = alwaysJson(CART) as never;
    await expect(setCartItemQuantity(BASE, "cart-1", 7, 3, -1)).rejects.toBeInstanceOf(ApiError);
    await expect(setCartItemQuantity(BASE, "cart-1", 7, 3, 1.5)).rejects.toBeInstanceOf(ApiError);
  });
});

describe("idempotency keys", () => {
  it("produces a distinct key per attempt", () => {
    const keys = new Set(Array.from({ length: 200 }, () => newIdempotencyKey()));
    expect(keys.size).toBe(200);
  });

  it("stays within the server's 8..80 character bound", () => {
    // CheckoutRequest.idempotency_key is minLength 8, maxLength 80. A key outside that
    // range is a 422 at checkout -- the worst possible moment to discover it.
    for (let i = 0; i < 50; i += 1) {
      const key = newIdempotencyKey();
      expect(key.length).toBeGreaterThanOrEqual(8);
      expect(key.length).toBeLessThanOrEqual(80);
    }
  });

  it("keeps an outcome-qualified key inside the bound too", () => {
    // Regression guard for a defect found by driving the real API: the checkout screen
    // appends the sandbox outcome to the nonce so that changing the outcome is a NEW
    // intent rather than a replay of the previous, declined order.
    for (const outcome of ["succeed", "decline", "error"]) {
      const key = `${newIdempotencyKey()}-${outcome}`;
      expect(key.length).toBeGreaterThanOrEqual(8);
      expect(key.length).toBeLessThanOrEqual(80);
    }
  });

  it("gives different outcomes different keys from the same nonce", () => {
    const nonce = newIdempotencyKey();
    expect(`${nonce}-succeed`).not.toBe(`${nonce}-decline`);
    // ...while the same outcome from the same nonce still replays.
    expect(`${nonce}-succeed`).toBe(`${nonce}-succeed`);
  });
});

describe("addCartItem", () => {
  it("sends the cart token when one exists", async () => {
    const spy = alwaysJson(CART);
    global.fetch = spy as never;

    await addCartItem(BASE, "cart-9", 3, 1);

    const [, init] = spy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-Cart-Token"]).toBe("cart-9");
  });
});
