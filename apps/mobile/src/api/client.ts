/**
 * HTTP client for the commerce API.
 *
 * Every failure the brief lists is a distinct, typed outcome rather than a generic thrown
 * Error, because the screens have to react differently: a 401 clears the session, a 429
 * shows a retry countdown, a malformed body is a bug to surface honestly, and a network
 * failure offers a retry. Collapsing them into one "something went wrong" is how a client
 * ends up logging a customer out because their Wi-Fi dropped.
 */

import { API_TIMEOUT_MS } from "../config";

export type ApiFailureKind =
  | "network" // request never produced a response
  | "timeout" // request exceeded API_TIMEOUT_MS
  | "unauthorized" // 401 -- session absent, invalid or expired
  | "forbidden" // 403
  | "not_found" // 404
  | "conflict" // 409 -- domain rule (e.g. out of stock)
  | "payment_declined" // 402
  | "rate_limited" // 429
  | "unavailable" // 502/503 -- provider or infrastructure
  | "client_error" // other 4xx
  | "server_error" // other 5xx
  | "malformed"; // 2xx whose body is not the shape we require

export class ApiError extends Error {
  readonly kind: ApiFailureKind;
  readonly status: number | null;
  /** Seconds from `Retry-After`, when the server supplied one. */
  readonly retryAfterSeconds: number | null;
  readonly correlationId: string | null;

  constructor(
    kind: ApiFailureKind,
    message: string,
    options: {
      status?: number | null;
      retryAfterSeconds?: number | null;
      correlationId?: string | null;
    } = {}
  ) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = options.status ?? null;
    this.retryAfterSeconds = options.retryAfterSeconds ?? null;
    this.correlationId = options.correlationId ?? null;
  }
}

/** Human-readable text for a failure. Never leaks a stack trace or provider payload. */
export function describeFailure(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Something went wrong. Please try again.";
  }
  switch (error.kind) {
    case "network":
      return "Cannot reach the store. Check your connection and try again.";
    case "timeout":
      return "The store took too long to respond. Please try again.";
    case "unauthorized":
      return "Your session has expired. Please sign in again.";
    case "forbidden":
      return "You do not have permission to do that.";
    case "not_found":
      return "That item is no longer available.";
    case "conflict":
      return error.message || "That is not possible right now.";
    case "payment_declined":
      return "The sandbox payment was declined. No charge was made.";
    case "rate_limited": {
      const wait = error.retryAfterSeconds;
      return wait && wait > 0
        ? `Too many requests. Please wait ${wait} second${wait === 1 ? "" : "s"} and try again.`
        : "Too many requests. Please wait a moment and try again.";
    }
    case "unavailable":
      return "The store is temporarily unavailable. Please try again shortly.";
    case "malformed":
      return "The store sent an unexpected response. Please try again.";
    case "server_error":
      return "The store had a problem. Please try again shortly.";
    case "client_error":
    default:
      return error.message || "That request could not be completed.";
  }
}

function kindForStatus(status: number): ApiFailureKind {
  if (status === 401) return "unauthorized";
  if (status === 402) return "payment_declined";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 429) return "rate_limited";
  if (status === 502 || status === 503) return "unavailable";
  if (status >= 500) return "server_error";
  return "client_error";
}

function parseRetryAfter(header: string | null): number | null {
  if (!header) return null;
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

/**
 * Pull a short message out of a FastAPI error body without ever returning a raw payload.
 *
 * FastAPI sends `{"detail": "..."}`, and 422 sends `{"detail": [ {...}, ... ]}`. The array
 * form is a validation report, not customer-facing text, so it is deliberately ignored.
 */
function extractDetail(body: unknown): string | null {
  if (typeof body !== "object" || body === null) return null;
  const detail = (body as { detail?: unknown }).detail;
  return typeof detail === "string" && detail.length <= 300 ? detail : null;
}

export type RequestOptions = {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

/**
 * Perform one API request.
 *
 * Resolves with the parsed JSON body. Rejects with `ApiError` for every failure mode.
 */
export async function request<T>(
  baseUrl: string,
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {}, signal } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  // Propagate an externally supplied abort (screen unmounted) into our controller.
  const onExternalAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", onExternalAbort);
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...headers,
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: controller.signal,
    });
  } catch (cause) {
    // An abort raised by our own timer is a timeout; anything else never reached the
    // server. Both are distinct from "the server answered with an error".
    const aborted = cause instanceof Error && cause.name === "AbortError";
    const externallyAborted = aborted && signal?.aborted === true;
    throw new ApiError(
      aborted && !externallyAborted ? "timeout" : "network",
      aborted && !externallyAborted ? "the request timed out" : "the store could not be reached"
    );
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", onExternalAbort);
  }

  const correlationId = response.headers.get("X-Correlation-ID");

  // Read the body once, as text, so a non-JSON error page cannot throw inside the parser
  // and be misreported as a network failure.
  let raw = "";
  try {
    raw = await response.text();
  } catch {
    throw new ApiError("malformed", "the response body could not be read", {
      status: response.status,
      correlationId,
    });
  }

  let parsed: unknown = null;
  if (raw.length > 0) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = null;
    }
  }

  if (!response.ok) {
    throw new ApiError(kindForStatus(response.status), extractDetail(parsed) ?? "request failed", {
      status: response.status,
      retryAfterSeconds: parseRetryAfter(response.headers.get("Retry-After")),
      correlationId,
    });
  }

  if (parsed === null && raw.length > 0) {
    throw new ApiError("malformed", "the response was not valid JSON", {
      status: response.status,
      correlationId,
    });
  }

  return parsed as T;
}
