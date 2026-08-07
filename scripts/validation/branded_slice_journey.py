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
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:18300"
HERO = "DDN-TS01"
HERO_SLUG = "the-source-tee"
SELECTED_SKU = "DDN-SRC-CAR-XS"

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "services" / "commerce-api"

# Synthetic-inventory vocabulary, mirrored from app.commerce.synthetic_inventory. Written
# out rather than imported so a mutation to that module cannot quietly redefine what this
# harness is checking for.
SYNTHETIC_STATUS = "synthetic_test_stock"
PROTOTYPE_STATUS = "prototype_unavailable"
TEST_QUANTITY = 25

results: dict = {"checks": [], "correlation_ids": {}, "data": {}}


def _test_password() -> str:
    """The local test customer's password, supplied by the runner.

    Never defaulted and never printed. A committed default would be a credential in the
    repository, and a generated one would make the run unrepeatable.
    """

    value = os.environ.get("SLICE_TEST_PASSWORD", "")
    if not value:
        raise SystemExit("SLICE_TEST_PASSWORD must be set by the runner")
    return value


def run_cli(args: list[str], *, mode: str | None = None) -> tuple[int, str]:
    """Invoke manage.py in a controlled environment. Returns (exit code, stdout+stderr)."""

    env = dict(os.environ)
    if mode is not None:
        env["COMMERCE_MODE"] = mode
    completed = subprocess.run(
        [sys.executable, "-B", "manage.py", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def last_json(output: str) -> dict:
    """Extract the trailing JSON object from CLI output.

    The console notification channel prints one human-readable line per message before
    manage.py prints its JSON summary, so the output is not a single document. Scanning
    backwards for the last parseable object is stable whether or not anything was logged
    ahead of it.
    """

    lines = output.strip().splitlines()
    for start in range(len(lines)):
        candidate = "\n".join(lines[start:]).strip()
        if candidate.startswith("{"):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return {}


def db_session():
    """A session against the same database the API is serving.

    Notifications have no read API -- by design, an outbox is not a customer-facing
    resource -- so their queued/claimed/sent states can only be observed here.
    """

    sys.path.insert(0, str(BACKEND))
    from app.commerce.db import SessionLocal

    return SessionLocal()


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


# ------------------------------------------------------- C. synthetic test inventory


def _hero() -> dict:
    _, product, _ = call("GET", f"/api/v1/catalog/products/{HERO_SLUG}")
    return product


def _variant(product: dict, sku: str) -> dict | None:
    return next((v for v in product["variants"] if v["sku"] == sku), None)


def _evidence_state(product: dict) -> dict:
    """The states synthetic inventory must never touch."""

    return {
        "origin_claim_status": product.get("origin_claim_status"),
        "intended_origin": product.get("intended_origin"),
        "country_of_origin": product.get("country_of_origin"),
        "material_claim_status": product.get("material_claim_status"),
        "legal_brand_status": product.get("legal_brand_status"),
        "media_status": product.get("media_status"),
        "evidence_status": product.get("evidence_status"),
        "media": [(m["role"], m["status"], m["url"]) for m in product.get("media", [])],
    }


def phase_inventory() -> None:
    print("\n=== C. COMMERCE_TEST_MODE SYNTHETIC INVENTORY ===")

    before = _hero()
    selected = _variant(before, SELECTED_SKU)
    record(f"selected SKU {SELECTED_SKU} exists", selected is not None)
    if selected is None:
        return

    # --- the prototype default, BEFORE anything is loaded --------------------------
    record("starting stock is zero", selected["available"] == 0, f"available={selected['available']}")
    record("variant not sellable", selected["sellable"] is False)
    record(
        f"variant inventory_status = {PROTOTYPE_STATUS}",
        selected["inventory_status"] == PROTOTYPE_STATUS,
        str(selected["inventory_status"]),
    )
    record("origin_claim_status = UNVERIFIED", before.get("origin_claim_status") == "UNVERIFIED")
    record(
        "legal_brand_status = LEGAL_CLEARANCE_PENDING",
        before.get("legal_brand_status") == "LEGAL_CLEARANCE_PENDING",
    )

    evidence_before = _evidence_state(before)
    starting_total = sum(v["available"] for v in before["variants"])
    record("whole product starts at zero stock", starting_total == 0, f"total={starting_total}")

    # --- the command must refuse, three different ways ------------------------------
    code, out = run_cli(["load-test-inventory", "--sku", SELECTED_SKU], mode="COMMERCE_TEST_MODE")
    record(
        "refused without --confirm-test-only",
        code != 0 and "confirmation" in out,
        out[:100],
    )

    code, out = run_cli(
        ["load-test-inventory", "--confirm-test-only", "--sku", SELECTED_SKU],
        mode="BRAND_PREVIEW_MODE",
    )
    record(
        "refused in BRAND_PREVIEW_MODE",
        code != 0 and "COMMERCE_TEST_MODE" in out,
        out[:100],
    )

    code, out = run_cli(
        ["load-test-inventory", "--confirm-test-only", "--sku", SELECTED_SKU],
        mode="PUBLIC_COMMERCE_MODE",
    )
    record(
        "refused in PUBLIC_COMMERCE_MODE",
        code != 0 and "PUBLIC_COMMERCE_MODE cannot be enabled" in out,
        out[:100],
    )
    # Recorded, not glossed over: this refusal arrives as an uncaught CommerceModeError
    # traceback, whereas the other two return the clean {"result": "refused"} JSON.
    # manage.py catches TestInventoryRefused but not CommerceModeError. The security
    # property is intact -- non-zero exit, nothing written -- but the operator sees a
    # stack trace instead of a stated refusal. Logged as a limitation, not fixed here:
    # it is outside this milestone and unrelated to the boundary correction.
    results["data"]["public_mode_refusal_mechanism"] = (
        "uncaught CommerceModeError traceback (fails closed; cosmetic defect)"
        if "Traceback" in out
        else "controlled JSON refusal"
    )
    record(
        "the PUBLIC_COMMERCE_MODE refusal writes nothing regardless of presentation",
        sum(v["available"] for v in _hero()["variants"]) == 0,
    )

    # Nothing was written by any of the three refusals.
    record(
        "no stock loaded by a refused command",
        sum(v["available"] for v in _hero()["variants"]) == 0,
    )

    # --- the permitted path ----------------------------------------------------------
    code, out = run_cli(
        ["load-test-inventory", "--confirm-test-only", "--sku", SELECTED_SKU,
         "--quantity", str(TEST_QUANTITY)],
        mode="COMMERCE_TEST_MODE",
    )
    record("succeeds in COMMERCE_TEST_MODE", code == 0, out[:120])
    loaded = last_json(out)
    record("command reports it loaded synthetic data", loaded.get("synthetic") is True)
    record("exactly one variant touched", loaded.get("variants_touched") == 1, str(loaded.get("variants_touched")))
    record("only the selected SKU", loaded.get("skus") == [SELECTED_SKU], str(loaded.get("skus")))

    after = _hero()
    selected_after = _variant(after, SELECTED_SKU)
    record(
        "selected SKU now carries stock",
        selected_after["available"] == TEST_QUANTITY,
        f"available={selected_after['available']}",
    )
    record(
        f"stock is TYPED as {SYNTHETIC_STATUS}",
        selected_after["inventory_status"] == SYNTHETIC_STATUS,
        str(selected_after["inventory_status"]),
    )
    others = [v for v in after["variants"] if v["sku"] != SELECTED_SKU]
    record(
        "every unrelated SKU remains at zero",
        all(v["available"] == 0 for v in others),
        f"non-zero: {[v['sku'] for v in others if v['available']]}",
    )
    record(
        "unrelated SKUs keep the prototype status",
        all(v["inventory_status"] == PROTOTYPE_STATUS for v in others),
    )

    # Other DEDUNET products must be untouched too, not just other variants.
    _, catalogue, _ = call("GET", "/api/v1/catalog/products")
    elsewhere = [
        (p["slug"], v["sku"], v["available"])
        for p in catalogue
        if p["slug"] != HERO_SLUG
        for v in p["variants"]
        if v["available"]
    ]
    record("no other DEDUNET product received stock", not elsewhere, str(elsewhere))

    # --- states that must not have moved ---------------------------------------------
    record(
        "origin, material, legal, media and evidence states unchanged",
        _evidence_state(after) == evidence_before,
        "changed" if _evidence_state(after) != evidence_before else "",
    )

    # --- idempotency -------------------------------------------------------------------
    code, out = run_cli(
        ["load-test-inventory", "--confirm-test-only", "--sku", SELECTED_SKU,
         "--quantity", str(TEST_QUANTITY)],
        mode="COMMERCE_TEST_MODE",
    )
    repeated = _variant(_hero(), SELECTED_SKU)
    record(
        "repeated load is idempotent, not cumulative",
        code == 0 and repeated["available"] == TEST_QUANTITY,
        f"available after second load={repeated['available']}",
    )

    # --- cleanup restores the prototype default ----------------------------------------
    code, out = run_cli(["clear-test-inventory", "--confirm-test-only"], mode="COMMERCE_TEST_MODE")
    cleared = _variant(_hero(), SELECTED_SKU)
    record("cleanup succeeds", code == 0, out[:100])
    record(
        "cleanup returns the selected SKU to zero",
        cleared["available"] == 0,
        f"available={cleared['available']}",
    )
    record(
        "cleanup restores the prototype status",
        cleared["inventory_status"] == PROTOTYPE_STATUS and cleared["sellable"] is False,
    )
    record(
        "cleanup leaves evidence states untouched",
        _evidence_state(_hero()) == evidence_before,
    )

    # Reload for the phases that follow. Recorded so the manifest shows the sequence.
    code, out = run_cli(
        ["load-test-inventory", "--confirm-test-only", "--sku", SELECTED_SKU,
         "--quantity", str(TEST_QUANTITY)],
        mode="COMMERCE_TEST_MODE",
    )
    reloaded = _variant(_hero(), SELECTED_SKU)
    record("reloaded for the customer journey", code == 0 and reloaded["available"] == TEST_QUANTITY)

    results["data"]["synthetic_inventory"] = {
        "selected_sku": SELECTED_SKU,
        "variant_id": selected["id"],
        "price_minor_units": selected["price_minor_units"],
        "currency": after.get("currency"),
        "starting_quantity": 0,
        "loaded_quantity": TEST_QUANTITY,
        "quantity_after_repeat_load": repeated["available"],
        "quantity_after_cleanup": cleared["available"],
        "quantity_after_reload": reloaded["available"],
        "inventory_status_when_loaded": SYNTHETIC_STATUS,
        "inventory_status_when_cleared": cleared["inventory_status"],
    }


def phase_preview_with_stock() -> None:
    """C.10 -- synthetic stock exists in the database, and preview still refuses.

    Run with the API restarted into BRAND_PREVIEW_MODE while the loaded rows are still
    present. This is the property that makes the mode switch safe: sellability is
    computed per request, so no cleanup window exists in which stale rows are buyable.
    """

    print("\n=== C.10 PREVIEW BLOCKS PURCHASE DESPITE STORED SYNTHETIC STOCK ===")

    product = _hero()
    selected = _variant(product, SELECTED_SKU)
    record(
        "synthetic stock is still stored",
        selected["available"] == TEST_QUANTITY,
        f"available={selected['available']}",
    )
    record(
        "the row is still typed synthetic",
        selected["inventory_status"] == SYNTHETIC_STATUS,
    )

    code, payload, _ = call(
        "POST", "/api/v1/cart/items", {"variant_id": selected["id"], "quantity": 1},
        label="preview_with_stock_cart",
    )
    record("cart-add refused despite stock", code == 409, f"HTTP {code}")
    record(
        "refusal names brand preview, not stock",
        isinstance(payload, dict) and "brand preview" in str(payload.get("detail", "")),
        str(payload.get("detail", ""))[:80] if isinstance(payload, dict) else "",
    )
    record(
        "nothing was reserved",
        _variant(_hero(), SELECTED_SKU)["available"] == TEST_QUANTITY,
    )


# ------------------------------------------------------- D. customer commerce journey

TEST_CUSTOMER = "slice.customer.local@dedunet.example"


def _authenticate() -> dict:
    """Register the dedicated local test customer, or log in if it already exists."""

    code, payload, _ = call(
        "POST",
        "/api/v1/auth/register",
        {"email": TEST_CUSTOMER, "password": _test_password(), "full_name": "Slice Test Customer"},
        label="register",
    )
    if code != 201:
        code, payload, _ = call(
            "POST",
            "/api/v1/auth/login",
            {"email": TEST_CUSTOMER, "password": _test_password()},
            label="login",
        )
    record("test customer authenticated", code in (200, 201), f"HTTP {code}")
    return {"Authorization": f"Bearer {payload['access_token']}"}


def phase_journey() -> None:
    print("\n=== D. CUSTOMER COMMERCE-TEST JOURNEY ===")

    product = _hero()
    selected = _variant(product, SELECTED_SKU)
    variant_id = selected["id"]
    unit_price = selected["price_minor_units"]
    stock_before = selected["available"]

    record("selected variant is purchasable", selected["sellable"] is True)
    record(
        "price is 7200 EUR minor units",
        unit_price == 7200 and product.get("currency") == "EUR",
        f"{unit_price} {product.get('currency')}",
    )

    auth = _authenticate()

    # --- cart ---------------------------------------------------------------------
    code, cart, _ = call("GET", "/api/v1/cart", label="cart_create")
    token = cart["cart_token"]
    record("cart created", code == 200 and bool(token))
    record("cart token persists", len(token) > 20)
    headers = {"X-Cart-Token": token}

    code, cart, _ = call(
        "POST", "/api/v1/cart/items", {"variant_id": variant_id, "quantity": 1},
        headers=headers, label="cart_add",
    )
    record("selected variant added", code == 200 and len(cart["lines"]) == 1, f"HTTP {code}")

    code, cart, _ = call(
        "POST", "/api/v1/cart/items", {"variant_id": variant_id, "quantity": 2}, headers=headers
    )
    record("quantity increased to 3", code == 200 and cart["lines"][0]["quantity"] == 3,
           str(cart["lines"][0]["quantity"]) if code == 200 else f"HTTP {code}")

    code, _, _ = call("DELETE", f"/api/v1/cart/items/{variant_id}", headers=headers)
    code, cart, _ = call(
        "POST", "/api/v1/cart/items", {"variant_id": variant_id, "quantity": 2}, headers=headers
    )
    quantity = cart["lines"][0]["quantity"]
    record("quantity decreased to 2", quantity == 2, str(quantity))

    # --- server-priced totals -------------------------------------------------------
    code, quote, _ = call("GET", "/api/v1/cart/quote", headers=headers, label="quote")
    record("checkout quote returned", code == 200, f"HTTP {code}")
    expected_subtotal = unit_price * quantity
    record(
        "subtotal is server-priced",
        quote["subtotal_minor_units"] == expected_subtotal,
        f"{quote['subtotal_minor_units']} vs expected {expected_subtotal}",
    )
    # VAT-inclusive, which is the EU consumer-retail norm and what pricing.py implements:
    #   total = subtotal - discount + shipping
    #   tax   = the component CONTAINED IN that total, not an addend
    # An earlier version of this check added tax on top and failed. That was the check
    # being wrong, not the API: adding VAT would have made the customer pay more than the
    # advertised price, which is the exact mistake the inclusive model prevents.
    record(
        "total = subtotal - discount + shipping",
        quote["total_minor_units"]
        == quote["subtotal_minor_units"] - quote["discount_minor_units"]
        + quote["shipping_minor_units"],
        str(quote),
    )
    record(
        "VAT is a component of the total, not added to it",
        0 < quote["tax_minor_units"] < quote["total_minor_units"],
        f"tax={quote['tax_minor_units']} of total={quote['total_minor_units']}",
    )

    # --- declined payment -------------------------------------------------------------
    # Measured as a DELTA. A declined checkout legitimately leaves a cancelled order row
    # behind -- that is the audit trail of an attempt that failed -- so "no order exists"
    # would be the wrong assertion. What must not happen is a SUCCESSFUL order appearing.
    _, orders_before, _ = call("GET", "/api/v1/me/orders", headers=auth)
    successful_before = {
        o["order_number"] for o in orders_before if o["status"] not in ("cancelled",)
    }

    decline_key = f"slice-decline-{datetime.now(timezone.utc).timestamp():.0f}"
    code, payload, _ = call(
        "POST", "/api/v1/checkout",
        {"payment_method_token": "pm_decline", "idempotency_key": decline_key},
        headers={**headers, **auth}, label="decline",
    )
    record("declined payment returns 402", code == 402, f"HTTP {code}")
    record(
        "decline exposes the correct reason",
        isinstance(payload, dict) and "declined" in str(payload.get("detail", "")).lower(),
        str(payload.get("detail", ""))[:80] if isinstance(payload, dict) else "",
    )

    code, orders, _ = call("GET", "/api/v1/me/orders", headers=auth)
    successful_after = {o["order_number"] for o in orders if o["status"] not in ("cancelled",)}
    record(
        "decline created no successful order",
        successful_after == successful_before,
        f"new successful orders: {sorted(successful_after - successful_before)}",
    )
    record(
        "the declined attempt is recorded as cancelled, not hidden",
        any(o["status"] == "cancelled" for o in orders),
        str(sorted({o["status"] for o in orders})),
    )

    code, cart_after, _ = call("GET", "/api/v1/cart", headers=headers)
    record(
        "decline did not consume the cart",
        cart_after["status"] != "converted" and len(cart_after["lines"]) == 1,
        f"status={cart_after['status']} lines={len(cart_after['lines'])}",
    )
    record(
        "decline released the reserved stock",
        _variant(_hero(), SELECTED_SKU)["available"] == stock_before,
        f"available={_variant(_hero(), SELECTED_SKU)['available']}",
    )

    # --- successful payment ------------------------------------------------------------
    success_key = f"slice-success-{datetime.now(timezone.utc).timestamp():.0f}"
    record("success uses a distinct idempotency intent", success_key != decline_key)

    code, payload, _ = call(
        "POST", "/api/v1/checkout",
        {"payment_method_token": "pm_success", "idempotency_key": success_key},
        headers={**headers, **auth}, label="success",
    )
    record("successful payment returns 201", code == 201, f"HTTP {code}")
    order = payload["order"]
    record("the attempt was not a replay of the decline", payload["replayed"] is False)
    record("a new order exists", bool(order["order_number"]))
    record("order status is paid", order["status"] == "paid", order["status"])
    record(
        "commerce_mode_at_checkout = COMMERCE_TEST_MODE",
        order["commerce_mode_at_checkout"] == "COMMERCE_TEST_MODE",
        str(order["commerce_mode_at_checkout"]),
    )
    record("order is flagged as a test order", order["is_test_order"] is True)
    record(
        "order total matches the quote",
        order["total_minor_units"] == quote["total_minor_units"],
        f"{order['total_minor_units']} vs {quote['total_minor_units']}",
    )
    record(
        "order lines carry the selected SKU",
        [line["sku"] for line in order["lines"]] == [SELECTED_SKU],
        str([line["sku"] for line in order["lines"]]),
    )

    # --- replaying the SAME key must return the SAME order, not a second one ----------
    code, replay, _ = call(
        "POST", "/api/v1/checkout",
        {"payment_method_token": "pm_success", "idempotency_key": success_key},
        headers={**headers, **auth}, label="replay",
    )
    record("replaying the key is idempotent", code == 201 and replay["replayed"] is True)
    record(
        "replay returns the same order number",
        replay["order"]["order_number"] == order["order_number"],
    )

    # --- inventory --------------------------------------------------------------------
    remaining = _variant(_hero(), SELECTED_SKU)["available"]
    record(
        "inventory reservation is exact",
        remaining == stock_before - quantity,
        f"{stock_before} - {quantity} = {stock_before - quantity}, actual {remaining}",
    )
    record("no overselling", remaining >= 0)

    code, oversell, _ = call(
        "POST", "/api/v1/cart/items", {"variant_id": variant_id, "quantity": remaining + 1},
        label="oversell",
    )
    record("over-quantity add is refused", code == 409, f"HTTP {code}")

    # --- converted cart -----------------------------------------------------------------
    code, converted, _ = call("GET", "/api/v1/cart", headers=headers)
    record(
        "the converted cart is marked converted",
        converted["status"] == "converted",
        str(converted["status"]),
    )
    code, fresh, _ = call("GET", "/api/v1/cart")
    record(
        "a new cart token is issued for the next purchase",
        fresh["cart_token"] != token and fresh["status"] != "converted",
        f"status={fresh['status']}",
    )

    # --- order history and detail --------------------------------------------------------
    code, orders, _ = call("GET", "/api/v1/me/orders", headers=auth, label="history")
    numbers = [o["order_number"] for o in orders]
    record("order history includes the order", order["order_number"] in numbers, str(numbers))

    code, detail, _ = call(
        "GET", f"/api/v1/me/orders/{order['order_number']}", headers=auth, label="order_detail"
    )
    record("order detail is readable", code == 200)
    record(
        "order detail states the truthful mode",
        detail["commerce_mode_at_checkout"] == "COMMERCE_TEST_MODE"
        and detail["is_test_order"] is True,
    )
    record("order detail totals match", detail["total_minor_units"] == order["total_minor_units"])

    results["data"]["journey"] = {
        "customer": TEST_CUSTOMER,
        "selected_sku": SELECTED_SKU,
        "variant_id": variant_id,
        "unit_price_minor_units": unit_price,
        "quantity": quantity,
        "stock_before": stock_before,
        "stock_after": remaining,
        "declined_idempotency_intent": decline_key,
        "successful_idempotency_intent": success_key,
        "order_number": order["order_number"],
        "commerce_mode_at_checkout": order["commerce_mode_at_checkout"],
        "total_minor_units": order["total_minor_units"],
        "currency": order["currency"],
        "cart_token_converted": True,
    }


# -------------------------------------------------- E. administration and notifications


def phase_admin_and_notifications() -> None:
    print("\n=== E. ADMINISTRATION AND NOTIFICATIONS ===")

    admin_email = os.environ.get("ADMIN_BOOTSTRAP_EMAIL", "")
    admin_password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if not admin_email or not admin_password:
        raise SystemExit("ADMIN_BOOTSTRAP_EMAIL and ADMIN_BOOTSTRAP_PASSWORD must be set")

    code, payload, _ = call(
        "POST", "/api/v1/auth/login", {"email": admin_email, "password": admin_password},
        label="admin_login",
    )
    record("administrator authenticated", code == 200, f"HTTP {code}")
    admin = {"Authorization": f"Bearer {payload['access_token']}"}

    order_number = results.get("carried", {}).get("order_number") or os.environ.get("SLICE_ORDER")
    record("order number carried from the journey", bool(order_number), str(order_number))

    # --- administration ------------------------------------------------------------
    code, orders, _ = call("GET", "/api/v1/admin/orders", headers=admin, label="admin_orders")
    record("admin can list orders", code == 200, f"HTTP {code}")
    target = next((o for o in orders if o["order_number"] == order_number), None)
    record("admin sees the test order", target is not None)
    if target is None:
        return

    record(
        "admin labels it a test order",
        target["is_test_order"] is True
        and target["commerce_mode_at_checkout"] == "COMMERCE_TEST_MODE",
        str(target["commerce_mode_at_checkout"]),
    )

    product = _hero()
    selected = _variant(product, SELECTED_SKU)
    record(
        "admin sees the synthetic inventory classification",
        selected["inventory_status"] == SYNTHETIC_STATUS,
        str(selected["inventory_status"]),
    )

    # --- the approved state transition -----------------------------------------------
    code, fulfilled, _ = call(
        "POST", f"/api/v1/admin/orders/{order_number}/fulfil", headers=admin, label="fulfil"
    )
    record("admin performs the approved transition", code == 200, f"HTTP {code}")
    record("order becomes shipped", fulfilled.get("status") == "shipped", str(fulfilled.get("status")))
    record("a tracking number is issued", bool(fulfilled.get("tracking_number")))

    # --- the customer sees it ----------------------------------------------------------
    code, payload, _ = call(
        "POST", "/api/v1/auth/login",
        {"email": TEST_CUSTOMER, "password": _test_password()},
    )
    customer = {"Authorization": f"Bearer {payload['access_token']}"}
    code, detail, _ = call(
        "GET", f"/api/v1/me/orders/{order_number}", headers=customer, label="customer_sees_state"
    )
    record("customer sees the updated state", detail["status"] == "shipped", str(detail["status"]))
    record("customer still sees the truthful mode", detail["is_test_order"] is True)

    # --- legacy catalogue isolation -------------------------------------------------------
    _, catalogue, _ = call("GET", "/api/v1/catalog/products")
    record(
        "DEDUNET catalogue carries external identity throughout",
        all(p.get("external_product_id") for p in catalogue),
    )
    legacy = [p for p in catalogue if not p.get("external_product_id")]
    record("legacy items are separately classified", not legacy, str([p["slug"] for p in legacy]))

    # --- notifications -----------------------------------------------------------------
    _notifications(order_number)


def _notifications(order_number: str) -> None:
    print("\n--- notifications ---")

    from sqlalchemy import select as _select

    sys.path.insert(0, str(BACKEND))
    from app.commerce.models import Notification

    with db_session() as session:
        rows = list(
            session.scalars(
                _select(Notification).where(Notification.subject.contains(order_number))
            ).all()
        )
        record("the order queued a lifecycle notification", len(rows) >= 1, f"{len(rows)} rows")
        if not rows:
            return

        confirmation = next((r for r in rows if r.template == "order_confirmation"), rows[0])
        record("subject carries the DEDUNET identity", "DEDUNET" in confirmation.subject,
               confirmation.subject[:70])
        record("subject marks it a test order", "[TEST ORDER]" in confirmation.subject,
               confirmation.subject[:70])
        record("notification key is stable", confirmation.template == "order_confirmation",
               confirmation.template)
        queued_id = confirmation.id
        pre_state = confirmation.status
        record("notification starts queued", pre_state == "queued", str(pre_state))
        total_before = session.scalar(_select(Notification.id).order_by(Notification.id.desc()))
        row_count_before = len(list(session.scalars(_select(Notification)).all()))

    # --- the worker claims and dispatches it -------------------------------------------
    code, out = run_cli(["dispatch-notifications"], mode="COMMERCE_TEST_MODE")
    record("worker cycle ran", code == 0, out[:140])
    dispatched = last_json(out).get("dispatched", {})
    record("worker claimed and sent", dispatched.get("sent", 0) >= 1, str(dispatched))
    record(
        "dispatch went through the console channel, not real mail",
        "[notification]" in out and os.environ.get("NOTIFICATION_CHANNEL", "console") == "console",
        "EXTERNAL_SMTP_DELIVERY_PENDING",
    )

    with db_session() as session:
        row = session.get(Notification, queued_id)
        record("final state is sent", row.status == "sent", str(row.status))
        record("dispatch was recorded", row.sent_at is not None)
        record("claim metadata is cleaned up",
               not row.claim_token and row.claim_expires_at is None and row.claimed_at is None,
               f"claim_token={row.claim_token!r} claimed_at={row.claimed_at} "
               f"expires={row.claim_expires_at}")
        record("the row was NOT deleted", row is not None)
        row_count_after = len(list(session.scalars(_select(Notification)).all()))
        record("no notification row was deleted", row_count_after >= row_count_before,
               f"{row_count_before} -> {row_count_after}")

        results["data"]["notification"] = {
            "id": row.id,
            "template": row.template,
            "subject": row.subject,
            "status_before": pre_state,
            "status_after": row.status,
            "attempts": row.attempts,
            "channel": os.environ.get("NOTIFICATION_CHANNEL", "console"),
            "claim_token_after": row.claim_token,
            "external_delivery": "EXTERNAL_SMTP_DELIVERY_PENDING",
        }


# --------------------------------------------------------------- F. session behaviour


def phase_session() -> None:
    print("\n=== F. SESSION BEHAVIOUR ===")

    code, _, _ = call(
        "GET", "/api/v1/me/orders", headers={"Authorization": "Bearer forged.invalid.token"}
    )
    record("forged session returns 401", code == 401, f"HTTP {code}")

    code, _, _ = call("GET", "/api/v1/me/orders", headers={"Authorization": "Bearer "})
    record("empty bearer returns 401", code == 401, f"HTTP {code}")

    # A structurally valid token with a broken signature must be rejected before its
    # payload is parsed, so a forged expiry cannot be honoured.
    import base64

    forged_payload = base64.urlsafe_b64encode(
        json.dumps({"sub": 1, "exp": 9999999999}).encode()
    ).decode().rstrip("=")
    code, _, _ = call(
        "GET", "/api/v1/me/orders",
        headers={"Authorization": f"Bearer {forged_payload}.not-a-real-signature"},
    )
    record("forged signature with a valid shape returns 401", code == 401, f"HTTP {code}")

    code, _, _ = call("GET", "/api/v1/me/orders")
    record("missing session returns 401", code == 401, f"HTTP {code}")

    code, _, hdrs = call("GET", "/ready", label="session_ready")
    record("/ready remains 200", code == 200)
    record("correlation id present on an unauthenticated call",
           bool(hdrs.get("X-Correlation-ID")), str(hdrs.get("X-Correlation-ID"))[:20])


# --------------------------------------------------- H. return to preview and confirm


def phase_cleanup() -> None:
    print("\n=== H. RETURN TO PREVIEW ===")

    product = _hero()
    selected = _variant(product, SELECTED_SKU)
    record(
        "selected SKU is back to zero",
        selected["available"] == 0,
        f"available={selected['available']}",
    )
    record(
        "selected SKU is back to the prototype status",
        selected["inventory_status"] == PROTOTYPE_STATUS and selected["sellable"] is False,
        str(selected["inventory_status"]),
    )
    record(
        "no DEDUNET variant carries synthetic stock",
        all(v["inventory_status"] == PROTOTYPE_STATUS for v in product["variants"]),
    )

    code, payload, _ = call(
        "POST", "/api/v1/cart/items", {"variant_id": selected["id"], "quantity": 1},
        label="cleanup_cart",
    )
    record("cart-add is blocked again", code == 409, f"HTTP {code}")
    record(
        "refusal names brand preview",
        isinstance(payload, dict) and "brand preview" in str(payload.get("detail", "")),
        str(payload.get("detail", ""))[:80] if isinstance(payload, dict) else "",
    )

    code, _, _ = call(
        "POST", "/api/v1/checkout",
        {"payment_method_token": "pm_success", "idempotency_key": "cleanup-must-fail"},
        headers={"X-Cart-Token": "no-such-cart"},
    )
    record("checkout is blocked again", code in (400, 401, 409), f"HTTP {code}")

    record("catalogue still lists 5 DEDUNET products",
           len(call("GET", "/api/v1/catalog/products")[1]) == 5)
    record("/ready 200", call("GET", "/ready")[0] == 200)
    record("/health 200", call("GET", "/health")[0] == 200)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        required=True,
        choices=[
            "truth", "preview", "ratelimit",
            "inventory", "preview-with-stock", "journey", "admin", "session", "cleanup",
        ],
    )
    parser.add_argument("--out")
    args = parser.parse_args()

    results["phase"] = args.phase
    results["generated_at"] = datetime.now(timezone.utc).isoformat()

    {
        "truth": phase_default_truth,
        "preview": phase_preview,
        "ratelimit": phase_rate_limit,
        "inventory": phase_inventory,
        "preview-with-stock": phase_preview_with_stock,
        "journey": phase_journey,
        "admin": phase_admin_and_notifications,
        "session": phase_session,
        "cleanup": phase_cleanup,
    }[args.phase]()

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
