"""Verify a packaged copy of the normalized brand assets against the brand manifests.

Runs in three places, deliberately the same code in all three:

  * inside the Docker build, so an image that is missing an asset FAILS TO BUILD rather
    than starting successfully and returning 404 for every media request;
  * in the test suite, against the repository checkout;
  * by hand, against any directory claiming to be a packaged asset root.

The failure this exists to prevent already happened once. `packages/brand/assets` sat
outside the API image's build context, so it could never be copied in. Nothing failed:
the image built, the container started, `/ready` returned 200, and every brand and
product media URL returned 404 in every containerised deployment. A build-time check is
the only place that catches it before deployment, because at runtime a missing asset and
a missing asset ROOT look identical from outside.

Bytes are compared by SHA-256, not by presence. A file that exists but was rewritten --
by Git line-ending normalization, for instance, which has already broken these exact
assets once -- is as broken as a file that is absent.

    python scripts/brand/verify_packaged_assets.py --root packages/brand/assets
    python scripts/brand/verify_packaged_assets.py --root /app/brand-assets \
        --assets /brand/assets.json --media /brand/product-media.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

def default_brand_dir() -> Path | None:
    """The checkout's brand package, or None when this script is not in a checkout.

    Resolved LAZILY, and this is not a style preference. Computing it at import time as
    `Path(__file__).resolve().parents[2]` raised IndexError the moment the script was
    copied to `/brand/` inside a Docker build stage — the same class of module-level path
    assumption that put the media root outside the image in the first place, and the same
    one `manage.py.contract_path` already documents. A default is only ever needed when
    both manifest arguments are omitted.
    """

    here = Path(__file__).resolve()
    if len(here.parents) < 3:
        return None
    return here.parents[2] / "packages" / "brand"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(root: Path, assets_manifest: Path, media_manifest: Path) -> tuple[bool, dict]:
    assets = json.loads(assets_manifest.read_text(encoding="utf-8"))
    media = json.loads(media_manifest.read_text(encoding="utf-8"))

    missing: list[str] = []
    mismatched: list[str] = []
    checked = 0

    for entry in assets:
        # `path` joins DIRECTLY onto the root -- the layout really is
        # <root>/assets/brand-prototype/..., with the "assets" segment repeated. That is
        # not a typo: it is the same join the media route performs, where the URL
        # /api/v1/media/assets/brand-prototype/... yields the asset_path
        # "assets/brand-prototype/...". Stripping the prefix here would verify a layout
        # the server does not actually serve.
        candidate = root / entry["path"]

        if not candidate.is_file():
            missing.append(entry["asset_id"])
            continue
        checked += 1
        if _sha256(candidate) != entry["sha256"]:
            mismatched.append(entry["asset_id"])

    # Every product-media relation must point at an asset that is actually present.
    media_missing: list[str] = []
    for entry in media:
        if not (root / entry["path"]).is_file():
            media_missing.append(entry["asset_id"])

    # An unexpected EXTRA file is reported too. The packaged root is meant to be exactly
    # the normalized package; anything else in there arrived from somewhere unreviewed.
    expected = {entry["path"] for entry in assets}
    present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} if root.is_dir() else set()
    unexpected = sorted(present - expected)

    report = {
        "root": str(root),
        "root_exists": root.is_dir(),
        "registered_assets": len(assets),
        "product_media_relations": len(media),
        "verified": checked - len(mismatched),
        "missing": missing,
        "mismatched": mismatched,
        "product_media_missing": media_missing,
        "unexpected_files": unexpected,
    }
    ok = (
        root.is_dir()
        and not missing
        and not mismatched
        and not media_missing
        and not unexpected
        and checked == len(assets)
    )
    report["result"] = "PACKAGED_BRAND_ASSETS_VERIFIED" if ok else "PACKAGED_BRAND_ASSETS_FAILED"
    return ok, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="directory claiming to be the asset root")
    parser.add_argument("--assets", help="assets.json (defaults to the checkout's copy)")
    parser.add_argument("--media", help="product-media.json (defaults to the checkout's copy)")
    args = parser.parse_args()

    brand = default_brand_dir()
    assets = Path(args.assets) if args.assets else (brand / "assets.json" if brand else None)
    media = Path(args.media) if args.media else (brand / "product-media.json" if brand else None)
    if assets is None or media is None:
        raise SystemExit(
            "cannot locate the brand manifests; pass --assets and --media explicitly"
        )

    ok, report = verify(Path(args.root), assets, media)
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
