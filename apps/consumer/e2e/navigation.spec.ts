import { test, expect } from "@playwright/test";
import { goto, urlFor, ROUTES, type RouteName } from "./routes";

/* §24. Every route is reached three ways, because they fail differently:
 *   - clicked, which exercises the router
 *   - direct URL, which exercises a cold document load
 *   - refreshed, which exercises server-side URL handling (an SPA on real paths needs a
 *     history fallback, and its absence is a 404 that only appears on reload)
 */

/** The heading each route must actually render. A hash that changes is not a route. */
const HEADINGS: Partial<Record<RouteName, RegExp>> = {
  home: /DEDUNET/i,
  dido: /Dido/i,
  discover: /Discover/i,
  discoverCategory: /Interview/i,
  looks: /Looks/i,
  look: /Quiet Interview/i,
  brands: /Brands/i,
  brand: /DEDUNET/i,
  shop: /Shop/i,
  product: /Measure Trouser/i,
  saved: /Saved/i,
  myStyle: /My Style/i,
  forBrands: /brands|styling intelligence/i,
  account: /Account|Sign in/i,
};

test.describe("direct URL load", () => {
  for (const [name, heading] of Object.entries(HEADINGS) as [RouteName, RegExp][]) {
    test(`${name} renders its own heading on a cold load`, async ({ page }) => {
      await goto(page, name);
      await expect(page.getByRole("heading", { level: 1 })).toContainText(heading);
      /* Exactly one h1 per document. Two is a structure bug that a screen reader
         surfaces long before a sighted reviewer notices. */
      await expect(page.locator("h1")).toHaveCount(1);
    });
  }
});

test.describe("refresh", () => {
  for (const name of Object.keys(HEADINGS) as RouteName[]) {
    test(`${name} survives a reload`, async ({ page }) => {
      await goto(page, name);
      await page.reload();
      await page.waitForLoadState("networkidle");
      await expect(page.getByRole("heading", { level: 1 })).toContainText(HEADINGS[name]!);
    });
  }
});

test("back and forward restore the previous route", async ({ page }) => {
  await goto(page, "home");
  await goto(page, "discover");
  await goto(page, "brands");

  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Discover/i);

  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/DEDUNET/i);

  await page.goForward();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Discover/i);
});

test("the primary journey is clickable end to end", async ({ page }) => {
  await goto(page, "home");

  await page.getByRole("link", { name: /discover/i }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Discover/i);

  await page.getByRole("link", { name: /dido/i }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Dido/i);

  await page.getByRole("link", { name: /^saved$/i }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Saved/i);

  await page.getByRole("link", { name: /account/i }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Account|Sign in/i);
});

test("an unknown route offers recovery rather than a blank page", async ({ page }) => {
  await goto(page, "missing");

  /* Not a blank page and not a raw exception: §23. The recovery link is the point —
     a 404 that dead-ends is still a dead end. */
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText(/does not exist|not found/i).first()).toBeVisible();

  await page.getByRole("link", { name: /DEDUNET|home/i }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/DEDUNET/i);
});

test("no route leaves the console carrying an error", async ({ page }) => {
  test.setTimeout(180_000); // walks every route in one test
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(String(e)));

  for (const name of Object.keys(ROUTES) as RouteName[]) {
    await page.goto(urlFor(name));
    await page.waitForLoadState("networkidle");
  }

  /* Failed API calls are a legitimate state this build must survive; an uncaught
     exception is not. Filter the former, fail on the latter. */
  const real = errors.filter((e) => !/Failed to load resource|ERR_|net::/i.test(e));
  expect(real, `console errors:\n${real.join("\n")}`).toHaveLength(0);
});
