import { defineConfig, devices } from "@playwright/test";

/* Browser-level acceptance for the DEDUNET consumer platform.
 *
 * This suite exists because Phase 2 shipped 493 passing tests over a build whose product
 * page was 4,766px of unstyled thumbnails and whose account page rendered raw form
 * controls. jsdom verifies what a function returns. It does not verify that the page
 * loads, that a stylesheet is attached, or that an image well contains an image.
 *
 * It is written to run against BOTH the classic client and its React replacement, so the
 * migration in ADR-0004 can be evidenced as parity rather than asserted as one. The only
 * difference between the two targets is how a route becomes a URL, which is what
 * DEDUNET_ROUTING selects. Assertions are on accessible names and visible text — never on
 * class names — precisely so they survive the change of implementation. */

const BASE = process.env.DEDUNET_BASE_URL ?? "http://localhost:13600";

/* The classic client is a hash router served under /storefront/; the React client uses
 * real paths at the origin root. Set to "hash" to point this suite at the old build. */
const ROUTING = process.env.DEDUNET_ROUTING ?? "path";

export default defineConfig({
  testDir: "./e2e",
  /* The evidence capture asserts nothing and takes minutes, so it is excluded from an
     acceptance run and enabled explicitly with DEDUNET_EVIDENCE=1. */
  testIgnore: process.env.DEDUNET_EVIDENCE ? undefined : /(evidence|home-visual)\.spec\.ts/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  /* One retry locally, and the reason matters.
   *
   * This suite drives a LIVE API on a developer machine. Under parallel browser load a
   * request occasionally does not complete in time; the application then renders its error
   * state, which is correct, and the test reports a missing feature, which is not. A single
   * retry separates "transient" from "broken" — a consistently failing test still fails,
   * twice, and is still a failure.
   *
   * This is not a way to make a red suite green. If a test needs the retry regularly, the
   * defect is real and the retry is hiding it: check the run report for flaky counts. */
  retries: process.env.CI ? 2 : 1,
  /* Capped rather than left to default, for two measured reasons.
   *
   * RESOURCE. The default is one worker per core, and at eight parallel browsers this
   * machine ran out of them: workers died with 0xC0000142 and Playwright reported the
   * crash as failed assertions on the accepted safety guards.
   *
   * REQUEST RATE. The API limits 300 requests per 60 seconds per client IP, and the whole
   * suite is one IP. Measured directly: a 400-request burst returns 233 x 200 and
   * 167 x 429, and ONE Home load now costs 22 requests to that origin — 20 of them static
   * brand media, which the limiter's default rule also covers. That is roughly thirteen
   * Home loads a minute before a single client is throttled.
   *
   * Two workers was enough before the visual rebuild and is not enough after it, because
   * the page legitimately shows far more imagery. One worker keeps the suite under the
   * threshold. It is slower and it is honest: the alternative is a gate that fails on
   * whichever surface happened to receive a 429.
   *
   * The limiter is NOT the thing to change here. That media is rate-limited alongside
   * mutating endpoints is a real observation about the product and is recorded for the
   * owner in evidence/phase-3/, not worked around in a test config.
   *
   * A suite that fails for reasons that are not about the application is worse than a
   * slower one. Raise this only alongside the limiter it has to live under. */
  workers: process.env.CI ? 1 : 1,
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never" }]]
    : [["list"], ["html", { open: "never" }]],
  outputDir: "./e2e-results",

  use: {
    baseURL: BASE,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    /* §26 asks for explicit viewport verification. The per-project viewport below is the
       desktop baseline; the responsive suite drives the rest itself. */
    testIdAttribute: "data-testid",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    /* WebKit matters more than the others here: physical iPhone Safari is a mandatory
       human acceptance target. This is NOT that acceptance — it is the automated check
       that should catch a WebKit-only break before a human ever picks up the device. */
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "mobile-safari", use: { ...devices["iPhone 13"] } },
  ],

  /* Started only when pointing at the React client's own dev server. Targeting the classic
     build or a container means the server is already up, and Playwright must not try to
     own it. */
  webServer: process.env.DEDUNET_BASE_URL
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:13600",
        reuseExistingServer: true,
        timeout: 120_000,
      },
});

export { ROUTING };
