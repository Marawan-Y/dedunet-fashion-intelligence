import { test } from "@playwright/test";
import { goto, type RouteName } from "./routes";

/* Screen evidence for section 41.
 *
 * Not part of the acceptance suite — it asserts nothing and cannot fail a build. It exists
 * to produce the artefacts a human reviews, at the two viewports section 41 asks for, and
 * it is a separate file so that `--grep-invert @evidence` keeps a normal run fast.
 *
 * Run it with:
 *   npx playwright test evidence --project=chromium
 *
 * Deliberately capturing the BUILT application rather than the dev server, because the
 * built application is what ships and is what section 24 asks to be tested.
 */

const ROUTES: RouteName[] = [
  "home",
  "dido",
  "discover",
  "discoverCategory",
  "looks",
  "look",
  "brands",
  "brand",
  "shop",
  "product",
  "saved",
  "myStyle",
  "forBrands",
  "account",
  "orders",
  "cart",
  "missing",
];

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

test.describe("@evidence screen capture", () => {
  test.describe.configure({ timeout: 180_000 });

  for (const viewport of VIEWPORTS) {
    test(`capture every route at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      for (const route of ROUTES) {
        await goto(page, route);

        /* Scroll the whole page first so lazy images decode, then return to the top.
           A full-page capture of a page whose images have never entered the viewport
           documents the placeholders rather than the product. */
        await page.evaluate(async () => {
          for (let y = 0; y < document.body.scrollHeight; y += window.innerHeight) {
            window.scrollTo(0, y);
            await new Promise((r) => setTimeout(r, 100));
          }
          window.scrollTo(0, 0);
        });
        await page.waitForTimeout(600);

        await page.screenshot({
          path: `../../evidence/phase-3/screens/${viewport.name}/${route}.png`,
          fullPage: true,
        });
      }
    });
  }

  /* The states a route only reaches under a condition, captured deliberately because they
     are the ones nobody looks at until a customer hits one. */
  test("capture the states that are not the happy path", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });

    /* Error: the API is unreachable. This is the state the classic client showed as a
       blank page for the whole of Phase 2 on any route that needed data. */
    await page.route("**/api/v1/**", (r) => r.abort());
    await goto(page, "shop");
    await page.waitForTimeout(1200);
    await page.screenshot({ path: "../../evidence/phase-3/screens/states/shop-api-unreachable.png", fullPage: true });

    await page.unroute("**/api/v1/**");

    /* Dido mid-conversation, with the honest refusal on screen. */
    await goto(page, "dido");
    for (const label of ["Interview", "Formal", "100 to 250"]) {
      const option = page.getByRole("button", { name: label, exact: true });
      if (await option.count()) {
        await option.first().click();
        await page.waitForTimeout(2000);
      }
    }
    await page.waitForTimeout(1500);
    await page.screenshot({ path: "../../evidence/phase-3/screens/states/dido-cannot-style-yet.png", fullPage: true });

    /* The purchase refusal, which is the accepted safety behaviour. */
    await goto(page, "product");
    await page.screenshot({ path: "../../evidence/phase-3/screens/states/product-purchase-refused.png", fullPage: true });

    /* Form validation, which is the surface that failed acceptance. */
    await goto(page, "account");
    await page.getByRole("button", { name: /^sign in$/i }).click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: "../../evidence/phase-3/screens/states/account-validation.png", fullPage: true });

    /* Reduced motion, to evidence that the setting is honoured. */
    await page.emulateMedia({ reducedMotion: "reduce" });
    await goto(page, "home");
    await page.waitForTimeout(600);
    await page.screenshot({ path: "../../evidence/phase-3/screens/states/home-reduced-motion.png" });
  });
});
