"""What the operations portal shows an operator about an order's provenance.

Human acceptance testing, Test 4H. The admin Orders page listed the synthetic acceptance
order exactly as it would list a real one:

    FC-FAFBAB8A   paid   EUR 80.90   1x DDN-SRC-CAR-XS   [Fulfil] [Cancel]

with no mention of `COMMERCE_TEST_MODE` and no mention of `is_test_order` anywhere on the
page. The backend had recorded both correctly since the provenance migration; the renderer
simply never read them. An operator could not tell a sandbox order from a real one, and the
row they were looking at carried a Fulfil button.

These tests render the real `apps/admin/admin.js` in a real DOM through jsdom, the same way
`test_web_gallery.py` renders the storefront gallery. A source-text assertion cannot
establish that a badge reaches the screen -- and "the backend field is correct" was already
true while the defect was live, so only the rendered output settles it.

The payloads are the SHAPE the admin API actually returns (`_order_payload` in
`app/commerce/api.py`), including the acceptance orders FC-FAFBAB8A and FC-639D8B8F.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ADMIN = REPO / "apps" / "admin"
NODE_PATHS = REPO / "apps" / "mobile" / "node_modules"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not (NODE_PATHS / "jsdom").is_dir(),
    reason="node with jsdom is required",
)


def _line(sku: str = "DDN-SRC-CAR-XS") -> dict:
    return {
        "sku": sku,
        "product_name": "The Source Tee",
        "size": "XS",
        "color": "Carbon",
        "quantity": 1,
        "unit_price_minor_units": 7200,
        "line_total_minor_units": 7200,
    }


def _order(number: str, status: str, **overrides) -> dict:
    """An admin order payload. Provenance keys are supplied per scenario, never defaulted."""

    order = {
        "order_number": number,
        "status": status,
        "currency": "EUR",
        "subtotal_minor_units": 7200,
        "discount_minor_units": 0,
        "shipping_minor_units": 890,
        "tax_minor_units": 1292,
        "total_minor_units": 8090,
        "promotion_code": "",
        "lines": [_line()],
        "shipments": [],
    }
    order.update(overrides)
    return order


# The two orders the human tester actually placed, exactly as /api/v1/admin/orders returns
# them. Verified against the staging database: both rows carry
# commerce_mode_at_checkout = COMMERCE_TEST_MODE.
PAID_TEST_ORDER = _order(
    "FC-FAFBAB8A", "paid", commerce_mode_at_checkout="COMMERCE_TEST_MODE", is_test_order=True
)
CANCELLED_TEST_ORDER = _order(
    "FC-639D8B8F", "cancelled", commerce_mode_at_checkout="COMMERCE_TEST_MODE", is_test_order=True
)

# A future real order. This must look completely ordinary: a label on genuine commerce is
# just as much a defect as no label on synthetic commerce.
REAL_PAID_ORDER = _order(
    "FC-REAL0001", "paid", commerce_mode_at_checkout="PUBLIC_COMMERCE_MODE", is_test_order=False
)

SCENARIOS = {
    "paid_test": [PAID_TEST_ORDER],
    "cancelled_test": [CANCELLED_TEST_ORDER],
    "acceptance_pair": [PAID_TEST_ORDER, CANCELLED_TEST_ORDER],
    "real_paid": [REAL_PAID_ORDER],
    # Optional provenance absent entirely -- an older record, or a projection that dropped
    # the columns. Must render, not throw.
    "absent": [_order("FC-NOPROV01", "paid")],
    "null_valued": [
        _order("FC-NULLPRV1", "paid", commerce_mode_at_checkout=None, is_test_order=None)
    ],
    # Each provenance signal alone must be sufficient.
    "mode_only": [_order("FC-MODEONLY", "paid", commerce_mode_at_checkout="COMMERCE_TEST_MODE")],
    "flag_only": [_order("FC-FLAGONLY", "paid", is_test_order=True)],
    # A line array that is missing, and an order with no lines at all.
    "no_lines": [_order("FC-NOLINES1", "paid", lines=[], is_test_order=True)],
    # Hostile strings on a labelled row: the marker is built from order data, so it is a
    # sink like any other.
    "hostile": [
        _order(
            "<img src=x onerror=alert(1)>",
            "paid",
            is_test_order=True,
            commerce_mode_at_checkout="<script>alert(1)</script>",
            lines=[_line("<svg onload=alert(1)>")],
        )
    ],
}

HARNESS = r"""
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const ADMIN = process.env.ADMIN_DIR;
const SCENARIOS = JSON.parse(process.env.SCENARIOS);

