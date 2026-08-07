"""Supported ASGI entrypoint with an EXPLICIT, fail-closed proxy trust boundary.

Why this module exists
----------------------
``app/rate_limit.py`` buckets by ``request.client.host`` and ignores ``X-Forwarded-For``
unless ``RATE_LIMIT_TRUSTED_PROXY_COUNT`` says a proxy really is in front. That logic is
correct, and it is still not sufficient, because it runs too late.

uvicorn installs ``ProxyHeadersMiddleware`` by default (``proxy_headers=True``) and, when
``forwarded_allow_ips`` is unset, trusts ``127.0.0.1``. For any client on loopback it
therefore reads ``X-Forwarded-For`` and REPLACES ``scope["client"]`` before a single line
of application code runs. The limiter then faithfully buckets by an attacker-chosen value.
Measured against ``python -m uvicorn app.main:app --port 18300``:

    control (no XFF)        401 x10 then 429 x6      limiter works
    varied spoofed XFF      401 x16, never limited   limiter bypassed

uvicorn does not validate the header either: ``get_trusted_client_host`` returns whatever
string it finds, so ``X-Forwarded-For: not-an-ip`` is accepted as a client identity.

The application cannot repair this after the fact. Once the middleware has overwritten
``scope["client"]`` the real peer address is gone -- it is not recorded anywhere else in
the scope. The boundary must therefore be configured on the SERVER, which is what this
module does, and it is stated explicitly rather than inherited from a default.

The contract
------------
``TRUSTED_PROXY_MODE``   ``none`` (default) or ``explicit``.

``none``
    ``proxy_headers=False`` AND ``forwarded_allow_ips=[]``. Forwarded headers are not
    interpreted at all, from any peer, including loopback. This is correct for local
    development, for local staging, and for any deployment where the process is reached
    directly. It is the default because the failure mode of guessing wrong is a silently
    bypassable rate limiter.

``explicit``
    Only for a deployment that genuinely sits behind a reverse proxy the operator
    controls. It requires ALL of the following, and refuses to start otherwise:

      - ``TRUSTED_PROXY_IPS``  -- the proxy addresses/networks, comma separated.
        A wildcard (``*``) is refused: "trust every peer" is the unsafe default this
        module exists to remove, and spelling it out does not make it safer.
      - ``RATE_LIMIT_TRUSTED_PROXY_COUNT`` >= 1 -- how many hops your own infrastructure
        appends, so the limiter knows which entry in the header is not attacker-controlled.
      - ``TRUSTED_PROXY_NETWORK_BOUNDARY`` -- a one-line description of what is actually
        enforcing that only those proxies can reach this port. Required as documentation:
        an allowlist is worthless if anything can connect and claim that source address.

Both modes log the resolved boundary at startup as one structured line, so what a running
process actually trusts is observable rather than inferred from the command line.

Usage
-----
    python -m app.server --host 127.0.0.1 --port 18300
    python -m app.server --host 0.0.0.0 --port 8000 --workers 1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass

__all__ = [
    "PROXY_MODE_EXPLICIT",
    "PROXY_MODE_NONE",
    "ProxyTrust",
    "ProxyTrustError",
    "build_config",
    "main",
    "resolve_proxy_trust",
]

PROXY_MODE_NONE = "none"
PROXY_MODE_EXPLICIT = "explicit"
SELECTABLE_PROXY_MODES = frozenset({PROXY_MODE_NONE, PROXY_MODE_EXPLICIT})

# Emitted once at startup. The regression suite asserts on this line, so it is part of the
# contract, not debug output.
STARTUP_EVENT = "asgi_proxy_trust_boundary"

# Emitted once at startup alongside the trust boundary. The acceptance harness asserts on
# this line, so it is part of the contract rather than debug output.
MEDIA_ROOT_EVENT = "brand_media_root"

_logger = logging.getLogger("fashion_commerce")


class ProxyTrustError(RuntimeError):
    """The proxy trust configuration is unusable. The server must not start."""


@dataclass(frozen=True)
class ProxyTrust:
    """The resolved boundary. Every field is stated; nothing is left to a default."""

    mode: str
    proxy_headers: bool
    forwarded_allow_ips: tuple[str, ...]
    trusted_proxy_hops: int
    network_boundary: str

    def as_dict(self) -> dict:
        return {
            "event": STARTUP_EVENT,
            "mode": self.mode,
            "proxy_headers": self.proxy_headers,
            "forwarded_allow_ips": list(self.forwarded_allow_ips),
            "trusted_proxy_hops": self.trusted_proxy_hops,
            "network_boundary": self.network_boundary,
        }


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def resolve_proxy_trust(env: dict | None = None) -> ProxyTrust:
    """Resolve the boundary from the environment, failing closed.

    Read at call time rather than import time so a test can vary it, following the
    ``payments.get_gateway`` and ``rate_limit.rate_limiting_enabled`` precedent.
    """

    environ = os.environ if env is None else env
    mode = (environ.get("TRUSTED_PROXY_MODE") or PROXY_MODE_NONE).strip().lower()

    if mode not in SELECTABLE_PROXY_MODES:
        raise ProxyTrustError(
            f"unknown TRUSTED_PROXY_MODE {mode!r}; expected one of "
            f"{sorted(SELECTABLE_PROXY_MODES)}"
        )

    if mode == PROXY_MODE_NONE:
        # Both settings, deliberately. proxy_headers=False is what actually keeps the
        # middleware out of the stack; the empty allowlist means that even if a future
        # edit re-enables the middleware, it trusts no peer. Neither is a uvicorn default:
        # uvicorn defaults to proxy_headers=True and forwarded_allow_ips="127.0.0.1".
        return ProxyTrust(
            mode=PROXY_MODE_NONE,
            proxy_headers=False,
            forwarded_allow_ips=(),
            trusted_proxy_hops=0,
            network_boundary="direct: no reverse proxy; forwarded headers are not interpreted",
        )

    allow = _split_csv(environ.get("TRUSTED_PROXY_IPS", ""))
    if not allow:
        raise ProxyTrustError(
            "TRUSTED_PROXY_MODE=explicit requires TRUSTED_PROXY_IPS naming the reverse "
            "proxy addresses or networks. Refusing to start with an unspecified allowlist."
        )
    if any(entry == "*" for entry in allow):
        raise ProxyTrustError(
            "TRUSTED_PROXY_IPS must not contain the wildcard '*'. Trusting every peer to "
            "declare its own address is the unsafe default this configuration exists to "
            "remove; naming it explicitly does not make it safe."
        )

    try:
        hops = int(environ.get("RATE_LIMIT_TRUSTED_PROXY_COUNT", "0").strip())
    except ValueError as exc:
        raise ProxyTrustError(
            "RATE_LIMIT_TRUSTED_PROXY_COUNT must be an integer"
        ) from exc
    if hops < 1:
        raise ProxyTrustError(
            "TRUSTED_PROXY_MODE=explicit requires RATE_LIMIT_TRUSTED_PROXY_COUNT >= 1. "
            "With 0 hops the limiter would key on the proxy's own address and throttle "
            "every customer as one client."
        )

    boundary = (environ.get("TRUSTED_PROXY_NETWORK_BOUNDARY") or "").strip()
    if not boundary:
        raise ProxyTrustError(
            "TRUSTED_PROXY_MODE=explicit requires TRUSTED_PROXY_NETWORK_BOUNDARY "
            "describing what prevents anything other than those proxies from reaching "
            "this port. An allowlist of source addresses is not a boundary on its own."
        )

    return ProxyTrust(
        mode=PROXY_MODE_EXPLICIT,
        proxy_headers=True,
        forwarded_allow_ips=tuple(allow),
        trusted_proxy_hops=hops,
        network_boundary=boundary,
    )


def build_config(
    *,
    host: str,
    port: int,
    workers: int = 1,
    log_level: str = "info",
    trust: ProxyTrust | None = None,
):
    """Build the uvicorn configuration with the boundary stated explicitly."""

    import uvicorn

    resolved = resolve_proxy_trust() if trust is None else trust
    return uvicorn.Config(
        "app.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        # THE FIX. Both are passed on every path, in both modes, so no uvicorn default is
        # ever what decides whether this process trusts a forwarded header.
        proxy_headers=resolved.proxy_headers,
        forwarded_allow_ips=list(resolved.forwarded_allow_ips),
    )


def _configure_logger() -> None:
    if not _logger.handlers:  # pragma: no cover - configured once per process
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the commerce API with an explicit proxy trust boundary.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--log-level", default="info", dest="log_level")
    args = parser.parse_args(argv)

    _configure_logger()

    try:
        trust = resolve_proxy_trust()
    except ProxyTrustError as exc:
        print(json.dumps({"event": STARTUP_EVENT, "status": "refused", "error": str(exc)}), file=sys.stderr)
        return 2

    # One structured line describing what this process trusts. Printed before serving so
    # it is present even if the port is already in use.
    _logger.info(json.dumps(trust.as_dict()))

    # Fail at BOOT if the asset root is not there, rather than serving a store whose every
    # image is a 404. This is the check that would have caught an image built without
    # packages/brand/assets: the container started, /ready returned 200 and the brand was
    # simply invisible. A readiness probe cannot see that, because media is not a
    # dependency /ready knows about.
    # Imported OUTSIDE the try. Inside it, an import failure left MediaRootUnavailable
    # unbound and the except clause raised UnboundLocalError over the real error.
    from .commerce.api import BRAND_MEDIA_ROOT_ENV, MediaRootUnavailable, assert_media_root

    try:
        media_root = assert_media_root()
    except MediaRootUnavailable as exc:
        print(
            json.dumps({"event": MEDIA_ROOT_EVENT, "status": "refused", "error": str(exc)}),
            file=sys.stderr,
        )
        return 3
    _logger.info(
        json.dumps(
            {
                "event": MEDIA_ROOT_EVENT,
                "media_root": str(media_root),
                "configured_by": BRAND_MEDIA_ROOT_ENV
                if os.getenv(BRAND_MEDIA_ROOT_ENV, "").strip()
                else "repository checkout fallback",
            }
        )
    )

    config = build_config(
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
        trust=trust,
    )
    uvicorn.Server(config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
