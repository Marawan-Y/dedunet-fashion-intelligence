import { test, expect } from "@playwright/test";
import { goto } from "./routes";

/* The accepted commerce guarantees, re-expressed at the browser level.
 *
 * These are not new requirements. Every one of them is an accepted, human-verified
 * behaviour of this platform, previously guarded only through jsdom harnesses that call
 * view functions directly. ADR-0004 migrates the client, so these must pass against the
 * replacement BEFORE cutover — that is the whole basis on which the migration claims to
 * have preserved the guarantees rather than merely to have kept the tests green.
 *
 * PUBLIC_COMMERCIAL_LAUNCH is BLOCKED. Nothing here may become permissive. */

test.describe("preview mode refuses the purchase invitation", () => {
  test("the control says it cannot be bought, and is disabled", async ({ page }) => {
    await goto(page, "product");

    await expect(
      page.getByRole("heading", { level: 1 }),
      "the product did not load, so its purchase gate could not be checked",
    ).toContainText(/Measure Trouser/i, { timeout: 20_000 });

    /* The accepted copy, exactly. A page that offers "Add to cart" for something the
       server will refuse is the defect this guard exists to prevent. */
    const control = page.getByRole("button", { name: "Not available to buy" });
    await expect(control).toBeVisible();
    await expect(control).toBeDisabled();

    await expect(page.getByRole("button", { name: "Add to cart" })).toHaveCount(0);
  });

  test("the refusal reason reaches the control that was disabled", async ({ page }) => {
    await goto(page, "product");

    /* A disabled button with the reason floating somewhere else on the page is not an
       explanation. `aria-describedby` is what makes it one. */
    /* Establish that the PRODUCT loaded before asserting anything about its purchase
       gate.
     *
     * Without this, a failed catalogue request renders the page's error state — which is
     * correct behaviour — and the missing button reports as "the refusal is missing",
     * which is a false accusation against an accepted safety guard. Asserting the heading
     * first makes the two failures say different things. */
    await expect(
      page.getByRole("heading", { level: 1 }),
      "the product did not load, so its purchase gate could not be checked",
    ).toContainText(/Measure Trouser/i, { timeout: 20_000 });

    const control = page.getByRole("button", { name: "Not available to buy" });
    await expect(control).toBeVisible({ timeout: 20_000 });

    const describedBy = await control.getAttribute("aria-describedby");
    expect(describedBy, "the disabled control must name its reason").toBeTruthy();

    const reason = page.locator(`#${describedBy}`);
    await expect(reason).toBeVisible();
    await expect(reason).toContainText(/preview/i);
  });
});

test("the mode disclosure replaces the static fallback once the mode is known", async ({ page }) => {
  await goto(page, "home");

  /* index.html ships copy that is true in EVERY permitted mode, because at parse time the
     page does not know which one it is in. Once /commerce/mode answers, the deployment's
     own disclosure replaces it. Asserting the resolved text proves the request happened
     and was applied — the fallback staying put is a silent failure. */
  const notice = page.getByRole("note").or(page.locator("[data-testid='commerce-mode-notice']"));
  await expect(notice.first()).toContainText(/Preview only|not available to purchase/i);
});

test("a stale session token is cleared when the API rejects it", async ({ page }) => {
  await goto(page, "home");

  /* An expired token that survives a 401 leaves the client claiming "signed in" while
     every authenticated request fails. The token must be gone after the rejection. */
  await page.evaluate(() => {
    localStorage.setItem("dedunet_token", "expired-token-that-the-api-will-reject");
    localStorage.setItem("dedunet_role", "customer");
  });

  /* The reload is load-bearing, not ceremony. A client that reads the token once at
     startup has no way to notice a token written afterwards, so seeding and navigating
     within the same document sends no Authorization header, provokes no 401, and the
     test would pass or fail for reasons that have nothing to do with the guard. Reload
     so the session is genuinely adopted before the request goes out. */
  await page.reload();
  await page.waitForLoadState("networkidle");

  await goto(page, "orders");
  await expect
    .poll(async () => page.evaluate(() => localStorage.getItem("dedunet_token")), {
      message: "a rejected token must not survive the 401",
      timeout: 8000,
    })
    .toBeNull();
});

test("signed out, the orders route sends the visitor to sign in", async ({ page }) => {
  await page.evaluate(() => localStorage.clear()).catch(() => {});
  await goto(page, "orders");

  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Account|Sign in/i);
});

test("nothing anywhere invites a purchase this deployment would refuse", async ({ page }) => {
  for (const route of ["home", "shop", "product", "cart", "looks", "look"] as const) {
    await goto(page, route);

    /* In BRAND_PREVIEW_MODE no surface may offer checkout. This is deliberately a sweep
       rather than a single page: the refusal was mirrored on the product page and the
       banner, and the defect that produced this guard was a DIFFERENT surface still
       making the offer. */
    await expect(
      page.getByRole("button", { name: /^(buy|check ?out|place order|pay)/i }),
      `${route} offered a purchase in preview mode`,
    ).toHaveCount(0);
  }
});
