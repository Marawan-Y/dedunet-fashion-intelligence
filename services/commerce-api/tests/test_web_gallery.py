"""The web DDN-TS01 media gallery, rendered in a real DOM.

`apps/web/app.js` is a browser script, so the only honest way to assert what it renders is
to render it. jsdom (already present for the mobile suite) provides the document; app.js
bootstraps on `hashchange`/`DOMContentLoaded`, neither of which jsdom fires on its own, so
the gallery function can be called directly against a fixed product payload.

The payload here is the SHAPE the API actually returns -- four media records with roles,
sort_order, Side A alt text and PROTOTYPE_CONCEPT status. If that contract changes, these
tests should fail, because the mobile Gallery consumes the same contract.

What this covers that a source-text assertion could not: that the placeholder is gone,
that all four images are emitted, that API order is preserved rather than re-sorted, and
that a product with no media renders nothing rather than a broken frame.
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

HERO = {
    "slug": "the-source-tee",
    "name": "The Source Tee",
    "currency": "EUR",
    "external_product_id": "DDN-TS01",
    "media": [
        {
            "asset_id": "DDN-TS01-FRONT", "role": "front", "sort_order": 0,
            "url": "/api/v1/media/assets/brand-prototype/products/ddn-ts01-front.svg",
            "alt_text": "Concept front view of The Source Tee", "status": "PROTOTYPE_CONCEPT",
        },
        {
            "asset_id": "DDN-TS01-BACK", "role": "back", "sort_order": 1,
            "url": "/api/v1/media/assets/brand-prototype/products/ddn-ts01-back.svg",
            "alt_text": "Concept back view of The Source Tee", "status": "PROTOTYPE_CONCEPT",
        },
        {
            "asset_id": "DDN-TS01-DETAIL", "role": "detail", "sort_order": 2,
            "url": "/api/v1/media/assets/brand-prototype/products/ddn-ts01-detail.svg",
            "alt_text": "Concept detail view of The Source Tee", "status": "PROTOTYPE_CONCEPT",
        },
        {
            "asset_id": "DDN-TS01-LIFESTYLE", "role": "lifestyle", "sort_order": 3,
            "url": "/api/v1/media/assets/brand-prototype/media/ddn-ts01-lifestyle.svg",
            "alt_text": "Abstract lifestyle concept for The Source Tee", "status": "PROTOTYPE_CONCEPT",
        },
    ],
}

HARNESS = r"""
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const WEB = process.env.WEB_DIR;
const product = JSON.parse(process.env.PRODUCT);

const dom = new JSDOM("<!doctype html><html><head></head><body><main id='main'></main></body></html>", {
  url: "http://storefront.test:13080/",
  runScripts: "outside-only",
});
const { window } = dom;
window.FASHION_POC_API_BASE = "http://api.test:18080";
window.DEDUNET_BRAND = { name: "DEDUNET", assets: {} };
window.fetch = () => Promise.reject(new Error("network disabled in this test"));

/* Dependency order, mirroring index.html. app.js consumes the design system and
     the data layer at load, so they must be evaluated first. */
  for (const file of ["media-url.js", "ds.js", "data.js", "app.js"]) {
  window.eval(fs.readFileSync(path.join(WEB, file), "utf8"));
}

function describe(node) {
  if (!node) return null;
  const imgs = Array.from(node.querySelectorAll("img"));
  return {
    className: node.className,
    imageCount: imgs.length,
    srcs: imgs.map((i) => i.getAttribute("src")),
    alts: imgs.map((i) => i.getAttribute("alt")),
    loading: imgs.map((i) => i.getAttribute("loading")),
    captions: Array.from(node.querySelectorAll("figcaption")).map((f) => f.textContent),
    note: (node.querySelector(".pdp__media-note") || {}).textContent || null,
    text: node.textContent,
    ariaHidden: node.getAttribute("aria-hidden"),
  };
}

