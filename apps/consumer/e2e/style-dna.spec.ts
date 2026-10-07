import { test, expect, type Page } from "@playwright/test";

/* Style DNA, end to end, against the deployed application.
 *
 * WHAT THIS SUITE IS ACTUALLY FOR.
 *
 * Style DNA is a persistence feature wearing a form's clothes. A unit test can prove a chip
 * toggles; only a real browser against a real server can prove the value is still there
 * after a refresh, after a brand-new browser context, and after being edited from what is
 * effectively a second device. Those three are the feature.
 *
 * It also guards two claims the page makes in words, which is the kind of thing that rots
 * silently: that there is no fabricated percentage anywhere on it, and that Saved activity
 * is not used to infer anything. Both are assertions about honesty rather than behaviour,
 * and both are exactly the sort that a later refactor would quietly break.
 *
 * CREDENTIALS COME FROM THE ENVIRONMENT AND ARE NEVER DEFAULTED, and the accounts are
 * created out of band with `manage.py create-test-customer` -- registration is limited to
 * five per hour against account farming, and a test suite is not a reason to loosen an
 * abuse control. The suite skips with a clear reason when the variables are absent.
 */

const BASE = process.env.DEDUNET_BASE_URL ?? "http://localhost:13600";
const EMAIL = process.env.DEDUNET_E2E_EMAIL_A ?? "";
const PASSWORD = process.env.DEDUNET_E2E_PASSWORD_A ?? "";
const CONFIGURED = Boolean(EMAIL) && Boolean(PASSWORD);

let token = "";

test.skip(
  !CONFIGURED,
  "set DEDUNET_E2E_EMAIL_A and DEDUNET_E2E_PASSWORD_A (create with manage.py create-test-customer)",
);

async function tokenFor(request: any): Promise<string> {
  const response = await request.post(`${BASE}/api/v1/auth/login`, {
    data: { email: EMAIL, password: PASSWORD },
  });
  if (!response.ok()) {
    throw new Error(`sign-in failed: ${response.status()} ${await response.text()}`);
  }
  return (await response.json()).access_token as string;
}

async function useSession(page: Page, value: string): Promise<void> {
  await page.addInitScript(
    ([key, v]) => {
      window.localStorage.setItem(key as string, v as string);
      window.localStorage.setItem("dedunet_role", "customer");
    },
    ["dedunet_token", value],
  );
}

