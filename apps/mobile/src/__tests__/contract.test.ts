/**
 * OpenAPI compatibility.
 *
 * Reads the COMMITTED contract at `packages/contracts/openapi/openapi.json` and asserts
 * that every endpoint and request field this app relies on still exists. If the backend
 * removes a path or renames a request field, this fails here rather than at runtime on a
 * device.
 *
 * Deliberate limit, stated rather than papered over: the commerce routes carry no
 * `response_model`, so the contract declares their 200 bodies as bare `{}`. This file can
 * therefore only pin REQUESTS. Response field names are pinned by `commerce.test.ts`
 * (which rejects a renamed field) and by the live smoke run recorded in the evidence.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { SANDBOX_PAYMENT_TOKENS } from "../api/types";

type OpenApi = {
  paths: Record<string, Record<string, unknown>>;
  components: { schemas: Record<string, { properties?: Record<string, unknown>; required?: string[] }> };
};

const CONTRACT_PATH = join(__dirname, "..", "..", "..", "..", "packages", "contracts", "openapi", "openapi.json");

const contract = JSON.parse(readFileSync(CONTRACT_PATH, "utf8")) as OpenApi;

describe("contract endpoints the mobile app depends on", () => {
  const required: [string, string][] = [
    ["/api/v1/catalog/products", "get"],
    ["/api/v1/catalog/products/{slug}", "get"],
    ["/api/v1/auth/login", "post"],
    ["/api/v1/auth/register", "post"],
    ["/api/v1/cart", "get"],
    ["/api/v1/cart/items", "post"],
    ["/api/v1/cart/items/{variant_id}", "delete"],
    ["/api/v1/cart/quote", "get"],
    ["/api/v1/checkout", "post"],
    ["/api/v1/me/orders", "get"],
    ["/api/v1/me/orders/{order_number}", "get"],
  ];

  it.each(required)("%s %s exists", (path, method) => {
    expect(contract.paths[path]).toBeDefined();
    expect(contract.paths[path]?.[method]).toBeDefined();
  });

  it("does not depend on the legacy fixture catalogue", () => {
    // The removed PoC called /api/v1/products, the legacy fixture endpoint with a
    // different auth model and a different payload. The rebuild uses /catalog/products.
    const source = readFileSync(join(__dirname, "..", "api", "commerce.ts"), "utf8");
    expect(source).toContain("/api/v1/catalog/products");
    expect(source).not.toMatch(/["'`]\/api\/v1\/products/);
  });
});

describe("request schemas the mobile app sends", () => {
  it("LoginRequest requires email and password", () => {
    const schema = contract.components.schemas.LoginRequest;
    expect(schema?.required).toEqual(expect.arrayContaining(["email", "password"]));
  });

  it("RegisterRequest requires email, password and full_name", () => {
    const schema = contract.components.schemas.RegisterRequest;
    expect(schema?.required).toEqual(expect.arrayContaining(["email", "password", "full_name"]));
    expect(Object.keys(schema?.properties ?? {})).toEqual(
      expect.arrayContaining(["email", "password", "full_name", "marketing_consent"])
    );
  });

  it("AddToCartRequest uses variant_id and quantity", () => {
    const schema = contract.components.schemas.AddToCartRequest;
    expect(schema?.required).toEqual(expect.arrayContaining(["variant_id", "quantity"]));
  });

  it("CheckoutRequest requires payment_method_token and idempotency_key", () => {
    const schema = contract.components.schemas.CheckoutRequest;
    expect(schema?.required).toEqual(
      expect.arrayContaining(["payment_method_token", "idempotency_key"])
    );
    expect(Object.keys(schema?.properties ?? {})).toEqual(
      expect.arrayContaining(["country_code", "promotion_code"])
    );
  });

  it("TokenResponse carries access_token and role", () => {
    const schema = contract.components.schemas.TokenResponse;
    expect(schema?.required).toEqual(expect.arrayContaining(["access_token", "role"]));
  });
});

describe("money on the wire", () => {
  /**
   * Scoped to the schemas the mobile app actually sends or receives.
   *
   * `price_eur` DOES still exist in `Product-Input` / `Product-Output`, and `budget_eur`
   * in `StylistRequest` — all part of the LEGACY fixture-backed PoC surface
   * (`/api/v1/products`, `/api/v1/stylist/recommend`) that the README documents as
   * preserved unchanged. The mobile app calls none of them, and `contract.test.ts` above
   * asserts that it never references `/api/v1/products`.
   *
   * An earlier version of this test asserted the string was absent from the WHOLE
   * contract. That was simply false, and a test that has to be deleted the moment someone
   * checks it is worse than no test. This one states the real boundary.
   */
  const COMMERCE_SCHEMAS = [
    "AddToCartRequest",
    "CheckoutRequest",
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "VariantSpec",
    "CreateProductRequest",
  ];

  it("no commerce schema exposes a major-unit price field", () => {
    for (const name of COMMERCE_SCHEMAS) {
      const serialised = JSON.stringify(contract.components.schemas[name] ?? {});
      expect(serialised).not.toContain("price_eur");
      expect(serialised).not.toContain("total_eur");
      expect(serialised).not.toContain("budget_eur");
    }
  });

  it("confirms the legacy PoC surface still carries major units, and is not used here", () => {
    // Recorded rather than asserted away: this is why the boundary above is scoped.
    const legacy = JSON.stringify(contract.components.schemas["Product-Output"] ?? {});
    expect(legacy).toContain("price_eur");
  });

  it("VariantSpec prices are integers, not numbers", () => {
    const schema = contract.components.schemas.VariantSpec;
    const price = schema?.properties?.price_minor_units as { type?: string } | undefined;
    expect(price?.type).toBe("integer");
  });
});

describe("sandbox payment tokens", () => {
  it("matches the tokens the sandbox gateway recognises", () => {
    // app/commerce/payments.py:102 keys its outcome off these exact strings.
    expect(SANDBOX_PAYMENT_TOKENS.decline).toBe("pm_decline");
    expect(SANDBOX_PAYMENT_TOKENS.error).toBe("pm_error");
    // Any other token succeeds; pm_success is our explicit, readable choice.
    expect(SANDBOX_PAYMENT_TOKENS.succeed).toBe("pm_success");
  });
});
