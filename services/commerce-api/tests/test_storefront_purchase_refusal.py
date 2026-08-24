"""The storefront's purchase invitation and empty order history, rendered in a real DOM.

Human iPhone Safari acceptance found two screens inviting a customer to do something the
deployment had already decided to refuse:

  A. product detail offered an ordinary, enabled "Add to cart" in BRAND_PREVIEW_MODE.
     Pressing it produced 409 "this catalogue is in brand preview". The server was correct
     throughout; the page was contradicting it.

  B. the empty order history said "You have no orders yet." full stop, which in preview
     mode reads as an invitation to place one. Nothing can be placed there.

Both are the class of defect this programme keeps closing -- a surface asserting something
the mode does not support -- already fixed on the native client in `1a90c10` and `4e4f8c0`
and in the storefront banner. These are the same two, one surface over.

`test_commerce_mode_disclosure.py` covers what each mode SAYS about itself. This covers
whether the storefront ACTS on it, which is a different failure and the one that shipped:
`modes.assert_purchasable` was right all along and no button ever asked it.

Rendered rather than asserted from source text. The defect was a screen offering the wrong
control, so a screen is what has to be inspected -- a source grep for "disabled" would pass
against a button that renders enabled.
"""

from __future__ import annotations

import json
import os
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

# The bodies `/api/v1/commerce/mode` actually returns, from `modes.describe`.
PREVIEW_MODE = {
    "mode": "BRAND_PREVIEW_MODE",
    "headline": "Preview only.",
    "detail": [
        "Nothing here is available to purchase.",
        "No order or payment can be completed.",
    ],
    "purchasable": False,
    "payments": "none",
    "public_commerce_enabled": False,
}

TEST_MODE = {
    "mode": "COMMERCE_TEST_MODE",
    "headline": "Internal commerce test mode.",
    "detail": [
        "Only synthetic test inventory is available.",
        "Payments use the sandbox adapter.",
        "No real card is charged.",
        "No real stock or fulfilment is involved.",
    ],
    "purchasable": True,
    "payments": "sandbox",
    "public_commerce_enabled": False,
}

# `modes.describe(None)` -- the deployment cannot state a permitted mode. Distinct from
# either working mode and never a silent fallback to one of them.
BLOCKED_MODE = {
    "mode": None,
    "headline": "Commerce is unavailable.",
    "detail": [
        "This deployment's commerce mode is not permitted.",
        "Nothing here is available to purchase.",
    ],
    "purchasable": False,
    "payments": "none",
    "public_commerce_enabled": False,
}

# A product the PRODUCT gate permits, so the MODE gate is the only thing that can refuse it.
# Deliberately sellable: a preview catalogue whose products were all `sellable: false` would
# let the product gate alone produce every expected result and prove nothing about the mode.
SELLABLE_PRODUCT = {
    "slug": "the-source-tee",
    "name": "The Source Tee",
    "description": "A prototype piece.",
    "currency": "EUR",
    "collection": "Source",
    "external_product_id": "DDN-TS01",
    "sellable": True,
    "material": "Cotton",
    "origin_claim_status": "UNVERIFIED",
    "country_of_origin": "XX",
    "intended_origin": "PT",
    "media": [],
    "variants": [
        {
            "id": 1,
            "sku": "DDN-TS01-M",
            "size": "M",
            "color": "Sand",
            "price_minor_units": 5900,
            "available": 4,
            "sellable": True,
        },
    ],
}

NON_SELLABLE_PRODUCT = {**SELLABLE_PRODUCT, "sellable": False}