/** Start every test from no profile, so none inherits another's state. */
async function resetProfile(request: any): Promise<void> {
  await request.delete(`${BASE}/api/v1/me/style-dna`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

async function readProfile(request: any): Promise<any> {
  const response = await request.get(`${BASE}/api/v1/me/style-dna`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.json();
}

async function openMyStyle(page: Page): Promise<void> {
  await page.goto("/my-style");
  await expect(page.getByTestId("section-how-you-dress")).toBeVisible({ timeout: 20_000 });
}

async function save(page: Page): Promise<void> {
  await page.getByTestId("style-save").click();
  await expect(page.getByTestId("style-status")).toContainText("saved", { timeout: 20_000 });
}

test.beforeAll(async ({ request }) => {
  if (!CONFIGURED) return;
  token = await tokenFor(request);
});

test.beforeEach(async ({ page, request }) => {
  await resetProfile(request);
  await useSession(page, token);
});

test.describe("Style DNA", () => {
  test("empty profile, then the full editor round trip, then persistence", async ({
    page,
    request,
  }) => {
    await openMyStyle(page);

    // Nothing set: no completeness line, because there is no profile to describe.
    await expect(page.getByTestId("style-completeness")).toHaveCount(0);

    // ---- set something in all five sections
    await page.getByTestId("chip-minimal").click();
    await page.getByTestId("chip-black").click();
    await page.getByTestId("colour-approach-mostly-neutral").click();
    await page.getByTestId("fit-tops").selectOption("relaxed");
    await page.getByTestId("size-tops").fill("M");
    await page.getByTestId("chip-cotton").click();
    await page.getByTestId("brand-dedunet").click();
    await page.getByTestId("budget-per-piece").fill("200");
    await page.getByTestId("budget-per-look").fill("600");

    await save(page);

    // ---- the server holds exactly what was entered
    const stored = await readProfile(request);
    expect(stored.exists).toBe(true);
    expect(stored.revision).toBe(1);
    expect(stored.personalization_enabled).toBe(true);
    expect(stored.style_directions).toContainEqual(
      expect.objectContaining({ slug: "minimal", stance: "PREFERRED" }),
    );
    expect(stored.colours).toContainEqual(
      expect.objectContaining({ slug: "black", stance: "PREFERRED" }),
    );
    expect(stored.colour_approach).toBe("mostly-neutral");
    expect(stored.fits).toContainEqual(
      expect.objectContaining({ garment_category: "tops", fit: "relaxed" }),
    );
    expect(stored.sizes).toContainEqual(
      expect.objectContaining({ garment_category: "tops", size_label: "M" }),
    );
    expect(stored.brands).toContainEqual(expect.objectContaining({ slug: "dedunet" }));
    // INTEGER minor units, never a float.
    expect(stored.budget.per_piece_minor_units).toBe(20000);
    expect(stored.budget.per_look_minor_units).toBe(60000);
    expect(stored.budget.currency).toBe("EUR");
    expect(stored.sections_with_preferences).toBe(5);

    // ---- survives a refresh
    await page.reload();
    await expect(page.getByTestId("chip-minimal")).toHaveAttribute("data-stance", "PREFERRED");
    await expect(page.getByTestId("budget-per-piece")).toHaveValue("200");
    await expect(page.getByTestId("style-completeness")).toContainText("5 of 5");
  });

  test("survives a brand new browser context, which is what persistence means", async ({
    page,
    browser,
    request,
  }) => {
    await openMyStyle(page);
    await page.getByTestId("chip-navy").click();
    await save(page);

    // A different context: no shared storage, no shared cache, no shared memory.
    const fresh = await browser.newContext();
    const other = await fresh.newPage();
    await useSession(other, token);
    await other.goto("/my-style");
    await expect(other.getByTestId("chip-navy")).toHaveAttribute("data-stance", "PREFERRED", {
      timeout: 20_000,
    });
    await fresh.close();

    expect((await readProfile(request)).colours).toContainEqual(
      expect.objectContaining({ slug: "navy" }),
    );
  });

  test("editing one value advances the revision", async ({ page, request }) => {
    await openMyStyle(page);
    await page.getByTestId("chip-classic").click();
    await save(page);
    expect((await readProfile(request)).revision).toBe(1);

    await page.getByTestId("chip-luxury").click();
    await save(page);
    const after = await readProfile(request);
    expect(after.revision).toBe(2);
    expect(after.style_directions.map((d: any) => d.slug).sort()).toEqual(["classic", "luxury"]);
  });

  test("a chip cycles like, avoid, unset", async ({ page }) => {
    await openMyStyle(page);
    const chip = page.getByTestId("chip-streetwear");

    await chip.click();
    await expect(chip).toHaveAttribute("data-stance", "PREFERRED");
    await chip.click();
    await expect(chip).toHaveAttribute("data-stance", "AVOIDED");
    await chip.click();
    // Back to no opinion, which is not the same as avoiding it.
    await expect(chip).toHaveAttribute("data-stance", "unset");
    await expect(chip).toHaveAttribute("aria-pressed", "false");
  });

  test("disabling personalisation keeps every value, and re-enabling restores use", async ({
    page,
    request,
  }) => {
    await openMyStyle(page);
    await page.getByTestId("chip-olive").click();
    await page.getByTestId("budget-per-piece").fill("150");
    await save(page);

    await page.getByTestId("personalisation-toggle").uncheck();
    await save(page);

    let stored = await readProfile(request);
    expect(stored.personalization_enabled).toBe(false);
    // The values are all still there. Disabling is not deleting.
    expect(stored.colours).toContainEqual(expect.objectContaining({ slug: "olive" }));
    expect(stored.budget.per_piece_minor_units).toBe(15000);
    await expect(page.getByTestId("personalisation-off-banner")).toBeVisible();

    await page.getByTestId("personalisation-toggle").check();
    await save(page);
    stored = await readProfile(request);
    expect(stored.personalization_enabled).toBe(true);
    expect(stored.colours).toContainEqual(expect.objectContaining({ slug: "olive" }));
  });

  test("delete empties the profile and leaves Saved items untouched", async ({
    page,
    request,
  }) => {
    // Save a brand first: the point is that it is STILL THERE afterwards.
    await request.post(`${BASE}/api/v1/me/saved/brands/dedunet`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    await openMyStyle(page);
    await page.getByTestId("chip-grey").click();
    await page.getByTestId("size-tops").fill("L");
    await save(page);

    await page.getByTestId("style-delete").click();
    await expect(page.getByTestId("delete-confirm")).toBeVisible();
    await page.getByTestId("delete-confirm-yes").click();

    await expect
      .poll(async () => (await readProfile(request)).exists, { timeout: 20_000 })
      .toBe(false);

    const emptied = await readProfile(request);
    expect(emptied.colours).toEqual([]);
    expect(emptied.sizes).toEqual([]);
    expect(emptied.revision).toBe(0);

    // Saved data is untouched: a narrow request stayed narrow.
    const saved = await request.get(`${BASE}/api/v1/me/saved/state`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect((await saved.json()).brands).toContain("dedunet");

    await request.delete(`${BASE}/api/v1/me/saved/brands/dedunet`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  });

  test("a stale edit is refused rather than silently overwriting", async ({ page, request }) => {
    await openMyStyle(page);
    await page.getByTestId("chip-red").click();
    await save(page);

    // Another device saves. The page is now holding revision 1.
    const elsewhere = await request.patch(`${BASE}/api/v1/me/style-dna`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        expected_revision: 1,
        colours: [{ slug: "pink", stance: "PREFERRED" }],
      },
    });
    expect(elsewhere.ok()).toBeTruthy();

    await page.getByTestId("chip-green").click();
    await page.getByTestId("style-save").click();

    await expect(page.getByTestId("style-conflict")).toBeVisible({ timeout: 20_000 });
    // And the other device's edit survived.
    expect((await readProfile(request)).colours).toContainEqual(
      expect.objectContaining({ slug: "pink" }),
    );
  });

  test("no fabricated percentage appears anywhere on the page", async ({ page }) => {
    await openMyStyle(page);
    await page.getByTestId("chip-minimal").click();
    await save(page);

    const body = (await page.locator("body").innerText()).toLowerCase();
    expect(body).not.toMatch(/\d+\s*%/);
    expect(body).not.toContain("style dna strength");
    expect(body).not.toContain("confidence");
    // What it says instead is a count the reader can verify.
    await expect(page.getByTestId("style-completeness")).toContainText("of 5 sections");
  });

  test("the page states that Saved activity is not used for inference", async ({ page }) => {
    await openMyStyle(page);
    await expect(page.getByTestId("saved-boundary-notice")).toContainText(
      "not currently used to infer",
    );
  });

  test("saving an item does not create or alter a Style DNA profile", async ({
    page,
    request,
  }) => {
    await request.post(`${BASE}/api/v1/me/saved/brands/dedunet`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    await openMyStyle(page);

    // Saving a brand must not have produced a brand preference, or a profile at all.
    expect((await readProfile(request)).exists).toBe(false);
    await expect(page.getByTestId("brand-dedunet")).toHaveAttribute("data-stance", "unset");

    await request.delete(`${BASE}/api/v1/me/saved/brands/dedunet`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  });

  test("every stored value is labelled as set by the customer", async ({ page, request }) => {
    await openMyStyle(page);
    await page.getByTestId("chip-linen").click();
    await save(page);

    const stored = await readProfile(request);
    for (const entry of [...stored.materials, ...stored.colours, ...stored.style_directions]) {
      expect(entry.source).toBe("USER_EXPLICIT");
    }
  });

  test("the editor is reachable and operable by keyboard", async ({ page }) => {
    await openMyStyle(page);
    const chip = page.getByTestId("chip-minimal");
    await chip.focus();
    await expect(chip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(chip).toHaveAttribute("data-stance", "PREFERRED");
    await page.keyboard.press("Space");
    await expect(chip).toHaveAttribute("data-stance", "AVOIDED");
  });

  test("controls meet the touch target minimum", async ({ page }) => {
    await openMyStyle(page);
    const box = await page.getByTestId("chip-minimal").boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  });

  test("an invalid budget is refused with a readable message", async ({ page }) => {
    await openMyStyle(page);
    await page.getByTestId("budget-per-piece").fill("two hundred");
    await page.getByTestId("style-save").click();
    await expect(page.getByTestId("style-status")).toContainText("not a number", {
      timeout: 20_000,
    });
  });

  test("signed out, My Style asks for a sign-in and stores nothing locally", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const anon = await context.newPage();
    await anon.goto("/my-style");

    await expect(anon.getByText("Sign in to build your Style DNA")).toBeVisible({
      timeout: 20_000,
    });
    // No local fake profile. The Saved phase's rule, applied to more personal data.
    const keys = await anon.evaluate(() => Object.keys(window.localStorage));
    expect(keys.filter((k) => k.toLowerCase().includes("style"))).toEqual([]);
    await context.close();
  });

  test("Dido states the profile is stored and not yet applied", async ({ page }) => {
    await page.goto("/dido");
    const body = await page.locator("body").innerText();
    expect(body).toContain("Stored, not yet applied");
    // And it must not claim to be using it.
    expect(body.toLowerCase()).not.toContain("using your style profile");
  });
});
