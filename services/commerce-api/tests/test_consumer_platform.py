"""The Phase 2 consumer platform, rendered in a real DOM.

Phase 2 repositions DEDUNET from a clothing store into a personal fashion intelligence
platform. The claims that repositioning makes are testable, and this file tests them:

  the landing route is the platform, not the catalogue
  Dido is the primary action
  no module claims personalisation that no engine can produce
  fixture content is always marked as fixture
  navigation differs between phone and desktop rather than being one shrunk
  capabilities that do not exist say so, and are distinguishable from "empty"

The last two matter most. A "coming soon" that looks like an empty result, and a fixture
that looks like production data, are the two ways a demonstration build starts lying.

`test_storefront_purchase_refusal.py` and `test_storefront_session_expiry.py` cover the
accepted commerce and session behaviour, which this phase must not disturb; they are
deliberately NOT duplicated here.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
WEB = REPO / "apps" / "web"
NODE_PATHS = REPO / "apps" / "mobile" / "node_modules"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not (NODE_PATHS / "jsdom").is_dir(),
    reason="node with jsdom is required",
)

PREVIEW_MODE = {
    "mode": "BRAND_PREVIEW_MODE",
    "headline": "Preview only.",
    "detail": ["Nothing here is available to purchase.", "No order or payment can be completed."],
    "purchasable": False,
    "payments": "none",
    "public_commerce_enabled": False,
}

HARNESS = r"""
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const WEB = process.env.WEB_DIR;
const MODE = JSON.parse(process.env.MODE);

/* The real index.html, not a document invented here. The shell IS part of what this phase
   delivers -- navigation, landmarks, the live region -- so a harness that supplied its own
   markup would be testing a page that does not ship. */
const html = fs.readFileSync(path.join(WEB, "index.html"), "utf8");

function boot() {
  const dom = new JSDOM(html, {
    url: "http://127.0.0.1:13080/storefront/",
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const { window } = dom;
  window.DEDUNET_API_BASE = "http://127.0.0.1:18080";
  window.DEDUNET_BRAND = { name: "DEDUNET", tagline: "Worth, worn.", assets: {} };
  window.scrollTo = () => {};
  window.fetch = (url) => {
    const u = String(url);
    const ok = (body) =>
      Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(body)) });
    if (u.includes("/api/v1/commerce/mode")) return ok(MODE);
    if (u.includes("/api/v1/catalog/products")) return ok([]);
    return ok({});
  };
  for (const file of ["media-url.js", "ds.js", "data.js", "app.js"]) {
    window.eval(fs.readFileSync(path.join(WEB, file), "utf8"));
  }
  return window;
}

/* jsdom fires DOMContentLoaded on its own, so app.js's boot `route()` runs asynchronously
   after `boot()` returns. A harness that rendered a view immediately would have it
   overwritten by that initial route -- which is exactly what happened. Settle first, then
   navigate through the router, so these tests exercise routing rather than bypassing it. */
async function settle(window, ms = 60) {
  await new Promise((r) => setTimeout(r, ms));
  return window;
}

async function go(window, hash, ms = 80) {
  window.location.hash = hash;
  window.route();
  await new Promise((r) => setTimeout(r, ms));
  return window;
}

const text = (w) => w.document.getElementById("main").textContent.replace(/\s+/g, " ").trim();
const q = (w, sel) => Array.from(w.document.querySelectorAll(sel));
const testids = (w, id) => q(w, `[data-testid="${id}"]`);

