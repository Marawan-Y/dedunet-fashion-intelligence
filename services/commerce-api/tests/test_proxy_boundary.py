"""ASGI proxy-header trust boundary, tested at the REAL server boundary.

Why this file launches a subprocess instead of using TestClient
--------------------------------------------------------------
The defect these tests exist for is not reachable in-process. `TestClient` builds the
ASGI scope itself and never installs uvicorn's `ProxyHeadersMiddleware`, so every
in-process test of `client_key` passes whether or not the deployed server rewrites the
peer address from `X-Forwarded-For`. `tests/test_rate_limit.py` was green throughout the
period in which a real `python -m uvicorn app.main:app` was trivially bypassable.

So each test here starts a real server process, over a real TCP socket, on loopback --
the exact topology in which the bypass was measured:

    control (no XFF)      401 x10 then 429   limiter works
    varied spoofed XFF    401 x16            limiter bypassed

Two independent layers are verified separately, because a test that cannot distinguish
them cannot prove either one:

  LAYER 1  `app/server.py` passes `proxy_headers=False` and `forwarded_allow_ips=[]`
           explicitly, so the middleware is never installed.
  LAYER 2  `rate_limit._peer_was_rewritten_upstream` refuses a peer the server rewrote,
           which still holds if someone starts the app with the bare uvicorn CLI.

`test_supported_server_*` cover layer 1. `test_unsafe_server_*` deliberately start a
server WITH proxy headers enabled -- simulating exactly that mistake -- and cover layer 2.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]

BAD_LOGIN = {"email": "nobody@dedunet.example", "password": "definitely-wrong"}
LOGIN_CAPACITY = 10  # rate_limit.RULES["login"].capacity
BURST = 16


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _request(url: str, *, method: str = "GET", body=None, headers=None):
    """One HTTP call returning (status, headers). Never raises for an HTTP status."""

    request = urllib.request.Request(
        url,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            **({"Content-Type": "application/json"} if body is not None else {}),
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
            return response.status, dict(response.headers)
    except urllib.error.HTTPError as exc:
        # HTTPError wraps a temporary file. Reading it is not enough -- it must be closed,
        # or the interpreter finalizes it later and pytest reports an unraisable
        # exception against whichever test happens to be running at the time.
        try:
            exc.read()
            return exc.code, dict(exc.headers)
        finally:
            exc.close()


def _lower(headers: dict) -> dict:
    return {key.lower(): value for key, value in headers.items()}


class Server:
    """A real server process on loopback."""

    def __init__(self, process: subprocess.Popen, port: int, log: Path, handle) -> None:
        self.process = process
        self.port = port
        self._log = log
        self._handle = handle

    def stop(self) -> None:
        """Terminate and release the log handle.

        The handle must be closed explicitly. Leaving it to the garbage collector makes
        the interpreter finalize it during pytest's teardown, which surfaces as an
        unraisable-exception error against an otherwise passing test.
        """

        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=30)
        if not self._handle.closed:
            self._handle.close()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def login(self, headers: dict | None = None) -> int:
        status, _ = _request(
            f"{self.base}/api/v1/auth/login", method="POST", body=BAD_LOGIN, headers=headers
        )
        return status

    def login_full(self, headers: dict | None = None):
        return _request(
            f"{self.base}/api/v1/auth/login", method="POST", body=BAD_LOGIN, headers=headers
        )

    def output(self) -> str:
        return self._log.read_text(encoding="utf-8", errors="replace")


def _supported_argv(port: int) -> list[str]:
    """The supported startup path, byte-for-byte what the Dockerfile and runbook use."""

    return [sys.executable, "-B", "-m", "app.server", "--host", "127.0.0.1", "--port", str(port)]


def _start(tmp_path: Path, *, extra_env: dict | None = None, argv_for_port=None) -> Server:
    port = _free_port()
    env = {
        **os.environ,
        # A private file database per server. The suite's in-memory URL cannot be shared
        # across processes, and pointing a subprocess at a developer's real database
        # would be worse than a slow test.
        "DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'boundary.sqlite3').as_posix()}",
        "APP_ENV": "test",
        "RATE_LIMIT_ENABLED": "1",
        "RATE_LIMIT_TRUSTED_PROXY_COUNT": "0",
        "COMMERCE_MODE": "COMMERCE_TEST_MODE",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        **(extra_env or {}),
    }
    # FORWARDED_ALLOW_IPS is uvicorn's own escape hatch and must not leak in from the
    # developer's shell and silently decide the result of a test about exactly that.
    env.pop("FORWARDED_ALLOW_IPS", None)

    # Build the schema first. /ready only runs SELECT 1, so a schemaless database still
    # reports ready and every login then returns 500 -- which would look like a limiter
    # result while measuring nothing. No seed data: these tests only need the login and
    # register endpoints to reach a real query and fail authentication honestly.
    schema = subprocess.run(
        [sys.executable, "-B", "-c", "from app.commerce.db import create_all; create_all()"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    assert schema.returncode == 0, f"could not create the test schema:\n{schema.stderr}"

    log = tmp_path / f"server-{port}.log"
    handle = log.open("w", encoding="utf-8")
    process = subprocess.Popen(
        (argv_for_port or _supported_argv)(port),
        cwd=BACKEND,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )

    server = Server(process, port, log, handle)
    deadline = time.time() + 60
    while time.time() < deadline:
        if process.poll() is not None:
            server.stop()
            pytest.fail(f"server exited with {process.returncode}:\n{server.output()}")
        try:
            status, _ = _request(f"{server.base}/ready")
            if status == 200:
                return server
        except OSError:
            pass
        time.sleep(0.25)

    server.stop()
    pytest.fail(f"server did not become ready:\n{server.output()}")


@pytest.fixture()
def supported_server(tmp_path):
    """The supported startup path, exactly as the Dockerfile and runbook use it."""

    server = _start(tmp_path)
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture()
def unsafe_server(tmp_path):
    """A server that DOES interpret forwarded headers from loopback.

    This is the mistake being defended against -- a bare `uvicorn app.main:app`, or
    `FORWARDED_ALLOW_IPS` set in the environment. Layer 1 is deliberately absent so that
    layer 2 is what is under test; if layer 2 is removed, these tests fail.
    """

    server = _start(
        tmp_path,
        argv_for_port=lambda port: [
            sys.executable, "-B", "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port),
            "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1",
        ],
    )
    try:
        yield server
    finally:
        server.stop()


# ------------------------------------------------------------------ layer 1: the server


def test_supported_server_states_its_proxy_boundary_explicitly(supported_server):
    """The resolved boundary is logged, so what a process trusts is observable.

    This is the assertion that fails when the explicit server option is removed. Without
    it, `proxy_headers` reverts to uvicorn's default of True and nothing in a running
    system would show that.
    """

    line = next(
        (
            json.loads(raw)
            for raw in supported_server.output().splitlines()
            if raw.startswith('{"event": "asgi_proxy_trust_boundary"')
        ),
        None,
    )

    assert line is not None, f"no boundary line was logged:\n{supported_server.output()}"
    assert line["mode"] == "none"
    assert line["proxy_headers"] is False, "the ASGI server would interpret forwarded headers"
    assert line["forwarded_allow_ips"] == [], "the ASGI server trusts a forwarder"
    assert line["trusted_proxy_hops"] == 0


def test_supported_server_limits_a_burst_from_one_client(supported_server):
    statuses = [supported_server.login() for _ in range(BURST)]

    assert statuses[:LOGIN_CAPACITY] == [401] * LOGIN_CAPACITY, statuses
    assert set(statuses[LOGIN_CAPACITY:]) == {429}, statuses


def test_supported_server_ignores_varied_forwarded_for(supported_server):
    """The bypass, as originally measured. One uninterrupted burst.

    The control burst drains the bucket; the spoofed burst follows immediately with a
    DIFFERENT value on every request. If the header were honoured anywhere in the stack
    each value would mint a fresh bucket and none of these would ever be limited -- which
    is exactly what a real server did before `app/server.py` existed.
    """

    control = [supported_server.login() for _ in range(BURST)]
    spoofed = [
        supported_server.login({"X-Forwarded-For": f"10.9.9.{i}"}) for i in range(BURST)
    ]

    assert 429 in control, f"the limiter never engaged at all: {control}"
    assert set(spoofed) == {429}, f"a spoofed X-Forwarded-For minted a fresh bucket: {spoofed}"


def test_supported_server_keeps_the_direct_peer_as_the_limiter_identity(supported_server):
    """A spoofed header must not merely fail to help -- it must change nothing.

    The spoofed requests are charged to the same bucket as the unspoofed ones, so the
    threshold is reached at the same point whether or not the header is present.
    """

    mixed = [
        supported_server.login({"X-Forwarded-For": "203.0.113.7"} if index % 2 else None)
        for index in range(BURST)
    ]

    assert mixed[:LOGIN_CAPACITY] == [401] * LOGIN_CAPACITY, mixed
    assert set(mixed[LOGIN_CAPACITY:]) == {429}, mixed


def test_supported_server_survives_a_malformed_forwarded_header(supported_server):
    """A crash is not a refusal. Neither is a 500."""

    malformed = ",,,", "not-an-ip", "999.999.999.999", " , ,", "a" * 500, "\t", "::::"
    statuses = [supported_server.login({"X-Forwarded-For": bad}) for bad in malformed]

    assert all(status in (401, 429) for status in statuses), statuses
    ready, _ = _request(f"{supported_server.base}/ready")
    assert ready == 200


def test_supported_server_429_is_readable_and_correlated(supported_server):
    for _ in range(BURST):
        status, raw = supported_server.login_full({"Origin": "http://localhost:13000"})
        if status == 429:
            headers = _lower(raw)
            assert headers.get("retry-after"), f"no Retry-After: {headers}"
            assert int(headers["retry-after"]) >= 1
            expose = headers.get("access-control-expose-headers", "")
            assert "Retry-After" in expose, f"Retry-After not readable cross-origin: {expose!r}"
            assert headers.get("x-correlation-id"), f"no correlation id: {headers}"
            return
    pytest.fail("the limiter never returned 429")


def test_supported_server_readiness_is_never_limited(supported_server):
    for _ in range(BURST * 2):
        supported_server.login()
    for _ in range(30):
        status, _ = _request(f"{supported_server.base}/ready")
        assert status == 200, "readiness was throttled; an orchestrator would restart a healthy API"


def test_registration_burst_is_limited_from_one_client(supported_server):
    """Registration has its own, much tighter bucket (5/hour)."""

    statuses = []
    for index in range(8):
        status, _ = _request(
            f"{supported_server.base}/api/v1/auth/register",
            method="POST",
            body={
                "email": f"boundary-test-{index}@dedunet.example",
                "password": "not-a-real-password-1234",
                "full_name": "Boundary Test",
            },
            headers={"X-Forwarded-For": f"198.51.100.{index}"},
        )
        statuses.append(status)

    assert 429 in statuses, f"registration was never limited despite varied XFF: {statuses}"


# ------------------------------------------------------------- layer 2: the application


def test_unsafe_server_still_cannot_be_bypassed(unsafe_server):
    """Layer 2 alone, with the server misconfigured to trust loopback forwarders.

    This is the bare-`uvicorn` mistake. The peer address IS rewritten here -- layer 1 is
    not present -- so the only thing standing between an attacker and an unlimited login
    endpoint is `_peer_was_rewritten_upstream`. Remove it and this test fails.
    """

    spoofed = [unsafe_server.login({"X-Forwarded-For": f"10.9.9.{i}"}) for i in range(BURST)]

    assert 429 in spoofed, f"varied X-Forwarded-For minted a fresh bucket per request: {spoofed}"
    assert spoofed[:LOGIN_CAPACITY] == [401] * LOGIN_CAPACITY, spoofed


def test_unsafe_server_does_not_let_a_forger_exhaust_a_direct_client(unsafe_server):
    """Sharing one bucket must not become a denial-of-service against real clients.

    A forged peer is charged to a single quarantine bucket, so exhausting it leaves the
    genuine loopback client's own bucket untouched.
    """

    for index in range(BURST * 2):
        unsafe_server.login({"X-Forwarded-For": f"10.9.9.{index}"})

    assert unsafe_server.login() == 401, "a forger exhausted the direct client's bucket"


# ------------------------------------------------- the contract for a future proxied deployment


def _resolve(**env):
    from app.server import resolve_proxy_trust

    return resolve_proxy_trust(env)


def test_unconfigured_environment_fails_closed():
    """The default must be the safe one. An operator who configures nothing gets no trust."""

    trust = _resolve()

    assert trust.mode == "none"
    assert trust.proxy_headers is False
    assert trust.forwarded_allow_ips == ()


EXPLICIT = {
    "TRUSTED_PROXY_MODE": "explicit",
    "TRUSTED_PROXY_IPS": "10.0.0.4",
    "RATE_LIMIT_TRUSTED_PROXY_COUNT": "1",
    "TRUSTED_PROXY_NETWORK_BOUNDARY": "only the ingress security group may reach :8000",
}


def test_explicit_mode_accepts_a_fully_specified_proxy():
    trust = _resolve(**EXPLICIT)

    assert trust.proxy_headers is True
    assert trust.forwarded_allow_ips == ("10.0.0.4",)
    assert trust.trusted_proxy_hops == 1


@pytest.mark.parametrize(
    ("dropped", "because"),
    [
        ("TRUSTED_PROXY_IPS", "an unspecified allowlist is uvicorn's unsafe default again"),
        ("RATE_LIMIT_TRUSTED_PROXY_COUNT", "0 hops keys every customer as one client"),
        ("TRUSTED_PROXY_NETWORK_BOUNDARY", "an allowlist is not a boundary on its own"),
    ],
)
def test_explicit_mode_refuses_an_incomplete_configuration(dropped, because):
    from app.server import ProxyTrustError

    env = {key: value for key, value in EXPLICIT.items() if key != dropped}
    with pytest.raises(ProxyTrustError):
        _resolve(**env), because


def test_explicit_mode_refuses_wildcard_trust():
    from app.server import ProxyTrustError

    with pytest.raises(ProxyTrustError, match="wildcard"):
        _resolve(**{**EXPLICIT, "TRUSTED_PROXY_IPS": "*"})


def test_unknown_mode_is_refused_rather_than_treated_as_none():
    """A typo must not silently select a mode. Failing closed still means failing."""

    from app.server import ProxyTrustError

    with pytest.raises(ProxyTrustError, match="unknown TRUSTED_PROXY_MODE"):
        _resolve(TRUSTED_PROXY_MODE="No-Proxy")


def test_build_config_passes_both_settings_to_uvicorn():
    """Neither setting may be left to a uvicorn default on any path."""

    from app.server import build_config, resolve_proxy_trust

    config = build_config(host="127.0.0.1", port=0, trust=resolve_proxy_trust({}))

    assert config.proxy_headers is False
    assert config.forwarded_allow_ips == []
