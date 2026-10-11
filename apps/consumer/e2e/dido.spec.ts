import { test, expect, type Page } from "@playwright/test";

/* Dido conversational intelligence, end to end, against the deployed application.
 *
 * WHAT ONLY A REAL BROWSER CAN PROVE HERE.
 *
 * That a styling conversation is SERVER-OWNED. A unit test can prove the merge rules; only
 * a fresh browser context can prove the conversation is still there when you come back to
 * it from somewhere else, which is the difference between a chat and a session.
 *
 * And that the boundary holds on screen. The brief must separate what came from the
 * customer's profile from what they said tonight, a session instruction must beat a stored
 * preference WITHOUT changing it, and no recommendation may appear anywhere — including at
 * the end, which is exactly where a customer expects an outfit.
 *
 * Credentials come from the environment and are never defaulted; the accounts are created
 * out of band because registration is limited to five per hour against account farming,
 * and a test suite is not a reason to loosen an abuse control.
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

const auth = () => ({ Authorization: `Bearer ${token}` });

/** A known Style DNA profile, so the "from your Style DNA" assertions mean something. */
async function setStyleDna(request: any, enabled: boolean): Promise<void> {
  await request.patch(`${BASE}/api/v1/me/style-dna`, {
    headers: auth(),
    data: {
      colours: [
        { slug: "black", stance: "PREFERRED" },
        { slug: "orange", stance: "AVOIDED" },
      ],
      materials: [{ slug: "wool", stance: "AVOIDED" }],
      sizes: [{ garment_category: "tops", size_system: "EU", size_label: "50" }],
      budget: { per_look_minor_units: 25000, currency: "EUR" },
      personalization_enabled: enabled,
    },
  });
}

async function readStyleDna(request: any): Promise<any> {
  return (await request.get(`${BASE}/api/v1/me/style-dna`, { headers: auth() })).json();
}

/** Remove every session so no test inherits another's conversation. */
async function resetSessions(request: any): Promise<void> {
  const current = await request.get(`${BASE}/api/v1/me/dido/sessions/current`, {
    headers: auth(),
  });
  if (!current.ok()) return;
  const body = await current.json();
  if (body.session) {
    await request.delete(`${BASE}/api/v1/me/dido/sessions/${body.session.session_id}`, {
      headers: auth(),
    });
  }
}

async function openDido(page: Page): Promise<void> {
  await page.goto("/dido");
  await expect(page.getByTestId("dido-disclosure")).toBeVisible({ timeout: 20_000 });
}

async function startConversation(page: Page): Promise<void> {
  await page.getByTestId("dido-start").click();
  await expect(page.getByTestId("dido-log")).toBeVisible({ timeout: 20_000 });
}

async function say(page: Page, text: string): Promise<void> {
  const log = page.getByTestId("dido-log");
  const before = await log.locator("li").count();

  await page.getByTestId("dido-input").fill(text);
  await page.getByTestId("dido-send").click();

  /* Wait for the CONVERSATION to grow, not for the button to re-enable.
   *
   * The first version waited on `toBeEnabled`, which could never be satisfied: a
   * successful send clears the draft, and the button is disabled both while sending AND
   * while the box is empty. The condition was unreachable in exactly the case it was
   * meant to detect. Two new turns -- the customer's and Dido's -- is the thing that
   * actually happened. */
  await expect
    .poll(async () => log.locator("li").count(), { timeout: 25_000 })
    .toBeGreaterThanOrEqual(before + 2);
  await expect(page.getByTestId("dido-send")).toHaveText("Send", { timeout: 25_000 });
}

test.beforeAll(async ({ request }) => {
  if (!CONFIGURED) return;
  token = await tokenFor(request);
});

test.beforeEach(async ({ page, request }) => {
  await resetSessions(request);
  await useSession(page, token);
});

test.afterAll(async ({ request }) => {
  if (!CONFIGURED) return;
  // Leave the account as the other suites expect to find it.
  await request.delete(`${BASE}/api/v1/me/style-dna`, { headers: auth() });
});

