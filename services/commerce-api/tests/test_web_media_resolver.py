"""The web client's asset URL resolution, executed as JavaScript.

`apps/web` has no JS test runner and adding one for a single module would be a larger
change than the module. But asserting on the SOURCE TEXT of a URL builder proves nothing
about the URLs it builds, and the defect being closed here was precisely a URL that looked
reasonable in source and resolved against the wrong origin at runtime. So these tests run
the real `apps/web/media-url.js` through Node and assert on its actual output.

Node is skipped rather than required: it is present on the GitHub `ubuntu-latest` runner
and on this workstation, and a missing Node must not turn into a red backend suite on a
machine that only does Python.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[3] / "apps" / "web"
MODULE = WEB / "media-url.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def run_js(expression: str) -> object:
    """Evaluate an expression against the real module and return the parsed result."""

    script = (
        f"const m = require({json.dumps(str(MODULE))});"
        f"process.stdout.write(JSON.stringify({expression}));"
    )
    completed = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, cwd=str(WEB)
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


API = "http://127.0.0.1:18000"


# ------------------------------------------------------------------ the six required cases


def test_same_origin_development():
    """Web and API on one host: still an absolute URL on the API port, not a bare path."""

    assert run_js(f'm.assetUrl("assets/brand-prototype/logos/logo-primary.svg", "{API}")') == (
        f"{API}/api/v1/media/assets/brand-prototype/logos/logo-primary.svg"
    )


def test_split_origin_web_and_api():
    """The whole point. The storefront origin must never appear in a media URL.

    This is the assertion that fails if resolution ever goes back to being relative to
    `window.location.origin`, which is what made the brand mark 404 on :13000 and :13080.
    """

    resolved = run_js(
        'm.assetUrl("/api/v1/media/assets/brand-prototype/logos/logo-primary.svg",'
        ' "http://127.0.0.1:18080")'
    )
    assert resolved == (
        "http://127.0.0.1:18080/api/v1/media/assets/brand-prototype/logos/logo-primary.svg"
    )
    assert "13080" not in resolved


def test_api_base_with_trailing_slash():
    """A trailing slash must not produce a double slash the server then 404s on."""

    assert run_js(f'm.assetUrl("/api/v1/media/x.svg", "{API}/")') == f"{API}/api/v1/media/x.svg"
    assert run_js(f'm.assetUrl("/api/v1/media/x.svg", "{API}///")') == f"{API}/api/v1/media/x.svg"


def test_media_path_with_leading_slash():
    """Leading slash present or absent must resolve identically."""

    with_slash = run_js(f'm.assetUrl("/assets/brand-prototype/logos/favicon.svg", "{API}")')
    without = run_js(f'm.assetUrl("assets/brand-prototype/logos/favicon.svg", "{API}")')
    assert with_slash == without == f"{API}/api/v1/media/assets/brand-prototype/logos/favicon.svg"


def test_absolute_url_is_returned_unchanged():
    """An already-addressed URL is a deliberate reference; rewriting it would retarget it."""

    for absolute in (
        "https://cdn.example.test/logo.svg",
        "http://other.example.test/a.png",
        "//cdn.example.test/b.svg",
    ):
        assert run_js(f'm.assetUrl({json.dumps(absolute)}, "{API}")') == absolute


def test_missing_or_malformed_path_returns_empty_string():
    """Empty, not a half-built URL. A half-built URL renders a broken-image glyph."""

    for bad in ("", "   ", None):
        assert run_js(f'm.assetUrl({json.dumps(bad)}, "{API}")') == ""
    # Traversal is refused client-side too, so the client never even asks.
    assert run_js(f'm.assetUrl("../../etc/passwd", "{API}")') == ""
    assert run_js(f'm.assetUrl("assets/../../secret.svg", "{API}")') == ""


# --------------------------------------------------------------------------- API base


def test_api_base_prefers_an_explicit_override():
    assert run_js('m.apiBase({ FASHION_POC_API_BASE: "https://api.example.test/" })') == (
        "https://api.example.test"
    )


def test_api_base_falls_back_to_the_page_host_on_the_api_port():
    """Same host, different port -- never the storefront's own port."""

    resolved = run_js(
        'm.apiBase({ location: { protocol: "http:", hostname: "127.0.0.1", port: "13080" } })'
    )
    assert resolved == "http://127.0.0.1:18000"


def test_asset_url_defaults_to_the_configured_api_base():
    """A call site that omits the base must not silently fall back to a relative path."""

    resolved = run_js(
        'm.assetUrl("assets/x.svg", m.apiBase({ FASHION_POC_API_BASE: "https://api.example.test" }))'
    )
    assert resolved == "https://api.example.test/api/v1/media/assets/x.svg"


# ------------------------------------------------------------------ markup hydration


def test_hydrate_assigns_src_and_href_from_data_asset():
    """The markup declares which asset it wants; the module assigns where it lives."""

    fake_dom = """
    (() => {
      const made = [];
      const node = (tag, asset) => ({
        tagName: tag, _attrs: { "data-asset": asset },
        getAttribute(k) { return this._attrs[k]; },
        setAttribute(k, v) { this._attrs[k] = v; },
      });
      const img = node("IMG", "assets/brand-prototype/logos/logo-primary.svg");
      const link = node("LINK", "assets/brand-prototype/logos/favicon.svg");
      const doc = { querySelectorAll: () => [img, link] };
      const count = m.hydrateAssetElements(doc, "http://api.example.test");
      return { count, img: img._attrs.src, link: link._attrs.href };
    })()
    """
    result = run_js(fake_dom)
    assert result["count"] == 2
    assert result["img"] == (
        "http://api.example.test/api/v1/media/assets/brand-prototype/logos/logo-primary.svg"
    )
    assert result["link"] == (
        "http://api.example.test/api/v1/media/assets/brand-prototype/logos/favicon.svg"
    )


def test_no_markup_still_references_the_api_path_directly():
    """A root-relative /api/ URL in the HTML is the defect, so it must not come back.

    Caught here rather than in review: the original brand mark and favicon were both
    plain `src="/api/v1/media/..."`, which is entirely reasonable-looking markup and
    resolves against the storefront in every deployed topology.
    """

    html = (WEB / "index.html").read_text(encoding="utf-8")
    offenders = [
        line.strip()
        for line in html.splitlines()
        if ('src="/api/' in line or 'href="/api/' in line)
    ]
    assert not offenders, f"markup references the API origin-relatively: {offenders}"
