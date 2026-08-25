"""What the storefront does when the server rejects a stored session.

Post-acceptance issue B, reproduced from the human tester's sequence:

    1. the customer signed in earlier
    2. the stored token later became invalid
    3. GET /api/v1/me/orders  ->  401 {"detail": "invalid or expired session"}
    4. the orders page said   ->  "You have no orders yet."
    5. the account page said  ->  "Signed in as customer."

The backend was right at every step. The client turned an authentication failure into a
factual claim about the customer's order history, kept the dead token, and went on
presenting them as signed in.

The correction has two halves and both matter. A 401 on a request that carried credentials
must end the session -- and nothing else may. Signing a customer out because a request timed
out is a worse defect than the one being fixed, so the negative cases here are not padding;
they are the reason the condition is narrow.
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

# Exactly what `current_customer` raises for a token it will not accept.
EXPIRED = {"status": 401, "detail": "invalid or expired session"}

# Failures that say nothing about the token and must leave the session alone.
NON_AUTH_FAILURES = {
    "network": {"reject": "Failed to fetch"},
    "timeout": {"reject": "The operation timed out"},
    "rate_limited": {"status": 429, "detail": "rate limit exceeded"},
    "server_error": {"status": 500, "detail": "internal error"},
    "bad_gateway": {"status": 502, "detail": "upstream failure"},
    "unavailable": {"status": 503, "detail": "temporarily unavailable"},
    "forbidden": {"status": 403, "detail": "administrator role required"},
    "not_found": {"status": 404, "detail": "order not found"},
    "conflict": {"status": 409, "detail": "out of stock"},
}

ORDER = {
    "order_number": "FC-FAFBAB8A",
    "status": "shipped",
    "commerce_mode_at_checkout": "COMMERCE_TEST_MODE",
    "is_test_order": True,
    "currency": "EUR",
    "subtotal_minor_units": 7200,
    "discount_minor_units": 0,
    "shipping_minor_units": 890,
    "tax_minor_units": 1292,
    "total_minor_units": 8090,
    "promotion_code": "",
    "lines": [
        {
            "sku": "DDN-SRC-CAR-XS",
            "product_name": "The Source Tee",
            "size": "XS",
            "color": "Carbon",
            "quantity": 1,
            "unit_price_minor_units": 7200,
            "line_total_minor_units": 7200,
        }
    ],
    "shipments": [{"carrier": "mock-carrier", "tracking_number": "TRK2CC820AABF", "status": "IN_TRANSIT"}],
}

HARNESS = r"""
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const WEB = process.env.WEB_DIR;
const FAILURES = JSON.parse(process.env.FAILURES);
const EXPIRED = JSON.parse(process.env.EXPIRED);
const ORDER = JSON.parse(process.env.ORDER);

function boot({ token = "", role = "", cart = "", responder }) {
  const dom = new JSDOM(
    "<!doctype html><html><head></head><body>" +
      '<p class="notice" id="commerce-mode-notice">shipped notice</p>' +
      "<div id='banner'></div><main id='main'></main></body></html>",
    { url: "http://127.0.0.1:13080/storefront/", runScripts: "outside-only" }
  );
  const { window } = dom;
  window.DEDUNET_API_BASE = "http://127.0.0.1:18080";
  window.DEDUNET_BRAND = { name: "DEDUNET", assets: {} };
  window.scrollTo = () => {};
  if (token) window.localStorage.setItem("dedunet_token", token);
  if (role) window.localStorage.setItem("dedunet_role", role);
  if (cart) window.localStorage.setItem("dedunet_cart", cart);
  window.fetch = responder;
  /* Dependency order, mirroring index.html. app.js consumes the design system and
     the data layer at load, so they must be evaluated first. */
  for (const file of ["media-url.js", "ds.js", "data.js", "app.js"]) {
    window.eval(fs.readFileSync(path.join(WEB, file), "utf8"));
  }
  return window;
}

/* Reads state through the RENDERED page, not through internals: the defect was a screen
   saying the wrong thing, so a screen is what has to be inspected. */
function describe(window) {
  window.viewAccount();
  const accountText = window.document.getElementById("main").textContent;
  return {
    accountText,
    claimsSignedIn: /Signed in as/.test(accountText),
    offersSignIn: /Sign in/.test(accountText),
    tokenInStorage: window.localStorage.getItem("dedunet_token"),
    roleInStorage: window.localStorage.getItem("dedunet_role"),
    cartInStorage: window.localStorage.getItem("dedunet_cart"),
  };
}

function responderFor(spec, body) {
  return (url, options) => {
    if (spec.reject !== undefined) return Promise.reject(new TypeError(spec.reject));
    if (spec.status !== undefined) {
      return Promise.resolve({
        ok: false,
        status: spec.status,
        text: () => Promise.resolve(JSON.stringify({ detail: spec.detail })),
      });
    }
    return Promise.resolve({
      ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(body)),
    });
  };
}

