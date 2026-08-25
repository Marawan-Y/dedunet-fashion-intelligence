import { api, session } from "./client";
import type {
  CatalogProduct,
  CommerceModeDisclosure,
  CustomerOrder,
  TokenResponse,
} from "./types";

/* Every call the consumer client makes, in one place.
 *
 * Named for what the customer is doing rather than for the URL, so a route change is a
 * change here and not in twelve components. */

/** The five DEDUNET prototypes. Not /api/v1/products, which is the legacy fixture set. */
export function fetchCatalog(signal?: AbortSignal): Promise<CatalogProduct[]> {
  return api<CatalogProduct[]>("/catalog/products", { signal });
}

export function fetchProduct(slug: string, signal?: AbortSignal): Promise<CatalogProduct> {
  return api<CatalogProduct>(`/catalog/products/${encodeURIComponent(slug)}`, { signal });
}

/**
 * What mode this deployment is in.
 *
 * Asked once at boot and shared, because it is a property of the deployment rather than of
 * the page being viewed. Two surfaces genuinely need the answer — the purchase gate and
 * the empty order history — and they wait on this one request rather than issuing their
 * own.
 */
export function fetchCommerceMode(signal?: AbortSignal): Promise<CommerceModeDisclosure> {
  return api<CommerceModeDisclosure>("/commerce/mode", { signal });
}

export function signIn(email: string, password: string): Promise<TokenResponse> {
  return api<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function register(input: {
  email: string;
  password: string;
  full_name: string;
  marketing_consent?: boolean;
}): Promise<TokenResponse> {
  return api<TokenResponse>("/auth/register", { method: "POST", body: input });
}

export function fetchOrders(signal?: AbortSignal): Promise<CustomerOrder[]> {
  return api<CustomerOrder[]>("/me/orders", { authenticated: true, signal });
}

export function signOut(): void {
  session.clear();
}
