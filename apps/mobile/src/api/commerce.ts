/**
 * Endpoint layer. One function per commerce operation the app performs.
 *
 * Response validation is deliberate and narrow: each function checks the shape it is about
 * to hand to a screen and raises `malformed` otherwise. Trusting the body means a renamed
 * server field surfaces as `undefined` inside a component -- typically as the string
 * "undefined" next to a price -- instead of as an honest error.
 */

import { ApiError, request } from "./client";
import type {
  Cart,
  CheckoutResult,
  Order,
  PriceBreakdown,
  Product,
  TokenResponse,
} from "./types";

// -------------------------------------------------------------------------- validation

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function malformed(what: string): never {
  throw new ApiError("malformed", `the store sent an unexpected ${what}`);
}

function requireProduct(value: unknown): Product {
  if (!isObject(value)) malformed("product");
  if (typeof value.slug !== "string" || typeof value.name !== "string") malformed("product");
  if (typeof value.currency !== "string") malformed("product");
  if (!Array.isArray(value.variants)) malformed("product");

  for (const variant of value.variants) {
    if (!isObject(variant)) malformed("variant");
    if (typeof variant.id !== "number") malformed("variant");
    if (typeof variant.price_minor_units !== "number") malformed("variant");
    if (typeof variant.available !== "number") malformed("variant");
  }
  return value as unknown as Product;
}

function requireCart(value: unknown): Cart {
  if (!isObject(value)) malformed("cart");
  if (typeof value.cart_token !== "string" || value.cart_token === "") malformed("cart");
  if (!Array.isArray(value.lines)) malformed("cart");
  for (const line of value.lines) {
    if (!isObject(line)) malformed("cart line");
    if (typeof line.variant_id !== "number") malformed("cart line");
    if (typeof line.quantity !== "number") malformed("cart line");
    if (typeof line.unit_price_minor_units !== "number") malformed("cart line");
  }
  return value as unknown as Cart;
}

function requireOrder(value: unknown): Order {
  if (!isObject(value)) malformed("order");
  if (typeof value.order_number !== "string") malformed("order");
  if (typeof value.total_minor_units !== "number") malformed("order");
  if (typeof value.currency !== "string") malformed("order");
  if (!Array.isArray(value.lines)) malformed("order");
  return value as unknown as Order;
}

function requireBreakdown(value: unknown): PriceBreakdown {
  if (!isObject(value)) malformed("quote");
  for (const key of [
    "subtotal_minor_units",
    "discount_minor_units",
    "shipping_minor_units",
    "tax_minor_units",
    "total_minor_units",
  ]) {
    if (typeof value[key] !== "number") malformed("quote");
  }
  if (typeof value.currency !== "string") malformed("quote");
  return value as unknown as PriceBreakdown;
}

// ------------------------------------------------------------------------------ headers

function cartHeader(cartToken: string | null): Record<string, string> {
  return cartToken ? { "X-Cart-Token": cartToken } : {};
}

function authHeader(accessToken: string): Record<string, string> {
  return { Authorization: `Bearer ${accessToken}` };
}

// ------------------------------------------------------------------------------ catalog

export async function listProducts(baseUrl: string, signal?: AbortSignal): Promise<Product[]> {
  const body = await request<unknown>(baseUrl, "/api/v1/catalog/products", { signal });
  if (!Array.isArray(body)) malformed("catalog");
  return body.map(requireProduct);
}

export async function getProduct(
  baseUrl: string,
  slug: string,
  signal?: AbortSignal
): Promise<Product> {
  const body = await request<unknown>(
    baseUrl,
    `/api/v1/catalog/products/${encodeURIComponent(slug)}`,
    { signal }
  );
  return requireProduct(body);
}

// --------------------------------------------------------------------------------- auth

export async function login(
  baseUrl: string,
  email: string,
  password: string
): Promise<TokenResponse> {
  const body = await request<unknown>(baseUrl, "/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
  });
  if (!isObject(body) || typeof body.access_token !== "string" || typeof body.role !== "string") {
    malformed("sign-in response");
  }
  return body as unknown as TokenResponse;
}

export async function register(
  baseUrl: string,
  email: string,
  password: string,
  fullName: string,
  marketingConsent: boolean
): Promise<TokenResponse> {
  const body = await request<unknown>(baseUrl, "/api/v1/auth/register", {
    method: "POST",
    body: {
      email,
      password,
      full_name: fullName,
      marketing_consent: marketingConsent,
    },
  });
  if (!isObject(body) || typeof body.access_token !== "string" || typeof body.role !== "string") {
    malformed("registration response");
  }
  return body as unknown as TokenResponse;
}

// --------------------------------------------------------------------------------- cart

export async function viewCart(baseUrl: string, cartToken: string | null): Promise<Cart> {
  const body = await request<unknown>(baseUrl, "/api/v1/cart", { headers: cartHeader(cartToken) });
  return requireCart(body);
}

