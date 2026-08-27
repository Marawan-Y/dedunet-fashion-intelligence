import { test, expect } from "@playwright/test";
import { goto } from "./routes";

/* THE PRODUCT PRICE, asserted in a real browser.
 *
 * The regression these guard against (F-2, staging cutover `455ac09`): every product page
 * rendered "Not priced". The client read a product-level `price_display` that
 * /api/v1/catalog/products has never sent, while the authoritative price sat on each
 * variant — every Source Tee variant is 7200 EUR minor units. The type definition asserted
 * in a comment that the catalogue had no prices, so nothing looked for them.
 *
 * `src/lib/money.test.ts` pins the derivation rule itself, including the range and absent
 * cases this catalogue's data cannot currently produce. These tests pin what a person
 * actually sees, which is the half that failed: the rule was never wrong, it was never
 * called.
 *
 * A PRICE IS NOT AN OFFER. Every one of these products is priced and none is purchasable,
 * so each test that asserts a price also asserts the refusal still stands beside it.
 */

test.describe("product price", () => {
  /* The React client only: `product-price` is its testid, and the direct product URLs
     below are real paths. The classic client rendered its own price from the same variant
     data under a hash route, and asserting this markup against it would be a false
     failure. */
  test.skip(
    (process.env.DEDUNET_ROUTING ?? "path") !== "path",
    "asserts the React client's price markup",
  );

  test("the Source Tee shows its authoritative price, not an unpriced state", async ({
    page,
  }) => {
    await page.goto("/product/the-source-tee");

    await expect(
      page.getByRole("heading", { level: 1 }),
      "the product did not load, so its price could not be checked",
    ).toContainText(/Source Tee/i, { timeout: 20_000 });

    /* 7200 EUR minor units, formatted by the canonical rule. Asserted as visible text
       rather than through the testid alone, because the defect was a person seeing the
       wrong words on a page. */
    /* EXACT text, not a substring. The accepted presentation is "€72.00" — the classic
       client never appended a currency code beside the symbol, and an early cut of this
       repair rendered "€72.00 EUR". `toHaveText` with a string asserts the whole node. */
    await expect(page.getByTestId("product-price")).toHaveText("€72.00");
    await expect(page.getByText("Not priced")).toHaveCount(0);
  });

  test("showing a price does not make the product purchasable", async ({ page }) => {
    /* THE POINT. F-2 must not be repaired by making the page look like a shop. */
    await page.goto("/product/the-source-tee");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/Source Tee/i, {
      timeout: 20_000,
    });

    await expect(page.getByTestId("product-price")).toHaveText(/€72\.00/);

    const control = page.getByRole("button", { name: "Not available to buy" });
    await expect(control).toBeVisible();
    await expect(control).toBeDisabled();
    await expect(page.getByRole("button", { name: "Add to cart" })).toHaveCount(0);
  });

  test("the preview disclosure still stands beside the price", async ({ page }) => {
    await page.goto("/product/the-source-tee");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/Source Tee/i, {
      timeout: 20_000,
    });
    await expect(page.getByText(/nothing here is available to (purchase|buy)/i).first()).toBeVisible();
  });

  test("the product route in the shared route table is priced too", async ({ page }) => {
    /* Not the Source Tee: proves the fix is the general rule and not one product special
       cased. The Measure Trouser is 14200 across all 12 of its variants. */
    await goto(page, "product");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/Measure Trouser/i, {
      timeout: 20_000,
    });
    await expect(page.getByTestId("product-price")).toHaveText("€142.00");
  });

  test("no product in the catalogue renders as unpriced", async ({ page }) => {
    /* The catalogue is five prototypes and every one of them carries a variant price. If a
       future product genuinely has none, "Not priced" is the correct and truthful render —
       and this test should then be changed deliberately, with the reason recorded, rather
       than the page quietly going blank. */
    await goto(page, "shop");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });

    const links = page.locator('a[href^="/product/"]');
    const slugs = new Set<string>();
    for (const href of await links.evaluateAll((els) =>
      els.map((e) => (e as HTMLAnchorElement).getAttribute("href") ?? ""),
    )) {
      if (href.startsWith("/product/")) slugs.add(href);
    }
    expect(slugs.size, "the shop listed no products to check").toBeGreaterThan(0);

    for (const href of slugs) {
      await page.goto(href);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
      await expect(
        page.getByTestId("product-price"),
        `${href} rendered without a price`,
      ).toHaveText(/€\d/);
    }
  });
});