/* A fresh document per scenario. render() replaces #main, so reusing one would leave the
   previous scenario's outcome influencing the next. */
function boot(orders) {
  const dom = new JSDOM(
    "<!doctype html><html><head></head><body>" +
      "<div id='banner'></div><main id='main'></main></body></html>",
    { url: "http://127.0.0.1:13080/admin/", runScripts: "outside-only" }
  );
  const { window } = dom;
  /* The staging origin, so a regression in the 09a666d seam shows up here too. */
  window.DEDUNET_API_BASE = "http://127.0.0.1:18080";
  window.localStorage.setItem("dedunet_admin_token", "harness-token-not-a-credential");

  const calls = [];
  window.fetch = (url, options) => {
    calls.push({ url: String(url), method: (options && options.method) || "GET" });
    const body = String(url).endsWith("/api/v1/admin/orders") ? JSON.stringify(orders) : "{}";
    return Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(body) });
  };
  window.confirm = () => true;

  for (const file of ["api-config.js", "admin.js"]) {
    window.eval(fs.readFileSync(path.join(ADMIN, file), "utf8"));
  }
  return { window, calls };
}

function describeRow(row) {
  const cells = Array.from(row.querySelectorAll("td"));
  const badges = Array.from(row.querySelectorAll(".tag--test"));
  const modes = Array.from(row.querySelectorAll(".provenance__mode"));
  return {
    text: row.textContent,
    cells: cells.map((c) => c.textContent),
    statusCell: cells[1] ? cells[1].textContent : null,
    totalCell: cells[2] ? cells[2].textContent : null,
    trackingCell: cells[3] ? cells[3].textContent : null,
    buttons: Array.from(row.querySelectorAll("button")).map((b) => b.textContent),
    badgeCount: badges.length,
    badgeText: badges.map((b) => b.textContent),
    modeText: modes.map((m) => m.textContent),
    /* Markup smuggled through a text sink would appear as elements, not as text. */
    injectedElements: Array.from(row.querySelectorAll("img, script, svg, iframe, object")).map(
      (n) => n.tagName.toLowerCase()
    ),
    /* And an inline handler would appear as an ATTRIBUTE. Searching the serialised HTML for
       the substring "onerror=" cannot distinguish that from correctly escaped text that
       merely contains those characters -- which is precisely what a hostile order number
       does. Enumerating real attributes can. */
    inlineHandlerAttributes: Array.from(row.querySelectorAll("*")).flatMap((n) =>
      Array.from(n.attributes)
        .map((a) => a.name)
        .filter((name) => name.toLowerCase().startsWith("on"))
    ),
  };
}

async function settle() {
  for (let i = 0; i < 8; i += 1) await new Promise((r) => setTimeout(r, 0));
}

