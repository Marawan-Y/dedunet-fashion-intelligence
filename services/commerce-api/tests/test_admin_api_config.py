"""Where the operations portal resolves its API, executed as JavaScript.

Human acceptance testing found the admin portal unusable in staging: it loaded, then every
request died as "Failed to fetch" before anyone could sign in. Reproduced —

    page origin          http://127.0.0.1:13080
    computed API base    http://127.0.0.1:18000   <- nothing listens there
    config seam          undefined                <- admin/config.js returned 404
    login request        FAILED: Failed to fetch

— because `admin.js` resolved its base inline against a hard-coded `:18000` and its markup
loaded no `config.js`. Staging publishes the API on 18080. The storefront already had this
seam; the admin was never given one.

These tests run the real `apps/admin/api-config.js` through Node. Asserting on the SOURCE
TEXT of a URL builder proves nothing about the URLs it builds, which is the entire shape of
this defect: the inline expression looked perfectly reasonable and pointed nowhere.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ADMIN = REPO / "apps" / "admin"
WEB = REPO / "apps" / "web"
MODULE = ADMIN / "api-config.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

STAGING_API = "http://127.0.0.1:18080"


def run_js(expression: str) -> object:
    """Evaluate an expression against the real module and return the parsed result."""

    script = (
        f"const m = require({json.dumps(str(MODULE))});"
        f"process.stdout.write(JSON.stringify({expression}));"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(ADMIN), env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def run_js_expecting_throw(expression: str) -> str:
    """Return the thrown message. Fails the test if nothing is thrown."""

    script = (
        f"const m = require({json.dumps(str(MODULE))});"
        f"try {{ const v = {expression};"
        f"  process.stdout.write('NO_THROW:' + String(v)); }}"
        f"catch (e) {{ process.stdout.write('THREW:' + e.message); }}"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(ADMIN), env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert completed.returncode == 0, completed.stderr
    out = completed.stdout
    assert out.startswith("THREW:"), f"expected a rejection, got {out!r}"
    return out[len("THREW:"):]


# ------------------------------------------------------- the seven required properties


def test_runtime_config_overrides_the_development_fallback():
    """What config.js sets must win over the built-in default."""

    resolved = run_js(f'm.apiBase({{ DEDUNET_API_BASE: "{STAGING_API}", location: {{ protocol: "http:", hostname: "127.0.0.1" }} }})')

    assert resolved == STAGING_API
    assert ":18000" not in resolved


def test_staging_configuration_resolves_to_the_staging_api_origin():
    """The exact defect: the portal on :13080 must reach the API on :18080."""

    resolved = run_js(
        'm.apiBase({ DEDUNET_API_BASE: "http://127.0.0.1:18080",'
        '            location: { protocol: "http:", hostname: "127.0.0.1", port: "13080" } })'
    )

    assert resolved == "http://127.0.0.1:18080"


def test_split_origin_admin_and_api():
    """Admin and API on different hosts entirely; the admin origin must not leak in."""

    resolved = run_js(
        'm.apiBase({ DEDUNET_API_BASE: "https://api.internal.example",'
        '            location: { protocol: "http:", hostname: "admin.internal.example", port: "13080" } })'
    )

    assert resolved == "https://api.internal.example"
    assert "admin.internal.example" not in resolved


def test_missing_configuration_uses_only_the_documented_development_fallback():
    """No config: this page's host on the documented development port, nothing else."""

    resolved = run_js('m.apiBase({ location: { protocol: "http:", hostname: "127.0.0.1", port: "13080" } })')
    assert resolved == "http://127.0.0.1:18000"

    port = run_js("m.DEV_API_PORT")
    assert port == 18000, "the documented development default changed silently"


def test_localhost_and_loopback_ip_are_each_preserved():
    """Distinct origins to CORS, so the spelling the operator browsed with must survive."""

    for hostname in ("localhost", "127.0.0.1"):
        resolved = run_js(f'm.apiBase({{ location: {{ protocol: "http:", hostname: "{hostname}" }} }})')
        assert resolved == f"http://{hostname}:18000", resolved

    # And an https page must not be downgraded to http.
    secure = run_js('m.apiBase({ location: { protocol: "https:", hostname: "localhost" } })')
    assert secure == "https://localhost:18000"


@pytest.mark.parametrize(
    "bad",
    [
        '"127.0.0.1:18080"',        # no scheme
        '"ftp://127.0.0.1:18080"',  # wrong scheme
        '"http://"',                # no host
        '"not a url at all"',
        '"http://host/with/path"',  # an origin, not a path
        '"  "',
        '"javascript:alert(1)"',
    ],
)
def test_malformed_configuration_is_rejected_clearly(bad):
    """Rejected loudly, never silently ignored.

    Silently falling back after a typo is how a portal ends up pointing at the wrong host
    while looking configured — which is exactly the failure being closed here.
    """

    message = run_js_expecting_throw(f"m.apiBase({{ DEDUNET_API_BASE: {bad} }})")
    assert "not a usable absolute origin" in message, message


