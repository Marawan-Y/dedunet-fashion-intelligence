"""The consumer's look slugs must match the authoritative registry.

WHY THIS GUARD EXISTS.

The Look domain now lives in the database and is what saved looks point at. The consumer
still RENDERS look copy from `apps/consumer/src/features/content.ts`, because rewiring the
Looks presentation was not needed to make saving real and the foundation is locked.

That leaves two sources for the same four looks, and exactly one way for it to hurt: if
someone renames a slug in `content.ts`, the Looks page keeps working, the save button keeps
rendering, and every save silently 404s -- because the slug the client sends no longer
exists in `looks`. The failure is invisible in review and only appears as "saving is broken
for looks" from a user.

So the two are asserted equal. The duplication is recorded as a known limitation; this test
is what makes it a survivable one rather than a trap.
"""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "apps").is_dir():
            return candidate
    raise RuntimeError(f"no apps/ directory above {here}")


def _frontend_look_slugs() -> list[str]:
    content = (
        _repo_root() / "apps" / "consumer" / "src" / "features" / "content.ts"
    ).read_text(encoding="utf-8")
    start = content.index("export const LOOKS")
    end = content.index("\nexport ", start + 10)
    block = content[start:end]
    return re.findall(r'slug: "([a-z0-9-]+)"', block)


def test_the_frontend_and_the_registry_agree_on_every_look_slug():
    from app.commerce.look_registry import CURATED_LOOKS

    frontend = sorted(_frontend_look_slugs())
    registry = sorted(spec["slug"] for spec in CURATED_LOOKS)

    assert frontend == registry, (
        "the consumer's look slugs and the authoritative registry have diverged.\n"
        f"  consumer: {frontend}\n"
        f"  registry: {registry}\n"
        "A slug that exists in one and not the other renders a save control that 404s."
    )


def test_every_frontend_look_references_products_the_registry_also_uses():
    """A look composed of different garments in the two places is the same class of drift."""

    from app.commerce.look_registry import CURATED_LOOKS

    content = (
        _repo_root() / "apps" / "consumer" / "src" / "features" / "content.ts"
    ).read_text(encoding="utf-8")
    start = content.index("export const LOOKS")
    end = content.index("\nexport ", start + 10)
    frontend_products = set(re.findall(r'productSlug: "([a-z0-9-]+)"', content[start:end]))

    registry_products = {
        item["product_slug"] for spec in CURATED_LOOKS for item in spec["items"]
    }
    assert frontend_products == registry_products, (
        f"look composition diverged.\n  consumer: {sorted(frontend_products)}\n"
        f"  registry: {sorted(registry_products)}"
    )
