import { api, session } from "./client";
import type {
  BrandDetail,
  BrandListing,
  CatalogProduct,
  CommerceModeDisclosure,
  CustomerOrder,
  DidoInUse,
  DidoOptions,
  DidoSessionPayload,
  LookPayload,
  SaveKind,
  SavedBrandEntry,
  SavedListing,
  SavedLookEntry,
  SavedOverview,
  SavedProductEntry,
  SavedState,
  StyleOptions,
  StyleProfile,
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

/* ------------------------------------------------------------------ fashion network */

/** The brand network. Real domain data -- not the hardcoded list this page once used. */
export function fetchBrands(signal?: AbortSignal): Promise<BrandListing> {
  return api<BrandListing>("/brands?limit=100", { signal });
}

/** One brand and its catalogue. 404s for a brand the caller may not see. */
export function fetchBrand(slug: string, signal?: AbortSignal): Promise<BrandDetail> {
  return api<BrandDetail>(`/brands/${encodeURIComponent(slug)}`, { signal });
}

/* ------------------------------------------------------------------ saved items */

/**
 * Everything the signed-in customer has saved, in ONE request.
 *
 * This is what stops a page of twenty cards issuing twenty save-status requests. Fetched
 * once when a session appears and patched locally on every mutation.
 */
export function fetchSavedState(signal?: AbortSignal): Promise<SavedState> {
  return api<SavedState>("/me/saved/state", { authenticated: true, signal });
}

export function fetchSavedOverview(signal?: AbortSignal): Promise<SavedOverview> {
  return api<SavedOverview>("/me/saved", { authenticated: true, signal });
}

export function fetchSavedProducts(signal?: AbortSignal): Promise<SavedListing<SavedProductEntry>> {
  return api<SavedListing<SavedProductEntry>>("/me/saved/products?limit=100", {
    authenticated: true,
    signal,
  });
}

export function fetchSavedBrands(signal?: AbortSignal): Promise<SavedListing<SavedBrandEntry>> {
  return api<SavedListing<SavedBrandEntry>>("/me/saved/brands?limit=100", {
    authenticated: true,
    signal,
  });
}

export function fetchSavedLooks(signal?: AbortSignal): Promise<SavedListing<SavedLookEntry>> {
  return api<SavedListing<SavedLookEntry>>("/me/saved/looks?limit=100", {
    authenticated: true,
    signal,
  });
}

/** Save. Idempotent on the server: a repeated call succeeds and creates nothing. */
export function saveItem(kind: SaveKind, slug: string): Promise<unknown> {
  return api(`/me/saved/${kind}/${encodeURIComponent(slug)}`, {
    method: "POST",
    authenticated: true,
  });
}

/** Unsave. Also idempotent: unsaving something not saved succeeds. */
export function unsaveItem(kind: SaveKind, slug: string): Promise<unknown> {
  return api(`/me/saved/${kind}/${encodeURIComponent(slug)}`, {
    method: "DELETE",
    authenticated: true,
  });
}

/** The curated looks. Public and unauthenticated -- editorial content, not an engine. */
export function fetchLooks(signal?: AbortSignal): Promise<LookPayload[]> {
  return api<LookPayload[]>("/looks", { signal });
}

export function fetchLook(slug: string, signal?: AbortSignal): Promise<LookPayload> {
  return api<LookPayload>(`/looks/${encodeURIComponent(slug)}`, { signal });
}

/* ------------------------------------------------------------------ Style DNA */

/** The controlled vocabularies. Public: these are the platform's words, not anyone's data. */
export function fetchStyleOptions(signal?: AbortSignal): Promise<StyleOptions> {
  return api<StyleOptions>("/style-dna/options", { signal });
}

/** The signed-in customer's profile. 200 with `exists: false` when there is none. */
export function fetchStyleProfile(signal?: AbortSignal): Promise<StyleProfile> {
  return api<StyleProfile>("/me/style-dna", { authenticated: true, signal });
}

/**
 * Partial update. Only the keys present are changed; a key sent as `[]` or `null` clears.
 *
 * `expectedRevision` is how a stale tab is caught rather than allowed to overwrite: the
 * server answers 409 and the client offers a reload instead of silently winning.
 */
export function patchStyleProfile(
  patch: Record<string, unknown>,
  expectedRevision: number | null,
): Promise<StyleProfile> {
  return api<StyleProfile>("/me/style-dna", {
    method: "PATCH",
    authenticated: true,
    body: expectedRevision === null ? patch : { ...patch, expected_revision: expectedRevision },
  });
}

/** Delete the profile. Saved items, orders and the account are untouched. */
export function deleteStyleProfile(): Promise<{ deleted: boolean; profile: StyleProfile }> {
  return api<{ deleted: boolean; profile: StyleProfile }>("/me/style-dna", {
    method: "DELETE",
    authenticated: true,
  });
}

/* ------------------------------------------------------------------ Dido */

/** The conversation vocabularies. Public: the platform's words, not anyone's data. */
export function fetchDidoOptions(signal?: AbortSignal): Promise<DidoOptions> {
  return api<DidoOptions>("/dido/options", { signal });
}

/** The active session, or null. 200 either way, so absence is not read out of an error. */
export function fetchCurrentDidoSession(
  signal?: AbortSignal,
): Promise<{ session: DidoSessionPayload | null }> {
  return api<{ session: DidoSessionPayload | null }>("/me/dido/sessions/current", {
    authenticated: true,
    signal,
  });
}

export function startDidoSession(): Promise<DidoSessionPayload> {
  return api<DidoSessionPayload>("/me/dido/sessions", {
    method: "POST",
    authenticated: true,
  });
}

/**
 * Send one message.
 *
 * `clientMessageId` makes a retry safe: the server returns the existing turn rather than
 * storing the message twice. A timeout the client never saw is the ordinary cause of a
 * double submit, and this is cheaper than making the customer wonder.
 */
export function sendDidoMessage(
  sessionId: number,
  message: string,
  expectedRevision: number,
  clientMessageId: string,
): Promise<DidoSessionPayload> {
  return api<DidoSessionPayload>(`/me/dido/sessions/${sessionId}/messages`, {
    method: "POST",
    authenticated: true,
    body: {
      message,
      expected_revision: expectedRevision,
      client_message_id: clientMessageId,
    },
  });
}

export function correctDidoBrief(
  sessionId: number,
  changes: Record<string, unknown>,
  expectedRevision: number,
): Promise<DidoSessionPayload> {
  return api<DidoSessionPayload>(`/me/dido/sessions/${sessionId}/brief`, {
    method: "PATCH",
    authenticated: true,
    body: { changes, expected_revision: expectedRevision },
  });
}

export function completeDidoSession(sessionId: number): Promise<DidoSessionPayload> {
  return api<DidoSessionPayload>(`/me/dido/sessions/${sessionId}/complete`, {
    method: "POST",
    authenticated: true,
  });
}

export function deleteDidoSession(sessionId: number): Promise<{ deleted: boolean }> {
  return api<{ deleted: boolean }>(`/me/dido/sessions/${sessionId}`, {
    method: "DELETE",
    authenticated: true,
  });
}

/** What the session is using, grouped by source. "What do you know about me?" */
export function fetchDidoInUse(sessionId: number): Promise<DidoInUse> {
  return api<DidoInUse>(`/me/dido/sessions/${sessionId}/in-use`, { authenticated: true });
}
