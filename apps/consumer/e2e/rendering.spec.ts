import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { goto, type RouteName } from "./routes";

/* The regression suite for the two defects that failed human acceptance at 9b63791.
 *
 * Both were invisible to 493 passing tests, and both are the same shape: the page rendered
 * a container and nothing verified that anything was IN it. These assertions look at the
 * composed page the way a person does. */

/** Routes whose whole purpose is to show clothing. An empty image well fails all of them. */
const EDITORIAL: RouteName[] = ["home", "discover", "looks", "look", "brands", "brand", "shop"];

test.describe("every media slot contains media", () => {
  for (const route of EDITORIAL) {
    test(`${route} renders no empty image wells`, async ({ page }) => {
      await goto(page, route);

      /* A media slot is anything the design system marks as one. It must contain a real
         painted image, an inline svg, or a CSS background — or, if the media genuinely
         does not exist, an explicitly labelled placeholder that says so. What it may not
         be is an empty coloured rectangle, which is what all 27 of them were. */
      const empty = await page.evaluate(() => {
        const slots = [...document.querySelectorAll("[data-media-slot]")];
        return slots
          .filter((s) => {
            if (s.querySelector("svg")) return false;
            if (s.hasAttribute("data-media-placeholder")) return false;
            /* An img with a real src counts as filled even if naturalWidth is still 0:
               below-the-fold images are lazy by design, and treating "not yet scrolled
               into view" as "empty" would punish the correct behaviour. Whether an image
               that DID load is broken is a separate assertion further down. */
            const img = s.querySelector("img");
            if (img && (img as HTMLImageElement).getAttribute("src")) return false;
            const bg = getComputedStyle(s).backgroundImage;
            if (bg && bg !== "none") return false;
            return true;
          })
          .map((s) => s.getAttribute("data-media-slot") ?? s.className);
      });

      expect(empty, `empty media slots: ${JSON.stringify(empty)}`).toHaveLength(0);
    });
  }
});

test.describe("no image is broken", () => {
  for (const route of EDITORIAL) {
    test(`${route} paints every img it renders`, async ({ page }) => {
      await goto(page, route);
      await page.waitForTimeout(500);

      const broken = await page.evaluate(() =>
        [...document.images]
          .filter((i) => i.complete && i.naturalWidth === 0)
          .map((i) => i.currentSrc || i.src),
      );
      expect(broken, `broken images: ${JSON.stringify(broken)}`).toHaveLength(0);
    });
  }
});

test.describe("every image is described", () => {
  for (const route of EDITORIAL) {
    test(`${route} gives every img an alt attribute`, async ({ page }) => {
      await goto(page, route);
      const missing = await page.evaluate(() =>
        [...document.images].filter((i) => !i.hasAttribute("alt")).map((i) => i.src),
      );
      expect(missing, `images with no alt: ${JSON.stringify(missing)}`).toHaveLength(0);
    });
  }
});

/* THE CSS CONTRACT.
 *
 * At 9b63791 `index.html` stopped loading `styles.css` while `app.js` kept emitting its
 * class names. Seventeen classes rendered with no rule in any attached stylesheet —
 * `two`, `form`, the whole `pdp__*` family — which is why Account rendered raw form
 * controls and the product page was 4,766px of unstyled thumbnails.
 *
 * No test could see it, because no test looked at the relationship between what the
 * document emits and what the stylesheets define. This one does. */
const ALL: RouteName[] = [
  "home", "dido", "discover", "discoverCategory", "looks", "look", "brands", "brand",
  "shop", "product", "saved", "myStyle", "forBrands", "account", "orders", "cart",
];

