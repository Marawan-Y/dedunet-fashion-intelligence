"""Integrity gate for the immutable DEDUNET Side A delivery.

This is the precondition for every later integration step. It is READ-ONLY: it never
writes to, repairs or normalises the incoming package. If any expected value differs the
integration must stop rather than "fix" evidence it does not own.

Every expected value is asserted EXACTLY. A count that drifts is a failure even when
nothing looks broken, because a silently smaller catalogue is precisely the defect an
importer would otherwise carry into the database.

Exit 0 = package verified. Exit 1 = DEDUNET_HANDOFF_INTEGRITY_FAILED.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "handoffs" / "incoming" / "side-a" / "DEDUNET_Platform_Integration_v1"

EXPECTED_CHECKSUMS = 54
EXPECTED_PRODUCTS = 5
EXPECTED_VARIANTS = 62
EXPECTED_SKUS = 62
EXPECTED_ASSETS = 31

# Stable Side A product identifiers. Position, filename and insertion order are never
# identity; these strings are.
EXPECTED_PRODUCT_IDS = {"DDN-TS01", "DDN-SH01", "DDN-TR01", "DDN-OS01", "DDN-SC01"}

failures: list[str] = []
notes: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}" + (f" - {detail}" if detail else ""))
    if not ok:
        failures.append(f"{label}: {detail}")
    return ok


def read_csv(path: Path) -> list[dict[str, str]]:
    # utf-8-sig: a BOM would otherwise become part of the first column name and every
    # lookup against that column would silently miss.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


# ------------------------------------------------------------------ 1. checksum manifest

def verify_checksums() -> None:
    manifest = PKG / "CHECKSUMS_SHA256.txt"
    if not check("manifest present", manifest.is_file(), str(manifest)):
        return

    lines = [ln for ln in manifest.read_text(encoding="utf-8").splitlines() if ln.strip()]
    check(
        "manifest entry count",
        len(lines) == EXPECTED_CHECKSUMS,
        f"expected {EXPECTED_CHECKSUMS}, found {len(lines)}",
    )

    verified = missing = mismatched = 0
    for line in lines:
        digest, _, rel = line.partition("  ")
        rel = rel.strip() or line.split()[-1]
        target = PKG / rel
        if not target.is_file():
            missing += 1
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual == digest.strip().lower():
            verified += 1
        else:
            mismatched += 1
            failures.append(f"checksum mismatch: {rel}")

    check(
        "checksums verified",
        verified == len(lines) and missing == 0 and mismatched == 0,
        f"{verified}/{len(lines)} verified, {missing} missing, {mismatched} mismatched",
    )

    # A file present in the package but absent from the manifest is unsigned content.
    on_disk = {
        p.relative_to(PKG).as_posix()
        for p in PKG.rglob("*")
        if p.is_file() and p.name != "CHECKSUMS_SHA256.txt"
    }
    listed = {(ln.split(maxsplit=1)[1]).strip() for ln in lines}
    unlisted = sorted(on_disk - listed)
    check("no unmanifested files", not unlisted, f"unlisted: {unlisted[:5]}")


# --------------------------------------------------------------------- 2. product data

def verify_products() -> list[dict]:
    path = PKG / "data" / "brand-prototype" / "product-master.json"
    if not check("product-master.json present", path.is_file()):
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        check("product-master.json parses", False, str(exc))
        return []
    check("product-master.json parses", True)

    products = raw if isinstance(raw, list) else raw.get("products", [])
    check(
        "product count",
        len(products) == EXPECTED_PRODUCTS,
        f"expected {EXPECTED_PRODUCTS}, found {len(products)}",
    )

    id_field = None
    for candidate in ("product_id", "id", "sku_prefix", "code"):
        if products and candidate in products[0]:
            id_field = candidate
            break
    if not check("product identifier field found", id_field is not None, f"keys={list(products[0].keys()) if products else []}"):
        return products
    notes.append(f"product identifier field: {id_field}")

    ids = [str(p[id_field]).strip() for p in products]
    check("product identifiers unique", len(ids) == len(set(ids)), f"{len(ids)} ids, {len(set(ids))} unique")
    check(
        "expected DDN product identifiers",
        set(ids) == EXPECTED_PRODUCT_IDS,
        f"found {sorted(ids)}",
    )

    csv_rows = read_csv(PKG / "data" / "brand-prototype" / "product-master.csv")
    check(
        "product-master.csv row count",
        len(csv_rows) == EXPECTED_PRODUCTS,
        f"expected {EXPECTED_PRODUCTS}, found {len(csv_rows)}",
    )
    return products


# --------------------------------------------------------------------- 3. variant data

def verify_variants(products: list[dict]) -> list[dict]:
    path = PKG / "data" / "brand-prototype" / "variant-master.csv"
    if not check("variant-master.csv present", path.is_file()):
        return []

    rows = read_csv(path)
    check(
        "variant count",
        len(rows) == EXPECTED_VARIANTS,
        f"expected {EXPECTED_VARIANTS}, found {len(rows)}",
    )

    headers = list(rows[0].keys()) if rows else []
    notes.append(f"variant columns: {headers}")

    sku_col = next((c for c in headers if c.strip().lower() in ("sku", "variant_sku")), None)
    pid_col = next(
        (c for c in headers if c.strip().lower() in ("product_id", "productid", "product")), None
    )
    if not check("variant SKU column found", sku_col is not None, f"headers={headers}"):
        return rows
    if not check("variant product-id column found", pid_col is not None, f"headers={headers}"):
        return rows

    skus = [r[sku_col].strip() for r in rows]
    check("SKU count", len(skus) == EXPECTED_SKUS, f"expected {EXPECTED_SKUS}, found {len(skus)}")
    duplicates = sorted({s for s in skus if skus.count(s) > 1})
    check("SKUs unique", len(set(skus)) == EXPECTED_SKUS and not duplicates, f"duplicates: {duplicates[:5]}")

    # Orphan check: every variant must attach to a product that actually exists.
    product_ids = set()
    for p in products:
        for candidate in ("product_id", "id", "sku_prefix", "code"):
            if candidate in p:
                product_ids.add(str(p[candidate]).strip())
                break
    orphans = sorted({r[pid_col].strip() for r in rows if r[pid_col].strip() not in product_ids})
    check("no orphan variants", not orphans, f"unknown product ids: {orphans}")

    per_product: dict[str, int] = {}
    for r in rows:
        per_product[r[pid_col].strip()] = per_product.get(r[pid_col].strip(), 0) + 1
    notes.append(f"variants per product: {dict(sorted(per_product.items()))}")
    check("every product has variants", len(per_product) == EXPECTED_PRODUCTS, f"{len(per_product)} products carry variants")

    # Duplicate option combinations within one product would make two rows indistinguishable.
    size_col = next((c for c in headers if c.strip().lower() in ("size", "size_code")), None)
    colour_col = next(
        (c for c in headers if c.strip().lower() in ("color", "colour", "color_name", "colour_name")),
        None,
    )
    if size_col and colour_col:
        combos = [
            (r[pid_col].strip(), r[size_col].strip(), r[colour_col].strip()) for r in rows
        ]
        dupes = sorted({c for c in combos if combos.count(c) > 1})
        check("no duplicate option combinations", not dupes, f"duplicates: {dupes[:5]}")
    else:
        notes.append(f"option-combination check skipped: size={size_col} colour={colour_col}")
    return rows


# ----------------------------------------------------------------------- 4. asset data

def verify_assets() -> list[dict]:
    path = PKG / "data" / "brand-prototype" / "asset-register.csv"
    if not check("asset-register.csv present", path.is_file()):
        return []

    rows = read_csv(path)
    check(
        "registered asset count",
        len(rows) == EXPECTED_ASSETS,
        f"expected {EXPECTED_ASSETS}, found {len(rows)}",
    )

    headers = list(rows[0].keys()) if rows else []
    notes.append(f"asset columns: {headers}")
    path_col = next(
        (c for c in headers if "path" in c.strip().lower() or "file" in c.strip().lower()), None
    )
    if not check("asset path column found", path_col is not None, f"headers={headers}"):
        return rows

    missing = []
    for r in rows:
        rel = r[path_col].strip().lstrip("/")
        if not (PKG / rel).is_file():
            missing.append(rel)
    check("every registered asset exists", not missing, f"missing: {missing[:5]}")

    ids = [r[headers[0]].strip() for r in rows]
    check("asset identifiers unique", len(ids) == len(set(ids)), f"{len(ids)} ids, {len(set(ids))} unique")
    return rows


# ------------------------------------------------------------------- 5. SVG/XML validity

def verify_svgs() -> None:
    svgs = sorted(PKG.rglob("*.svg"))
    bad = []
    for svg in svgs:
        try:
            ET.parse(svg)
        except ET.ParseError as exc:
            bad.append(f"{svg.relative_to(PKG).as_posix()}: {exc}")
    check("all SVGs parse as XML", not bad, f"{len(svgs)} files; invalid: {bad[:3]}")
    notes.append(f"svg files: {len(svgs)}")


# ------------------------------------------------------------------------ 6. JSON parsing

def verify_json() -> None:
    files = sorted(PKG.rglob("*.json"))
    bad = []
    for f in files:
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            bad.append(f"{f.relative_to(PKG).as_posix()}: {exc}")
    check("all JSON parses", not bad, f"{len(files)} files; invalid: {bad[:3]}")
    notes.append(f"json files: {len(files)}")


# ----------------------------------------------------------- 7. no legacy brand leakage

def verify_no_legacy_brand() -> None:
    pattern = re.compile(r"\bMERET\b|\bMERYT\b", re.IGNORECASE)
    offenders = []
    for f in PKG.rglob("*"):
        if not f.is_file() or f.suffix.lower() in {".png", ".zip"}:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if pattern.search(text):
            offenders.append(f.relative_to(PKG).as_posix())
    check("no MERET/MERYT inside the Side A package", not offenders, f"offenders: {offenders[:5]}")


def main() -> int:
    print(f"Side A package: {PKG.relative_to(ROOT).as_posix()}\n")
    verify_checksums()
    print()
    products = verify_products()
    print()
    verify_variants(products)
    print()
    verify_assets()
    print()
    verify_json()
    verify_svgs()
    verify_no_legacy_brand()

    print("\n--- notes ---")
    for n in notes:
        print(f"  {n}")

    print()
    if failures:
        print(f"FAILURES: {len(failures)}")
        for f in failures:
            print(f"  - {f}")
        print("\nDEDUNET_HANDOFF_INTEGRITY_FAILED")
        return 1

    print("RESULT: DEDUNET_HANDOFF_INTEGRITY_VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