HARNESS = r"""
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const WEB = process.env.WEB_DIR;
const MODES = JSON.parse(process.env.MODES);
const PRODUCTS = JSON.parse(process.env.PRODUCTS);

/* The notice element exactly as index.html ships it, so the client boots the way it does in
   a browser rather than into a document invented here. */
function boot({ modeBody, product, orders, token = "", modeHangs = false }) {
  const dom = new JSDOM(
    "<!doctype html><html><head></head><body>" +
      '<p class="notice" role="note" id="commerce-mode-notice">shipped notice</p>' +
      "<div id='banner'></div><main id='main'></main></body></html>",
    { url: "http://127.0.0.1:13080/storefront/", runScripts: "outside-only" }
  );
  const { window } = dom;
  window.DEDUNET_API_BASE = "http://127.0.0.1:18080";
  window.DEDUNET_BRAND = { name: "DEDUNET", assets: {} };
  window.scrollTo = () => {};
  if (token) {
    window.localStorage.setItem("dedunet_token", token);
    window.localStorage.setItem("dedunet_role", "customer");
  }

  const calls = [];
  window.fetch = (url) => {
    const u = String(url);
    calls.push(u);
    const ok = (body) =>
      Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(body)) });

    if (u.includes("/api/v1/commerce/mode")) {
      /* Never settles. Proves the bounded wait, not a slow one. */
      if (modeHangs) return new Promise(() => {});
      if (modeBody === "network-failure") return Promise.reject(new TypeError("Failed to fetch"));
      return ok(modeBody);
    }
    if (u.includes("/api/v1/me/orders")) return ok(orders === undefined ? [] : orders);
    if (u.includes("/api/v1/catalog/products/")) return ok(product);
    return ok({});
  };

  for (const file of ["media-url.js", "app.js"]) {
    window.eval(fs.readFileSync(path.join(WEB, file), "utf8"));
  }
  window.__calls = calls;
  return window;
}

/* Boot the mode request the way the page does, and let the views wait on it. `modeReady`
   is a lexical binding in the evaluated script, so it is set through the same
   DOMContentLoaded listener a browser fires rather than assigned from outside. */
function startMode(window) {
  window.document.dispatchEvent(
    new window.Event("DOMContentLoaded", { bubbles: true, cancelable: false })
  );
}

function describeButton(window) {
  const main = window.document.getElementById("main");
  const buttons = Array.from(main.querySelectorAll("button"));
  /* The add control is the primary button; size buttons carry .size. */
  const add = buttons.find((b) => b.className.includes("btn--primary")) || null;
  const describedBy = add ? add.getAttribute("aria-describedby") : null;
  const reason = describedBy ? main.querySelector("#" + describedBy) : null;
  return {
    found: add !== null,
    label: add ? add.textContent : null,
    disabled: add ? add.disabled : null,
    describedBy,
    reasonText: reason ? reason.textContent : null,
    reasonPresent: reason !== null,
    mainText: main.textContent.replace(/\s+/g, " ").trim(),
  };
}

function mainText(window) {
  return window.document.getElementById("main").textContent.replace(/\s+/g, " ").trim();
}

(async () => {
  const result = { product: {}, orders: {} };

  /* ---------------------------------------------------------------- issue A */
  const productCases = {
    preview_mode_sellable_product: { modeBody: MODES.preview, product: PRODUCTS.sellable },
    preview_mode_non_sellable_product: { modeBody: MODES.preview, product: PRODUCTS.nonSellable },
    test_mode_sellable_product: { modeBody: MODES.test, product: PRODUCTS.sellable },
    test_mode_non_sellable_product: { modeBody: MODES.test, product: PRODUCTS.nonSellable },
    blocked_mode_sellable_product: { modeBody: MODES.blocked, product: PRODUCTS.sellable },
    blocked_mode_non_sellable_product: { modeBody: MODES.blocked, product: PRODUCTS.nonSellable },
    mode_unreachable_sellable_product: { modeBody: "network-failure", product: PRODUCTS.sellable },
    mode_unreachable_non_sellable_product: {
      modeBody: "network-failure",
      product: PRODUCTS.nonSellable,
    },
  };

  for (const [name, spec] of Object.entries(productCases)) {
    const window = boot(spec);
    startMode(window);
    window.location.hash = "#/product/the-source-tee";
    await window.viewProduct("the-source-tee");
    result.product[name] = describeButton(window);
  }

  /* A hanging mode request must not hold the page in "Loading...". */
  {
    const window = boot({ modeHangs: true, product: PRODUCTS.sellable });
    startMode(window);
    const started = Date.now();
    await window.viewProduct("the-source-tee");
    result.product.mode_hangs = {
      ...describeButton(window),
      elapsedMs: Date.now() - started,
    };
  }

  /* ---------------------------------------------------------------- issue B */
  const orderCases = {
    preview: MODES.preview,
    test: MODES.test,
    blocked: MODES.blocked,
    unreachable: "network-failure",
  };

  for (const [name, modeBody] of Object.entries(orderCases)) {
    const window = boot({ modeBody, orders: [], token: "session-token-not-a-credential" });
    startMode(window);
    window.location.hash = "#/orders";
    await window.viewOrders();
    result.orders[name] = { text: mainText(window) };
  }

  /* A customer WITH orders must never see any of the three, and must not wait for a mode
     request to find that out. */
  {
    const window = boot({
      modeHangs: true,
      orders: [{ order_number: "DDN-1001", status: "paid", total_minor_units: 5900 }],
      token: "session-token-not-a-credential",
    });
    startMode(window);
    const started = Date.now();
    window.location.hash = "#/orders";
    await window.viewOrders();
    result.orders.with_orders_mode_hangs = {
      text: mainText(window),
      elapsedMs: Date.now() - started,
    };
  }

  /* A hanging mode request on the empty branch must still render, bounded. */
  {
    const window = boot({ modeHangs: true, orders: [], token: "session-token-not-a-credential" });
    startMode(window);
    const started = Date.now();
    window.location.hash = "#/orders";
    await window.viewOrders();
    result.orders.empty_mode_hangs = {
      text: mainText(window),
      elapsedMs: Date.now() - started,
    };
  }

  /* ------------------------------------------------- one request, not one per view
     Counted for ONE view and for THREE, and compared. An absolute count would be measuring
     jsdom -- which fires its own DOMContentLoaded as the document settles, on top of the
     one dispatched here -- rather than measuring the client. What matters is that the
     number does not grow with the number of views. */
  const countModeRequests = async (views) => {
    const window = boot({
      modeBody: MODES.preview,
      product: PRODUCTS.sellable,
      orders: [],
      token: "session-token-not-a-credential",
    });
    startMode(window);
    for (let i = 0; i < views; i += 1) {
      await window.viewProduct("the-source-tee");
      await window.viewOrders();
    }
    return window.__calls.filter((u) => u.includes("/commerce/mode")).length;
  };
  result.modeRequests = {
    oneRound: await countModeRequests(1),
    threeRounds: await countModeRequests(3),
  };

  process.stdout.write(JSON.stringify(result));
})().catch((error) => {
  process.stderr.write(String((error && error.stack) || error));
  process.exit(1);
});
"""


