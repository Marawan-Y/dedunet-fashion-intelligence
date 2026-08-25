import { test } from "@playwright/test";
import { goto } from "./routes";

/* Home at the five widths section 11 names. Capture only — asserts nothing. */
const WIDTHS = [390, 430, 768, 1280, 1440];

test.describe("@evidence home visual", () => {
  test.describe.configure({ timeout: 240_000 });

  for (const width of WIDTHS) {
    test(`home at ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: width < 700 ? 844 : 900 });
      await goto(page, "home");

      /* Scroll the whole page so lazy plates decode and every reveal has fired, then
         return to the top: a full-page capture taken before the reveals would document
         the animation rather than the page. */
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += Math.round(window.innerHeight * 0.6)) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 160));
        }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(2600);

      await page.screenshot({ path: `../../evidence/phase-3/home-visual/${width}.png`, fullPage: true });
      await page.screenshot({ path: `../../evidence/phase-3/home-visual/${width}-fold.png` });
    });
  }
});
