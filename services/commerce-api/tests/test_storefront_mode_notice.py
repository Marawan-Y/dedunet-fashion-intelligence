"""The storefront's top notice, rendered in a real DOM.

Post-acceptance issue A. `apps/web/index.html` shipped a fixed sentence:

    "Prototype storefront. Preview only -- nothing here is available to purchase, and no
     real order is placed or card charged."

and nothing ever revised it. Human acceptance completed a full sandbox journey in
COMMERCE_TEST_MODE -- synthetic stock, cart, declined payment, successful payment,
fulfilment -- with that sentence at the top of every page. The commerce behaviour was
correct; the page was lying about it.

`test_commerce_mode_disclosure.py` covers what each mode SAYS. This covers whether the
storefront actually shows it, which is a different failure and the one that was shipped: the
copy was right in the mode module all along, and no browser ever asked for it.
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

# The bodies `/api/v1/commerce/mode` actually returns, taken from `modes.describe`.
PREVIEW = {
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

COMMERCE_TEST = {
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

BLOCKED = {
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

# Payloads that must leave the shipped sentence in place rather than render a fragment.
UNUSABLE = {
    "empty_object": {},
    "no_headline": {"detail": ["something"]},
    "no_detail": {"headline": "Preview only."},
    "empty_detail": {"headline": "Preview only.", "detail": []},
    "blank_headline": {"headline": "   ", "detail": ["x"]},
    "detail_not_a_list": {"headline": "Preview only.", "detail": "not a list"},
    "null_body": None,
}

# Markup smuggled through the disclosure. The notice is server-supplied text, but so was
# every other string this client renders, and the XSS discipline is file-wide.
HOSTILE = {
    "mode": "COMMERCE_TEST_MODE",
    "headline": "<img src=x onerror=alert(1)>",
    "detail": ["<script>alert(1)</script>", "</p><iframe src=evil>"],
    "purchasable": True,
    "payments": "sandbox",
    "public_commerce_enabled": False,
}

HARNESS = r"""
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const WEB = process.env.WEB_DIR;
const CASES = JSON.parse(process.env.CASES);
const SHIPPED = process.env.SHIPPED_NOTICE;

/* The notice element exactly as index.html ships it, so the fallback under test is the real
   fallback rather than one invented in this harness. */
function boot(responder) {
  const dom = new JSDOM(
    "<!doctype html><html><head></head><body>" +
      '<p class="notice" role="note" id="commerce-mode-notice">' + SHIPPED + "</p>" +
      "<div id='banner'></div><main id='main'></main></body></html>",
    { url: "http://127.0.0.1:13080/storefront/", runScripts: "outside-only" }
  );
  const { window } = dom;
  window.DEDUNET_API_BASE = "http://127.0.0.1:18080";
  window.DEDUNET_BRAND = { name: "DEDUNET", assets: {} };
  window.scrollTo = () => {};
  window.fetch = responder;
  /* Dependency order, mirroring index.html. app.js consumes the design system and
     the data layer at load, so they must be evaluated first. */
  for (const file of ["media-url.js", "ds.js", "data.js", "app.js"]) {
    window.eval(fs.readFileSync(path.join(WEB, file), "utf8"));
  }
  return window;
}

const respondWith = (body) => () =>
  Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(body)) });

function describeNotice(window) {
  const host = window.document.getElementById("commerce-mode-notice");
  return {
    text: host.textContent.replace(/\s+/g, " ").trim(),
    html: host.innerHTML,
    headline: (host.querySelector(".notice__headline") || {}).textContent || null,
    lines: Array.from(host.querySelectorAll(".notice__line")).map((n) => n.textContent),
    role: host.getAttribute("role"),
    /* Markup would arrive as elements, not text. */
    injected: Array.from(host.querySelectorAll("img, script, iframe, svg, object")).map((n) =>
      n.tagName.toLowerCase()
    ),
    handlers: Array.from(host.querySelectorAll("*")).flatMap((n) =>
      Array.from(n.attributes).map((a) => a.name).filter((x) => x.toLowerCase().startsWith("on"))
    ),
  };
}

