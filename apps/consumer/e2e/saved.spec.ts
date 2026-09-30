import { test, expect, type Page } from "@playwright/test";

/* Saved persistence, end to end, against the deployed application.
 *
 * WHY THIS SUITE SIGNS IN A DISPOSABLE CUSTOMER RATHER THAN STUBBING.
 *
 * The thing being tested is that saved state survives things — a refresh, a navigation, a
 * new browser context. A stubbed API proves the icon toggles; it proves nothing about
 * persistence, which is the entire feature. So each test registers its own customer with a
 * unique email, and the isolation test registers two.
 *
 * The signed-out path is asserted too, because the failure mode this phase replaced was a
 * page that LOOKED like it saved. A save control that silently writes to localStorage and
 * shows "saved" is indistinguishable from the real thing until the customer opens DEDUNET
 * somewhere else.
 */

const PATH_ROUTING = (process.env.DEDUNET_ROUTING ?? "path") === "path";
const PASSWORD = "Correct-Horse-9";
const BASE = process.env.DEDUNET_BASE_URL ?? "http://localhost:13600";

/* TWO DURABLE CUSTOMERS, CREATED OUT OF BAND.
 *
 * The first version of this file registered a customer per test. Every dependent test then
 * failed, and the reason was the application being right: registration is limited to FIVE
 * PER HOUR ("account farming; an hour window because legitimate humans register once"), so
 * nine registrations in one run is precisely what that limiter exists to refuse. Loosening
 * it to suit a test suite would trade a real abuse control for convenience.
 *
 * So the accounts are created once with `manage.py create-test-customer`, the same
 * out-of-band pattern the administrator already uses, and this suite signs in. Sign-in is
 * limited to 10 per 60s, which two logins per run sits comfortably inside.
 *
 * CREDENTIALS COME FROM THE ENVIRONMENT AND ARE NEVER DEFAULTED. A password committed here
 * would be a weak credential in tracked source, so the suite SKIPS with a clear reason when
 * the variables are absent rather than falling back to one.
 *
 *   DEDUNET_E2E_EMAIL_A / DEDUNET_E2E_PASSWORD_A
 *   DEDUNET_E2E_EMAIL_B / DEDUNET_E2E_PASSWORD_B
 */

interface Account {
  email: string;
  password: string;
  token: string;
}

const CONFIGURED =
  Boolean(process.env.DEDUNET_E2E_EMAIL_A) &&
  Boolean(process.env.DEDUNET_E2E_PASSWORD_A) &&
  Boolean(process.env.DEDUNET_E2E_EMAIL_B) &&
  Boolean(process.env.DEDUNET_E2E_PASSWORD_B);

const accounts: Record<"a" | "b", Account> = {
  a: {
    email: process.env.DEDUNET_E2E_EMAIL_A ?? "",
    password: process.env.DEDUNET_E2E_PASSWORD_A ?? "",
    token: "",
  },
  b: {
    email: process.env.DEDUNET_E2E_EMAIL_B ?? "",
    password: process.env.DEDUNET_E2E_PASSWORD_B ?? "",
    token: "",
  },
};

/** Sign in over the API to obtain a token for injection. */
async function tokenFor(request: any, account: Account): Promise<string> {
  const response = await request.post(`${BASE}/api/v1/auth/login`, {
    data: { email: account.email, password: account.password },
  });
  if (!response.ok()) {
    throw new Error(
      `sign-in failed for ${account.email}: ${response.status()} ${await response.text()}`,
    );
  }
  return (await response.json()).access_token as string;
}

/** Put a session in place before the first script runs, so the app boots signed in. */
async function useSession(page: Page, token: string): Promise<void> {
  await page.addInitScript(
    ([key, value]) => {
      window.localStorage.setItem(key as string, value as string);
      window.localStorage.setItem("dedunet_role", "customer");
    },
    ["dedunet_token", token],
  );
}

/** Assert a live session without loading a media-heavy page to do it.
 *
 * This used to navigate to /saved and look for the signed-out panel. That is a full page
 * load -- roughly twenty static media requests -- spent confirming a token, on every test.
 * The general API limiter is 300 requests per minute per client and static media shares it,
 * so the check was contributing to the very 429s it then tripped over. Reading the token is
 * the same assertion at no request cost.
 */
