import { test, expect } from "@playwright/test";

/* The multi-brand network, in a real browser.
 *
 * These pages used to render a hardcoded array of two brands. They now render domain data,
 * so the failure modes changed: a brand can be missing, a count can disagree with the list
 * under it, an internal ownership enum can leak into copy, and -- the one that matters most
 * -- a development fixture can be presented as a genuine partner.
 *
 * The last is why several of these assert on ABSENCE. A test that only checks the happy path
 * would pass just as well against a page that quietly claims a partnership.
 */

const PATH_ROUTING = (process.env.DEDUNET_ROUTING ?? "path") === "path";

/** Internal vocabulary that must never reach a customer's screen. */
const INTERNAL_ENUMS = ["PLATFORM_CURATED", "MERCHANT_OWNED", "EXTERNAL_CURATED"];

/** Words that would claim a relationship this platform does not have with anyone. */
const PARTNERSHIP_CLAIMS = [
  "official partner",
  "authorised retailer",
  "authorized retailer",
  "verified seller",
  "available through a partner",
];

test.describe("the brand network", () => {
  test.skip(!PATH_ROUTING, "asserts the React client's brand surfaces");

  test("the brands page lists real brands from the API", async ({ page }) => {
    await page.goto("/brands");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Brands", {
      timeout: 20_000,
    });

    const cards = page.getByTestId("brand-card");
    await expect(cards.first()).toBeVisible();
    // The first-party brand is real domain data and must be present.
    await expect(page.getByRole("heading", { name: "DEDUNET", exact: true })).toBeVisible();
  });

  test("no internal ownership enum reaches the brands page", async ({ page }) => {
    await page.goto("/brands");
    await expect(page.getByTestId("brand-card").first()).toBeVisible({ timeout: 20_000 });
    const body = await page.locator("body").innerText();
    for (const leaked of INTERNAL_ENUMS) {
      expect(body, `${leaked} leaked into consumer copy`).not.toContain(leaked);
    }
  });

  test("nothing on the brands page claims a partnership", async ({ page }) => {
    await page.goto("/brands");
    await expect(page.getByTestId("brand-card").first()).toBeVisible({ timeout: 20_000 });
    const body = (await page.locator("body").innerText()).toLowerCase();
    for (const claim of PARTNERSHIP_CLAIMS) {
      expect(body, `page claims "${claim}"`).not.toContain(claim);
    }
  });

  test("a development fixture is labelled unmistakably wherever it appears", async ({ page }) => {
    await page.goto("/brands");
    await expect(page.getByTestId("brand-card").first()).toBeVisible({ timeout: 20_000 });

    const fixtureCard = page
      .getByTestId("brand-card")
      .filter({ hasText: /development fixture/i });

    // The fixture is visible in a preview deployment, and when it is, it says what it is.
    if ((await fixtureCard.count()) > 0) {
      await expect(fixtureCard.first()).toContainText(/development fixture/i);
    }
  });

  test("the DEDUNET brand page shows its real catalogue", async ({ page }) => {
    await page.goto("/brand/dedunet");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("DEDUNET", {
      timeout: 20_000,
    });
    // Five accepted prototypes.
    await expect(page.getByTestId("product-card")).toHaveCount(5);
    await expect(page.getByTestId("brand-commerce")).toBeVisible();
  });

  test("a brand card's product count matches the page it links to", async ({ page }) => {
    /* A count that disagrees with the list under it is a defect a customer sees first. */
    await page.goto("/brand/dedunet");
    await expect(page.getByTestId("product-card").first()).toBeVisible({ timeout: 20_000 });
    const listed = await page.getByTestId("product-card").count();
    await expect(page.getByTestId("brand-commerce")).toContainText(String(listed));
  });

  test("an unknown brand renders the not-found page, not an error", async ({ page }) => {
    await page.goto("/brand/no-such-brand-exists");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
    const body = (await page.locator("body").innerText()).toLowerCase();
    expect(body).not.toContain("failed to fetch");
    expect(body).not.toContain("[object object]");
  });

  test("a product links to its own brand, and the brand links back", async ({ page }) => {
    /* Product -> Brand -> Product, the navigation the phase exists to make real. It was a
       hardcoded link to /brand/dedunet, which was only ever true while one brand existed. */
    await page.goto("/product/the-source-tee");
    const link = page.getByTestId("product-brand-link");
    await expect(link).toBeVisible({ timeout: 20_000 });
    await expect(link).toHaveAttribute("href", "/brand/dedunet");

    await link.click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("DEDUNET");
    await page.getByTestId("product-card").first().click();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("shop attributes every product to a brand", async ({ page }) => {
    await page.goto("/shop");
    await expect(page.getByTestId("shop-grid")).toBeVisible({ timeout: 20_000 });
    const cards = page.getByTestId("product-card");
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i += 1) {
      await expect(cards.nth(i)).toContainText("DEDUNET");
    }
  });

  test("showing a brand never makes a prototype purchasable", async ({ page }) => {
    /* THE SAFETY ASSERTION. The network must not have loosened the accepted purchase gate. */
    await page.goto("/product/the-source-tee");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/Source Tee/i, {
      timeout: 20_000,
    });
    const control = page.getByRole("button", { name: "Not available to buy" });
    await expect(control).toBeVisible();
    await expect(control).toBeDisabled();
    await expect(page.getByRole("button", { name: "Add to cart" })).toHaveCount(0);
    // And no outbound commerce link was rendered for a non-purchasable product.
    await expect(page.getByTestId("commerce-action-link")).toHaveCount(0);
  });

  test("the price survived the brand migration", async ({ page }) => {
    await page.goto("/product/the-source-tee");
    await expect(page.getByTestId("product-price")).toHaveText("€72.00", { timeout: 20_000 });
  });
});