(async () => {
  const result = {};

  /* ---------------------------------------------------------------- home */
  {
    const w = await settle(boot());
    await go(w, "#/");
    const hero = w.document.querySelector('[data-testid="hero"]');
    result.home = {
      text: text(w),
      heroPresent: hero !== null,
      heroText: hero ? hero.textContent.replace(/\s+/g, " ").trim() : null,
      primaryCta: (w.document.querySelector('[data-testid="cta-dido"]') || {}).textContent || null,
      primaryCtaHref: (w.document.querySelector('[data-testid="cta-dido"]') || {}).getAttribute
        ? w.document.querySelector('[data-testid="cta-dido"]').getAttribute("href") : null,
      secondaryCta: (w.document.querySelector('[data-testid="cta-discover"]') || {}).textContent || null,
      occasionCount: testids(w, "occasion-card").length,
      occasionHrefs: testids(w, "occasion-card").map((n) => n.getAttribute("href")),
      fixtureBadges: testids(w, "fixture-badge").length,
      forYouUnavailable: testids(w, "for-you").length,
      modules: q(w, "[data-testid^='module-']").map((n) => n.getAttribute("data-testid")),
      h1Count: q(w, "h1").length,
      h1Text: q(w, "h1").map((n) => n.textContent.trim()),
    };
  }

  /* ---------------------------------------------------------------- routing */
  {
    const w = await settle(boot());
    /* The landing default is the whole repositioning in one line. */
    await go(w, "");
    result.defaultRoute = { text: text(w).slice(0, 160) };

    await go(w, "#/nope-does-not-exist");
    result.unknownRoute = {
      text: text(w),
      hasErrorState: testids(w, "error-state").length > 0,
    };
  }

  /* ---------------------------------------------------------------- navigation */
  {
    const w = await settle(boot());
    const desktop = q(w, ".nav a");
    const mobile = q(w, ".mobile-nav a");
    w.location.hash = "#/discover";
    w.markActiveNav();
    result.nav = {
      desktop: desktop.map((a) => a.textContent.trim()),
      desktopRoutes: desktop.map((a) => a.getAttribute("data-route")),
      mobile: mobile.map((a) => a.textContent.trim()),
      mobileRoutes: mobile.map((a) => a.getAttribute("data-route")),
      didoIsPrimaryDesktop: desktop.some((a) => a.className.includes("nav__dido")),
      didoIsCentreMobile: mobile.length === 5 && mobile[2].className.includes("mobile-nav__dido"),
      activeAfterDiscover: q(w, '[aria-current="page"]').map((a) => a.getAttribute("data-route")),
      landmarks: {
        header: q(w, "header").length,
        main: q(w, "main").length,
        footer: q(w, "footer").length,
        navs: q(w, "nav[aria-label]").length,
      },
      liveRegion: (w.document.getElementById("ds-live") || {}).getAttribute
        ? w.document.getElementById("ds-live").getAttribute("aria-live") : null,
      skipLink: (w.document.querySelector(".skip") || {}).getAttribute
        ? w.document.querySelector(".skip").getAttribute("href") : null,
    };
  }

  /* ---------------------------------------------------------------- discover */
  {
    const w = await settle(boot());
    await go(w, "#/discover");
    const all = { text: text(w), chips: testids(w, "discover-chip").length,
                  cards: testids(w, "look-card").length };
    await go(w, "#/discover/interview");
    const filtered = { text: text(w), cards: testids(w, "look-card").length,
                       pressed: testids(w, "discover-chip").filter((c) => c.getAttribute("aria-pressed") === "true").length };
    await go(w, "#/discover/not-a-real-category");
    const unknown = { hasError: testids(w, "error-state").length > 0, text: text(w) };
    result.discover = { all, filtered, unknown };
  }

  /* ---------------------------------------------------------------- looks */
  {
    const w = await settle(boot());
    await go(w, "#/looks");
    const list = { cards: testids(w, "look-card").length, fixtures: testids(w, "fixture-badge").length };
    await go(w, "#/look/quiet-interview");
    const detail = {
      text: text(w),
      items: q(w, ".look-item").length,
      fixtures: testids(w, "fixture-badge").length,
      saveDisabled: (testids(w, "look-save")[0] || {}).disabled,
    };
    await go(w, "#/look/no-such-look");
    const missing = { hasError: testids(w, "error-state").length > 0 };
    result.looks = { list, detail, missing };
  }

  /* ---------------------------------------------------------------- brands */
  {
    const w = await settle(boot());
    await go(w, "#/brands");
    const list = { cards: testids(w, "brand-card").length, text: text(w) };
    await go(w, "#/brand/dedunet");
    const firstParty = { text: text(w), commerce: (testids(w, "brand-commerce")[0] || {}).textContent };
    await go(w, "#/brand/example-partner");
    const partner = { text: text(w), commerce: (testids(w, "brand-commerce")[0] || {}).textContent };
    await go(w, "#/brand/example-external");
    const external = { text: text(w), commerce: (testids(w, "brand-commerce")[0] || {}).textContent };
    result.brands = { list, firstParty, partner, external };
  }

  /* ---------------------------------------------------------------- saved / my style */
  {
    const w = await settle(boot());
    await go(w, "#/saved");
    result.saved = {
      text: text(w),
      sections: ["saved-looks", "saved-products", "saved-brands"].map((id) => testids(w, id).length),
      empties: testids(w, "empty-state").length,
      notBuiltCount: (text(w).match(/is not built yet/g) || []).length,
    };
    await go(w, "#/my-style");
    result.myStyle = {
      text: text(w),
      sections: q(w, '[data-testid="style-sections"] article').length,
      unavailable: testids(w, "style-profile").length,
    };
  }

  /* ---------------------------------------------------------------- dido */
  {
    const w = await settle(boot());
    await go(w, "#/dido");
    const figure = testids(w, "dido-figure")[0];
    const before = figure.dataset.state;
    const opts = testids(w, "dido-option");
    opts[0].dispatchEvent(new w.Event("click"));
    const duringThinking = testids(w, "dido-thinking").length;
    const stateDuring = figure.dataset.state;
    await new Promise((r) => setTimeout(r, 900));
    result.dido = {
      text: text(w),
      figurePresent: figure !== undefined,
      role: figure.getAttribute("role"),
      ariaLabel: figure.getAttribute("aria-label"),
      stateBefore: before,
      stateDuring,
      stateAfter: figure.dataset.state,
      thinkingShown: duringThinking,
      thinkingRole: (testids(w, "dido-thinking")[0] || {}).getAttribute
        ? "still-present" : "removed",
      optionCount: opts.length,
      log: w.document.querySelector('[data-testid="dido-log"]').textContent.replace(/\s+/g, " "),
      liveRegion: w.document.getElementById("ds-live").textContent,
      disclosure: (testids(w, "dido-disclosure")[0] || {}).textContent || null,
    };
  }

  /* ---------------------------------------------------------------- for brands */
  {
    const w = await settle(boot());
    await go(w, "#/for-brands");
    result.forBrands = {
      text: text(w),
      available: q(w, '[data-testid="brands-available"] li').length,
      later: q(w, '[data-testid="brands-later"] li').length,
      honesty: (testids(w, "for-brands-honesty")[0] || {}).textContent || null,
    };
  }

  /* ---------------------------------------------------------------- shop */
  {
    const w = await settle(boot());
    await go(w, "#/shop");
    result.shop = { text: text(w), h1: (w.document.querySelector("h1") || {}).textContent };
  }

  /* ---------------------------------------------------------------- ds states */
  {
    const w = await settle(boot());
    const box = w.document.getElementById("main");
    const cases = {};
    for (const status of [0, 401, 403, 404, 409, 429, 500, 503]) {
      box.replaceChildren(w.DS.errorState({ status, message: "" }));
      cases[status] = box.textContent.replace(/\s+/g, " ").trim();
    }
    box.replaceChildren(w.DS.errorState({ status: 500, message: "database is on fire" }));
    cases.withServerMessage = box.textContent.replace(/\s+/g, " ").trim();
    box.replaceChildren(w.DS.skeletonGrid(3));
    cases.skeleton = { busy: box.firstChild.getAttribute("aria-busy"),
                       cards: box.querySelectorAll(".skeleton--media").length };
    result.states = cases;
  }

  process.stdout.write(JSON.stringify(result));
})().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