test.describe("Dido conversational intelligence", () => {
  test("a rich free-text request is understood, and known fields are not re-asked", async ({
    page,
    request,
  }) => {
    await setStyleDna(request, true);
    await openDido(page);
    await startConversation(page);

    // Style DNA is in play, and the page says so rather than leaving it to be assumed.
    await expect(page.getByTestId("dido-personalisation")).toContainText("using your Style DNA");

    await say(page, "I have a job interview tomorrow, business casual, around 200 euros.");

    // All three landed, so Dido must not mechanically ask for any of them.
    await expect(page.getByTestId("brief-occasion")).toContainText("interview");
    await expect(page.getByTestId("brief-dress_code")).toContainText("business casual");
    await expect(page.getByTestId("brief-budget_total")).toContainText("€200.00");

    /* Asked ONCE, at the start, when nothing was known -- and not again once the
     * customer has supplied it. The first version of this assertion scanned the whole
     * log and failed on Dido's opening question, which is the one time asking is
     * correct. Counting is the real claim. */
    const log = (await page.getByTestId("dido-log").innerText()).toLowerCase();
    expect(log.split("where are you going?").length - 1).toBe(1);
    expect(log).not.toContain("how formal does it need to be?");
  });

  test("the brief separates profile values from what was said tonight", async ({
    page,
    request,
  }) => {
    await setStyleDna(request, true);
    await openDido(page);
    await startConversation(page);
    await say(page, "A wedding, formal");

    // From the profile.
    await expect(page.getByTestId("brief-style-dna")).toContainText("wool");
    // From this conversation.
    await expect(page.getByTestId("brief-session")).toContainText("wedding");

    // Stated sizes are shown verbatim and labelled as unconverted.
    await expect(page.getByTestId("brief-sizes")).toContainText("EU 50");
    await expect(page.getByTestId("brief-sizes")).toContainText("does not convert");
  });

  test("a session override wins, and the Style DNA profile does not change", async ({
    page,
    request,
  }) => {
    await setStyleDna(request, true);
    const before = await readStyleDna(request);

    await openDido(page);
    await startConversation(page);
    await say(page, "Dinner, smart casual, 90 euros");
    await say(page, "Actually, no black for this one.");

    await expect(page.getByTestId("brief-colour_avoidances")).toContainText("black");

    // THE PROFILE IS UNTOUCHED. This is the central promise of the phase.
    const after = await readStyleDna(request);
    expect(after.colours).toEqual(before.colours);
    expect(after.revision).toBe(before.revision);
  });

  test("the conversation survives a refresh and a brand new browser context", async ({
    page,
    browser,
    request,
  }) => {
    await setStyleDna(request, true);
    await openDido(page);
    await startConversation(page);
    await say(page, "An outdoor wedding, formal");

    await page.reload();
    await expect(page.getByTestId("brief-occasion")).toContainText("wedding", {
      timeout: 20_000,
    });

    // A different context: no shared storage, no shared cache, no shared memory. This is
    // what distinguishes a server-owned session from a browser-local chat.
    const fresh = await browser.newContext();
    const other = await fresh.newPage();
    await useSession(other, token);
    await other.goto("/dido");
    await expect(other.getByTestId("brief-occasion")).toContainText("wedding", {
      timeout: 20_000,
    });
    await fresh.close();
  });

  test("the brief can be corrected, and a correction does not touch the profile", async ({
    page,
    request,
  }) => {
    await setStyleDna(request, true);
    const before = await readStyleDna(request);

    await openDido(page);
    await startConversation(page);
    await say(page, "A wedding, formal, 300 euros");

    await page.getByTestId("brief-clear-occasion").click();
    await expect(page.getByTestId("brief-occasion")).toHaveCount(0, { timeout: 20_000 });

    const after = await readStyleDna(request);
    expect(after.revision).toBe(before.revision);
  });

  test("completing the brief produces NO recommendation and says so", async ({
    page,
    request,
  }) => {
    await setStyleDna(request, true);
    await openDido(page);
    await startConversation(page);
    await say(page, "Interview, business casual, 200 euros");

    await page.getByTestId("dido-complete").click();
    await expect(page.getByTestId("dido-completed")).toBeVisible({ timeout: 20_000 });

    // The sentence at exactly the point a customer expects an outfit.
    await expect(page.getByTestId("dido-completed")).toContainText(
      "does not yet rank products",
    );

    const body = (await page.locator("main").innerText()).toLowerCase();
    for (const forbidden of ["we recommend", "best match", "add to cart", "in stock"]) {
      expect(body).not.toContain(forbidden);
    }
  });

  test("Dido explains why it asked, from policy rather than prose", async ({ page }) => {
    await openDido(page);
    await startConversation(page);
    await page.getByTestId("dido-why").click();
    await expect(page.getByTestId("dido-why-answer")).toBeVisible();
    await expect(page.getByTestId("dido-why-answer")).not.toHaveText("");
  });

  test("what do you know about me, answered by source", async ({ page, request }) => {
    await setStyleDna(request, true);
    await openDido(page);
    await startConversation(page);
    await page.getByTestId("dido-what-you-know").click();
    await expect(page.getByTestId("dido-in-use")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("dido-in-use")).toContainText("From your Style DNA");
  });

  test("guided choices are offered beside the text box", async ({ page }) => {
    await openDido(page);
    await startConversation(page);
    await expect(page.getByTestId("dido-options")).toBeVisible();
    await page.getByTestId("dido-option-wedding").click();
    await expect(page.getByTestId("brief-occasion")).toContainText("wedding", {
      timeout: 20_000,
    });
  });

  test("deleting a session removes it and leaves Style DNA alone", async ({ page, request }) => {
    await setStyleDna(request, true);
    await openDido(page);
    await startConversation(page);
    await say(page, "A wedding");

    await page.getByTestId("dido-delete").click();
    await expect(page.getByTestId("dido-start")).toBeVisible({ timeout: 20_000 });

    const current = await (
      await request.get(`${BASE}/api/v1/me/dido/sessions/current`, { headers: auth() })
    ).json();
    expect(current.session).toBeNull();

    expect((await readStyleDna(request)).exists).toBe(true);
  });

  test("the conversation log is a polite live region and does not steal focus", async ({
    page,
  }) => {
    await openDido(page);
    await startConversation(page);

    const log = page.getByTestId("dido-log");
    await expect(log).toHaveAttribute("aria-live", "polite");

    /* Focus must survive a reply arriving: being thrown out of the input mid-sentence is
     * the specific failure an impolite live region causes.
     *
     * Submitted with Enter rather than by clicking Send, because clicking moves focus to
     * the button by design and the first version of this test was measuring its own
     * click rather than the live region. */
    const input = page.getByTestId("dido-input");
    const before = await page.getByTestId("dido-log").locator("li").count();
    await input.fill("A wedding");
    await input.press("Enter");
    await expect
      .poll(async () => page.getByTestId("dido-log").locator("li").count(), { timeout: 25_000 })
      .toBeGreaterThanOrEqual(before + 2);
    await expect(input).toBeFocused();
  });

  test("controls meet the touch target minimum", async ({ page }) => {
    await openDido(page);
    await startConversation(page);
    const box = await page.getByTestId("dido-send").boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  });

  test("the input does not trigger an iOS zoom, which is what jumps the layout", async ({
    page,
  }) => {
    await openDido(page);
    await startConversation(page);
    const fontSize = await page
      .getByTestId("dido-input")
      .evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    // Below 16px, iOS Safari zooms on focus and pushes the controls out of reach.
    expect(fontSize).toBeGreaterThanOrEqual(16);
  });

  test("signed out, Dido asks for a sign-in and stores nothing locally", async ({ browser }) => {
    const context = await browser.newContext();
    const anon = await context.newPage();
    await anon.goto("/dido");

    await expect(anon.getByText("Sign in to style with Dido")).toBeVisible({ timeout: 20_000 });
    const keys = await anon.evaluate(() => Object.keys(window.localStorage));
    expect(keys.filter((k) => k.toLowerCase().includes("dido"))).toEqual([]);
    await context.close();
  });

  test("the boundary is stated before the conversation, not after it", async ({ page }) => {
    await openDido(page);
    const disclosure = await page.getByTestId("dido-disclosure").innerText();
    expect(disclosure.toLowerCase()).toContain("does not pick the clothes");
    // The OLD disclosure is gone: it said there was no intelligence at all, which became
    // false the moment this phase shipped.
    expect(disclosure.toLowerCase()).not.toContain("not the intelligence");
  });

  test("the home page does not animate a capability that does not exist", async ({ page }) => {
    await page.goto("/");
    // The section reveals on scroll, so bring it into view before reading the page text.
    await page.getByText(/choosing the clothes is not/i).scrollIntoViewIfNeeded();
    const body = (await page.locator("body").innerText()).toLowerCase();
    // The note must name the half that is not built...
    expect(body).toContain("choosing the clothes is not");
    // ...and must no longer claim the whole intelligence is missing.
    expect(body).not.toContain("the intelligence behind it is not");
    // The hero must not claim the engine either.
    expect(body).not.toContain("it builds complete looks");
  });
});

test.describe("Dido with personalisation off", () => {
  test("no profile value is used, and Dido says so", async ({ page, request }) => {
    await setStyleDna(request, false);
    await openDido(page);
    await startConversation(page);

    await expect(page.getByTestId("dido-personalisation")).toContainText("not being used");
    await expect(page.getByTestId("brief-style-dna")).toHaveCount(0);

    // The opening turn states it too, where it will actually be read.
    await expect(page.getByTestId("dido-log")).toContainText("not being used");
  });

  test("the same preference stated by hand becomes session input", async ({ page, request }) => {
    await setStyleDna(request, false);
    await openDido(page);
    await startConversation(page);
    await say(page, "Dinner, smart casual, I like navy, 90 euros");

    await expect(page.getByTestId("brief-session")).toContainText("navy");
    await expect(page.getByTestId("brief-style-dna")).toHaveCount(0);

    // And the profile is still exactly as it was.
    const profile = await readStyleDna(request);
    expect(profile.exists).toBe(true);
    expect(profile.personalization_enabled).toBe(false);
  });
});