def test_trailing_slashes_are_normalised():
    """A double slash in the built URL is a 404 the operator cannot explain."""

    for suffix in ("/", "///"):
        assert run_js(f'm.apiBase({{ DEDUNET_API_BASE: "{STAGING_API}{suffix}" }})') == STAGING_API


# --------------------------------------------------- the request actually targets it


def test_admin_login_request_targets_the_configured_api_base():
    """admin.js must build its login URL from the seam, not from the page origin."""

    source = (ADMIN / "admin.js").read_text(encoding="utf-8")

    assert "window.DedunetAdminConfig.apiBase()" in source, (
        "admin.js does not resolve its API base through the shared seam"
    )
    # Every request goes through one helper that prefixes API_BASE.
    assert re.search(r"fetch\(\s*`\$\{API_BASE\}\$\{path\}`", source), (
        "admin.js does not prefix its requests with API_BASE"
    )
    assert "/api/v1/auth/login" in source


def test_no_deployment_port_is_scattered_through_admin_logic():
    """18080 must appear nowhere in application code — it comes from the build argument.

    18000 is permitted exactly once, in api-config.js, as the documented development
    default. Anywhere else it is a hard-coded deployment assumption.
    """

    def strip_comments(text: str) -> str:
        """Remove block and line comments. A prose mention of a port is not a dependency."""

        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return re.sub(r"^\s*//.*$", "", text, flags=re.M)

    offenders = []
    for path in sorted(ADMIN.glob("*.js")):
        code = strip_comments(path.read_text(encoding="utf-8"))
        if "18080" in code:
            offenders.append(f"{path.name}: contains the staging port 18080 in code")
        if "18000" in code:
            # Permitted exactly once, as the named development constant.
            if path.name != "api-config.js" or code.count("18000") != 1:
                offenders.append(f"{path.name}: hard-codes the development port 18000")
            elif "DEV_API_PORT = 18000" not in code:
                offenders.append(f"{path.name}: 18000 appears outside the DEV_API_PORT constant")

    assert not offenders, offenders


def test_admin_markup_loads_the_config_seam_before_the_application():
    """Ordering is load-bearing: admin.js reads the seam at module scope."""

    html = (ADMIN / "index.html").read_text(encoding="utf-8")
    order = [
        html.index('src="config.js"'),
        html.index('src="api-config.js"'),
        html.index('src="admin.js"'),
    ]
    assert order == sorted(order), "config.js and api-config.js must precede admin.js"


def test_admin_config_file_ships_configuring_nothing():
    """The committed default must not pin a deployment; the build argument supplies it."""

    config = (ADMIN / "config.js").read_text(encoding="utf-8")
    active = [
        line for line in config.splitlines()
        if "DEDUNET_API_BASE" in line and not line.strip().startswith(("*", "/*", "//"))
    ]
    assert not active, f"committed admin config.js sets a value: {active}"


# ------------------------------------------------- the two surfaces must not disagree


def test_admin_and_storefront_agree_on_precedence_and_default_port():
    """Two seams that disagree about where the API is would be worse than one that is wrong.

    Both must prefer FASHION_POC_API_BASE, then DEDUNET_API_BASE, then the same development
    port — otherwise one surface silently works and the other silently does not.
    """

    admin_resolved = run_js(
        'm.apiBase({ FASHION_POC_API_BASE: "http://legacy.example",'
        '            DEDUNET_API_BASE: "http://generated.example" })'
    )
    assert admin_resolved == "http://legacy.example"

    web_module = WEB / "media-url.js"
    script = (
        f"const w = require({json.dumps(str(web_module))});"
        'process.stdout.write(JSON.stringify({'
        '  precedence: w.apiBase({ FASHION_POC_API_BASE: "http://legacy.example",'
        '                          DEDUNET_API_BASE: "http://generated.example" }),'
        '  fallback: w.apiBase({ location: { protocol: "http:", hostname: "127.0.0.1" } })'
        '}));'
    )
    completed = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, encoding="utf-8", cwd=str(WEB)
    )
    assert completed.returncode == 0, completed.stderr
    web = json.loads(completed.stdout)

    assert web["precedence"] == admin_resolved, "the two surfaces disagree on precedence"
    assert web["fallback"] == run_js('m.apiBase({ location: { protocol: "http:", hostname: "127.0.0.1" } })'), (
        "the two surfaces disagree on the development default"
    )


def test_the_image_build_generates_config_for_both_surfaces():
    """A seam nothing populates is not a seam. The Dockerfile must fill both."""

    dockerfile = (WEB / "Dockerfile").read_text(encoding="utf-8")

    assert "ARG API_BASE_URL" in dockerfile
    assert "storefront admin" in dockerfile, (
        "the build generates config.js for only one surface; the admin was left unconfigured "
        "once already and that is the defect this guards"
    )
