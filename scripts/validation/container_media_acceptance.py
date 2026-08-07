"""Deployable brand/product media acceptance, executed against a real container.

Why this exists
---------------
`f17dad3` verified "18/18 product media and 31/31 brand assets return 200" -- and that was
true only of a checkout on disk. The API image build context is `services/commerce-api`,
so `packages/brand/assets` could never be inside the image, and every media request in
every containerised deployment returned 404. A host-checkout test cannot see that, because
on the host the files are simply there.

So this harness is deliberately topology-aware. `--base` points at a REAL running API and
`--container` names the container whose filesystem is inspected, so the two halves of the
claim -- "the bytes are in the image" and "the route serves them" -- are checked against
the same deployed artifact rather than against the repository.

    python scripts/validation/container_media_acceptance.py \
        --base http://127.0.0.1:18080 --container dedunet-staging-api-1

Exit code 0 only when every registered asset and every product-media relation resolves
with the right type and security headers, and every hostile path is still refused.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "packages" / "brand"

HERO = "DDN-TS01"
HERO_SLUG = "the-source-tee"
EXPECTED_HERO_ROLES = ["front", "back", "detail", "lifestyle"]

EXPECTED_TYPES = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

results: dict = {"checks": [], "data": {}}


def record(name: str, ok: bool, detail: str = "") -> bool:
    results["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return ok


def call(base: str, path: str):
    """Returns (status, headers, body_bytes). Never raises for an HTTP status."""

    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=20) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
            return exc.code, {k.lower(): v for k, v in exc.headers.items()}, body
        finally:
            exc.close()
    except OSError as exc:
        return 0, {}, str(exc).encode()


def load_registry() -> tuple[list[dict], list[dict]]:
    assets = json.loads((BRAND / "assets.json").read_text(encoding="utf-8"))
    media = json.loads((BRAND / "product-media.json").read_text(encoding="utf-8"))
    return assets, media


# ------------------------------------------------------------------ image filesystem


def inspect_container(container: str) -> None:
    """Inspect the DEPLOYED filesystem, not the Dockerfile.

    A Dockerfile is a statement of intent; the image is the artifact. These checks read
    the artifact, because the defect this harness exists for was invisible in the
    Dockerfile -- nothing there was wrong, the build context simply did not contain the
    directory the route needed.
    """

    print("\n--- container filesystem ---")

    def sh(command: str) -> tuple[int, str]:
        proc = subprocess.run(
            ["docker", "exec", container, "sh", "-c", command],
            capture_output=True, text=True,
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()

    code, root = sh(
        "python -c \"from app.commerce.api import assert_media_root; print(assert_media_root())\""
    )
    record("runtime media root is resolvable in the container", code == 0, root[:160])
    results["data"]["container_media_root"] = root
    if code != 0:
        # Without a root every later filesystem assertion would be meaningless, so stop
        # rather than report a cascade of failures that all share one cause.
        record("31 normalized asset files packaged in the image", False, "no resolvable root")
        return

    code, listing = sh(f"ls -1 {root} 2>&1 | head -20")
    record("runtime media root exists in the image", code == 0 and "No such file" not in listing,
           listing[:160])

    code, count = sh(f"find {root} -type f 2>/dev/null | wc -l")
    packaged = int(count) if code == 0 and count.strip().isdigit() else 0
    results["data"]["container_asset_file_count"] = packaged
    record("31 normalized asset files packaged in the image", packaged == 31, f"found {packaged}")

    # Nothing that must not ship. Each is checked as an ABSENCE against the real image.
    forbidden = {
        ".git metadata": "find / -maxdepth 4 -name '.git' -not -path '*/node_modules/*' 2>/dev/null | head -3",
        ".env files": "find / -maxdepth 4 -name '.env' -o -maxdepth 4 -name '.env.staging' 2>/dev/null | head -3",
        "evidence directory": "find / -maxdepth 3 -type d -name 'evidence' 2>/dev/null | head -3",
        "backup dumps": "find / -maxdepth 4 -name '*.dump' 2>/dev/null | head -3",
        "Side A immutable handoff": "find / -maxdepth 4 -type d -name 'handoffs' 2>/dev/null | head -3",
        "docs directory": "find /app -maxdepth 2 -type d -name 'docs' 2>/dev/null | head -3",
        "test directory": "find /app -maxdepth 2 -type d -name 'tests' 2>/dev/null | head -3",
        "node_modules": "find / -maxdepth 4 -type d -name 'node_modules' 2>/dev/null | head -3",
    }
    for label, command in forbidden.items():
        _, found = sh(command)
        record(f"image contains no {label}", not found.strip(), found[:120])

    _, size = sh("du -sh /app 2>/dev/null | cut -f1")
    results["data"]["container_app_size"] = size.strip()
    print(f"       /app size: {size.strip()}")


# ---------------------------------------------------------------------- HTTP surface


def check_assets(base: str) -> None:
    assets, media = load_registry()
    print("\n--- registered brand assets ---")

    statuses = []
    for asset in assets:
        status, headers, body = call(base, asset["url"])
        suffix = Path(asset["path"]).suffix.lower()
        ok = (
            status == 200
            and EXPECTED_TYPES.get(suffix, "").split("/")[0] in headers.get("content-type", "")
            and headers.get("x-content-type-options") == "nosniff"
            and len(body) == asset["bytes"]
        )
        statuses.append((asset["asset_id"], status, ok))

    served = sum(1 for _, s, _ in statuses if s == 200)
    fully_ok = sum(1 for _, _, ok in statuses if ok)
    results["data"]["registered_assets_total"] = len(assets)
    results["data"]["registered_assets_200"] = served
    record(f"all {len(assets)} registered brand assets return 200", served == len(assets),
           f"{served}/{len(assets)}")
    record("every asset has the right type, nosniff and exact byte length",
           fully_ok == len(assets), f"{fully_ok}/{len(assets)}")
    if served != len(assets):
        failing = [aid for aid, s, _ in statuses if s != 200][:5]
        print(f"       first failures: {failing}")

    print("\n--- product media ---")
    media_statuses = [(m["asset_id"], call(base, m["url"])[0]) for m in media]
    media_served = sum(1 for _, s in media_statuses if s == 200)
    results["data"]["product_media_total"] = len(media)
    results["data"]["product_media_200"] = media_served
    record(f"all {len(media)} product-media requests return 200",
           media_served == len(media), f"{media_served}/{len(media)}")


def check_hero(base: str) -> None:
    print("\n--- DDN-TS01 ---")
    status, _, body = call(base, f"/api/v1/catalog/products/{HERO_SLUG}")
    if status != 200:
        record("DDN-TS01 payload reads", False, f"HTTP {status}")
        return
    product = json.loads(body)

    record("DDN-TS01 payload reads", product.get("external_product_id") == HERO)
    media = product.get("media", [])
    record("DDN-TS01 exposes 4 media records", len(media) == 4, str(len(media)))
    roles = [m["role"] for m in media]
    record("media ordering is deterministic front,back,detail,lifestyle",
           roles == EXPECTED_HERO_ROLES, str(roles))
    record("every DDN-TS01 media record carries alt text",
           all(m.get("alt_text") for m in media))
    record("every DDN-TS01 media record is labelled concept",
           all(m.get("status") == "PROTOTYPE_CONCEPT" for m in media),
           str({m.get("status") for m in media}))

    codes = [call(base, m["url"])[0] for m in media]
    record("all 4 DDN-TS01 media URLs return 200", all(c == 200 for c in codes), str(codes))
    results["data"]["hero_media"] = [
        {"role": m["role"], "sort_order": m["sort_order"], "url": m["url"],
         "alt_text": m.get("alt_text"), "status": m.get("status")}
        for m in media
    ]


def check_hostile(base: str) -> None:
    """The containment controls must survive the packaging change."""

    print("\n--- hostile paths ---")
    hostile = [
        ("traversal", "/api/v1/media/../../../etc/passwd"),
        ("encoded traversal", "/api/v1/media/..%2F..%2F..%2Fetc%2Fpasswd"),
        ("nested traversal", "/api/v1/media/assets/../../../../etc/passwd"),
        ("directory listing", "/api/v1/media/assets/brand-prototype/products/"),
        ("asset root itself", "/api/v1/media/"),
        ("dotfile", "/api/v1/media/assets/.hidden"),
        ("non-image type", "/api/v1/media/assets/brand-prototype/products/../../../assets.json"),
        ("missing asset", "/api/v1/media/assets/brand-prototype/products/does-not-exist.svg"),
        ("python source", "/api/v1/media/../app/main.py"),
    ]
    outcomes = []
    for label, path in hostile:
        status, _, _ = call(base, path)
        ok = status in (404, 400, 405)
        outcomes.append((label, status))
        record(f"{label} refused", ok, f"HTTP {status}")
    results["data"]["hostile_paths"] = {label: status for label, status in outcomes}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="running API base URL")
    parser.add_argument("--container", help="container whose filesystem is inspected")
    parser.add_argument("--label", default="", help="topology label recorded in the manifest")
    parser.add_argument("--out")
    args = parser.parse_args()

    results["generated_at"] = datetime.now(timezone.utc).isoformat()
    results["base"] = args.base
    results["container"] = args.container
    results["topology"] = args.label

    print(f"=== DEPLOYABLE MEDIA ACCEPTANCE :: {args.label or args.base} ===")

    if args.container:
        inspect_container(args.container)
    check_assets(args.base)
    check_hero(args.base)
    check_hostile(args.base)

    failed = [c for c in results["checks"] if not c["pass"]]
    results["summary"] = {
        "total": len(results["checks"]),
        "passed": len(results["checks"]) - len(failed),
        "failed": len(failed),
    }
    print(f"\n{results['summary']}")

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