const result = {
  gallery: describe(window.productGallery(product)),
  single: describe(window.productGallery({ ...product, media: [product.media[0]] })),
  empty: describe(window.productGallery({ ...product, media: [] })),
  missingKey: describe(window.productGallery({ name: "No Media Product" })),
  card: describe(window.cardMedia(product)),
  cardNoMedia: describe(window.cardMedia({ ...product, media: [] })),
};
process.stdout.write(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def rendered() -> dict:
    # Inherit the real environment and add to it. A minimal env crashed Node outright on
    # Windows (exit 134), because it needs SystemRoot and friends to initialise at all.
    env = {
        **os.environ,
        "WEB_DIR": str(WEB),
        "PRODUCT": json.dumps(HERO),
        "NODE_PATH": str(NODE_PATHS),
    }
    completed = subprocess.run(
        ["node", "-e", HARNESS],
        capture_output=True,
        text=True,
        # Explicit UTF-8. Without it Python decodes with the Windows locale codec and the
        # em dash in "Concept artwork — not product photography." arrives as mojibake,
        # failing a test about wording for reasons that have nothing to do with wording.
        encoding="utf-8",
        cwd=str(REPO / "apps" / "mobile"),
        env={**env, "PYTHONIOENCODING": "utf-8"},
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# ------------------------------------------------------------------------- the gallery


def test_all_four_media_records_are_rendered(rendered):
    """The defect was a placeholder letter where four images belonged."""

    assert rendered["gallery"]["imageCount"] == 4, rendered["gallery"]


def test_api_ordering_is_preserved(rendered):
    """Front, back, detail, lifestyle -- the server's order, not one invented here.

    Re-sorting client-side is how two surfaces end up showing the same product's images in
    different orders. Mobile renders the API order; so does this.
    """

    assert [c.lower() for c in rendered["gallery"]["captions"]] == [
        "front", "back", "detail", "lifestyle"
    ], rendered["gallery"]["captions"]
    assert [Path(s).name for s in rendered["gallery"]["srcs"]] == [
        "ddn-ts01-front.svg",
        "ddn-ts01-back.svg",
        "ddn-ts01-detail.svg",
        "ddn-ts01-lifestyle.svg",
    ]


def test_media_resolves_against_the_api_origin_not_the_storefront(rendered):
    """The document is served from storefront.test:13080; media must come from the API."""

    for src in rendered["gallery"]["srcs"]:
        assert src.startswith("http://api.test:18080/api/v1/media/"), src
        assert "storefront.test" not in src


def test_side_a_alt_text_is_used_verbatim(rendered):
    assert rendered["gallery"]["alts"] == [
        "Concept front view of The Source Tee",
        "Concept back view of The Source Tee",
        "Concept detail view of The Source Tee",
        "Abstract lifestyle concept for The Source Tee",
    ]


def test_concept_media_is_labelled_as_concept_artwork(rendered):
    """A prototype rendering must never read as a photograph of a real garment."""

    assert rendered["gallery"]["note"] == "Concept artwork — not product photography."


def test_the_placeholder_letter_is_gone(rendered):
    """`aria-hidden` + a single initial was the whole of the old product 'media'."""

    assert rendered["gallery"]["ariaHidden"] is None
    assert rendered["gallery"]["text"].strip() != "T"


def test_every_gallery_image_loads_eagerly(rendered):
    """Four small concept SVGs the customer opened the page to see.

    Lazy thumbnails previously collapsed to zero height, never intersected the viewport
    and therefore never loaded at all -- a deadlock, not a saving.
    """

    assert set(rendered["gallery"]["loading"]) == {"eager"}


# ------------------------------------------------------------------------ edge cases


def test_a_single_media_record_renders_without_a_thumbnail_strip(rendered):
    assert rendered["single"]["imageCount"] == 1


def test_no_media_renders_nothing_rather_than_an_empty_frame(rendered):
    """Returning null lets the caller fall back to the placeholder deliberately."""

    assert rendered["empty"] is None


def test_a_product_without_a_media_key_does_not_throw(rendered):
    assert rendered["missingKey"] is None


# ---------------------------------------------------------------------- catalogue card


def test_card_uses_the_front_image(rendered):
    assert rendered["card"]["imageCount"] == 1
    assert Path(rendered["card"]["srcs"][0]).name == "ddn-ts01-front.svg"
    assert rendered["card"]["alts"][0] == "Concept front view of The Source Tee"


def test_card_without_media_keeps_the_initial_placeholder(rendered):
    """The placeholder is retained as a FALLBACK, not deleted."""

    assert rendered["cardNoMedia"]["imageCount"] == 0
    assert rendered["cardNoMedia"]["text"].strip() == "T"
    assert rendered["cardNoMedia"]["ariaHidden"] == "true"