@pytest.fixture(scope="module")
def page() -> dict:
    completed = subprocess.run(
        ["node", "-e", HARNESS],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(REPO / "apps" / "mobile"),
        env={**os.environ, "WEB_DIR": str(WEB), "MODE": json.dumps(PREVIEW_MODE),
             "NODE_PATH": str(NODE_PATHS), "PYTHONIOENCODING": "utf-8"},
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# ==================================================================== positioning


def test_the_landing_route_is_the_platform_not_the_catalogue(page):
    """The whole repositioning, reduced to one assertion.

    The default hash was `#/catalog`. A platform whose front door is a product grid is a
    shop with extra pages, whatever the rest of the navigation says.
    """

    landing = page["defaultRoute"]["text"]
    assert "Personal fashion intelligence" in landing, landing
    assert "Collection" not in landing


def test_the_hero_sells_styling_not_products(page):
    hero = page["home"]["heroText"]
    assert "DEDUNET" in hero
    assert "Personal fashion intelligence." in hero
    assert "helps you decide what to wear" in hero
    for banned in ("Shop now", "Buy now", "Collection"):
        assert banned not in hero, f"hero still positions around {banned!r}"


def test_dido_is_the_primary_call_to_action(page):
    """Primary, not merely present. Order and prominence are the claim."""

    assert page["home"]["primaryCta"].strip().lower() == "style me with dido"
    assert page["home"]["primaryCtaHref"] == "#/dido"
    assert page["home"]["secondaryCta"].strip().lower() == "discover looks"


def test_the_occasion_chooser_is_on_the_home_page(page):
    assert "What are you dressing for?" in page["home"]["text"]
    assert page["home"]["occasionCount"] == 11, page["home"]["occasionCount"]
    assert all(h.startswith("#/dido?occasion=") for h in page["home"]["occasionHrefs"])


def test_the_home_modules_exist(page):
    modules = set(page["home"]["modules"])
    for expected in ("module-for-you", "module-trending", "module-editors",
                     "module-under-100", "module-under-200", "module-brands",
                     "module-dido", "module-for-brands"):
        assert expected in modules, f"{expected} missing from {sorted(modules)}"


# ==================================================================== honesty


def test_no_module_claims_personalisation_that_cannot_be_produced(page):
    """"Selected for you" over fixture content would be a personalisation claim.

    Style DNA does not exist and neither does the recommendation engine, so the module
    states that rather than dressing up demonstration looks as a personal selection. This
    is the single easiest place for a demo build to start lying.
    """

    assert page["home"]["forYouUnavailable"] == 1
    assert "Personalised look selection is not built yet" in page["home"]["text"]


def test_fixture_content_is_always_marked(page):
    """§29. A demonstration look must never be mistakable for verified data."""

    assert page["home"]["fixtureBadges"] >= 4, page["home"]["fixtureBadges"]
    assert page["looks"]["list"]["fixtures"] >= 1
    assert page["looks"]["detail"]["fixtures"] >= 1


def test_unavailable_is_distinguishable_from_empty(page):
    """Two different facts, and rendering them the same way is how "not built" reads as
    "you have nothing"."""

    saved = page["saved"]
    assert saved["sections"] == [1, 1, 1], saved
    assert saved["notBuiltCount"] == 3, saved
    assert saved["empties"] == 0, "an unbuilt capability must not render as an empty result"


def test_saved_does_not_fabricate_persistence(page):
    """A save button that silently forgets is worse than one that says it is not built."""

    assert page["looks"]["detail"]["saveDisabled"] is True


def test_only_dedunet_is_presented_as_a_real_brand(page):
    """§11 forbids inventing commercial partnerships."""

    for key in ("partner", "external"):
        text = page["brands"][key]["text"]
        assert "no such brand exists" in text.lower(), (key, text)
    assert "no such brand exists" not in page["brands"]["firstParty"]["text"].lower()


def test_brand_ownership_terms_never_reach_the_consumer(page):
    """The model is ADR-0002's; the vocabulary is not the customer's."""

    for key in ("firstParty", "partner", "external"):
        text = page["brands"][key]["text"]
        for term in ("PLATFORM_CURATED", "MERCHANT_OWNED", "EXTERNAL_CURATED", "ownership_type"):
            assert term not in text, f"{term} leaked into {key}"


def test_consumer_brand_labels_are_used_instead(page):
    assert "DEDUNET selection" in page["brands"]["list"]["text"]
    assert "Partner brand" in page["brands"]["list"]["text"]
    assert "External brand" in page["brands"]["list"]["text"]


def test_commerce_route_is_stated_per_brand(page):
    """Route is where the money goes, and it is independent of who owns the brand."""

    assert page["brands"]["firstParty"]["commerce"] == "Not available to buy"
    assert page["brands"]["partner"]["commerce"] == "Available on DEDUNET"
    assert page["brands"]["external"]["commerce"] == "View at the brand"


def test_for_brands_separates_available_from_later(page):
    fb = page["forBrands"]
    assert fb["available"] >= 3 and fb["later"] >= 5, fb
    assert "not accepting brands" in fb["honesty"].lower()
    assert "not built" in fb["honesty"].lower()


# ==================================================================== navigation


def test_desktop_navigation_is_the_specified_set_in_order(page):
    assert page["nav"]["desktop"] == [
        "Style with Dido", "Discover", "Looks", "Brands", "Shop", "Saved", "Account",
    ], page["nav"]["desktop"]


def test_mobile_navigation_is_five_destinations_with_dido_at_the_centre(page):
    """Not the desktop bar shrunk. A different information architecture for a different
    context, which is what §21 asks for."""

    assert page["nav"]["mobile"] == ["Home", "Discover", "Dido", "Saved", "Account"], page["nav"]["mobile"]
    assert page["nav"]["didoIsCentreMobile"] is True
    assert page["nav"]["didoIsPrimaryDesktop"] is True


def test_the_active_route_is_marked_for_assistive_technology(page):
    """`aria-current` is the source of truth and the CSS keys off it, so the highlight and
    the announcement cannot drift apart."""

    active = page["nav"]["activeAfterDiscover"]
    assert "#/discover" in active, active


def test_the_page_has_semantic_landmarks(page):
    lm = page["nav"]["landmarks"]
    assert lm["header"] == 1 and lm["main"] == 1 and lm["footer"] == 1
    assert lm["navs"] >= 2, "each nav needs its own accessible name"


def test_a_skip_link_and_one_live_region_exist(page):
    assert page["nav"]["skipLink"] == "#main"
    assert page["nav"]["liveRegion"] == "polite"


def test_exactly_one_h1_per_page(page):
    """Heading order is a navigation mechanism for screen-reader users, not decoration."""

    assert page["home"]["h1Count"] == 1, page["home"]["h1Text"]


# ==================================================================== discover / looks


def test_discover_lists_categories_and_filters_by_them(page):
    d = page["discover"]
    assert d["all"]["chips"] >= 18, d["all"]["chips"]
    assert d["all"]["cards"] >= 5
    assert d["filtered"]["cards"] >= 1
    assert d["filtered"]["cards"] < d["all"]["cards"], "the category filter did nothing"
    assert d["filtered"]["pressed"] == 1, "the active category is not marked"


def test_an_unknown_discover_category_is_a_404_not_an_empty_grid(page):
    assert page["discover"]["unknown"]["hasError"] is True


def test_a_look_shows_its_pieces_prices_and_reasoning(page):
    detail = page["looks"]["detail"]
    assert detail["items"] == 3, detail["items"]
    assert "The Quiet Interview" in detail["text"]
    assert "Total" in detail["text"]
    assert "€278.00" in detail["text"], detail["text"]
    assert "Unbroken vertical line" in detail["text"], "the rationale is missing"


def test_a_missing_look_is_an_error_not_a_blank_page(page):
    assert page["looks"]["missing"]["hasError"] is True


# ==================================================================== dido shell


def test_the_dido_character_is_present_and_labelled(page):
    d = page["dido"]
    assert d["figurePresent"] is True
    assert d["role"] == "img"
    assert "Dido" in d["ariaLabel"]


def test_dido_moves_through_its_animation_states(page):
    """The animator seam, exercised. A later Rive or Lottie renderer implements the same
    contract, so this test survives the swap."""

    d = page["dido"]
    assert d["stateBefore"] == "asking"
    assert d["stateDuring"] == "thinking"
    assert d["stateAfter"] == "presenting"
    assert d["thinkingShown"] == 1


def test_the_state_change_is_announced_to_screen_readers(page):
    assert page["dido"]["liveRegion"], "no status was announced"
    assert "Dido" in page["dido"]["liveRegion"]


def test_dido_does_not_fake_a_recommendation(page):
    """The single most important assertion in this file.

    Phase 2 builds Dido's SURFACE. An engine that does not exist must not appear to work,
    and a scripted "here is your outfit" would be exactly that.
    """

    d = page["dido"]
    assert "can't build looks yet" in d["log"] or "can't style it yet" in d["log"], d["log"]
    assert "arrives in a later platform phase" in d["disclosure"]
    assert "will not invent a recommendation" in d["disclosure"]


def test_dido_offers_occasions_rather_than_a_blank_prompt(page):
    assert page["dido"]["optionCount"] >= 6


# ==================================================================== states


@pytest.mark.parametrize("status,expected", [
    (0, "Cannot reach DEDUNET"),
    (401, "Your session has ended"),
    (403, "Not available on this account"),
    (404, "Not found"),
    (409, "Not available"),
    (429, "Too many requests"),
    (500, "DEDUNET had a problem"),
    (503, "Temporarily unavailable"),
])
def test_every_failure_status_has_its_own_copy(page, status, expected):
    """§23 forbids a generic "Load failed" where context exists. The status IS context."""

    assert expected in page["states"][str(status)], page["states"][str(status)]


def test_the_servers_message_appears_below_our_sentence_not_instead_of_it(page):
    combined = page["states"]["withServerMessage"]
    assert "DEDUNET had a problem" in combined
    assert "database is on fire" in combined


def test_a_loading_state_reserves_the_layout(page):
    """A skeleton, not the word "Loading…", so arriving content does not shift the page."""

    assert page["states"]["skeleton"]["busy"] == "true"
    assert page["states"]["skeleton"]["cards"] == 3


def test_an_unknown_route_renders_an_error_not_a_blank_page(page):
    assert page["unknownRoute"]["hasErrorState"] is True
    assert "does not exist" in page["unknownRoute"]["text"]


# ==================================================================== shop


def test_the_shop_still_works_and_is_framed_as_one_destination(page):
    assert page["shop"]["h1"].strip() == "Shop"
    assert "start with Dido" in page["shop"]["text"], page["shop"]["text"]


# ==================================================================== source guards


def test_each_client_script_publishes_exactly_one_global_namespace():
    """`ds.js` and `data.js` are IIFEs.

    Without that, every helper in them is a global, and `app.js` declaring
    `const el = window.DS.el` collides with `ds.js`'s `function el` -- a SyntaxError that
    takes the whole page down. jsdom's per-file `window.eval` gives each script its own
    scope and hides it; a browser loading real <script> tags does not, and it did not.
    """

    for name, namespace in (("ds.js", "window.DS ="), ("data.js", "window.DedunetData =")):
        source = (WEB / name).read_text(encoding="utf-8")
        assert "(function () {" in source, f"{name} is not wrapped"
        assert source.rstrip().endswith("})();"), f"{name} is not closed"
        assert namespace in source, f"{name} does not publish its namespace"


def test_the_design_system_consumes_only_brand_tokens():
    """Components reference `--ds-*`; the semantic layer maps those onto `--ddn-*`.

    A raw hex in the component layer means a colour outside the delivered palette, which is
    how the storefront ended up with a second palette nobody had reconciled.
    """

    components = (WEB / "components.css").read_text(encoding="utf-8")
    stripped = re.sub(r"/\*.*?\*/", "", components, flags=re.DOTALL)
    hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", stripped)
    assert not hexes, f"component layer names raw colours: {sorted(set(hexes))}"


def test_the_semantic_layer_is_built_on_the_generated_tokens():
    ds = (WEB / "design-system.css").read_text(encoding="utf-8")
    assert "var(--ddn-color-background)" in ds
    assert "var(--ddn-type-displayfont)" in ds
    assert (WEB / "tokens.generated.css").is_file(), "generated tokens are not shipped"


def test_reduced_motion_is_handled_centrally():
    """Every duration routes through the design-system tokens, so one media query zeroes
    them all rather than each component remembering to opt out."""

    ds = (WEB / "design-system.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in ds
    assert "--ds-duration: 1ms" in ds

    shell = (WEB / "shell.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in shell, "the Dido animation has no reduced-motion path"
    assert ".dido-iris { animation: none !important; }" in shell


def test_the_mobile_navigation_is_not_a_media_query_afterthought():
    """Mobile-first: the tab bar is the DEFAULT and the desktop header is the enhancement.

    Asserted structurally -- `.nav` starts hidden and appears at a min-width, rather than
    starting visible and being hidden at a max-width, which is what "designed desktop then
    shrunk" looks like in CSS.
    """

    shell = (WEB / "shell.css").read_text(encoding="utf-8")
    assert ".nav { display: none; }" in shell
    assert "@media (min-width: 1024px)" in shell
    assert "max-width" not in shell.split(".mobile-nav")[1][:400], (
        "the mobile navigation is gated on a max-width, i.e. desktop-first"
    )