(async () => {
  const result = {};

  /* ---- the acceptance sequence, end to end */
  {
    const window = boot({
      token: "stale-token-not-a-credential",
      role: "customer",
      cart: "cart-token-not-a-credential",
      responder: responderFor(EXPIRED),
    });
    window.location.hash = "#/orders";
    await window.viewOrders();
    const ordersText = window.document.getElementById("main").textContent;
    const bannerText = window.document.getElementById("banner").textContent;
    const hash = window.location.hash;
    result.acceptanceSequence = {
      ordersText,
      bannerText,
      hash,
      /* Matches the mode-derived family ("No orders yet. ..."), not the retired sentence
         "You have no orders yet." this defect was reported against. Anchored on the part
         every mode shares, so the probe still fires whichever wording a regression picks.
         See test_storefront_purchase_refusal.py for the wording itself. */
      claimsNoOrders: /No orders yet/.test(ordersText),
      ...describe(window),
    };
  }

  /* ---- an expired session met on the order-detail route */
  {
    const window = boot({
      token: "stale-token-not-a-credential",
      role: "customer",
      responder: responderFor(EXPIRED),
    });
    await window.viewOrder("FC-FAFBAB8A");
    result.orderDetail = {
      bannerText: window.document.getElementById("banner").textContent,
      hash: window.location.hash,
      ...describe(window),
    };
  }

  /* ---- failures that must NOT end the session */
  result.preserved = {};
  for (const [name, spec] of Object.entries(FAILURES)) {
    const window = boot({
      token: "valid-token-not-a-credential",
      role: "customer",
      cart: "cart-token-not-a-credential",
      responder: responderFor(spec),
    });
    window.location.hash = "#/orders";
    let threw = null;
    try {
      await window.viewOrders();
    } catch (e) {
      threw = String(e && e.message ? e.message : e);
    }
    result.preserved[name] = { threw, ...describe(window) };
  }

  /* ---- a successful authenticated request keeps the session */
  {
    const window = boot({
      token: "valid-token-not-a-credential",
      role: "customer",
      responder: responderFor({}, [ORDER]),
    });
    window.location.hash = "#/orders";
    await window.viewOrders();
    result.success = {
      ordersText: window.document.getElementById("main").textContent,
      ...describe(window),
    };
  }

  /* ---- a protected route after expiry must ask for a sign-in, not retry blindly */
  {
    const calls = [];
    const window = boot({
      token: "stale-token-not-a-credential",
      role: "customer",
      responder: (url, options) => {
        calls.push(String(url));
        return responderFor(EXPIRED)(url, options);
      },
    });
    window.location.hash = "#/orders";
    await window.viewOrders();
    const afterFirst = calls.length;
    // Route again, as a customer clicking "Orders" would.
    window.location.hash = "#/orders";
    await window.viewOrders();
    result.afterExpiry = {
      requestsBeforeSecondAttempt: afterFirst,
      requestsAfterSecondAttempt: calls.length,
      hash: window.location.hash,
      ...describe(window),
    };
  }

  /* ---- the 401 must be attributed to OUR credentials, not to any 401 */
  {
    const window = boot({ responder: responderFor({ status: 401, detail: "invalid credentials" }) });
    let flagged = null;
    try {
      await window.api("/api/v1/auth/login", { method: "POST", body: "{}" });
    } catch (e) {
      flagged = Boolean(e.sessionExpired);
    }
    result.unauthenticated401 = { flaggedAsExpiry: flagged };
  }

  /* ---- the predicate itself, over the full status space */
  {
    const window = boot({ responder: responderFor({}) });
    const matrix = {};
    for (const status of [200, 400, 401, 403, 404, 409, 422, 429, 500, 502, 503]) {
      matrix[`${status}_with_credentials`] = window.isSessionRejection(status, true);
      matrix[`${status}_without_credentials`] = window.isSessionRejection(status, false);
    }
    result.predicate = matrix;
  }

  process.stdout.write(JSON.stringify(result));
})().catch((e) => {
  process.stderr.write(String(e && e.stack ? e.stack : e));
  process.exit(1);
});
"""


@pytest.fixture(scope="module")
def rendered() -> dict:
    completed = subprocess.run(
        ["node", "-e", HARNESS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO / "apps" / "mobile"),
        env={
            **os.environ,
            "WEB_DIR": str(WEB),
            "FAILURES": json.dumps(NON_AUTH_FAILURES),
            "EXPIRED": json.dumps(EXPIRED),
            "ORDER": json.dumps(ORDER),
            "NODE_PATH": str(NODE_PATHS),
            "PYTHONIOENCODING": "utf-8",
        },
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# ------------------------------------------------ the reported scenario, step by step


def test_an_expired_session_no_longer_reports_an_empty_order_history(rendered):
    """Step 4 of the report. This was not a degraded message but a false one.

    "You have no orders yet" is a statement about the customer's history, asserted on the
    strength of a request the server refused to answer.

    The sentence has since been replaced by mode-derived copy (iPhone acceptance issue B),
    so the probe matches the "No orders yet" stem all three variants share rather than the
    retired sentence. Without that update this assertion would pass on a string that can no
    longer be produced -- green for the wrong reason, and blind to the defect returning.
    """

    assert rendered["acceptanceSequence"]["claimsNoOrders"] is False, (
        rendered["acceptanceSequence"]["ordersText"]
    )


def test_an_expired_session_clears_the_stored_token(rendered):
    assert rendered["acceptanceSequence"]["tokenInStorage"] is None
    assert rendered["acceptanceSequence"]["roleInStorage"] is None


def test_the_account_view_no_longer_claims_the_customer_is_signed_in(rendered):
    """Step 5 of the report, and the symptom the tester actually saw."""

    result = rendered["acceptanceSequence"]

    assert result["claimsSignedIn"] is False, result["accountText"]
    assert result["offersSignIn"] is True, result["accountText"]


def test_the_customer_is_told_why_and_sent_somewhere_useful(rendered):
    """A silent redirect is only half a fix: the customer must know their session ended."""

    result = rendered["acceptanceSequence"]

    assert result["hash"] == "#/account"
    assert "session has expired" in result["bannerText"].lower(), result["bannerText"]


def test_the_cart_survives_an_expired_session(rendered):
    """The basket is the device's, not the session's -- the mobile client agrees.

    Losing it would turn a re-authentication into lost work.
    """

    assert rendered["acceptanceSequence"]["cartInStorage"] == "cart-token-not-a-credential"


def test_the_order_detail_route_behaves_the_same_way(rendered):
    """Every protected route goes through one policy; none re-derive it locally."""

    result = rendered["orderDetail"]

    assert result["tokenInStorage"] is None
    assert result["claimsSignedIn"] is False
    assert result["hash"] == "#/account"
    assert "session has expired" in result["bannerText"].lower()


def test_a_protected_route_after_expiry_requires_signing_in_again(rendered):
    """It must stop presenting protected pages, not keep retrying with a dead token."""

    result = rendered["afterExpiry"]

    assert result["requestsAfterSecondAttempt"] == result["requestsBeforeSecondAttempt"], (
        "the client retried a protected endpoint after the session was cleared"
    )
    assert result["hash"] == "#/account"
    assert result["claimsSignedIn"] is False


# --------------------------------------------- everything that must NOT end the session


@pytest.mark.parametrize("failure", sorted(NON_AUTH_FAILURES))
def test_a_non_authentication_failure_never_signs_the_customer_out(rendered, failure):
    """A dropped connection, a busy limiter or a failing server is not a rejected token.

    Signing a customer out for any of these would be a worse defect than the one being
    fixed here, because it would fire during ordinary flaky-network use.
    """

    result = rendered["preserved"][failure]

    assert result["tokenInStorage"] == "valid-token-not-a-credential", result
    assert result["roleInStorage"] == "customer"
    assert result["claimsSignedIn"] is True, result["accountText"]


def test_a_successful_request_preserves_the_session(rendered):
    result = rendered["success"]

    assert result["tokenInStorage"] == "valid-token-not-a-credential"
    assert result["claimsSignedIn"] is True
    assert "FC-FAFBAB8A" in result["ordersText"]


def test_a_failed_sign_in_is_not_treated_as_an_expired_session(rendered):
    """`POST /auth/login` answers 401 for a wrong password, with no session in play.

    Attributing that to session expiry would be harmless today and wrong in principle: the
    rule is "the server rejected OUR credentials", and an unauthenticated request sent none.
    """

    assert rendered["unauthenticated401"]["flaggedAsExpiry"] is False


# ------------------------------------------------------------------- the rule in isolation


def test_only_a_credentialed_401_counts_as_a_session_rejection(rendered):
    """The predicate over the whole status space, so no status can drift into the rule."""

    matrix = rendered["predicate"]

    assert matrix["401_with_credentials"] is True
    assert matrix["401_without_credentials"] is False

    for key, value in matrix.items():
        if key == "401_with_credentials":
            continue
        assert value is False, f"{key} was treated as a session rejection"


def test_signing_out_and_being_signed_out_clear_the_same_keys():
    """Two definitions of "signed out" is how one of them forgets a key.

    The Sign out button and the 401 path both call `clearCustomerAuth`.
    """

    source = (WEB / "app.js").read_text(encoding="utf-8")

    assert source.count("function clearCustomerAuth") == 1
    # The only removals of the session keys happen inside that one function.
    assert source.count('localStorage.removeItem("dedunet_token")') == 1
    assert source.count('localStorage.removeItem("dedunet_role")') == 1
    # ...and the cart is never removed by it.
    start = source.index("function clearCustomerAuth")
    end = source.index("function isSessionRejection")
    assert "dedunet_cart" not in source[start:end]
