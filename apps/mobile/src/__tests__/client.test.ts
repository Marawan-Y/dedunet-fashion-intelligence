/**
 * Failure-taxonomy tests for the HTTP client.
 *
 * Each of the failure modes the brief lists is asserted to produce its own `kind`, because
 * the screens branch on that value. A test that only checked "it threw" would pass with
 * every failure collapsed into one, which is the bug.
 */

import { ApiError, describeFailure, request } from "../api/client";

function jsonResponse(body: unknown, init: { status?: number; headers?: Record<string, string> } = {}) {
  const { status = 200, headers = {} } = init;
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

const BASE = "http://127.0.0.1:18000";

/** Await a rejection and return it as a typed ApiError, failing if it resolved. */
async function captureError(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) return error;
    throw error;
  }
  throw new Error("expected the request to reject, but it resolved");
}

describe("request", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("returns the parsed body on success", async () => {
    global.fetch = jest.fn().mockResolvedValue(jsonResponse([{ slug: "a" }])) as never;
    await expect(request(BASE, "/api/v1/catalog/products")).resolves.toEqual([{ slug: "a" }]);
  });

  it("classifies 401 as unauthorized", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(jsonResponse({ detail: "invalid or expired session" }, { status: 401 })) as never;

    await expect(request(BASE, "/api/v1/me/orders")).rejects.toMatchObject({
      kind: "unauthorized",
      status: 401,
    });
  });

  it("classifies 429 and surfaces Retry-After", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      jsonResponse(
        { detail: "rate limit exceeded", reason: "RATE_LIMIT_EXCEEDED" },
        { status: 429, headers: { "Retry-After": "37" } }
      )
    ) as never;

    const error = await captureError(request(BASE, "/api/v1/auth/login", { method: "POST" }));

    expect(error).toBeInstanceOf(ApiError);
    expect(error.kind).toBe("rate_limited");
    expect(error.retryAfterSeconds).toBe(37);
    expect(describeFailure(error)).toContain("37 second");
  });

  it("classifies 402 as a declined payment", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(jsonResponse({ detail: "payment was declined" }, { status: 402 })) as never;

    const error = await captureError(request(BASE, "/api/v1/checkout", { method: "POST" }));
    expect(error.kind).toBe("payment_declined");
    expect(describeFailure(error)).toContain("No charge was made");
  });

  it("classifies 503 as temporarily unavailable, not a hard failure", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(jsonResponse({ detail: "payment provider unavailable" }, { status: 503 })) as never;

    await expect(request(BASE, "/api/v1/checkout", { method: "POST" })).rejects.toMatchObject({
      kind: "unavailable",
    });
  });

  it("classifies 409 as a conflict and keeps the server's short message", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      jsonResponse({ detail: "not enough stock available for that quantity" }, { status: 409 })
    ) as never;

    const error = await captureError(request(BASE, "/api/v1/cart/items", { method: "POST" }));
    expect(error.kind).toBe("conflict");
    expect(describeFailure(error)).toBe("not enough stock available for that quantity");
  });

  it("classifies a rejected fetch as a network failure, not an auth failure", async () => {
    // The distinction matters: treating a dropped connection as a 401 would sign the
    // customer out because their Wi-Fi blipped.
    global.fetch = jest.fn().mockRejectedValue(new TypeError("Network request failed")) as never;

    const error = await captureError(request(BASE, "/api/v1/catalog/products"));
    expect(error.kind).toBe("network");
    expect(error.kind).not.toBe("unauthorized");
  });

  it("distinguishes a timeout from a plain network failure", async () => {
    // Caught by the mutation harness: replacing the AbortError check with `false` made
    // every timeout report as "network" and no test noticed. The two are different to a
    // customer -- a timeout is worth retrying immediately, an unreachable host is not --
    // and describeFailure gives them different text.
    const abort = new Error("The operation was aborted");
    abort.name = "AbortError";
    global.fetch = jest.fn().mockRejectedValue(abort) as never;

    const error = await captureError(request(BASE, "/api/v1/catalog/products"));

    expect(error.kind).toBe("timeout");
    expect(error.kind).not.toBe("network");
    expect(describeFailure(error)).toContain("too long");
  });

  it("reports an externally cancelled request as a network failure, not a timeout", async () => {
    // A screen unmounting aborts its own request. That is not the server being slow.
    const controller = new AbortController();
    controller.abort();
    const abort = new Error("aborted");
    abort.name = "AbortError";
    global.fetch = jest.fn().mockRejectedValue(abort) as never;

    const error = await captureError(
      request(BASE, "/api/v1/catalog/products", { signal: controller.signal })
    );
    expect(error.kind).toBe("network");
  });

  it("reports a non-JSON 200 body as malformed rather than crashing", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      new Response("<html>gateway</html>", { status: 200, headers: { "Content-Type": "text/html" } })
    ) as never;

    await expect(request(BASE, "/api/v1/catalog/products")).rejects.toMatchObject({
      kind: "malformed",
    });
  });

  it("never leaks a FastAPI 422 validation array into customer-facing text", async () => {
    global.fetch = jest.fn().mockResolvedValue(
      jsonResponse({ detail: [{ loc: ["body", "email"], msg: "field required" }] }, { status: 422 })
    ) as never;

    const error = await captureError(request(BASE, "/api/v1/auth/register", { method: "POST" }));
    expect(describeFailure(error)).not.toContain("loc");
    expect(describeFailure(error)).not.toContain("[object Object]");
  });

  it("captures the correlation id when the server sends one", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(
        jsonResponse({ detail: "nope" }, { status: 500, headers: { "X-Correlation-ID": "abc123" } })
      ) as never;

    const error = await captureError(request(BASE, "/api/v1/catalog/products"));
    expect(error.correlationId).toBe("abc123");
  });

  it("sends the cart token and bearer token as headers when supplied", async () => {
    const spy = jest.fn().mockResolvedValue(jsonResponse({ cart_token: "t", lines: [] }));
    global.fetch = spy as never;

    await request(BASE, "/api/v1/cart", {
      headers: { "X-Cart-Token": "cart-1", Authorization: "Bearer sess-1" },
    });

    const [, init] = spy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-Cart-Token"]).toBe("cart-1");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer sess-1");
  });
});

describe("describeFailure", () => {
  it("gives every failure kind its own customer-facing sentence", () => {
    const kinds = [
      "network",
      "timeout",
      "unauthorized",
      "forbidden",
      "not_found",
      "rate_limited",
      "unavailable",
      "malformed",
      "server_error",
      "payment_declined",
    ] as const;

    const messages = kinds.map((kind) => describeFailure(new ApiError(kind, "")));
    expect(new Set(messages).size).toBe(kinds.length);
    for (const message of messages) {
      expect(message.length).toBeGreaterThan(0);
      expect(message).not.toContain("undefined");
    }
  });

  it("does not leak a stack trace for an unknown error", () => {
    const message = describeFailure(new Error("boom at line 42"));
    expect(message).not.toContain("boom");
    expect(message).not.toContain("line 42");
  });
});
