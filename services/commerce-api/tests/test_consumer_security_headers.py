"""The document security header contract for the consumer client.

WHY THIS FILE EXISTS.

nginx does not inherit `add_header` from an outer scope into a location that declares an
`add_header` of its own. The consumer client declared the four security headers once at
server level, which looked correct and was not: `location = /index.html` and
`location /assets/` each set `Cache-Control`, so both discarded all four. Because every
route in the SPA is served from `index.html` through the history fallback, **every HTML
document the application served carried none of them** — no `X-Frame-Options`, so the app
was framable. `/admin`, which declares no header of its own, kept all four and looked like
evidence the contract worked.

That regression reached staging in the cutover at `455ac09` and is recorded as F-1 in
`evidence/staging-cutover/STAGING_CUTOVER_EXECUTION.md`.

THE INVARIANT THESE TESTS PIN:

    every `location` block that declares its own `add_header` must ALSO include
    `security-headers.conf`.

That is the property a future edit can break silently. Someone adding a cache rule to a new
location is not thinking about clickjacking, and nothing in nginx warns them — the headers
simply stop being sent. These tests fail instead.

They are STATIC assertions about configuration, deliberately. They are not a substitute for
asserting the headers on a real HTTP response from the deployed application, which the
Playwright suite does in `e2e/security-headers.spec.ts`. Config can be right while a
deployment is wrong; a response can be right today and regress on the next edit. Both.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "apps").is_dir():
            return candidate
    raise RuntimeError(f"no apps/ directory above {here}; run from a full checkout")


REPO_ROOT = _repo_root()
TEMPLATE = REPO_ROOT / "apps" / "consumer" / "default.conf.template"
CONTRACT = REPO_ROOT / "apps" / "consumer" / "security-headers.conf"
LEGACY_CONF = REPO_ROOT / "apps" / "web" / "nginx.conf"
DOCKERFILE = REPO_ROOT / "apps" / "consumer" / "Dockerfile"

INCLUDE_DIRECTIVE = "include /etc/nginx/security-headers.conf;"

# The contract. The first three are exactly what the classic client served and what the
# owner accepted; Referrer-Policy was already declared in the consumer template before the
# repair. Nothing here was invented while fixing F-1.
REQUIRED_HEADERS = {
    "X-Robots-Tag": "noindex, nofollow",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _location_blocks(conf: str) -> list[tuple[str, str]]:
    """Return (header_line, body) for each `location` block, braces balanced.

    A regex cannot do this correctly once a block nests, so the depth is counted. The
    consumer template is small; being right matters more than being clever.
    """

    conf = _strip_comments(conf)
    blocks: list[tuple[str, str]] = []
    for match in re.finditer(r"^\s*(location[^\n{]*)\{", conf, re.M):
        start = match.end()
        depth = 1
        index = start
        while index < len(conf) and depth:
            if conf[index] == "{":
                depth += 1
            elif conf[index] == "}":
                depth -= 1
            index += 1
        blocks.append((match.group(1).strip(), conf[start : index - 1]))
    return blocks


def test_the_contract_file_exists_and_declares_every_required_header():
    assert CONTRACT.is_file(), f"{CONTRACT} is missing; the template includes it"
    body = CONTRACT.read_text(encoding="utf-8")
    for name, value in REQUIRED_HEADERS.items():
        assert re.search(
            rf'^\s*add_header\s+{re.escape(name)}\s+"{re.escape(value)}"\s+always\s*;',
            body,
            re.M,
        ), f"{name}: \"{value}\" always; is missing from security-headers.conf"


def test_every_required_header_is_marked_always():
    """`always` is not decoration.

    Without it nginx omits the header on error responses -- a 404 or a 500 would ship
    unprotected, and an error page is precisely where injected content tends to land.
    """

    body = _strip_comments(CONTRACT.read_text(encoding="utf-8"))
    for line in body.splitlines():
        if line.strip().startswith("add_header"):
            assert line.rstrip().endswith("always;"), f"add_header without `always`: {line.strip()}"


def test_server_scope_includes_the_contract():
    """Locations that add no header of their own inherit from here -- `/` and `/admin`."""

    conf = _strip_comments(TEMPLATE.read_text(encoding="utf-8"))
    for block_header, body in _location_blocks(conf):
        conf = conf.replace(body, "")
    assert INCLUDE_DIRECTIVE in conf, "the server block does not include security-headers.conf"


# The ONE location exempt from the include rule, and why.
#
# `/api/` proxies the commerce API, which sets its own baseline security headers in
# app/main.py -- including `Referrer-Policy: no-referrer`, STRICTER than the document
# policy. nginx `add_header` appends rather than replaces, so including the contract there
# emitted Referrer-Policy twice and the spec takes the LAST valid value: the proxy silently
# downgraded the API's deliberate no-referrer. Measured on a real response during the F-1
# repair, not theorised.
#
# The exemption is named here so it stays a decision. Anything added to this set needs the
# same kind of reason.
EXEMPT_LOCATIONS = {"location /api/"}


def test_the_api_location_does_not_override_the_upstream_referrer_policy():
    """The exemption, asserted rather than trusted.

    If someone adds the contract include to /api/, the API's stricter `no-referrer` is
    downgraded on every JSON response. That is a weakening, and it must fail here.
    """

    blocks = {h: b for h, b in _location_blocks(TEMPLATE.read_text(encoding="utf-8"))}
    api = next((b for h, b in blocks.items() if h.replace(" ", "") == "location/api/"), None)
    assert api is not None, "no `location /api/` block found in the template"
    assert INCLUDE_DIRECTIVE not in api, (
        "the /api location includes the document header contract, which appends a second "
        "Referrer-Policy and downgrades the API's stricter no-referrer. Remove it."
    )


def test_the_api_still_sets_its_own_baseline_security_headers():
    """The other half of the exemption: it is only safe while the API does this itself."""

    main = (REPO_ROOT / "services" / "commerce-api" / "app" / "main.py").read_text(
        encoding="utf-8"
    )
    for header, value in (
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "no-referrer"),
    ):
        assert f'response.headers["{header}"] = "{value}"' in main, (
            f"the API no longer sets {header}: {value}, so exempting /api/ from the nginx "
            "contract now leaves API responses unprotected"
        )


def test_no_location_silently_drops_the_document_security_headers():
    """THE REGRESSION GUARD. This is the test that would have caught F-1.

    Any location that declares an `add_header` has opted out of the inherited ones, whether
    or not whoever wrote it realised. It must opt back in explicitly, or be a named
    exemption with a recorded reason.
    """

    offenders = []
    for block_header, body in _location_blocks(TEMPLATE.read_text(encoding="utf-8")):
        if block_header in EXEMPT_LOCATIONS:
            continue
        declares_own = re.search(r"^\s*add_header\s", _strip_comments(body), re.M)
        if not declares_own:
            continue
        if INCLUDE_DIRECTIVE not in body:
            offenders.append(block_header)

    assert not offenders, (
        "these locations declare add_header and therefore DISCARD the server-level "
        "security headers, without including them back:\n  "
        + "\n  ".join(offenders)
        + f"\n\nAdd `{INCLUDE_DIRECTIVE}` inside each. See apps/consumer/security-headers.conf."
    )


def test_the_document_location_includes_the_contract():
    """`= /index.html` specifically: every SPA route is served from it."""

    blocks = dict(_location_blocks(TEMPLATE.read_text(encoding="utf-8")))
    document = next((b for h, b in blocks.items() if h.replace(" ", "").startswith("location=/index.html")), None)
    assert document is not None, "no `location = /index.html` block found in the template"
    assert INCLUDE_DIRECTIVE in document, (
        "the index.html location does not include the security headers -- every route in "
        "the SPA is served from this file, so this is every document on the site"
    )


def test_cache_control_behaviour_is_preserved_alongside_the_headers():
    """The repair must not have traded caching correctness for headers.

    index.html must stay uncached (it names the hashed bundle) and hashed assets must stay
    immutable. A repair that silently dropped either would be a different regression.
    """

    blocks = {h.replace(" ", ""): b for h, b in _location_blocks(TEMPLATE.read_text(encoding="utf-8"))}
    document = blocks.get("location=/index.html", "")
    assert "no-store" in document, "index.html must not be cacheable"

    assets = next((b for h, b in blocks.items() if h.startswith("location/assets/")), "")
    assert "immutable" in assets, "hashed assets must stay immutably cacheable"


def test_the_contract_is_a_superset_of_what_the_classic_client_served():
    """No protection the accepted legacy staging client sent may be missing here.

    This is the parity assertion for the regression: the cutover replaced a client that
    served three of these, and the replacement must not serve fewer.
    """

    legacy = _strip_comments(LEGACY_CONF.read_text(encoding="utf-8"))
    legacy_headers = set(re.findall(r"add_header\s+([A-Za-z-]+)\s", legacy))
    assert legacy_headers, "parsed no add_header from the classic client; the parser is wrong"
    missing = legacy_headers - set(REQUIRED_HEADERS)
    assert not missing, f"the classic client served headers the consumer contract omits: {missing}"


def test_the_contract_ships_in_the_image_from_a_read_only_layer():
    """It must be COPYed into /etc/nginx, not written into conf.d.

    conf.d is a tmpfs at runtime -- the entrypoint renders the template into it -- and the
    container root filesystem is read-only. A contract file expected to appear in conf.d
    would simply not exist at start, and nginx would fail to load the config.
    """

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(
        r"^COPY\s+apps/consumer/security-headers\.conf\s+/etc/nginx/security-headers\.conf\s*$",
        dockerfile,
        re.M,
    ), "the Dockerfile does not COPY security-headers.conf to /etc/nginx/"


@pytest.mark.parametrize("name", sorted(REQUIRED_HEADERS))
def test_no_header_is_defined_twice_in_the_template(name: str):
    """One definition, in the contract file.

    Re-declaring a value inline is how four headers drift into four different values across
    five locations. The template may include the contract; it may not restate it.
    """

    template = _strip_comments(TEMPLATE.read_text(encoding="utf-8"))
    assert f"add_header {name}" not in template, (
        f"{name} is declared inline in the template; include security-headers.conf instead"
    )
