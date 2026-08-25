import { ApiError, NetworkError } from "./types";

/* The API seam.
 *
 * Where the API lives is baked in at BUILD time, exactly as the classic client did it and
 * for the same reason: the web container runs with a read-only root filesystem, so nothing
 * may write into the served directory after start. ADR-0004 keeps that guarantee.
 *
 * An unset base means "the page host on the development API port", which is correct for a
 * bare checkout and for docker-compose.yml, and wrong for staging — whose API is published
 * on 18080. Staging passes the value through at image build.
 */
const DEV_API_PORT = "18000";

function resolveBase(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (configured) return configured.replace(/\/+$/, "");

  /* Same-origin: the API is reachable on this host, so requests need no base at all.
   *
   * Two real topologies want this. In development the Vite server proxies /api to the
   * backend, which keeps requests same-origin and means no CORS entry is needed for a port
   * that exists on one machine. In deployment it is the reverse-proxy shape, where one
   * gateway fronts both the client and the API — which is also the configuration the
   * browser E2E suite runs against, so the suite exercises the built artefact rather than
   * a dev server. */
  if (import.meta.env.DEV || import.meta.env.VITE_API_SAME_ORIGIN === "true") return "";

  if (typeof window === "undefined") return "";
  return `${window.location.protocol}//${window.location.hostname}:${DEV_API_PORT}`;
}

export const API_BASE = resolveBase();

const API_PREFIX = "/api/v1";

/**
 * Resolve a server-relative media path to something an `src` can load.
 *
 * The API is a different origin from this client in every supported topology, so a
 * root-relative path resolves against the CLIENT and 404s. This is the one place that
 * knows it, which is why no component builds a media URL by hand.
 */
export function mediaUrl(pathOrUrl: string | null | undefined): string {
  if (!pathOrUrl) return "";
  if (/^(https?:)?\/\//i.test(pathOrUrl) || pathOrUrl.startsWith("data:")) return pathOrUrl;
  const path = pathOrUrl.startsWith("/") ? pathOrUrl : `${API_PREFIX}/media/${pathOrUrl}`;
  return `${API_BASE}${path}`;
}

/* ------------------------------------------------------------------ session storage */

const TOKEN_KEY = "dedunet_token";
const ROLE_KEY = "dedunet_role";
const CART_KEY = "dedunet_cart";

/* Read through to localStorage on every access rather than caching at module load.
 *
 * The classic client read the token once at startup into a module-level object. That is a
 * real bug surface — a token written afterwards was never adopted, and it is also what made
 * the first version of the 401 browser test pass for the wrong reason. Reading through
 * means there is one source of truth and no staleness window. */
export const session = {
  get token(): string {
    return localStorage.getItem(TOKEN_KEY) ?? "";
  },
  get role(): string {
    return localStorage.getItem(ROLE_KEY) ?? "";
  },
  get cartToken(): string {
    return localStorage.getItem(CART_KEY) ?? "";
  },
  get signedIn(): boolean {
    return Boolean(localStorage.getItem(TOKEN_KEY));
  },
  adopt(token: string, role: string): void {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(ROLE_KEY, role);
    notify();
  },
  /** Forget the customer session. The cart is kept deliberately: the basket is the device's. */
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    notify();
  },
};

const listeners = new Set<() => void>();
function notify() {
  for (const l of listeners) l();
}
export function onSessionChange(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Should this failure end the session?
 *
 * ONLY a 401 answered to a request that actually carried our credentials. Everything else
 * is the network, the server or a limiter having a bad moment, and none of them are
 * evidence about the token:
 *
 *   transport failure    no response, so no status to read
 *   429                  the request was never evaluated
 *   5xx                  the server failed to answer, not refused to
 *   403                  authenticated fine, just not permitted
 *   401 unauthenticated  a failed sign-in attempt; there is no session to end
 *
 * Signing a customer out because their train went into a tunnel is a worse defect than the
 * one this prevents, so the condition is narrow on purpose. Accepted behaviour, carried
 * across from the classic client unchanged.
 */
function isSessionRejection(status: number, sentCredentials: boolean): boolean {
  return status === 401 && sentCredentials;
}

/* ---------------------------------------------------------------------- the request */

export interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** Send the bearer token if there is one. Off by default so a public call cannot
   *  accidentally turn a 401 into a sign-out. */
  authenticated?: boolean;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options.headers,
  };

  const token = session.token;
  const sentCredentials = Boolean(options.authenticated && token);
  if (sentCredentials) headers["Authorization"] = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const url = `${API_BASE}${API_PREFIX}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal ?? null,
    });
  } catch (cause) {
    /* No response at all. Deliberately NOT a session rejection: there is no status, so
       there is no evidence the token is bad. */
    throw new NetworkError(cause instanceof Error ? cause.message : "Failed to fetch");
  }

  if (!response.ok) {
    if (isSessionRejection(response.status, sentCredentials)) session.clear();
    throw new ApiError(await readError(response), response.status, sentCredentials);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** The server's own message when it gives one; never a swallowed body. */
async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown; message?: unknown };
    const detail = payload.detail ?? payload.message;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  } catch {
    /* Not JSON. Fall through to the status line, which is still more use than "error". */
  }
  return `${response.status} ${response.statusText}`.trim();
}
