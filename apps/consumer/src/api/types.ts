/* Types for the commerce API.
 *
 * Written against packages/contracts/openapi/openapi.json AND against the payloads the
 * running service actually returns, because the two disagree in one way that matters: the
 * OpenAPI `Product` schema describes the legacy fixture catalogue served at
 * /api/v1/products, while the DEDUNET catalogue at /api/v1/catalog/products has a
 * different shape entirely — media roles, claim statuses, and no price.
 *
 * The five DEDUNET products carry NO price and are all sellable:false. That is not missing
 * data to be filled in with a plausible number. They are prototypes with no commercial
 * price, and any total this application displays would be invented. Nothing here provides
 * a default for it.
 */

/** How confident the platform is about a stated fact. Never render one as a claim. */
export type ClaimStatus = "UNVERIFIED" | "SUPPLIER_STATED" | "TEST_VERIFIED";

export type PublicationStatus = "preview" | "published" | "archived";

export interface ProductMedia {
  asset_id: string;
  role: "front" | "back" | "detail" | "lifestyle" | string;
  sort_order: number;
  path: string;
  /** Server-relative. Resolve through mediaUrl() before putting it in a src. */
  url: string;
  alt_text: string;
  status: string;
}

export interface CatalogVariant {
  sku: string;
  size: string;
  color: string;
  stock?: number;
}

/** A product in the DEDUNET catalogue. */
export interface CatalogProduct {
  slug: string;
  name: string;
  description: string;
  category: string;
  collection: string;
  collection_id: string;
  material: string;
  care_instructions: string;
  /** Deliberately the invalid code "XX" so it cannot be mistaken for a substantiated claim. */
  country_of_origin: string;
  intended_origin: string;
  currency: string;
  image_url: string;
  external_product_id: string;
  publication_status: PublicationStatus;
  /** false for every DEDUNET prototype. The purchase gate reads this. */
  sellable: boolean;
  inventory_status: string;
  evidence_status: string;
  material_claim_status: ClaimStatus;
  origin_claim_status: ClaimStatus;
  legal_brand_status: string;
  media_status: string;
  media: ProductMedia[];
  variants: CatalogVariant[];
  /** Absent on every prototype. Present only if a priced catalogue is ever served. */
  price_minor_units?: number;
  price_display?: string;
}

/** What commerce mode the deployment is in. Never assumed; always asked. */
export interface CommerceModeDisclosure {
  mode: "BRAND_PREVIEW_MODE" | "COMMERCE_TEST_MODE" | "PUBLIC_COMMERCE_MODE";
  headline: string;
  detail: string[];
  purchasable: boolean;
  payments: string;
  public_commerce_enabled: boolean;
}

export interface TokenResponse {
  access_token: string;
  role: string;
  token_type?: string;
}

export interface CustomerOrder {
  order_number: string;
  status: string;
  created_at: string;
  total_display?: string;
  currency?: string;
}

/** A failure that a view can render without knowing what went wrong. */
export class ApiError extends Error {
  readonly status: number;
  /** True when the request carried our credentials, which is what makes a 401 a session
   *  rejection rather than a failed sign-in attempt. */
  readonly sentCredentials: boolean;

  constructor(message: string, status: number, sentCredentials: boolean) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.sentCredentials = sentCredentials;
  }
}

/** Transport failure: no response, therefore no status and no evidence about the token. */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}