@pytest.fixture(scope="module")
def rendered() -> dict:
    env = {
        **os.environ,
        "WEB_DIR": str(WEB),
        "MODES": json.dumps({"preview": PREVIEW_MODE, "test": TEST_MODE, "blocked": BLOCKED_MODE}),
        "PRODUCTS": json.dumps({"sellable": SELLABLE_PRODUCT, "nonSellable": NON_SELLABLE_PRODUCT}),
        "NODE_PATH": str(NODE_PATHS),
        "PYTHONIOENCODING": "utf-8",
    }
    completed = subprocess.run(
        ["node", "-e", HARNESS],
        capture_output=True,
        text=True,
        # Explicit UTF-8, for the same reason test_web_gallery.py gives: the Windows locale
        # codec turns the em dashes in this copy into mojibake and fails wording tests for
        # reasons that have nothing to do with wording.
        encoding="utf-8",
        cwd=str(REPO / "apps" / "mobile"),
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# ======================================================================= issue A
#
# The MODE gate. `assert_purchasable` refuses every purchase in brand preview whatever the
# product says, so a sellable product in preview mode is the case that isolates it.


def test_preview_mode_does_not_offer_to_add_a_sellable_product(rendered):
    """The reported defect, with the product gate deliberately not firing.

    Every product in the current preview catalogue also carries `sellable: false`, so a
    client mirroring only the product gate looks correct against today's seed. That is a
    property of the data, not a rule the server enforces. This case holds the product
    sellable so only the mode can refuse it.
    """

    case = rendered["product"]["preview_mode_sellable_product"]
    assert case["found"] is True, case
    assert case["disabled"] is True, case
    assert case["label"] == "Not available to buy", case


def test_preview_mode_states_the_reason_next_to_the_control(rendered):
    case = rendered["product"]["preview_mode_sellable_product"]
    assert case["reasonPresent"] is True, case
    assert case["describedBy"] == "purchase-refusal", case
    assert "preview" in case["reasonText"].lower(), case


def test_a_non_sellable_product_is_refused_in_commerce_test_mode(rendered):
    """The PRODUCT gate, isolated: a permitted mode, a product that still may not be sold."""

    case = rendered["product"]["test_mode_non_sellable_product"]
    assert case["disabled"] is True, case
    assert case["label"] == "Not available to buy", case
    assert case["reasonPresent"] is True, case


def test_the_two_refusals_do_not_share_a_reason(rendered):
    """Two different facts about the deployment. A customer told the wrong one is misinformed.

    The same discipline `modes.py` applies to PREVIEW_DISCLOSURE and
    COMMERCE_TEST_DISCLOSURE: a shared sentence is how one mode's truth ends up on another
    mode's screen.
    """

    mode_reason = rendered["product"]["preview_mode_sellable_product"]["reasonText"]
    product_reason = rendered["product"]["test_mode_non_sellable_product"]["reasonText"]
    assert mode_reason != product_reason, (mode_reason, product_reason)


def test_commerce_test_mode_still_offers_a_sellable_product(rendered):
    """The fix must not disable purchasing where purchasing is exactly what is being tested.

    Without this, "disable the button" passes every other test in this file by disabling it
    everywhere, and the internal commerce-test journey -- synthetic stock, cart, sandbox
    checkout -- becomes unperformable.
    """

    case = rendered["product"]["test_mode_sellable_product"]
    assert case["found"] is True, case
    assert case["disabled"] is False, case
    assert case["label"] == "Add to cart", case
    assert case["reasonPresent"] is False, case


def test_a_deployment_that_cannot_state_its_mode_still_refuses_a_non_sellable_product(rendered):
    """The mode is unknown, so the mode gate cannot fire -- the product gate must."""

    case = rendered["product"]["blocked_mode_non_sellable_product"]
    assert case["disabled"] is True, case
    assert case["label"] == "Not available to buy", case


def test_an_unresolved_mode_does_not_refuse_a_sellable_product_on_its_own(rendered):
    """Deliberate, and the one place this client is permissive.

    The mode gate cannot be evaluated against a mode nobody has stated. Refusing anyway
    would block a legitimate purchase in COMMERCE_TEST_MODE for as long as the mode call is
    unanswered, and the server -- which is the authority -- would have allowed it. The
    product gate still applies, and in a preview catalogue it is what fires.
    """

    for name in ("blocked_mode_sellable_product", "mode_unreachable_sellable_product"):
        case = rendered["product"][name]
        assert case["disabled"] is False, (name, case)
        assert case["label"] == "Add to cart", (name, case)


def test_an_unreachable_mode_endpoint_still_refuses_a_non_sellable_product(rendered):
    case = rendered["product"]["mode_unreachable_non_sellable_product"]
    assert case["disabled"] is True, case


def test_a_hanging_mode_request_does_not_hold_the_product_page(rendered):
    """`api()` has no timeout, so an unbounded await would leave the page in "Loading...".

    A blank page is the outcome `route`'s own catch exists to prevent; reintroducing it
    here through the mode wait would be a worse defect than the copy this change fixes.
    """

    case = rendered["product"]["mode_hangs"]
    assert case["found"] is True, case
    assert "Loading" not in case["mainText"], case
    assert case["elapsedMs"] < 10000, case["elapsedMs"]


# ======================================================================= issue B


def test_preview_mode_does_not_invite_an_order_it_will_refuse(rendered):
    text = rendered["orders"]["preview"]["text"]
    assert "No orders yet." in text, text
    assert "Purchasing is unavailable while this catalogue is in preview." in text, text


def test_preview_mode_never_promises_sandbox_orders(rendered):
    """The native equivalent of this defect (`4e4f8c0`) was exactly this sentence."""

    text = rendered["orders"]["preview"]["text"]
    assert "sandbox" not in text.lower(), text


def test_commerce_test_mode_says_what_it_can_actually_support(rendered):
    text = rendered["orders"]["test"]["text"]
    assert "Sandbox test orders you place will appear here." in text, text


def test_the_two_modes_do_not_share_an_empty_history_message(rendered):
    preview = rendered["orders"]["preview"]["text"]
    test = rendered["orders"]["test"]["text"]
    assert preview != test, preview


def test_an_unresolved_mode_promises_nothing(rendered):
    """Before the deployment has said what it allows, the honest answer is that we do not know.

    Promising sandbox ordering here would reintroduce the defect for exactly the window in
    which the client cannot know better; promising preview would understate a live sandbox.
    """

    for name in ("blocked", "unreachable"):
        text = rendered["orders"][name]["text"]
        assert "No orders yet." in text, (name, text)
        assert "once this deployment allows purchasing" in text, (name, text)
        assert "sandbox" not in text.lower(), (name, text)
        assert "preview" not in text.lower(), (name, text)


def test_the_retired_sentence_is_gone_from_every_mode(rendered):
    """'You have no orders yet.' was the reported wording. No mode may reproduce it."""

    for name, case in rendered["orders"].items():
        assert "You have no orders yet" not in case["text"], (name, case["text"])


def test_a_customer_with_orders_never_waits_for_the_mode(rendered):
    """The empty branch is the only one that needs the mode.

    The populated branch must not acquire a dependency on it -- an order history that
    stalls behind a disclosure request would be a regression introduced by a copy fix.
    """

    case = rendered["orders"]["with_orders_mode_hangs"]
    assert "DDN-1001" in case["text"], case
    assert case["elapsedMs"] < 1000, case["elapsedMs"]


def test_a_hanging_mode_request_does_not_hold_the_orders_page(rendered):
    case = rendered["orders"]["empty_mode_hangs"]
    assert "No orders yet." in case["text"], case
    assert case["elapsedMs"] < 10000, case["elapsedMs"]


# ======================================================================= shared plumbing


def test_the_mode_is_not_requested_again_for_each_view(rendered):
    """The mode is a property of the deployment, not of the page being viewed.

    A per-view request would put a disclosure call in front of every navigation and, on a
    rate-limited deployment, spend the customer's request budget on it.

    Asserted as "six views cost no more than two" rather than against a fixed number,
    because jsdom fires its own DOMContentLoaded as the document settles in addition to the
    one the harness dispatches. Pinning an absolute count would measure the test
    environment; comparing the two rounds measures the client.
    """

    counts = rendered["modeRequests"]
    assert counts["threeRounds"] == counts["oneRound"], counts


def test_an_unknown_mode_string_is_not_adopted():
    """Validated against a known set rather than stored raw.

    Everything downstream decides what a customer is invited to do, so a payload naming
    PUBLIC_COMMERCE_MODE -- which `current_mode()` refuses outright -- must land in the
    "not known" case and not become a third behaviour.
    """

    source = (WEB / "app.js").read_text(encoding="utf-8")
    assert "KNOWN_MODES.includes(mode)" in source, "the mode must be validated, not adopted"
    assert '"BRAND_PREVIEW_MODE", "COMMERCE_TEST_MODE"' in source

    # As a STRING LITERAL, which is the only form the client could compare or store. The
    # name appears in prose above `KNOWN_MODES` explaining why it is excluded, and that
    # comment is the design rather than a violation of it -- a bare `not in source` check
    # would forbid documenting the exclusion it exists to enforce.
    assert '"PUBLIC_COMMERCE_MODE"' not in source, (
        "the storefront must not carry the refused mode as a value it can act on"
    )
