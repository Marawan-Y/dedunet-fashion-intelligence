/**
 * Types for the commerce API.
 *
 * Source of truth, in order:
 *   1. `packages/contracts/openapi/openapi.json` for every REQUEST body and for
 *      `TokenResponse`, which are the only commerce shapes the contract types.
 *   2. `services/commerce-api/app/commerce/api.py` for the RESPONSE payloads, which the
 *      contract declares as bare `{}` because the routes carry no `response_model`.
 *
 * That gap is real and is recorded in the Workstream F evidence: the response field names
 * below are pinned by `__tests__/contract.test.ts`, which reads the committed contract and
 * asserts the request shapes, and by the live smoke run against the API. No field here was
 * invented.
 */

// ------------------------------------------------------------------ catalog (api.py:191)

export type Variant = {
  id: number;
  sku: string;
  size: string;
  color: string;
  price_minor_units: number;
  available: number;
};

export type Product = {
  slug: string;
  name: string;
  description: string;
  category: string;
  collection: string;
  material: string;
  care_instructions: string;
  /**
   * ISO-3166 alpha-2, or the deliberately invalid `XX`.
   *
   * `XX` means origin is NOT substantiated. The UI must never render this as
   * "Made in ...". See `originLabel()` in `src/origin.ts`.
   */
  country_of_origin: string;
  currency: string;
  image_url: string;
  variants: Variant[];
};

// --------------------------------------------------------------------- auth (api.py:78)

export type TokenResponse = {
  access_token: string;
  token_type: string;
  role: string;
};

// --------------------------------------------------------------------- cart (api.py:264)

export type CartLine = {
  variant_id: number;
  sku: string;
  product_name: string;
  size: string;
  color: string;
  quantity: number;
  unit_price_minor_units: number;
};

export type Cart = {
  cart_token: string;
  status: string;
  lines: CartLine[];
};

// ------------------------------------------------------------------- quote (pricing.py:57)

export type PriceBreakdown = {
  subtotal_minor_units: number;
  discount_minor_units: number;
  shipping_minor_units: number;
  tax_minor_units: number;
  total_minor_units: number;
  currency: string;
  promotion_code: string;
};

// ------------------------------------------------------------------- order (api.py:340)

export type OrderLine = {
  sku: string;
  product_name: string;
  size: string;
  color: string;
  quantity: number;
  unit_price_minor_units: number;
  line_total_minor_units: number;
};

export type Shipment = {
  carrier: string;
  tracking_number: string;
  status: string;
};

export type Order = {
  order_number: string;
  status: string;
  currency: string;
  subtotal_minor_units: number;
  discount_minor_units: number;
  shipping_minor_units: number;
  tax_minor_units: number;
  total_minor_units: number;
  promotion_code: string;
  placed_at: string | null;
  lines: OrderLine[];
  shipments: Shipment[];
};

/** POST /api/v1/checkout returns the order plus whether this was an idempotent replay. */
export type CheckoutResult = {
  order: Order;
  replayed: boolean;
};

/**
 * Sandbox payment-method tokens (`app/commerce/payments.py:102`).
 *
 * These select the outcome, exactly as a real provider sandbox does. They are NOT card
 * numbers and no card is ever charged.
 */
export const SANDBOX_PAYMENT_TOKENS = {
  succeed: "pm_success",
  decline: "pm_decline",
  error: "pm_error",
} as const;

export type SandboxOutcome = keyof typeof SANDBOX_PAYMENT_TOKENS;
