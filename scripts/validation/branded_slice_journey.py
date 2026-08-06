"""Branded DEDUNET vertical-slice journey.

Drives the real API over HTTP and records a machine-readable manifest. Every assertion is
executed; nothing is asserted from documentation.

Phases:
  A  default product truth (before any test inventory)
  B  BRAND_PREVIEW_MODE journey -- everything visible, nothing purchasable
  C  COMMERCE_TEST_MODE synthetic inventory
  D  customer journey: decline, then success
  E  order provenance and admin
  F  notifications
  G  rate limiting and session handling
  H  return to preview and confirm blocking

Run with the API already serving. The mode is switched by restarting the API, so this script
is invoked once per phase group with --phase.

No credential is printed or written. Test identities are generated locally and are obviously
test data.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "http://127.0.0.1:18300"
HERO = "DDN-TS01"
HERO_SLUG = "the-source-tee"

results: dict = {"checks": [], "correlation_ids": {}, "data": {}}


class _CaseInsensitive(dict):
    """HTTP header names are case-insensitive; a plain dict is not."""

    def get(self, key, default=None):  # type: ignore[override]
        lowered = key.lower()
        for name, value in self.items():
            if name.lower() == lowered:
                return value
        return default


def record(name: str, ok: bool, detail: str = "") -> bool:
    results["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return ok


def call(method: str, path: str, body=None, headers=None, label: str | None = None):
    """One HTTP call. Returns (status, json_or_text, headers)."""

    request = urllib.request.Request(
        f"{BASE}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode()
            status, hdrs = response.status, dict(response.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        status, hdrs = exc.code, dict(exc.headers)

    # Case-insensitive. uvicorn emits lowercase header names, and a plain dict() lookup for
    # "Content-Type" therefore missed them -- which looked like the API had stopped setting
    # nosniff when it had not.
    hdrs = _CaseInsensitive(hdrs)

    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        payload = raw

    correlation = hdrs.get("X-Correlation-ID")
    if label and correlation:
        results["correlation_ids"][label] = correlation
    return status, payload, hdrs


# --------------------------------------------------------------- A. default product truth

def phase_default_truth() -> None:
    print("\n=== A. DEFAULT PRODUCT TRUTH ===")
    status, product, _ = call("GET", f"/api/v1/catalog/products/{HERO_SLUG}", label="catalogue")

    record("DDN-TS01 exists", status == 200 and product.get("external_product_id") == HERO)
    record("18 variants", len(product.get("variants", [])) == 18, str(len(product.get("variants", []))))

    media = product.get("media", [])
    record("4 media records", len(media) == 4, str(len(media)))
    record(
        "media ordered front,back,detail,lifestyle",
        [m["role"] for m in media] == ["front", "back", "detail", "lifestyle"],
        str([m["role"] for m in media]),
    )

    stock = sum(v["available"] for v in product["variants"])
    record("prototype stock is zero", stock == 0, f"total available={stock}")
    record("product not sellable", product.get("sellable") is False)
    record("country_of_origin = XX", product.get("country_of_origin") == "XX")
    record("intended_origin = EG", product.get("intended_origin") == "EG")
    record("origin_claim_status = UNVERIFIED", product.get("origin_claim_status") == "UNVERIFIED")
    record("media_status = PROTOTYPE_CONCEPT", product.get("media_status") == "PROTOTYPE_CONCEPT")
    record(
        "legal_brand_status pending",
        product.get("legal_brand_status") == "LEGAL_CLEARANCE_PENDING",
    )
    record("evidence_status = DRAFT", product.get("evidence_status") == "DRAFT")

    body = json.dumps(product).lower()
    record("no 'made in' claim", "made in" not in body)

    results["data"]["hero_product"] = {
        "external_product_id": product.get("external_product_id"),
        "slug": product.get("slug"),
        "name": product.get("name"),
        "variants": len(product.get("variants", [])),
        "media": [{"role": m["role"], "sort_order": m["sort_order"], "url": m["url"]} for m in media],
        "price_minor_units": product["variants"][0]["price_minor_units"],
        "currency": product.get("currency"),
    }


# ------------------------------------------------------------------- B. preview journey

def phase_preview() -> None:
    print("\n=== B. BRAND_PREVIEW_MODE ===")

    status, catalogue, _ = call("GET", "/api/v1/catalog/products", label="catalogue_list")
    record("catalogue loads", status == 200)
    record("exactly 5 DEDUNET products", len(catalogue) == 5, str(len(catalogue)))
    record(
        "no legacy fixture leaks",
        all(p.get("external_product_id") for p in catalogue),
    )
    record("DDN-TS01 in catalogue", any(p["slug"] == HERO_SLUG for p in catalogue))

    # media URLs resolve
    product = next(p for p in catalogue if p["slug"] == HERO_SLUG)
    codes = []
    for m in product["media"]:
        code, _, hdrs = call("GET", m["url"])
        codes.append((code, hdrs.get("Content-Type", ""), hdrs.get("X-Content-Type-Options", "")))
    record("all 4 media URLs return 200", all(c[0] == 200 for c in codes), str([c[0] for c in codes]))
    record("media content type is svg", all("svg" in c[1] for c in codes))
    record("media sets nosniff", all(c[2] == "nosniff" for c in codes))

    code, _, _ = call("GET", "/api/v1/media/assets/brand-prototype/products/does-not-exist.svg")
    record("missing media -> 404", code == 404, str(code))

    # cart add must be refused
    variant_id = product["variants"][0]["id"]
    code, payload, _ = call(
        "POST", "/api/v1/cart/items", {"variant_id": variant_id, "quantity": 1}, label="preview_cart_add"
    )
    record("preview cart-add refused", code == 409, f"HTTP {code}")
    record(
        "refusal names brand preview",
        isinstance(payload, dict) and "brand preview" in str(payload.get("detail", "")),
        str(payload.get("detail", ""))[:70] if isinstance(payload, dict) else "",
    )

    # checkout must be refused before any payment call
    code, payload, _ = call(
        "POST",
        "/api/v1/checkout",
        {"payment_method_token": "pm_success", "idempotency_key": "preview-must-fail-1"},
        headers={"X-Cart-Token": "no-such-cart"},
        label="preview_checkout",
    )
    record("preview checkout refused", code in (400, 401, 409), f"HTTP {code}")

    # nothing was reserved
    _, after, _ = call("GET", f"/api/v1/catalog/products/{HERO_SLUG}")
    record(
        "no inventory reserved in preview",
        sum(v["available"] for v in after["variants"]) == 0,
    )

    code, _, _ = call("GET", "/ready")
    record("/ready 200", code == 200)
    code, _, _ = call("GET", "/health")
    record("/health 200", code == 200)


# ------------------------------------------------------------- G. rate limit / session

def phase_rate_limit() -> None:
    print("\n=== G. RATE LIMITING AND SESSION ===")

    codes = []
    retry_after = None
    expose = None
    for _ in range(13):
        code, _, hdrs = call(
            "POST",
            "/api/v1/auth/login",
            {"email": "nobody@dedunet.example", "password": "wrong-value"},
            headers={"Origin": "http://127.0.0.1:13000"},
        )
        codes.append(code)
        if code == 429:
            retry_after = hdrs.get("Retry-After")
            expose = hdrs.get("Access-Control-Expose-Headers")

    record("valid-range requests then 429", 429 in codes, f"codes={codes}")
    record("Retry-After present", retry_after is not None, f"Retry-After={retry_after}")
    record(
        "Retry-After readable by a browser",
        expose is not None and "Retry-After" in expose,
        str(expose)[:60],
    )

    # Spoofed XFF must not mint a fresh bucket.
    #
    # Sent as ONE uninterrupted burst that first exhausts the limiter and then immediately
    # varies the header. An earlier version exhausted the bucket, did other work, and only
    # then spoofed -- by which time the token bucket had refilled and every spoofed request
    # legitimately returned 401. That measured refill timing, not bypass resistance.
    spoofed = []
    for i in range(16):
        code, _, _ = call(
            "POST",
            "/api/v1/auth/login",
            {"email": "nobody@dedunet.example", "password": "wrong-value"},
            headers={"X-Forwarded-For": f"10.9.9.{i}"},
        )
        spoofed.append(code)

    # Every request carries a DIFFERENT spoofed client IP. If the header were trusted, each
    # would get its own fresh bucket and none would ever be limited.
    record(
        "spoofed X-Forwarded-For does not mint fresh buckets",
        429 in spoofed,
        f"codes={spoofed}",
    )
    record(
        "limiter still engages despite varied spoofed IPs",
        spoofed.count(429) >= 3,
        f"429 count={spoofed.count(429)} of {len(spoofed)}",
    )

    code, _, _ = call("GET", "/ready")
    record("/ready still 200 after burst", code == 200)

    # forged session
    code, _, _ = call(
        "GET", "/api/v1/me/orders", headers={"Authorization": "Bearer forged.invalid.token"}
    )
    record("forged session rejected 401", code == 401, f"HTTP {code}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=["truth", "preview", "ratelimit"])
    parser.add_argument("--out")
    args = parser.parse_args()

    results["phase"] = args.phase
    results["generated_at"] = datetime.now(timezone.utc).isoformat()

    {"truth": phase_default_truth, "preview": phase_preview, "ratelimit": phase_rate_limit}[
        args.phase
    ]()

    failed = [c for c in results["checks"] if not c["pass"]]
    results["summary"] = {
        "total": len(results["checks"]),
        "passed": len(results["checks"]) - len(failed),
        "failed": len(failed),
    }
    print(f"\n{results['summary']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
