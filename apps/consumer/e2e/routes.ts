import { expect, type Page } from "@playwright/test";

/**
 * The route table, as user-facing destinations rather than URLs.
 *
 * Kept separate from the URL form because this suite runs against two implementations:
 * the classic hash router under `/storefront/#/discover` and the React client at
 * `/discover`. A test says `goto(page, "discover")` and neither knows nor cares.
 */
export const ROUTES = {
  home: "/",
  dido: "/dido",
  discover: "/discover",
  discoverCategory: "/discover/interview",
  looks: "/looks",
  look: "/look/quiet-interview",
  brands: "/brands",
  brand: "/brand/dedunet",
  shop: "/shop",
  product: "/product/the-measure-trouser",
  saved: "/saved",
  myStyle: "/my-style",
  forBrands: "/for-brands",
  account: "/account",
  orders: "/orders",
  cart: "/cart",
  missing: "/nonsense-route-that-does-not-exist",
} as const;

export type RouteName = keyof typeof ROUTES;

const HASH = (process.env.DEDUNET_ROUTING ?? "path") === "hash";

/** The URL a route becomes, in whichever routing style the target uses. */
export function urlFor(route: RouteName): string {
  const path = ROUTES[route];
  return HASH ? `/storefront/#${path}` : path;
}

/**
 * Navigate by real URL — a full document load, which is what "direct URL" means.
 *
 * Deliberately NOT waitForLoadState("networkidle"). A Vite dev server holds an HMR
 * WebSocket open for the life of the page, so the network is never idle and every call
 * burns the full timeout before failing for a reason that has nothing to do with the
 * application. Waiting for the route's own heading is both faster and a stronger
 * assertion: it waits for the thing the test actually cares about having rendered.
 */
export async function goto(page: Page, route: RouteName): Promise<void> {
  await page.goto(urlFor(route), { waitUntil: "domcontentloaded" });
  /* The 404 route has a heading too, so this is safe for every destination. Swallowed on
     timeout so the assertion that follows reports the real problem rather than this. */
  await page
    .locator("main h1")
    .first()
    .waitFor({ state: "attached", timeout: 15_000 })
    .catch(() => undefined);

  /* Then wait for the data to settle.
   *
   * The heading renders before the data arrives, so asserting straight after it measures
   * the skeleton — which is how "brands renders at least 40 elements" failed at 24 while
   * the page was in fact fine.
   *
   * toHaveCount(0) rather than waitFor({state:"detached"}): the latter burns its full
   * timeout on the many routes that fetch nothing and therefore never render a skeleton at
   * all, which took the suite from six minutes to over thirty. This polls and returns
   * immediately when the count is already zero. */
  await expect(page.locator('[data-testid="loading-state"]'))
    .toHaveCount(0, { timeout: 15_000 })
    .catch(() => undefined);
}