/** Adds `quantity` to whatever is already on the line (`services.py:501` is additive). */
export async function addCartItem(
  baseUrl: string,
  cartToken: string | null,
  variantId: number,
  quantity: number
): Promise<Cart> {
  const body = await request<unknown>(baseUrl, "/api/v1/cart/items", {
    method: "POST",
    headers: cartHeader(cartToken),
    body: { variant_id: variantId, quantity },
  });
  return requireCart(body);
}

export async function removeCartItem(
  baseUrl: string,
  cartToken: string | null,
  variantId: number
): Promise<Cart> {
  const body = await request<unknown>(baseUrl, `/api/v1/cart/items/${variantId}`, {
    method: "DELETE",
    headers: cartHeader(cartToken),
  });
  return requireCart(body);
}

/**
 * Set a line to an absolute quantity.
 *
 * The API has no update-quantity endpoint: `POST /cart/items` ADDS to the existing line
 * (`desired = existing.quantity + quantity`), and the only other verb is DELETE. So:
 *
 *   - increase  -> POST the difference;
 *   - decrease  -> DELETE the line, then POST the new quantity;
 *   - zero      -> DELETE.
 *
 * The decrease path is genuinely not atomic. If the second call fails, the line is gone
 * rather than merely unchanged, so the caller is handed the real cart from whichever call
 * last succeeded and the customer sees the true state. Making this look atomic would be a
 * lie about a server that offers no such guarantee. A `PATCH /cart/items/{variant_id}`
 * endpoint would remove the whole problem and is recorded as a follow-up.
 */
export async function setCartItemQuantity(
  baseUrl: string,
  cartToken: string | null,
  variantId: number,
  currentQuantity: number,
  desiredQuantity: number
): Promise<Cart> {
  if (!Number.isSafeInteger(desiredQuantity) || desiredQuantity < 0) {
    throw new ApiError("client_error", "quantity must be a whole number");
  }
  if (desiredQuantity === currentQuantity) {
    return viewCart(baseUrl, cartToken);
  }
  if (desiredQuantity === 0) {
    return removeCartItem(baseUrl, cartToken, variantId);
  }
  if (desiredQuantity > currentQuantity) {
    return addCartItem(baseUrl, cartToken, variantId, desiredQuantity - currentQuantity);
  }
  await removeCartItem(baseUrl, cartToken, variantId);
  return addCartItem(baseUrl, cartToken, variantId, desiredQuantity);
}

/**
 * Price the cart.
 *
 * `services.quote_cart` raises "the cart is empty" -> HTTP 400 for an empty cart, so an
 * empty basket is a normal state reported as `null`, not an error banner.
 */
export async function quoteCart(
  baseUrl: string,
  cartToken: string | null,
  countryCode = "DE",
  promotionCode = ""
): Promise<PriceBreakdown | null> {
  const query = new URLSearchParams({ country_code: countryCode });
  if (promotionCode !== "") query.set("promotion_code", promotionCode);
  try {
    const body = await request<unknown>(baseUrl, `/api/v1/cart/quote?${query.toString()}`, {
      headers: cartHeader(cartToken),
    });
    return requireBreakdown(body);
  } catch (error) {
    if (error instanceof ApiError && error.status === 400) return null;
    throw error;
  }
}

// ----------------------------------------------------------------------------- checkout

export async function checkout(
  baseUrl: string,
  cartToken: string,
  accessToken: string,
  paymentMethodToken: string,
  idempotencyKey: string,
  countryCode = "DE",
  promotionCode = ""
): Promise<CheckoutResult> {
  const body = await request<unknown>(baseUrl, "/api/v1/checkout", {
    method: "POST",
    headers: { ...cartHeader(cartToken), ...authHeader(accessToken) },
    body: {
      payment_method_token: paymentMethodToken,
      idempotency_key: idempotencyKey,
      country_code: countryCode,
      promotion_code: promotionCode,
    },
  });
  if (!isObject(body)) malformed("checkout response");
  return {
    order: requireOrder(body.order),
    replayed: body.replayed === true,
  };
}

// ------------------------------------------------------------------------------- orders

export async function listOrders(baseUrl: string, accessToken: string): Promise<Order[]> {
  const body = await request<unknown>(baseUrl, "/api/v1/me/orders", {
    headers: authHeader(accessToken),
  });
  if (!Array.isArray(body)) malformed("order list");
  return body.map(requireOrder);
}

export async function getOrder(
  baseUrl: string,
  accessToken: string,
  orderNumber: string
): Promise<Order> {
  const body = await request<unknown>(
    baseUrl,
    `/api/v1/me/orders/${encodeURIComponent(orderNumber)}`,
    { headers: authHeader(accessToken) }
  );
  return requireOrder(body);
}

/**
 * Idempotency key for a checkout attempt.
 *
 * Stable per attempt and never reused, so a retried request replays the original order
 * rather than creating a second one. `Math.random` is fine here: this is a collision-
 * avoidance key, not a security token.
 */
export function newIdempotencyKey(): string {
  const random = Math.random().toString(36).slice(2, 12);
  return `mob-${Date.now().toString(36)}-${random}`;
}
