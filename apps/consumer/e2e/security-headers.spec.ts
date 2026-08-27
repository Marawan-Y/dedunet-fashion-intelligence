import { test, expect } from "@playwright/test";

/* THE DOCUMENT SECURITY HEADER CONTRACT, asserted on real HTTP responses.
 *
 * The regression these guard against (F-1, staging cutover `455ac09`): nginx does not
 * inherit `add_header` into a location that declares one of its own, so the two locations
 * that set Cache-Control — `= /index.html` and `/assets/` — silently discarded all four
 * security headers. Every route in this SPA is served from index.html through the history
 * fallback, so that was every document on the site, shipped without X-Frame-Options.
 *
 * `services/commerce-api/tests/test_consumer_security_headers.py` pins the CONFIGURATION
 * invariant — every location that adds a header includes the contract back. That is the
 * test that catches the next person's edit. These tests are the other half: configuration
 * being right does not prove a deployment serves it, which is exactly the gap that let F-1
 * be reported as "declared at server level" while no document carried them.
 *
 * SCOPE. These describe the consumer nginx image. They are skipped unless the suite is
 * pointed at a deployed container, because a Vite dev server serves none of them and the
 * classic client served a subset — a failure in either case would be an accusation against
 * an application that was never responsible for these headers.
 */

const DEPLOYED = Boolean(process.env.DEDUNET_BASE_URL);
const PATH_ROUTING = (process.env.DEDUNET_ROUTING ?? "path") === "path";

const REQUIRED: Record<string, string> = {
  "x-robots-tag": "noindex, nofollow",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "referrer-policy": "strict-origin-when-cross-origin",
};

test.describe("security headers on deployed responses", () => {
  test.skip(
    !DEPLOYED || !PATH_ROUTING,
    "describes the consumer nginx image; set DEDUNET_BASE_URL to a deployed container",
  );

  /* The document paths that matter. Each reaches index.html by a different route through
     nginx, and F-1 hit all of them while /admin stayed correct and hid the problem. */
  for (const [label, path] of [
    ["the root document", "/"],
    ["a deep SPA route served by the history fallback", "/shop"],
    ["a nested SPA route", "/product/the-source-tee"],
    ["index.html requested directly", "/index.html"],
  ] as const) {
    test(`${label} carries every required security header`, async ({ request }) => {
      const response = await request.get(path);
      expect(response.status(), `${path} did not return 200`).toBe(200);

      const headers = response.headers();
      for (const [name, value] of Object.entries(REQUIRED)) {
        expect(headers[name], `${path} is missing ${name}`).toBeDefined();
        expect(headers[name]?.toLowerCase(), `${path} sent the wrong ${name}`).toBe(
          value.toLowerCase(),
        );
      }
    });
  }

  test("a hashed static asset carries them too", async ({ request }) => {
    /* /assets/ sets Cache-Control and so discarded the inherited headers exactly as
       index.html did. nosniff is the one that genuinely matters on a script. */
    const document = await request.get("/");
    const html = await document.text();
    const asset = html.match(/\/assets\/[A-Za-z0-9._-]+\.js/)?.[0];
    expect(asset, "no hashed asset referenced by the document").toBeTruthy();

    const response = await request.get(asset!);
    expect(response.status()).toBe(200);
    const headers = response.headers();
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    /* And the caching behaviour the location exists for is still intact -- the repair must
       not have traded one property for the other. */
    expect(headers["cache-control"]).toContain("immutable");
  });

  test("an API response keeps the upstream's own, stricter headers", async ({ request }) => {
    /* /api is the one location NOT given the document contract. The API sets its own
       baseline headers and its Referrer-Policy is `no-referrer`, which is STRICTER than the
       document policy. nginx add_header appends, and the Referrer Policy spec takes the
       last value -- so adding the contract here downgraded the API on every response.
       That was measured during this repair and removed. This test keeps it removed. */
    const response = await request.get("/api/v1/commerce/mode");
    expect(response.status()).toBe(200);
    const headers = response.headers();

    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["cache-control"]).toContain("no-store");

    /* The assertion that matters: no weaker policy appended beside the upstream's. */
    expect(headers["referrer-policy"]).toBe("no-referrer");
    expect(headers["referrer-policy"]).not.toContain("strict-origin-when-cross-origin");
  });

  test("the document is still uncacheable, so a stale bundle cannot be pinned", async ({
    request,
  }) => {
    const headers = (await request.get("/")).headers();
    expect(headers["cache-control"]).toContain("no-store");
  });

  test("same-origin /api still reaches the commerce API through the proxy", async ({
    request,
  }) => {
    /* The headers repair touched the /api location. This proves it did not break the
       proxying the cutover exists to provide. */
    const response = await request.get("/api/v1/commerce/mode");
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.mode).toBe("BRAND_PREVIEW_MODE");
    expect(body.purchasable).toBe(false);
  });
});
