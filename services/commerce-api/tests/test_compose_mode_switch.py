"""The commerce mode must be overridable in every deployed topology.

`modes.current_mode()` reads `COMMERCE_MODE` from the process environment, and every test
of it passes in-process because pytest can set that variable freely. The deployed stacks
could not: Docker Compose forwards no arbitrary shell variable into a container, so unless
a service declares the key, `COMMERCE_MODE=... docker compose up -d api` sets it in the
operator's shell and nowhere else.

That is exactly what happened. `docker-compose.staging.yml` declared `APP_ENV`,
`SEED_DEMO_DATA`, `RATE_LIMIT_ENABLED` and the rest — but not `COMMERCE_MODE`. Measured on
the running stack before the fix:

    container COMMERCE_MODE=[]        after asking for BRAND_PREVIEW_MODE
    GET  /api/v1/catalog/products     6 products, including a legacy fixture item
    POST /api/v1/cart/items           HTTP 200 — the item went into a bag

A tester following the acceptance script would have believed they were in brand preview
while the store was in commerce-test mode and purchasable. The silence is the danger: the
command succeeds, the container restarts, and nothing reports that the request was ignored.

After the fix, the same commands give `[BRAND_PREVIEW_MODE]`, 5 products, and HTTP 409.

These assertions are static because the property is static: a key that is absent from the
compose file can never be overridden at runtime, whatever the application does with it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
COMPOSE_FILES = {
    "local": REPO / "docker-compose.yml",
    "staging": REPO / "docker-compose.staging.yml",
}


def api_environment_block(compose_text: str) -> str:
    """The `api` service's `environment:` block, as raw text.

    Deliberately crude rather than a YAML dependency: the suite carries no YAML parser and
    adding one to assert on six lines of configuration would be the larger change.
    """

    api = re.search(r"\n  api:\n(.*?)(?=\n  [a-z0-9_-]+:\n|\Z)", compose_text, re.S)
    assert api, "no `api` service found in the compose file"
    env = re.search(r"\n    environment:\n(.*?)(?=\n    [a-z_]+:|\Z)", api.group(1), re.S)
    assert env, "the `api` service declares no `environment:` block"
    return env.group(1)


@pytest.mark.parametrize("name", sorted(COMPOSE_FILES))
def test_compose_declares_commerce_mode_so_it_can_be_overridden(name):
    """Undeclared means unoverridable. This is the whole defect."""

    block = api_environment_block(COMPOSE_FILES[name].read_text(encoding="utf-8"))

    assert "COMMERCE_MODE:" in block, (
        f"{COMPOSE_FILES[name].name} does not declare COMMERCE_MODE for the api service, so "
        "`COMMERCE_MODE=... docker compose up -d api` sets it in the operator's shell and "
        "nowhere else. The mode silently stays at the default."
    )


@pytest.mark.parametrize("name", sorted(COMPOSE_FILES))
def test_commerce_mode_default_is_empty_not_a_literal_mode(name):
    """`${COMMERCE_MODE:-}`, not `${COMMERCE_MODE:-COMMERCE_TEST_MODE}`.

    An empty value is falsy in `modes.current_mode()`, which then applies `DEFAULT_MODE`.
    Hard-coding a literal here would fork the default: one value in `modes.py` and another
    in each compose file, free to drift apart.
    """

    block = api_environment_block(COMPOSE_FILES[name].read_text(encoding="utf-8"))
    declared = re.search(r"COMMERCE_MODE:\s*(\S+)", block)

    assert declared, "COMMERCE_MODE is declared but has no value expression"
    assert declared.group(1) == "${COMMERCE_MODE:-}", (
        f"expected an empty-defaulting passthrough so modes.DEFAULT_MODE stays the single "
        f"source of the default; found {declared.group(1)!r}"
    )


def test_empty_commerce_mode_falls_back_to_the_application_default(monkeypatch):
    """The behaviour the empty default relies on, asserted rather than assumed."""

    from app.commerce import modes

    monkeypatch.setenv("COMMERCE_MODE", "")
    assert modes.current_mode() == modes.DEFAULT_MODE

    monkeypatch.setenv("COMMERCE_MODE", "BRAND_PREVIEW_MODE")
    assert modes.current_mode() == modes.BRAND_PREVIEW


def test_public_commerce_mode_is_still_refused_however_it_is_supplied(monkeypatch):
    """Making the mode overridable must not make public commerce reachable.

    This is the risk the fix creates: a switch that previously did nothing now works, so
    the refusal it could reach has to be re-proven.
    """

    from app.commerce import modes

    for spelling in ("PUBLIC_COMMERCE_MODE", "public_commerce_mode", "  Public_Commerce_Mode  "):
        monkeypatch.setenv("COMMERCE_MODE", spelling)
        with pytest.raises(modes.CommerceModeError, match="cannot be enabled by configuration"):
            modes.current_mode()