(async () => {
  const result = {};

  for (const [name, orders] of Object.entries(SCENARIOS)) {
    const { window } = boot(orders);
    let error = null;
    try {
      await window.viewOrders();
    } catch (e) {
      error = String(e && e.message ? e.message : e);
    }
    const main = window.document.getElementById("main");
    result[name] = {
      error,
      pageText: main.textContent,
      pageHtml: main.innerHTML,
      headers: Array.from(main.querySelectorAll("thead th")).map((t) => t.textContent),
      rows: Array.from(main.querySelectorAll("tbody tr")).map(describeRow),
    };
  }

  /* The pure predicate, over inputs a renderer cannot easily be driven to. */
  {
    const { window } = boot([]);
    const cases = {
      both: { is_test_order: true, commerce_mode_at_checkout: "COMMERCE_TEST_MODE" },
      flagOnly: { is_test_order: true },
      modeOnly: { commerce_mode_at_checkout: "COMMERCE_TEST_MODE" },
      realOrder: { is_test_order: false, commerce_mode_at_checkout: "PUBLIC_COMMERCE_MODE" },
      empty: {},
      nulls: { is_test_order: null, commerce_mode_at_checkout: null },
      stringFalse: { is_test_order: "false", commerce_mode_at_checkout: "PUBLIC_COMMERCE_MODE" },
      stringTrue: { is_test_order: "true", commerce_mode_at_checkout: "PUBLIC_COMMERCE_MODE" },
      zero: { is_test_order: 0, commerce_mode_at_checkout: "PUBLIC_COMMERCE_MODE" },
      one: { is_test_order: 1, commerce_mode_at_checkout: "PUBLIC_COMMERCE_MODE" },
      blankMode: { is_test_order: false, commerce_mode_at_checkout: "" },
      undefinedOrder: null,
    };
    const predicate = {};
    for (const [name, order] of Object.entries(cases)) {
      predicate[name] = window.isTestOrder(order);
    }
    result.predicate = predicate;
    /* A real order must produce no marker node at all, not an empty one. */
    result.markerForRealOrder = window.testOrderMarker(cases.realOrder);
    result.markerForAbsentProvenance = window.testOrderMarker({});
  }

  /* The two privileged controls, actually clicked. */
  {
    const { window, calls } = boot([PAID_TEST_ORDER_PLACEHOLDER]);
    await window.viewOrders();
    const button = Array.from(window.document.querySelectorAll("tbody tr button")).find(
      (b) => b.textContent === "Fulfil"
    );
    button.click();
    await settle();
    result.fulfilCalls = calls.filter((c) => c.method === "POST");
  }
  {
    const { window, calls } = boot([PAID_TEST_ORDER_PLACEHOLDER]);
    await window.viewOrders();
    const button = Array.from(window.document.querySelectorAll("tbody tr button")).find(
      (b) => b.textContent === "Cancel"
    );
    button.click();
    await settle();
    result.cancelCalls = calls.filter((c) => c.method === "POST");
  }

  process.stdout.write(JSON.stringify(result));
})().catch((e) => {
  process.stderr.write(String(e && e.stack ? e.stack : e));
  process.exit(1);
});
"""


@pytest.fixture(scope="module")
def rendered() -> dict:
    harness = HARNESS.replace("PAID_TEST_ORDER_PLACEHOLDER", json.dumps(PAID_TEST_ORDER))
    # Inherit the real environment: a minimal one crashes Node on Windows, which cost the
    # gallery suite an afternoon before it was inherited there too.
    completed = subprocess.run(
        ["node", "-e", harness],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO / "apps" / "mobile"),
        env={
            **os.environ,
            "ADMIN_DIR": str(ADMIN),
            "SCENARIOS": json.dumps(SCENARIOS),
            "NODE_PATH": str(NODE_PATHS),
            "PYTHONIOENCODING": "utf-8",
        },
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# ------------------------------------------------ A. the test order is unmistakably marked


def test_the_acceptance_order_is_labelled_a_test_order(rendered):
    """The defect, stated positively: FC-FAFBAB8A must announce itself as synthetic.

    Asserted on the ROW, not the page. A badge somewhere in a header would satisfy a
    page-level check while leaving the operator unable to tell which row it applies to.
    """

    row = rendered["paid_test"]["rows"][0]

    assert row["badgeCount"] == 1, row
    assert row["badgeText"] == ["TEST ORDER"], row["badgeText"]
    assert "TEST ORDER" in row["text"]
    assert "FC-FAFBAB8A" in row["text"]


def test_the_label_sits_in_the_same_cell_as_the_order_number(rendered):
    """Adjacency is the point: a marker two columns away is a marker easily read as belonging
    to a neighbouring row."""

    order_cell = rendered["paid_test"]["rows"][0]["cells"][0]
    assert "FC-FAFBAB8A" in order_cell
    assert "TEST ORDER" in order_cell


# ---------------------------------------------------------- B. the mode itself is visible


def test_the_commerce_mode_is_shown_verbatim(rendered):
    """`COMMERCE_TEST_MODE` is the wording of the audit record and of acceptance step 13.

    Showing it unchanged means an operator can match the screen to those without having to
    trust that a paraphrase means the same thing.
    """

    row = rendered["paid_test"]["rows"][0]

    assert row["modeText"] == ["COMMERCE_TEST_MODE"], row["modeText"]
    assert "COMMERCE_TEST_MODE" in row["text"]


def test_both_signals_appear_when_the_api_sends_both(rendered):
    row = rendered["paid_test"]["rows"][0]
    assert "TEST ORDER" in row["text"] and "COMMERCE_TEST_MODE" in row["text"]


@pytest.mark.parametrize("scenario", ["mode_only", "flag_only"])
def test_either_provenance_signal_alone_is_enough(rendered, scenario):
    """`is_test_order` is derived from the mode server-side, so they always agree today.

    Requiring both would make the label depend on that derivation never being dropped from a
    projection. Either one labels the row.
    """

    row = rendered[scenario]["rows"][0]
    assert row["badgeText"] == ["TEST ORDER"], row


def test_the_flag_alone_still_labels_even_with_no_mode_string(rendered):
    """No mode to show: the badge appears, and no empty element is emitted beside it."""

    row = rendered["flag_only"]["rows"][0]
    assert row["badgeText"] == ["TEST ORDER"]
    assert row["modeText"] == [], row["modeText"]


# ------------------------------------------------------- C. a real order is left untouched


def test_a_real_order_gets_no_test_label(rendered):
    """A future genuine order must look completely ordinary.

    Labelling real commerce as synthetic is the mirror-image defect and no less serious:
    an operator who learns the badge is unreliable stops reading it.
    """

    page = rendered["real_paid"]
    row = page["rows"][0]

    assert row["badgeCount"] == 0, row
    assert "TEST ORDER" not in page["pageText"]
    assert "COMMERCE_TEST_MODE" not in page["pageText"]
    # And nothing was lost from the row itself.
    assert "FC-REAL0001" in row["text"]
    assert row["statusCell"] == "paid"
    assert row["totalCell"] == "€80.90"


def test_the_marker_is_absent_not_empty_for_a_real_order(rendered):
    """`null`, so no stray container is left in the markup to be styled or read aloud."""

    assert rendered["markerForRealOrder"] is None
    assert rendered["markerForAbsentProvenance"] is None


def test_the_predicate_is_strict_about_what_counts(rendered):
    """Only an exact `true` and the exact mode string.

    JSON that has been through a form encoder or a spreadsheet arrives as `"false"`, which is
    truthy, and as `0`/`1`, which are not booleans. A loose check would brand real orders;
    the mode string is the backstop that lets this stay strict safely.
    """

    p = rendered["predicate"]

    assert p["both"] is True
    assert p["flagOnly"] is True
    assert p["modeOnly"] is True

    assert p["realOrder"] is False
    assert p["empty"] is False
    assert p["nulls"] is False
    assert p["stringFalse"] is False, "the string 'false' is truthy and must not label an order"
    assert p["stringTrue"] is False, "only a real boolean true counts"
    assert p["zero"] is False
    assert p["one"] is False
    assert p["blankMode"] is False
    assert p["undefinedOrder"] is False


# ------------------------------------------- D. missing provenance must not break the page


@pytest.mark.parametrize("scenario", ["absent", "null_valued", "no_lines"])
def test_incomplete_payloads_render_without_throwing(rendered, scenario):
    """The optional fields are optional. A page that throws shows the operator nothing at
    all, which is strictly worse than a page that shows an unlabelled order."""

    page = rendered[scenario]

    assert page["error"] is None, page["error"]
    assert len(page["rows"]) == 1, page
    assert page["rows"][0]["text"], "the row rendered empty"


def test_an_order_with_no_provenance_keys_is_not_labelled(rendered):
    """Absence is not evidence of a test order. Silence, not a guess."""

    assert rendered["absent"]["rows"][0]["badgeCount"] == 0
    assert "TEST ORDER" not in rendered["absent"]["pageText"]


def test_an_order_with_no_lines_still_labels_and_renders(rendered):
    """The marker must not depend on anything else in the row being present."""

    row = rendered["no_lines"]["rows"][0]
    assert row["badgeText"] == ["TEST ORDER"]
    assert "FC-NOLINES1" in row["text"]


# ------------------------------------------------ E/F. the existing rendering is unchanged


def test_paid_rendering_is_unchanged(rendered):
    """Status, total, tracking and columns are exactly as before the label was added."""

    page = rendered["paid_test"]
    row = page["rows"][0]

    assert page["headers"] == ["Order", "Status", "Total", "Tracking", "Actions"]
    assert row["statusCell"] == "paid"
    assert row["totalCell"] == "€80.90", row["totalCell"]
    assert row["trackingCell"] == "—"
    assert "1× DDN-SRC-CAR-XS" in row["cells"][0]


def test_cancelled_rendering_is_unchanged(rendered):
    """A cancelled test order keeps its status and loses its Fulfil control."""

    row = rendered["cancelled_test"]["rows"][0]

    assert row["statusCell"] == "cancelled"
    assert row["totalCell"] == "€80.90"
    assert row["buttons"] == [], "a cancelled order must offer no fulfil or cancel action"
    # ...and is still labelled, because it too was placed against the sandbox.
    assert row["badgeText"] == ["TEST ORDER"]


def test_the_acceptance_pair_renders_together_as_the_operator_sees_it(rendered):
    """Both acceptance orders in one table, in API order, each labelled."""

    rows = rendered["acceptance_pair"]["rows"]

    assert len(rows) == 2
    assert "FC-FAFBAB8A" in rows[0]["text"] and rows[0]["statusCell"] == "paid"
    assert "FC-639D8B8F" in rows[1]["text"] and rows[1]["statusCell"] == "cancelled"
    assert [r["badgeText"] for r in rows] == [["TEST ORDER"], ["TEST ORDER"]]


# ----------------------------------------------------- G. the controls still do their job


def test_the_paid_row_still_offers_fulfil_and_cancel(rendered):
    assert rendered["paid_test"]["rows"][0]["buttons"] == ["Fulfil", "Cancel"]


def test_fulfil_still_posts_to_the_fulfil_endpoint(rendered):
    """Clicked for real in the DOM, against a stubbed transport. The label must not have
    displaced or rebound the control it sits next to."""

    assert rendered["fulfilCalls"] == [
        {"url": "http://127.0.0.1:18080/api/v1/admin/orders/FC-FAFBAB8A/fulfil", "method": "POST"}
    ], rendered["fulfilCalls"]


def test_cancel_still_posts_to_the_cancel_endpoint(rendered):
    assert rendered["cancelCalls"] == [
        {"url": "http://127.0.0.1:18080/api/v1/admin/orders/FC-FAFBAB8A/cancel", "method": "POST"}
    ], rendered["cancelCalls"]


# ------------------------------------------------------------------ H. no markup smuggling


def test_hostile_order_data_is_rendered_as_text_not_markup(rendered):
    """The marker is built from order data, so it is a sink like every other node here.

    `el()` inserts strings as `textContent`; this proves it, rather than trusting that the
    new code happened to use it.

    Asserted on nodes and attributes rather than on substrings of the serialised HTML. A
    correctly escaped order number reading `&lt;img src=x onerror=alert(1)&gt;` *contains*
    the text "onerror=" while being completely inert, so a substring search reports a breach
    that is not there -- a test that fails for the wrong reason is no better than one that
    passes for the wrong reason.
    """

    page = rendered["hostile"]
    row = page["rows"][0]

    assert row["injectedElements"] == [], row["injectedElements"]
    assert row["inlineHandlerAttributes"] == [], row["inlineHandlerAttributes"]
    # No unescaped open tag survived anywhere on the page.
    for tag in ("<img", "<script", "<svg", "<iframe"):
        assert tag not in page["pageHtml"], tag
    # The payloads are present as inert text, escaped.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page["pageHtml"]
    assert "&lt;img src=x onerror=alert(1)&gt;" in page["pageHtml"]
    # ...and the row is still labelled, carrying the hostile string as its mode text.
    assert row["badgeText"] == ["TEST ORDER"]
    assert row["modeText"] == ["<script>alert(1)</script>"]


def test_the_provenance_code_introduces_no_markup_sink():
    """Belt and braces alongside `test_frontend_security.py`, scoped to the new functions."""

    source = (ADMIN / "admin.js").read_text(encoding="utf-8")
    start = source.index("function isTestOrder")
    end = source.index("async function viewOrders")
    block = source[start:end]

    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert sink not in block, f"the provenance renderer uses {sink}"


# ------------------------------------------- I. the 09a666d API-base correction is intact


def test_requests_still_go_to_the_configured_api_origin(rendered):
    """The page is served from :13080; every admin request must reach the API on :18080.

    The defect closed at 09a666d was the portal calling a port nothing listens on. This
    change touches the same file, so the seam is re-checked from the rendered page rather
    than assumed.
    """

    for call in rendered["fulfilCalls"] + rendered["cancelCalls"]:
        assert call["url"].startswith("http://127.0.0.1:18080/"), call
        assert ":18000" not in call["url"], call
        assert ":13080" not in call["url"], call


def test_admin_still_resolves_its_api_base_through_the_shared_seam():
    source = (ADMIN / "admin.js").read_text(encoding="utf-8")
    assert "window.DedunetAdminConfig.apiBase()" in source


def test_the_provenance_change_did_not_reintroduce_a_deployment_port():
    """No port literal entered with the new code.

    Scoped to the block this change added. The whole-file guarantee lives in
    `test_admin_api_config.py::test_no_deployment_port_is_scattered_through_admin_logic`,
    which strips comments first -- necessary, because `admin.js` documents the :18000 defect
    in prose and a naive whole-file search flags that explanation as the thing it explains.
    """

    source = (ADMIN / "admin.js").read_text(encoding="utf-8")
    block = source[source.index("function isTestOrder") : source.index("async function viewOrders")]

    assert "18080" not in block
    assert "18000" not in block