(async () => {
  const result = { shipped: SHIPPED.replace(/\s+/g, " ").trim(), cases: {} };

  for (const [name, body] of Object.entries(CASES)) {
    const window = boot(respondWith(body));
    let error = null;
    try {
      await window.loadCommerceNotice();
    } catch (e) {
      error = String(e && e.message ? e.message : e);
    }
    result.cases[name] = { error, ...describeNotice(window) };
  }

  /* Transport and server failures: the disclosure must survive them unchanged. */
  const failures = {
    network: () => Promise.reject(new TypeError("Failed to fetch")),
    server_error: () =>
      Promise.resolve({ ok: false, status: 500, text: () => Promise.resolve('{"detail":"boom"}') }),
    not_found: () =>
      Promise.resolve({ ok: false, status: 404, text: () => Promise.resolve("{}") }),
    unparseable: () =>
      Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve("<html>nope") }),
  };
  result.failures = {};
  for (const [name, responder] of Object.entries(failures)) {
    const window = boot(responder);
    let error = null;
    try {
      await window.loadCommerceNotice();
    } catch (e) {
      error = String(e && e.message ? e.message : e);
    }
    result.failures[name] = { error, ...describeNotice(window) };
  }

  /* Which endpoint was asked, and on which origin.
     jsdom fires DOMContentLoaded by itself once the document settles, so app.js's own
     listeners run too and the catalogue route appears here as well. That is the real page
     behaviour; the assertion is about the notice's request, not about the total. */
  {
    const calls = [];
    const window = boot((url) => {
      calls.push(String(url));
      return Promise.resolve({
        ok: true, status: 200, text: () => Promise.resolve(JSON.stringify(CASES.preview)),
      });
    });
    await window.loadCommerceNotice();
    result.requests = calls;
  }

  process.stdout.write(JSON.stringify(result));
})().catch((e) => {
  process.stderr.write(String(e && e.stack ? e.stack : e));
  process.exit(1);
});
"""


def shipped_notice() -> str:
    """The notice paragraph exactly as `index.html` ships it."""

    html = (WEB / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<p class="notice"[^>]*id="commerce-mode-notice"[^>]*>(.*?)</p>', html, re.S)
    assert match, "index.html has no #commerce-mode-notice paragraph"
    return match.group(1)


@pytest.fixture(scope="module")
def rendered() -> dict:
    cases = {
        "preview": PREVIEW,
        "commerce_test": COMMERCE_TEST,
        "blocked": BLOCKED,
        "hostile": HOSTILE,
        **UNUSABLE,
    }
    completed = subprocess.run(
        ["node", "-e", HARNESS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO / "apps" / "mobile"),
        env={
            **os.environ,
            "WEB_DIR": str(WEB),
            "CASES": json.dumps(cases),
            "SHIPPED_NOTICE": shipped_notice(),
            "NODE_PATH": str(NODE_PATHS),
            "PYTHONIOENCODING": "utf-8",
        },
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# ------------------------------------------------------ preview renders preview messaging


def test_preview_mode_renders_the_preview_disclosure(rendered):
    case = rendered["cases"]["preview"]

    assert case["headline"] == "Preview only."
    assert case["lines"] == [
        "Nothing here is available to purchase.",
        "No order or payment can be completed.",
    ]


def test_preview_mode_replaces_the_shipped_sentence(rendered):
    """Not appended to it: two disclosures on one bar is one too many to read."""

    assert rendered["cases"]["preview"]["text"] != rendered["shipped"]
    assert "DEDUNET prototype storefront." not in rendered["cases"]["preview"]["text"]


# ----------------------------------------------- commerce-test renders sandbox messaging


def test_commerce_test_mode_renders_the_sandbox_disclosure(rendered):
    """The defect, stated positively: this is what the acceptance journey should have shown."""

    case = rendered["cases"]["commerce_test"]

    assert case["headline"] == "Internal commerce test mode."
    assert case["lines"] == [
        "Only synthetic test inventory is available.",
        "Payments use the sandbox adapter.",
        "No real card is charged.",
        "No real stock or fulfilment is involved.",
    ]


def test_commerce_test_mode_does_not_claim_nothing_is_purchasable(rendered):
    """The exact false sentence the tester saw while completing a sandbox purchase."""

    text = rendered["cases"]["commerce_test"]["text"]

    assert "Nothing here is available to purchase" not in text
    assert "No order or payment can be completed" not in text


def test_commerce_test_mode_makes_no_real_payment_or_shipping_claim(rendered):
    text = rendered["cases"]["commerce_test"]["text"].lower()

    assert "sandbox" in text
    assert "no real card is charged" in text
    assert "no real stock or fulfilment is involved" in text
    for claim in ("your card has been charged", "your order will ship", "real payment"):
        assert claim not in text


# ------------------------------------------------------ the two modes cannot be confused


def test_the_two_modes_render_different_notices(rendered):
    """The guard against the copy collapsing into one message on the way to the screen.

    The API can distinguish the modes perfectly and this client can still render one string
    for both -- which is exactly the shape of the original defect, one layer down.
    """

    preview = rendered["cases"]["preview"]["text"]
    commerce_test = rendered["cases"]["commerce_test"]["text"]

    assert preview != commerce_test
    assert rendered["cases"]["preview"]["headline"] != rendered["cases"]["commerce_test"]["headline"]
    assert not set(rendered["cases"]["preview"]["lines"]) & set(
        rendered["cases"]["commerce_test"]["lines"]
    )


# ------------------------------------------------- blocked mode is not ordinary commerce


def test_a_blocked_mode_does_not_render_normal_commerce_messaging(rendered):
    case = rendered["cases"]["blocked"]

    assert case["headline"] == "Commerce is unavailable."
    assert "Nothing here is available to purchase." in case["lines"]
    assert "sandbox" not in case["text"].lower()
    assert "Preview only." not in case["text"]


# --------------------------------------------------- an unusable answer changes nothing


@pytest.mark.parametrize("case", sorted(UNUSABLE))
def test_an_unusable_disclosure_leaves_the_shipped_sentence_alone(rendered, case):
    """Half a disclosure is worse than the mode-independent one the page shipped with.

    The shipped sentence is true in every permitted mode, so keeping it is never wrong --
    only less specific.
    """

    result = rendered["cases"][case]

    assert result["error"] is None, result["error"]
    assert result["text"] == rendered["shipped"], result["text"]


@pytest.mark.parametrize("failure", ["network", "server_error", "not_found", "unparseable"])
def test_a_failed_mode_request_leaves_the_shipped_sentence_alone(rendered, failure):
    """A disclosure is not a feature: it must not surface a transport error to a customer."""

    result = rendered["failures"][failure]

    assert result["error"] is None, result["error"]
    assert result["text"] == rendered["shipped"]


def test_the_shipped_sentence_claims_nothing_mode_specific():
    """It is shown before the mode is known, so it must be true in every permitted mode."""

    text = shipped_notice().replace("\n", " ").lower()

    # Neither mode's specific claim may appear in the mode-independent fallback.
    assert "nothing here is available to purchase" not in text
    assert "preview only" not in text
    assert "sandbox" not in text
    # ...and what it does say must hold in both.
    assert "no real card is charged" in text


# ------------------------------------------------------------------ wiring and safety


def test_the_notice_is_taken_from_the_commerce_mode_endpoint(rendered):
    """Not from the catalogue. Inferring the mode from stock would make it a guess.

    Asserted on the notice's own request rather than on every request the page makes: the
    page legitimately loads the catalogue too, and a test that forbade that would fail for a
    reason with nothing to do with the disclosure.
    """

    mode_requests = [url for url in rendered["requests"] if "/commerce/mode" in url]

    assert mode_requests, rendered["requests"]
    assert all(url == "http://127.0.0.1:18080/api/v1/commerce/mode" for url in mode_requests)


def test_the_notice_loader_calls_no_other_endpoint():
    """One request, to one path, named once in the source."""

    source = (WEB / "app.js").read_text(encoding="utf-8")
    start = source.index("async function loadCommerceNotice")
    end = source.index("function setBanner")
    block = source[start:end]

    paths = re.findall(r'"(/api/v1/[^"]*)"', block)
    assert paths == ["/api/v1/commerce/mode"], paths


def test_hostile_disclosure_text_is_rendered_as_text(rendered):
    case = rendered["cases"]["hostile"]

    assert case["injected"] == [], case["injected"]
    assert case["handlers"] == [], case["handlers"]
    assert "<script" not in case["html"]
    assert "<img" not in case["html"]
    assert "&lt;script&gt;" in case["html"]


def test_the_notice_keeps_its_role_after_rerendering(rendered):
    """It is announced to assistive technology; replacing the children must not drop that."""

    for case in ("preview", "commerce_test", "blocked"):
        assert rendered["cases"][case]["role"] == "note"


def test_the_storefront_introduces_no_markup_sink():
    """Scoped to the new code, alongside the file-wide guard in test_frontend_security.py."""

    source = (WEB / "app.js").read_text(encoding="utf-8")
    start = source.index("function renderCommerceNotice")
    end = source.index("function setBanner")
    block = source[start:end]

    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert sink not in block, f"the commerce notice uses {sink}"


def test_the_mode_is_never_inferred_from_the_catalogue():
    """The requirement is explicit: derive the disclosure from the mode, not from stock.

    A client that decides "there is stock, so this must be commerce-test" would be right
    today and wrong the moment a preview catalogue carries a non-zero count for any reason.
    """

    source = (WEB / "app.js").read_text(encoding="utf-8")
    start = source.index("function renderCommerceNotice")
    end = source.index("function setBanner")
    block = source[start:end]

    for inferred in ("available", "variants", "products", "stock", "sellable"):
        assert inferred not in block, f"the notice consults {inferred!r} instead of the mode"