test.describe("no class renders without a rule", () => {
  for (const route of ALL) {
    test(`${route} emits only classes some stylesheet defines`, async ({ page }) => {
      await goto(page, route);

      const orphans = await page.evaluate(() => {
        const defined = new Set<string>();
        const walk = (rules: CSSRuleList) => {
          for (const rule of rules) {
            const sel = (rule as CSSStyleRule).selectorText;
            if (sel) {
              for (const m of sel.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)) defined.add(m[1]!);
            }
            const nested = (rule as CSSGroupingRule).cssRules;
            if (nested) walk(nested);
          }
        };
        for (const sheet of document.styleSheets) {
          try { walk(sheet.cssRules); } catch { /* cross-origin sheet; not ours */ }
        }

        const used = new Set<string>();
        for (const el of document.querySelectorAll("[class]")) {
          for (const c of el.classList) used.add(c);
        }
        return [...used].filter((c) => !defined.has(c)).sort();
      });

      expect(orphans, `classes with no CSS rule: ${JSON.stringify(orphans)}`).toHaveLength(0);
    });
  }
});

/* §5: a route does not count as implemented because a fixture exists and a hash changed.
 * These floors are deliberately low — they catch a stub, not a thin page. At 9b63791 brand
 * detail rendered 13 elements and Account rendered 20. */
const SUBSTANCE: Record<string, number> = {
  home: 120, discover: 60, looks: 50, look: 40, brands: 40, brand: 40,
  shop: 50, product: 60, dido: 40, saved: 25, myStyle: 40, forBrands: 30, account: 40,
};

test.describe("routes render substance, not stubs", () => {
  for (const [route, floor] of Object.entries(SUBSTANCE)) {
    test(`${route} renders at least ${floor} elements`, async ({ page }) => {
      await goto(page, route as RouteName);

      /* A route whose data failed to load renders its error state, which is correct
         behaviour and a completely different fact from "this route is a stub". Reporting
         the element count for it accuses the wrong thing. */
      await assertLoaded(page, route);

      const count = await page.locator("main *").count();
      expect(count, `${route} rendered ${count} elements`).toBeGreaterThanOrEqual(floor);
    });
  }
});

/* The empty-slot check above is only as good as the slots the client marks. A client that
 * marks none of them passes it while showing nothing — which is exactly how 27 empty image
 * wells shipped. This asserts the outcome instead of the annotation: an editorial route
 * shows clothing, or it is not doing its job. */
const MINIMUM_IMAGERY: Partial<Record<RouteName, number>> = {
  home: 3, discover: 3, looks: 3, look: 1, brands: 2, brand: 1, shop: 3,
};

test.describe("editorial routes actually show clothing", () => {
  for (const [route, floor] of Object.entries(MINIMUM_IMAGERY) as [RouteName, number][]) {
    test(`${route} paints at least ${floor} images`, async ({ page }) => {
      await goto(page, route);
      await assertLoaded(page, route);

      /* Scroll the page so lazy images below the fold actually decode. Without this the
         assertion measures how much fits above the fold, which is a viewport-height test
         wearing an imagery test's name. */
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += window.innerHeight) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 120));
        }
        window.scrollTo(0, 0);
      });
      /* Poll rather than sample once after a fixed wait.
       *
       * Lazy images decode asynchronously after the scroll that reveals them, so a single
       * reading taken n milliseconds later measures machine load as much as the page. This
       * asks repeatedly until the count is reached or the budget runs out, which is the
       * same assertion without the race. */
      await expect
        .poll(
          () => page.evaluate(() => [...document.images].filter((i) => i.naturalWidth > 0).length),
          { message: `${route} did not paint ${floor} images`, timeout: 15_000 },
        )
        .toBeGreaterThanOrEqual(floor);
    });
  }
});

/**
 * Fail with the truth when a route could not load its data.
 *
 * Every surface here renders an error state rather than a blank page when a request fails,
 * which is the behaviour section 23 asks for. But an error state has few elements and no
 * images, so a test measuring substance or imagery reports "this route is a stub" — an
 * accusation against a feature that is present and working. This makes the two failures say
 * different things, and quotes what the page actually said.
 */
async function assertLoaded(page: Page, route: string): Promise<void> {
  const error = page.getByTestId("error-state");
  if (await error.count()) {
    const detail = (await error.first().innerText()).replace(/\s+/g, " ").trim();
    throw new Error(`${route} did not load its data; the page reported: ${detail}`);
  }
}