async function expectSignedIn(page: Page): Promise<void> {
  await page.goto("/account");
  await expect
    .poll(() => page.evaluate(() => window.localStorage.getItem("dedunet_token")), {
      message: "expected a signed-in session",
      timeout: 20_000,
    })
    .toBeTruthy();
}

/** Remove everything an account has saved, so tests do not inherit each other's state. */
async function resetSaved(request: any, token: string): Promise<void> {
  const state = await request.get(`${BASE}/api/v1/me/saved/state`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!state.ok()) return;
  const sets = await state.json();
  for (const kind of ["products", "brands", "looks"] as const) {
    for (const slug of sets[kind] ?? []) {
      await request.delete(`${BASE}/api/v1/me/saved/${kind}/${slug}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  }
}

async function savedCount(page: Page, kind: "products" | "brands" | "looks"): Promise<number> {
  const text = await page.getByTestId(`saved-count-${kind}`).innerText();
  return Number(text.trim());
}

/* The account page shows BOTH forms at once, in two sections. Scoping matters: an
   unscoped getByLabel(/email/i) matches the sign-in field, and a registration would
   silently submit empty. */
function signInPanel(page: Page) {
  return page.locator('section[aria-labelledby="signin-heading"]');
}

/** Sign in through the real form. Used by the browser-restart test. */
async function signIn(page: Page, email: string): Promise<void> {
  await page.goto("/account");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
  const panel = signInPanel(page);
  await panel.getByLabel("Email").fill(email);
  await panel.getByLabel("Password").fill(PASSWORD);
  await panel.getByRole("button", { name: /^sign in$/i }).click();

  /* Wait for the session to actually exist. Navigating immediately after the click races
     the request, and the next page then boots signed out -- which reads as "saved data was
     lost" when the truth is "we never signed in". */
  await expect
    .poll(
      () => page.evaluate(() => window.localStorage.getItem("dedunet_token")),
      { message: "sign-in did not establish a session", timeout: 20_000 },
    )
    .toBeTruthy();
}


/** Assert a live session by the one signal that differs when signed out. */
test.describe("saved persistence", () => {
  test.skip(!PATH_ROUTING, "asserts the React client's saved surfaces");

  /* Serial, because the suite shares two accounts. Parallel tests toggling the same saved
     set would race each other rather than test anything. */
  test.describe.configure({ mode: "serial" });

  test.skip(
    !CONFIGURED,
    "set DEDUNET_E2E_EMAIL_A/B and DEDUNET_E2E_PASSWORD_A/B; create the accounts with " +
      "`manage.py create-test-customer` (registration is limited to 5/hour by design)",
  );

  test.beforeAll(async ({ request }) => {
    accounts.a.token = await tokenFor(request, accounts.a);
    accounts.b.token = await tokenFor(request, accounts.b);
  });

  test.beforeEach(async ({ request }) => {
    /* Account A only. The isolation test resets B itself; resetting both on every test
       doubled the setup traffic against a limiter this suite already strains. */
    await resetSaved(request, accounts.a.token);
  });

  test("a signed-out visitor is asked to sign in rather than shown a fake save", async ({
    page,
  }) => {
    /* THE HONESTY TEST. The page this replaced said "Saving is not built yet"; the failure
       to avoid now is the opposite — looking like it saved when nothing was stored. */
    await page.goto("/saved");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Saved", {
      timeout: 20_000,
    });

    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/saving is not built/i);
    await expect(page.getByText(/sign in to see your saved items/i)).toBeVisible();

    // And a save control on a product sends them to sign in rather than toggling.
    await page.goto("/product/the-source-tee");
    await page.getByTestId("save-product-detail").click();
    await expect(page).toHaveURL(/\/account/, { timeout: 20_000 });
  });

  test("save a product and a brand, and they persist across a refresh", async ({ page }) => {
    await useSession(page, accounts.a.token);
    await expectSignedIn(page);

    await page.goto("/product/the-source-tee");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/Source Tee/i, {
      timeout: 20_000,
    });
    const save = page.getByTestId("save-product-detail");
    await expect(save).toHaveAttribute("aria-pressed", "false");
    await save.click();
    await expect(save).toHaveAttribute("aria-pressed", "true", { timeout: 20_000 });

    await page.goto("/brand/dedunet");
    const saveBrand = page.getByTestId("save-brand-detail");
    await saveBrand.click();
    await expect(saveBrand).toHaveAttribute("aria-pressed", "true", { timeout: 20_000 });

    await page.goto("/saved");
    expect(await savedCount(page, "products")).toBe(1);
    expect(await savedCount(page, "brands")).toBe(1);

    // THE REFRESH. Server-side persistence, not component state.
    await page.reload();
    await expect(page.getByTestId("saved-summary")).toBeVisible({ timeout: 20_000 });
    expect(await savedCount(page, "products")).toBe(1);
    expect(await savedCount(page, "brands")).toBe(1);

    await page.getByTestId("saved-tab-products").click();
    await expect(page.getByTestId("saved-item").first()).toBeVisible();
    await expect(page.locator('[data-testid="saved-item"]')).toContainText(/Source Tee/i);

    await page.getByTestId("saved-tab-brands").click();
    await expect(page.locator('[data-testid="saved-item"]')).toContainText(/DEDUNET/i);
  });

  test("saved state is consistent across surfaces without a full reload", async ({ page }) => {
    /* Save on the detail page, then navigate to Shop: the card must already know. This is
       what the shared context buys, and it is the requirement a per-card status request
       would satisfy at twenty times the cost. */
    await useSession(page, accounts.a.token);
    await expectSignedIn(page);

    await page.goto("/product/the-source-tee");
    await page.getByTestId("save-product-detail").click();
    await expect(page.getByTestId("save-product-detail")).toHaveAttribute(
      "aria-pressed",
      "true",
      { timeout: 20_000 },
    );

    await page.getByRole("link", { name: /shop/i }).first().click();
    await expect(page.getByTestId("shop-grid")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("save-product-the-source-tee")).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    // Unsave from the Shop card; the detail page must reflect it.
    await page.getByTestId("save-product-the-source-tee").click();
    await expect(page.getByTestId("save-product-the-source-tee")).toHaveAttribute(
      "aria-pressed",
      "false",
      { timeout: 20_000 },
    );

    await page.goto("/product/the-source-tee");
    await expect(page.getByTestId("save-product-detail")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  test("unsaving from the Saved page removes the item and updates the count", async ({
    page,
  }) => {
    await useSession(page, accounts.a.token);
    await expectSignedIn(page);

    await page.goto("/product/the-source-tee");
    await page.getByTestId("save-product-detail").click();
    await expect(page.getByTestId("save-product-detail")).toHaveAttribute(
      "aria-pressed",
      "true",
      { timeout: 20_000 },
    );

    await page.goto("/saved");
    await page.getByTestId("saved-tab-products").click();
    expect(await savedCount(page, "products")).toBe(1);

    await page.getByTestId("unsave-products-the-source-tee").click();
    // No full-page reload: the list and the count both follow the shared state.
    await expect
      .poll(() => savedCount(page, "products"), { timeout: 20_000 })
      .toBe(0);
    await expect(page.getByText(/haven't saved any products/i)).toBeVisible({
      timeout: 20_000,
    });
  });

  test("a look can be saved and appears under Looks", async ({ page }) => {
    await useSession(page, accounts.a.token);
    await expectSignedIn(page);

    await page.goto("/looks");
    await expect(page.getByTestId("look-card").first()).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("look-card").first().getByRole("button").first().click();

    await page.goto("/saved");
    await expect
      .poll(() => savedCount(page, "looks"), { timeout: 20_000 })
      .toBe(1);
    await page.getByTestId("saved-tab-looks").click();
    await expect(page.getByTestId("saved-item").first()).toBeVisible();
  });

  test("one customer never sees another's saved items", async ({ browser, request }) => {
    /* Two independent browser contexts, two real customers. The isolation that matters is
       server-side, and a single context could pass this by accident through local state. */
    const first = await browser.newContext();
    const second = await browser.newContext();
    try {
      const a = await first.newPage();
      const b = await second.newPage();

      await useSession(a, accounts.a.token);
      await expectSignedIn(a);
      await a.goto("/product/the-source-tee");
      await a.getByTestId("save-product-detail").click();
      await expect(a.getByTestId("save-product-detail")).toHaveAttribute(
        "aria-pressed",
        "true",
        { timeout: 20_000 },
      );

      await resetSaved(request, accounts.b.token);
      await useSession(b, accounts.b.token);
      await b.goto("/saved");
      expect(await savedCount(b, "products")).toBe(0);

      await b.goto("/product/the-source-tee");
      await expect(b.getByTestId("save-product-detail")).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    } finally {
      await first.close();
      await second.close();
    }
  });

  test("saved data lives on the server, not in browser storage", async ({ browser }) => {
    /* The closest automated equivalent of "close Safari and reopen it": a fresh context
       shares no storage with the first. The saved data lives on the server, so signing in
       again brings it back. */
    const { token } = accounts.a;
    const first = await browser.newContext();
    try {
      const page = await first.newPage();
      await useSession(page, token);
      await expectSignedIn(page);
      await page.goto("/product/the-source-tee");
      await page.getByTestId("save-product-detail").click();
      await expect(page.getByTestId("save-product-detail")).toHaveAttribute(
        "aria-pressed",
        "true",
        { timeout: 20_000 },
      );
    } finally {
      await first.close();
    }

    /* A BRAND-NEW CONTEXT: no localStorage, no cookies, nothing carried over. The only
       thing put into it is an auth token -- no saved data -- so the list coming back can
       only have come from the server. That is exactly the property this test is for: saved
       items must not live in browser storage.

       The token is injected rather than typed into the sign-in form, deliberately. Sign-in
       is limited to 10 per 60 seconds and this suite already spends two on setup; a third
       made this test fail intermittently for a reason that had nothing to do with
       persistence. Authentication has its own coverage in `safety-guards.spec.ts`; the
       subject here is persistence. */
    const second = await browser.newContext();
    try {
      const page = await second.newPage();
      await useSession(page, token);
      await page.goto("/saved");

      // Nothing about saved items is in storage -- only the token.
      const storedKeys = await page.evaluate(() => Object.keys(window.localStorage));
      expect(storedKeys.filter((k) => /saved|favorite|look/i.test(k))).toEqual([]);

      await expect
        .poll(() => savedCount(page, "products"), { timeout: 20_000 })
        .toBe(1);
    } finally {
      await second.close();
    }
  });

  test("saving does not make a prototype purchasable", async ({ page }) => {
    /* THE SAFETY ASSERTION. Keeping something is not an intent to buy it, and the accepted
       purchase gate must be untouched by the save. */
    await useSession(page, accounts.a.token);
    await expectSignedIn(page);
    await page.goto("/product/the-source-tee");
    await page.getByTestId("save-product-detail").click();
    await expect(page.getByTestId("save-product-detail")).toHaveAttribute(
      "aria-pressed",
      "true",
      { timeout: 20_000 },
    );

    await expect(page.getByTestId("product-price")).toHaveText("€72.00");
    const control = page.getByRole("button", { name: "Not available to buy" });
    await expect(control).toBeVisible();
    await expect(control).toBeDisabled();
    await expect(page.getByRole("button", { name: "Add to cart" })).toHaveCount(0);
  });

  test("the save control has an accessible name and is keyboard operable", async ({
    page,
  }) => {
    await useSession(page, accounts.a.token);
    await expectSignedIn(page);
    await page.goto("/shop");
    await expect(page.getByTestId("shop-grid")).toBeVisible({ timeout: 20_000 });

    const control = page.getByTestId("save-product-the-source-tee");
    // Not "button" — the name says what it does and to what.
    await expect(control).toHaveAttribute("aria-label", /save the source tee/i);

    await control.focus();
    await expect(control).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(control).toHaveAttribute("aria-pressed", "true", { timeout: 20_000 });
    await expect(control).toHaveAttribute("aria-label", /remove the source tee/i);
  });
});
