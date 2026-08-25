import { test, expect } from "@playwright/test";
import { goto, type RouteName } from "./routes";

/* §27, structural. This is not an audited accessibility result and must never be reported
 * as one — there is no axe run and no screen-reader pass here. It asserts the structure
 * those audits depend on, so a regression is caught before an audit is ever booked. */

const ROUTES: RouteName[] = [
  "home", "dido", "discover", "looks", "look", "brands", "brand",
  "shop", "product", "saved", "myStyle", "forBrands", "account",
];

test.describe("landmarks and headings", () => {
  for (const route of ROUTES) {
    test(`${route} has one main, one h1 and no skipped heading levels`, async ({ page }) => {
      await goto(page, route);

      await expect(page.getByRole("main")).toHaveCount(1);
      await expect(page.getByRole("banner")).toHaveCount(1);
      await expect(page.locator("h1")).toHaveCount(1);

      /* A jump from h1 to h3 is how a screen-reader user loses the outline. */
      const skips = await page.evaluate(() => {
        const levels = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")]
          .map((h) => Number(h.tagName[1]));
        const bad: string[] = [];
        for (let i = 1; i < levels.length; i++) {
          if (levels[i]! - levels[i - 1]! > 1) bad.push(`h${levels[i - 1]} -> h${levels[i]}`);
        }
        return bad;
      });
      expect(skips, `skipped heading levels: ${skips.join(", ")}`).toHaveLength(0);
    });
  }
});

test("every navigation is distinguishable by name", async ({ page }) => {
  await goto(page, "home");

  /* Several unnamed <nav>s are announced identically and a user cannot tell which is
     which. Each must carry its own accessible name. */
  const unnamed = await page.evaluate(() =>
    [...document.querySelectorAll("nav")]
      .filter((n) => !n.getAttribute("aria-label") && !n.getAttribute("aria-labelledby"))
      .length,
  );
  expect(unnamed, "every nav needs an accessible name").toBe(0);
});

test("the skip link is the first thing keyboard focus reaches", async ({ page }, testInfo) => {
  await goto(page, "home");

  /* The contract, asserted on every engine: the skip link is the first element in the
     document's tab order, and it points at main. */
  const contract = await page.evaluate(() => {
    const tabbable = [...document.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )].filter((el) => !el.hasAttribute("disabled"));
    const first = tabbable[0];
    return {
      text: first?.textContent?.trim() ?? "",
      href: first?.getAttribute("href") ?? "",
      focusable: first ? first.tabIndex >= 0 : false,
    };
  });

  expect(contract.text).toMatch(/skip/i);
  expect(contract.href).toBe("#main");
  expect(contract.focusable).toBe(true);

  /* The keypress, asserted only where the engine tabs to links at all.
   *
   * Safari does not put links in the tab order unless the user turns on full keyboard
   * access — it is off by default — so pressing Tab in WebKit skips straight past the skip
   * link to the first tabbable non-link. That is the browser's behaviour and not this
   * application's defect, and asserting it here would be asserting that WebKit is Chrome.
   * The DOM contract above is what actually has to hold, and it holds everywhere. */
  const tabsToLinks = !testInfo.project.name.includes("webkit")
    && !testInfo.project.name.includes("safari");
  if (!tabsToLinks) return;

  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
  expect(focused).toMatch(/skip/i);
});

test("focus is visible when navigating by keyboard", async ({ page }) => {
  await goto(page, "home");

  /* Tab until focus actually lands on something, rather than assuming the second press
     does it.
   *
   * The engines genuinely differ here and neither is wrong. Chromium tabs through links,
   * so the second press is a nav link. WebKit does not put links in the tab order unless
   * the user turns on full keyboard access, so on Home the only tabbable element is the
   * looks rail — and the press after it returns focus to `body` as the order wraps.
   * Asserting "the second Tab" therefore tests the engine, not the application. Asserting
   * "whatever Tab reaches is visibly focused" tests the thing that matters. */
  let indicator: { found: boolean; visible: boolean; on: string } = {
    found: false,
    visible: false,
    on: "",
  };

  for (let press = 0; press < 6; press++) {
    await page.keyboard.press("Tab");
    indicator = await page.evaluate(() => {
      const a = document.activeElement as HTMLElement | null;
      if (!a || a === document.body) return { found: false, visible: false, on: "body" };
      const s = getComputedStyle(a);
      const outline = s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0;
      const shadow = s.boxShadow !== "none" && s.boxShadow !== "";
      return {
        found: true,
        visible: outline || shadow,
        on: `${a.tagName}.${String(a.className).slice(0, 30)}`,
      };
    });
    if (indicator.found) break;
  }

  expect(indicator.found, "Tab reached nothing focusable at all").toBe(true);
  expect(
    indicator.visible,
    `no visible focus indicator on ${indicator.on}`,
  ).toBe(true);
});

test.describe("form controls are labelled", () => {
  for (const route of ["account", "shop", "myStyle"] as RouteName[]) {
    test(`${route} binds a label to every field`, async ({ page }) => {
      await goto(page, route);

      const unlabelled = await page.evaluate(() => {
        const out: string[] = [];
        for (const el of document.querySelectorAll("input, select, textarea")) {
          const input = el as HTMLInputElement;
          if (input.type === "hidden") continue;
          const byFor = input.id && document.querySelector(`label[for="${CSS.escape(input.id)}"]`);
          const wrapped = input.closest("label");
          const aria = input.getAttribute("aria-label") || input.getAttribute("aria-labelledby");
          if (!byFor && !wrapped && !aria) out.push(`${input.type}#${input.id || "(no id)"}`);
        }
        return out;
      });

      expect(unlabelled, `unlabelled fields: ${unlabelled.join(", ")}`).toHaveLength(0);
    });
  }
});

test("reduced motion is respected", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await goto(page, "home");

  /* §9 requires every animation to have a reduced-motion behaviour. Zeroing the durations
     centrally is what makes that true by construction rather than per-component. */
  const animated = await page.evaluate(() => {
    const out: string[] = [];
    for (const el of document.querySelectorAll("main *, header *")) {
      const s = getComputedStyle(el);
      const dur = parseFloat(s.animationDuration) || 0;
      const trans = parseFloat(s.transitionDuration) || 0;
      if (dur > 0.05 || trans > 0.05) out.push(`${el.tagName}.${el.className}`);
    }
    return out.slice(0, 10);
  });

  expect(animated, `still animating under reduced motion: ${animated.join(", ")}`).toHaveLength(0);
});

test("status changes are announced through a live region", async ({ page }) => {
  await goto(page, "home");

  /* Implicit regions count too: role="status" is a polite live region whether or not
     aria-live is spelled out, and counting only the explicit ones would miss exactly the
     duplication this guards against. Loading skeletons have detached by now. */
  const regions = await page.locator('[aria-live], [role="status"]').count();
  expect(regions, "there must be a live region for status messages").toBeGreaterThan(0);

  /* Several competing live regions is how a message ends up announced by none of them. */
  expect(regions, "too many live regions compete with each other").toBeLessThanOrEqual(2);
});
