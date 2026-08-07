"""The brand media root: where it resolves from, and how it fails.

The distinction under test is the one whose absence hid a two-day outage: a MISSING ASSET
is a 404, and a MISSING ASSET ROOT is a deployment failure. When both were 404, an image
built without `packages/brand/assets` started cleanly, answered `/ready` with 200, and
served nothing — and no probe could tell.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.commerce import api as commerce_api
from app.main import app

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent.parent
LOGO = "/api/v1/media/assets/brand-prototype/logos/logo-primary.svg"

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_media_root_env(monkeypatch):
    monkeypatch.delenv(commerce_api.BRAND_MEDIA_ROOT_ENV, raising=False)


# ------------------------------------------------------------------------ resolution


def test_checkout_fallback_finds_the_repository_package():
    """With nothing configured, a checkout still serves its own assets."""

    root = commerce_api.resolve_media_root()
    assert root is not None
    assert root == (REPO / "packages" / "brand" / "assets").resolve()
    assert root.is_dir()


def test_an_explicit_root_overrides_the_checkout(monkeypatch, tmp_path):
    """Deployment configuration wins. This is what the container sets."""

    monkeypatch.setenv(commerce_api.BRAND_MEDIA_ROOT_ENV, str(tmp_path))
    assert commerce_api.resolve_media_root() == tmp_path.resolve()


def test_a_missing_root_is_refused_rather_than_silently_empty(monkeypatch, tmp_path):
    monkeypatch.setenv(commerce_api.BRAND_MEDIA_ROOT_ENV, str(tmp_path / "nowhere"))
    with pytest.raises(commerce_api.MediaRootUnavailable):
        commerce_api.assert_media_root()


# ------------------------------------------------------------------- served behaviour


def test_assets_are_served_from_the_configured_root(monkeypatch):
    response = client.get(LOGO)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_the_media_route_sets_nosniff_itself_not_only_the_global_middleware():
    """Both layers set nosniff, so neither is detectable through the app.

    `main.correlation_and_access_log` stamps `X-Content-Type-Options` on EVERY response,
    and the media route sets it again on its own `FileResponse`. That redundancy is
    deliberate defence in depth — but it also means a request-level assertion passes when
    either one is removed, which let a mutation of the route's header survive.

    So this asserts the route's OWN header by calling the handler directly, with no
    middleware in the path. The request-level test above still covers the combination.
    """

    response = commerce_api.get_media("assets/brand-prototype/logos/logo-primary.svg")

    assert response.headers["x-content-type-options"] == "nosniff", dict(response.headers)
    assert response.media_type == "image/svg+xml"


def test_a_missing_asset_under_a_valid_root_is_404(monkeypatch):
    response = client.get("/api/v1/media/assets/brand-prototype/logos/not-a-real-asset.svg")
    assert response.status_code == 404


def test_a_missing_root_is_503_not_404(monkeypatch, tmp_path):
    """503, so a misdeployment is distinguishable from a typo in an asset name.

    This is the assertion that would have caught the container having no assets at all:
    every URL returning 404 looks exactly like a catalogue with no imagery configured.
    """

    monkeypatch.setenv(commerce_api.BRAND_MEDIA_ROOT_ENV, str(tmp_path / "absent"))
    response = client.get(LOGO)
    assert response.status_code == 503
    assert "does not exist" in response.json()["detail"]


def test_containment_still_holds_against_a_configured_root(monkeypatch, tmp_path):
    """Repointing the root must not weaken traversal containment."""

    monkeypatch.setenv(commerce_api.BRAND_MEDIA_ROOT_ENV, str(tmp_path))
    (tmp_path / "inside.svg").write_text("<svg/>", encoding="utf-8")
    secret = tmp_path.parent / "outside.svg"
    secret.write_text("<svg/>", encoding="utf-8")

    assert client.get("/api/v1/media/inside.svg").status_code == 200
    for escape in ("../outside.svg", "..%2Foutside.svg", "a/../../outside.svg"):
        assert client.get(f"/api/v1/media/{escape}").status_code == 404


# ------------------------------------------------------------ the packaged-asset check


def test_the_repository_package_passes_the_packaging_verifier():
    """The same check the Docker build runs, so a break is caught before a build."""

    completed = subprocess.run(
        [
            sys.executable, "-B",
            str(REPO / "scripts" / "brand" / "verify_packaged_assets.py"),
            "--root", str(REPO / "packages" / "brand" / "assets"),
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["result"] == "PACKAGED_BRAND_ASSETS_VERIFIED"
    assert report["registered_assets"] == 31
    assert report["product_media_relations"] == 18
    assert report["missing"] == [] and report["mismatched"] == []


def test_the_verifier_detects_a_missing_asset(tmp_path):
    """A verifier that cannot fail is decoration. This proves it fails."""

    import shutil

    incomplete = tmp_path / "assets"
    shutil.copytree(REPO / "packages" / "brand" / "assets", incomplete)
    victim = incomplete / "assets" / "brand-prototype" / "products" / "ddn-ts01-front.svg"
    victim.unlink()

    completed = subprocess.run(
        [
            sys.executable, "-B",
            str(REPO / "scripts" / "brand" / "verify_packaged_assets.py"),
            "--root", str(incomplete),
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert report["result"] == "PACKAGED_BRAND_ASSETS_FAILED"
    assert "DDN-TS01-FRONT" in report["missing"]


def test_the_verifier_detects_rewritten_bytes(tmp_path):
    """Line-ending normalization has silently rewritten these assets before."""

    import shutil

    tampered = tmp_path / "assets"
    shutil.copytree(REPO / "packages" / "brand" / "assets", tampered)
    victim = tampered / "assets" / "brand-prototype" / "logos" / "logo-primary.svg"
    victim.write_bytes(victim.read_bytes() + b"\n")

    completed = subprocess.run(
        [
            sys.executable, "-B",
            str(REPO / "scripts" / "brand" / "verify_packaged_assets.py"),
            "--root", str(tampered),
        ],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert completed.returncode == 1
    assert "LOGO-PRIMARY-001" in json.loads(completed.stdout)["mismatched"]
